"""Abstract LLM interface and implementations (Groq/OpenAI/local).

Features:
- Stream-based token generation
- Optional signal emission for LLM lifecycle events
- Structured output support (extracts JSON/signals from response)
"""
from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
from openai import OpenAI
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_CPP_AVAILABLE = False
import os
import json
import re
from ..config import (
    LLM_BACKEND,
    GGUF_MODEL_PATH,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    DEEPSEEK_API_KEY,
    OPENAI_BASE_URL,
    GROQ_BASE_URL,
    DEEPSEEK_BASE_URL,
    OPENAI_MODEL,
    GROQ_MODEL,
    DEEPSEEK_MODEL,
)
from ..core.signals import emit_signal, SignalName

os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"


def extract_signals_from_response(response: str) -> Dict[str, Any]:
    """
    Extract structured signals from LLM response.
    
    Format: LLM may include a <signals> block in its response:
    
        Thanks, I have everything I need.
        
        <signals>
        {
          "intake.user_data_collected": {
            "confidence": 0.92,
            "fields": ["email", "name"]
          }
        }
        </signals>
    
    Handles:
    - Nested JSON objects
    - Multiple signal blocks
    - Malformed JSON
    - Extra whitespace
    
    Malformed signals are silently ignored to prevent LLM issues from crashing core.
    
    Args:
        response: Full LLM response text
    
    Returns:
        Dictionary of signals, or empty dict if none found
    """
    signals_result = {}
    
    # Find all <signals>...</signals> blocks
    signal_blocks = re.findall(
        r"<signals>\s*(.*?)\s*</signals>",
        response,
        re.DOTALL
    )
    
    for block in signal_blocks:
        signals_dict = _parse_signal_block_json(block.strip())
        if signals_dict:
            signals_result.update(signals_dict)
    
    # Validate structure: should be {signal_name: {payload}}
    if isinstance(signals_result, dict):
        return signals_result
    
    return {}


def _parse_signal_block_json(text: str) -> Dict[str, Any]:
    """Parse JSON from signal block with robust error handling.
    
    Tries multiple parsing strategies:
    1. Direct JSON parse (well-formed JSON)
    2. Matching braces extraction (nested JSON)
    3. Regex-based extraction (malformed JSON recovery)
    """
    if not text or not text.strip():
        return {}
    
    # Strategy 1: Direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Find matching braces and extract JSON
    text = text.strip()
    if text.startswith('{') and text.endswith('}'):
        try:
            brace_count = 0
            for i, char in enumerate(text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                
                # When count returns to 0, we found matching close brace
                if brace_count == 0 and i > 0:
                    json_str = text[:i+1]
                    try:
                        result = json.loads(json_str)
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        pass
                    break
        except Exception:
            pass
    
    # Strategy 3: Extract JSON-like structure using regex
    # Matches {...} with potential nested braces
    json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    
    return {}


class LLMInterface(ABC):
    """Abstract base for LLM implementations."""
    
    @abstractmethod
    def stream_completion(
        self,
        messages: list,
        max_tokens: int,
        temperature: float,
        emit_signals: bool = True,
    ) -> Iterator[str]:
        """
        Stream chat completion, yielding text tokens.
        
        Args:
            messages: Message history
            max_tokens: Max response length
            temperature: Response creativity (0.0-1.0)
            emit_signals: If True, emit llm.generation_start/complete signals
        
        Yields:
            Text tokens as they arrive
        """
        pass


class LocalLLM(LLMInterface):
    """Local LLaMA.cpp implementation."""
    
    def __init__(self):
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python is not installed. Use a cloud backend or install: uv add llama-cpp-python")
        print("⏳ Loading Qwen2.5-3B (Q5_K_M GGUF) on CPU...")
        try:
            self.model = Llama(
                model_path=GGUF_MODEL_PATH,
                n_ctx=2048,
                n_threads=8,
                n_threads_batch=8,
                n_batch=512,
                n_gqa=1,
                verbose=False,
                use_mmap=True,
                use_mlock=False,
                rope_freq_base=1000000.0,
            )
            print("✅ Qwen2.5-3B loaded successfully")
        except Exception as e:
            print(f"❌ FAILED to load GGUF model: {e}")
            raise
    
    def stream_completion(
        self,
        messages: list,
        max_tokens: int,
        temperature: float,
        emit_signals: bool = True,
    ) -> Iterator[str]:
        """Stream completion from local model with optional signal emission."""
        if emit_signals:
            emit_signal(
                SignalName.LLM_GENERATION_START,
                payload={"model": "qwen2.5-3b", "backend": "local"},
                context={"source": "local_llm"},
            )
        
        try:
            stream = self.model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            response_text = ""
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    token = delta["content"]
                    response_text += token
                    yield token
            
            if emit_signals:
                # Emit generation_complete signal
                emit_signal(
                    SignalName.LLM_GENERATION_COMPLETE,
                    payload={"tokens_generated": max_tokens, "backend": "local"},
                    context={"source": "local_llm"},
                )
                
                # Extract and emit any signals from response
                signals_dict = extract_signals_from_response(response_text)
                for signal_name, signal_payload in signals_dict.items():
                    emit_signal(
                        signal_name,
                        payload=signal_payload,
                        context={"source": "llm_response", "backend": "local"},
                    )
        except Exception as e:
            if emit_signals:
                emit_signal(
                    SignalName.LLM_GENERATION_ERROR,
                    payload={"error": str(e)},
                    context={"source": "local_llm"},
                )
            raise


class CloudLLM(LLMInterface):
    """Cloud-based LLM (Groq/OpenAI/DeepSeek)."""
    
    def __init__(self, backend: str):
        self.backend = backend
        self.client = self._get_client()
        self.model = self._get_model()
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI-compatible client."""
        if self.backend == "openai":
            return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        elif self.backend == "groq":
            return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
        elif self.backend == "deepseek":
            return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        else:
            raise ValueError(f"Unknown cloud backend: {self.backend}")
    
    def _get_model(self) -> str:
        """Get model name for backend."""
        if self.backend == "openai":
            return OPENAI_MODEL
        elif self.backend == "groq":
            return GROQ_MODEL
        elif self.backend == "deepseek":
            return DEEPSEEK_MODEL
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def stream_completion(
        self,
        messages: list,
        max_tokens: int,
        temperature: float,
        emit_signals: bool = True,
    ) -> Iterator[str]:
        """Stream completion from cloud LLM with optional signal emission."""
        if emit_signals:
            emit_signal(
                SignalName.LLM_GENERATION_START,
                payload={"model": self.model, "backend": self.backend},
                context={"source": "cloud_llm"},
            )
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            
            response_text = ""
            for event in stream:
                if not event.choices:
                    continue
                
                delta = event.choices[0].delta
                if not delta:
                    continue
                
                if hasattr(delta, "content") and delta.content is not None:
                    response_text += delta.content
                    yield delta.content
            
            if emit_signals:
                # Emit generation_complete signal
                emit_signal(
                    SignalName.LLM_GENERATION_COMPLETE,
                    payload={"tokens_generated": max_tokens, "backend": self.backend},
                    context={"source": "cloud_llm"},
                )
                
                # Extract and emit any signals from response
                signals_dict = extract_signals_from_response(response_text)
                for signal_name, signal_payload in signals_dict.items():
                    emit_signal(
                        signal_name,
                        payload=signal_payload,
                        context={"source": "llm_response", "backend": self.backend},
                    )
        except Exception as e:
            if emit_signals:
                emit_signal(
                    SignalName.LLM_GENERATION_ERROR,
                    payload={"error": str(e)},
                    context={"source": "cloud_llm"},
                )
            raise


# Cache for cloud clients
_cloud_clients = {}


def get_llm() -> LLMInterface:
    """Factory function to get appropriate LLM implementation."""
    if LLM_BACKEND == "local":
        return LocalLLM()
    else:
        if LLM_BACKEND not in _cloud_clients:
            _cloud_clients[LLM_BACKEND] = CloudLLM(LLM_BACKEND)
        return _cloud_clients[LLM_BACKEND]

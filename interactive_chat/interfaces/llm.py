"""Abstract LLM interface and implementations (Groq/OpenAI/local)."""
from abc import ABC, abstractmethod
from typing import Iterator
from openai import OpenAI
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_CPP_AVAILABLE = False
import os
from config import (
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

os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"


class LLMInterface(ABC):
    """Abstract base for LLM implementations."""
    
    @abstractmethod
    def stream_completion(
        self,
        messages: list,
        max_tokens: int,
        temperature: float,
    ) -> Iterator[str]:
        """Stream chat completion, yielding text tokens."""
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
    ) -> Iterator[str]:
        """Stream completion from local model."""
        stream = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                yield delta["content"]


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
    ) -> Iterator[str]:
        """Stream completion from cloud LLM."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        
        for event in stream:
            if not event.choices:
                continue
            
            delta = event.choices[0].delta
            if not delta:
                continue
            
            if hasattr(delta, "content") and delta.content is not None:
                yield delta.content


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

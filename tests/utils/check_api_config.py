#!/usr/bin/env python3
"""Check API key configuration."""

import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("API KEY CONFIGURATION CHECK")
print("="*60)

# Check each API key
from interactive_chat.config import (
    GROQ_API_KEY, 
    OPENAI_API_KEY, 
    DEEPSEEK_API_KEY,
    LLM_BACKEND,
    GROQ_BASE_URL,
    OPENAI_BASE_URL,
    DEEPSEEK_BASE_URL,
)

print(f"\n[CONFIG] LLM_BACKEND: {LLM_BACKEND}")

print(f"\n[GROQ]")
print(f"  API Key loaded: {'✓' if GROQ_API_KEY else '✗'}")
if GROQ_API_KEY:
    print(f"  Key format: {GROQ_API_KEY[:10]}...{GROQ_API_KEY[-10:]}")
else:
    print(f"  ERROR: GROQ_API_KEY not set in .env file!")
print(f"  Base URL: {GROQ_BASE_URL}")

print(f"\n[OPENAI]")
print(f"  API Key loaded: {'✓' if OPENAI_API_KEY else '✗'}")
if OPENAI_API_KEY:
    print(f"  Key format: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-10:]}")
else:
    print(f"  ERROR: OPENAI_API_KEY not set in .env file!")
print(f"  Base URL: {OPENAI_BASE_URL}")

print(f"\n[DEEPSEEK]")
print(f"  API Key loaded: {'✓' if DEEPSEEK_API_KEY else '✗'}")
if DEEPSEEK_API_KEY:
    print(f"  Key format: {DEEPSEEK_API_KEY[:10]}...{DEEPSEEK_API_KEY[-10:]}")
else:
    print(f"  ERROR: DEEPSEEK_API_KEY not set in .env file!")
print(f"  Base URL: {DEEPSEEK_BASE_URL}")

# Test the current backend
print(f"\n{'='*60}")
print("TESTING CURRENT BACKEND")
print(f"{'='*60}")

try:
    print(f"\n[TEST] Creating LLM client for {LLM_BACKEND}...")
    from interactive_chat.interfaces import get_llm
    llm = get_llm()
    print(f"✓ LLM client created successfully!")
    print(f"  Type: {type(llm).__name__}")
    
    if hasattr(llm, 'backend'):
        print(f"  Backend: {llm.backend}")
    if hasattr(llm, 'model'):
        print(f"  Model: {llm.model}")
        
except Exception as e:
    print(f"✗ Failed to create LLM client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*60}")
print("✅ All API keys configured!")
print(f"{'='*60}\n")

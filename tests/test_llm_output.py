#!/usr/bin/env python3
"""Test script to show what the LLM outputs and how filtering works"""
import sys
import os
import re
# Add the interactive_chat directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "interactive_chat"))

from config import get_system_prompt, INSTRUCTION_PROFILES

# Get system prompt
system_prompt = get_system_prompt("ielts_instructor")

print("=" * 70)
print("SYSTEM PROMPT SIGNALS SECTION:")
print("=" * 70)
# Find and print just the signals section
lines = system_prompt.split("\n")
in_signals = False
for i, line in enumerate(lines):
    if "SIGNALS YOU MAY EMIT:" in line:
        # Print from here for 10 lines
        for j in range(i, min(i+6, len(lines))):
            print(lines[j])
        break

print("\n" + "=" * 70)
print("SIMULATED LLM OUTPUTS:")
print("=" * 70)

# These are realistic outputs that the LLM might produce
test_outputs = [
    "Where are you from?\n\n<signals>\n{\n  \"custom.exam.question_asked\": {\n    \"confidence\": 0.9,\n    \"topic\": \"home\"\n  }\n}\n</signals>",
    
    "That's great! Thank you for sharing.\n\n<signals>\n{\n  \"custom.exam.response_received\": {\n    \"confidence\": 0.85,\n    \"duration_sec\": 35\n  },\n  \"custom.exam.fluency_observation\": {\n    \"observation\": \"Good fluency with natural pacing\",\n    \"confidence\": 0.88\n  }\n}\n</signals>",
    
    "Can you tell me about your hometown?",  # No signals
]

print("\nTesting signal filtering:\n")

for i, output in enumerate(test_outputs, 1):
    print(f"\n--- Test {i} ---")
    print(f"RAW LLM OUTPUT:\n{output}")
    
    # Apply our filtering logic
    clean = re.sub(r"<signals>\s*\{.*?\}\s*</signals>", "", output, flags=re.DOTALL).strip()
    
    print(f"\nAFTER FILTERING (goes to TTS):\n{clean}")
    
    # Check for signals
    signals_match = re.search(r"<signals>(.*?)</signals>", output, re.DOTALL)
    if signals_match:
        print(f"\nSignals extracted: YES")
    else:
        print(f"\nSignals extracted: NO")
    
    print("-" * 70)

print("\n" + "=" * 70)
print("ANALYSIS:")
print("=" * 70)
print("""
The issue might be:
1. LLM is not following the instruction to emit signals
2. Signals are being emitted but in wrong format
3. The filtering regex is not working correctly

Let me check each test case filtering...
""")


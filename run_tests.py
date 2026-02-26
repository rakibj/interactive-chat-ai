#!/usr/bin/env python3
"""
Test Runner - Execute all tests organized in /tests

Usage:
    uv run pytest tests/ -v              # Run all tests
    uv run pytest tests/ -v --tb=short   # Run with short traceback
    uv run pytest tests/ --cov=interactive_chat  # Run with coverage
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run all tests with pytest."""
    print("="*60)
    print("RUNNING ALL TESTS")
    print("="*60)
    
    # Find tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    if not tests_dir.exists():
        print("❌ Error: tests/ directory not found")
        return False
    
    print(f"📁 Tests directory: {tests_dir}")
    print(f"📊 Test categories:")
    print(f"   ✓ Unit tests (test_headless_*.py, test_signal*.py)")
    print(f"   ✓ Phase tests (test_phase*.py)")
    print(f"   ✓ Integration tests (test_api*.py, test_integration*.py)")
    print(f"   ✓ E2E tests (test_e2e_*.py, test_websocket*.py)")
    print(f"   ℹ️  Debug/Utils (tests/utils/)")
    print()
    
    # Run pytest
    cmd = ["uv", "run", "pytest", str(tests_dir), "-v"]
    
    print(f"🚀 Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    
    print("\n" + "="*60)
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return result.returncode == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

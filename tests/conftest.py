"""Pytest configuration and fixtures for tests."""

import sys
import io
from pathlib import Path
from unittest.mock import MagicMock

# Fix Windows Unicode console encoding early
if sys.platform == "win32":
    try:
        # Ensure stdout/stderr can handle UTF-8
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding='utf-8', errors='replace'
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding='utf-8', errors='replace'
        )
    except (AttributeError, TypeError):
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock audio-related and utility modules before any imports
sys.modules['sounddevice'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['config'] = MagicMock()

# Mock utils as a package with submodules
utils_mock = MagicMock()
utils_mock.text = MagicMock()
utils_mock.text.lexical_bias = MagicMock(return_value=0.0)
utils_mock.text.energy_decay_score = MagicMock(return_value=0.0)
sys.modules['utils'] = utils_mock
sys.modules['utils.text'] = utils_mock.text

# pytest hook to prevent fixture scope issues
def pytest_runtest_teardown(item, nextitem):
    """Handle teardown properly on Windows"""
    pass

"""Pytest configuration and fixtures for tests."""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set encoding for Python and its subprocesses  
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock only modules that are problematic and not actually needed
sys.modules['sounddevice'] = MagicMock()

sys.modules['config'] = MagicMock()

# Mock utils as a package with submodules
utils_mock = MagicMock()
utils_mock.text = MagicMock()
utils_mock.text.lexical_bias = MagicMock(return_value=0.0)
utils_mock.text.energy_decay_score = MagicMock(return_value=0.0)
sys.modules['utils'] = utils_mock
sys.modules['utils.text'] = utils_mock.text

# Workaround for torch.__spec__ issue in this environment
# Patch importlib.util.find_spec to handle torch gracefully
import importlib.util as _importlib_util
_original_find_spec = _importlib_util.find_spec

def _patched_find_spec(name, *args, **kwargs):
    """Patched find_spec that handles torch.__spec__ issue."""
    try:
        return _original_find_spec(name, *args, **kwargs)
    except ValueError as e:
        if "torch.__spec__ is not set" in str(e):
            # Return None for torch if __spec__ issue occurs
            # This will make is_torch_available() return False
            return None
        raise

_importlib_util.find_spec = _patched_find_spec


# pytest hook for proper Windows encoding handling
def pytest_configure(config):
    """Configure pytest with proper UTF-8 encoding for Windows."""
    if sys.platform == "win32":
        try:
            # Use reconfigure if available (Python 3.7+)
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, UnicodeEncodeError):
            # Silent fallback if reconfigure not available or fails
            pass

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

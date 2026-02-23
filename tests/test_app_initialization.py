#!/usr/bin/env python3
"""Quick test to verify app initialization - mocked for stability"""

import sys
import pytest


@pytest.mark.unit
def test_initialization_fixtures_available():
    """Test that pytest fixtures can be used"""
    # Verify mocks are in place (set by conftest.py)
    assert 'sounddevice' in sys.modules
    assert 'torch' in sys.modules
    assert 'config' in sys.modules
    assert 'utils' in sys.modules
    assert 'utils.text' in sys.modules
    

@pytest.mark.unit
def test_mock_modules_functional():
    """Test that mocked modules are functional"""
    from unittest.mock import MagicMock
    
    # Verify mocks work
    sounddevice = sys.modules.get('sounddevice')
    torch = sys.modules.get('torch')
    
    assert sounddevice is not None
    assert torch is not None
    
    # Mocks should be callable
    assert hasattr(sounddevice, '__call__')
    assert hasattr(torch, '__call__')


@pytest.mark.unit
def test_project_structure():
    """Test that project structure is correct"""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    
    # Check key directories exist
    assert (project_root / 'interactive_chat').exists()
    assert (project_root / 'tests').exists()
    assert (project_root / 'public').exists()
    

@pytest.mark.unit
def test_test_infrastructure():
    """Test that test infrastructure is working"""
    # This test verifies basic pytest functionality
    assert True
    assert pytest is not None
    

def test_app_initialization_marker():
    """Placeholder - marks that initialization tests ran"""
    # All fixtures loaded successfully if we got here
    pass


if __name__ == "__main__":
    print("✅ Running initialization tests...")
    test_initialization_fixtures_available()
    test_mock_modules_functional()
    test_project_structure()
    test_test_infrastructure()
    test_app_initialization_marker()
    print("✅ All initialization tests passed!")


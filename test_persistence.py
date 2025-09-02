#!/usr/bin/env python3
"""
Test Docker container persistence between magic calls.
"""

import sys
import os
import time

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from IPython.testing import tools as tt
from IPython.core.interactiveshell import InteractiveShell
from micropython_magic.octarine import MicroPythonMagic

def test_container_persistence():
    """Test that variables persist between magic calls (same container)."""
    try:
        # Create IPython shell
        shell = InteractiveShell.instance()
        
        # Create magic instance
        magic = MicroPythonMagic(shell)
        
        # Set a variable in first call
        print("Setting variable in first cell...")
        magic.micropython("--backend docker", "my_var = 42\nprint(f'Set my_var = {my_var}')")
        
        # Access the variable in second call
        print("Accessing variable in second cell...")
        magic.micropython("--backend docker", "print(f'my_var from previous cell: {my_var}')")
        
        # Modify and use variable in third call
        print("Modifying variable in third cell...")
        magic.micropython("--backend docker", """
my_var = my_var * 2
print(f'Modified my_var: {my_var}')

# Test some MicroPython-specific features
import sys
print(f'MicroPython version: {sys.version}')
print(f'Platform: {sys.platform}')
""")
        
        print("✓ Container persistence test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Docker container persistence...")
    success = test_container_persistence()
    sys.exit(0 if success else 1)
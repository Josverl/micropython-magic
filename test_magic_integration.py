#!/usr/bin/env python3
"""
Test integration of Docker backend with magic commands.
"""

import sys
import os

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from IPython.testing import tools as tt
from IPython.core.interactiveshell import InteractiveShell
from micropython_magic.octarine import MicroPythonMagic

def test_magic_integration():
    """Test that the magic commands work with Docker backend."""
    try:
        # Create IPython shell
        shell = InteractiveShell.instance()
        
        # Create magic instance
        magic = MicroPythonMagic(shell)
        
        # Test line magic with Docker backend
        print("Testing line magic with Docker backend...")
        result = magic.mpy_line("--backend docker --info")
        print(f"✓ Line magic info: {result}")
        
        # Test simple execution
        print("Testing simple execution...")
        result = magic.mpy_line("--backend docker print('Hello from magic!')")
        print(f"✓ Simple execution: {result}")
        
        # Test cell magic
        print("Testing cell magic...")
        cell_code = "print('Cell execution with Docker!')\nprint(f'2 + 3 = {2 + 3}')"
        result = magic.micropython("--backend docker", cell_code)
        print(f"✓ Cell magic executed")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Magic Commands with Docker backend...")
    success = test_magic_integration()
    sys.exit(0 if success else 1)
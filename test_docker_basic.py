#!/usr/bin/env python3
"""
Basic test for Docker MicroPython support.
"""

import sys
import os

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from micropython_magic.docker_backend import DockerMicroPython
from IPython.testing import tools as tt
from IPython.core.interactiveshell import InteractiveShell

def test_docker_backend_creation():
    """Test that we can create a Docker backend."""
    try:
        # Create a mock shell
        shell = InteractiveShell.instance()
        
        # Create Docker backend
        docker_backend = DockerMicroPython(shell)
        print("✓ Docker backend created successfully")
        
        # Test basic connection
        result = docker_backend.select_device(None)
        print(f"✓ Connection test: {result}")
        
        # Test simple execution
        output = docker_backend._exec_micropython_code("print('Hello from Docker!')", 10)
        print(f"✓ Simple execution: {output}")
        
        # Test expression evaluation
        output2 = docker_backend._exec_micropython_code("print(2 + 2)", 10)
        print(f"✓ Expression evaluation: {output2}")
        
        # Clean up
        docker_backend.stop()
        print("✓ Docker backend stopped")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Docker MicroPython backend...")
    success = test_docker_backend_creation()
    sys.exit(0 if success else 1)
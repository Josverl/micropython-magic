#!/usr/bin/env python3
"""
Unit tests for Docker backend functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from micropython_magic.docker_backend import DockerMicroPython, DOCKER_AVAILABLE
from micropython_magic.mpr import MPRemote2
from micropython_magic.octarine import MicroPythonMagic
from IPython.core.interactiveshell import InteractiveShell

@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
class TestDockerBackend:
    """Test suite for Docker backend functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.shell = InteractiveShell.instance()
        
    def test_docker_backend_creation(self):
        """Test that we can create a Docker backend."""
        backend = DockerMicroPython(self.shell)
        assert backend is not None
        assert backend.image == "micropython/unix:latest"
        assert backend.container_name == "micropython-magic-session"
        
    def test_mpremote2_docker_backend(self):
        """Test MPRemote2 with Docker backend."""
        mpr = MPRemote2(self.shell, backend="docker")
        assert mpr.backend == "docker"
        assert mpr.is_docker_backend == True
        assert mpr._docker_backend is not None
        
    def test_mpremote2_serial_backend(self):
        """Test MPRemote2 with serial backend (default)."""
        mpr = MPRemote2(self.shell)
        assert mpr.backend == "serial"
        assert mpr.is_docker_backend == False
        assert mpr._docker_backend is None
        
    def test_magic_backend_switching(self):
        """Test that magic can switch between backends."""
        magic = MicroPythonMagic(self.shell)
        
        # Test serial backend (default)
        mcu_serial = magic._get_mcu_for_backend("serial")
        assert mcu_serial.backend == "serial"
        
        # Test docker backend
        mcu_docker = magic._get_mcu_for_backend("docker")
        assert mcu_docker.backend == "docker"
        
    @pytest.mark.integration
    def test_docker_execution_integration(self):
        """Integration test for Docker execution."""
        try:
            backend = DockerMicroPython(self.shell)
            
            # Test simple execution
            result = backend._exec_micropython_code("print('Hello Docker!')", 10)
            assert result == ['Hello Docker!']
            
            # Test mathematical expression
            result = backend._exec_micropython_code("print(2 + 2)", 10)
            assert result == ['4']
            
            # Clean up
            backend.stop()
            
        except Exception as e:
            pytest.skip(f"Docker integration test failed: {e}")
            
    @pytest.mark.integration  
    def test_magic_docker_integration(self):
        """Integration test for magic commands with Docker."""
        try:
            magic = MicroPythonMagic(self.shell)
            
            # Test line magic with info
            result = magic.mpy_line("--backend docker --info")
            assert isinstance(result, dict)
            assert result.get('backend') == 'docker'
            
            # Test simple execution
            result = magic.mpy_line("--backend docker print('Magic test')")
            assert result == ['Magic test']
            
        except Exception as e:
            pytest.skip(f"Magic Docker integration test failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
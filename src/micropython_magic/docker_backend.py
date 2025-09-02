"""Docker backend for MicroPython execution.

This module provides Docker-based MicroPython execution as an alternative to 
serial MCU connections, using the micropython/unix Docker image.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Union

from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log

from micropython_magic.logger import MCUException
from micropython_magic.interactive import TIMEOUT

JSON_START = "<json~"
JSON_END = "~json>"
DONT_KNOW = "<~?~>"

# Check if Docker is available
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False


class DockerMicroPython:
    """Docker-based MicroPython backend using micropython/unix container."""
    
    def __init__(
        self,
        shell: InteractiveShell,
        image: str = "micropython/unix:latest",
        container_name: Optional[str] = None,
    ):
        if not DOCKER_AVAILABLE:
            raise ImportError("Docker backend requires 'docker' package. Install with: pip install docker")
            
        self.shell = shell
        self.image = image
        # Use a fixed container name for persistence across magic instances
        self.container_name = container_name or "micropython-magic-session"
        self.timeout = TIMEOUT
        self._docker_client = None
        self._container = None
        
    @property
    def docker_client(self):
        """Lazy initialization of Docker client."""
        if self._docker_client is None:
            try:
                self._docker_client = docker.from_env()
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Docker: {e}")
        return self._docker_client
    
    @property 
    def container(self):
        """Get or create the MicroPython container."""
        if self._container is None:
            self._ensure_container()
        return self._container
        
    def _ensure_container(self):
        """Ensure the MicroPython container is running."""
        try:
            # Try to find existing container
            try:
                self._container = self.docker_client.containers.get(self.container_name)
                if self._container.status == 'running':
                    # Container is already running, good to go
                    return
                elif self._container.status in ['stopped', 'exited']:
                    log.info(f"Starting existing container {self.container_name}")
                    self._container.start()
                    time.sleep(1)
                    return
                else:
                    # Container is in a problematic state, remove and recreate
                    log.info(f"Container {self.container_name} in state {self._container.status}, removing")
                    self._container.remove(force=True)
                    self._container = None
            except docker.errors.NotFound:
                # Container doesn't exist, we'll create it below
                pass
                
            # Create new container with a long-running process
            # Use sleep to keep the container alive, we'll exec into it for MicroPython
            log.info(f"Creating new container {self.container_name}")
            self._container = self.docker_client.containers.run(
                self.image,
                command=["sleep", "infinity"],  # Keep container alive
                name=self.container_name,
                detach=True,
                remove=False,
            )
            # Wait a moment for container to start
            time.sleep(2)
                
        except Exception as e:
            raise ConnectionError(f"Failed to create/start container: {e}")
    
    def run_cmd(
        self,
        cmd: List[str],
        *,
        auto_connect: bool = True,
        stream_out: bool = True,
        shell: bool = True,
        timeout: Union[int, float] = 0,
        follow: bool = True,
    ):
        """Execute a command in the Docker container."""
        timeout = timeout or self.timeout
        
        try:
            if cmd[0] == "connect":
                # Handle connect commands (no-op for Docker)
                return []
            elif cmd[0] == "eval":
                # Handle eval commands
                if len(cmd) > 1:
                    expression = cmd[1]
                    return self._exec_micropython_code(f"print({expression})", timeout)
            elif cmd[0] == "exec":
                # Handle exec commands  
                if len(cmd) > 1:
                    code = cmd[1]
                    return self._exec_micropython_code(code, timeout)
            elif cmd[0] == "soft-reset":
                # Handle soft reset
                return self._soft_reset()
            elif cmd[0] == "reset":
                # Handle hard reset
                return self._hard_reset()
            elif cmd[0] == "run":
                # Handle run file command
                if len(cmd) > 1:
                    filename = cmd[1]
                    return self._run_file(filename, timeout)
            else:
                log.warning(f"Unsupported command for Docker backend: {cmd}")
                return []
                
        except Exception as e:
            if "failed to connect" in str(e).lower():
                raise ConnectionError(str(e))
            raise MCUException(str(e))
    
    def _exec_micropython_code(self, code: str, timeout: float) -> List[str]:
        """Execute MicroPython code in the container."""
        try:
            # For simple execution, just run the code directly
            # For more complex persistence, we would need to maintain a REPL session
            
            # Execute the code directly in micropython
            result = self.container.exec_run(
                ["micropython", "-c", code],
                stdout=True,
                stderr=True,
                tty=False,
            )
            
            output = result.output.decode('utf-8', errors='ignore')
            if result.exit_code != 0:
                raise MCUException(f"MicroPython execution failed: {output}")
            
            return output.strip().split('\n') if output.strip() else []
                
        except Exception as e:
            log.error(f"Failed to execute MicroPython code: {e}")
            raise MCUException(str(e))
    
    def _run_file(self, filename: str, timeout: float) -> List[str]:
        """Run a file in the container."""
        try:
            # Copy file to container
            container_path = "/tmp/run_file.py"
            
            # Create tar archive with the file
            import tarfile
            import io
            
            tar_data = io.BytesIO()
            with tarfile.open(fileobj=tar_data, mode='w') as tar:
                tar.add(filename, arcname="run_file.py")
            tar_data.seek(0)
            
            # Put the archive in the container
            self.container.put_archive("/tmp", tar_data.getvalue())
            
            # Execute the file
            result = self.container.exec_run(
                ["micropython", container_path],
                stdout=True,
                stderr=True,
                tty=False,
            )
            
            output = result.output.decode('utf-8', errors='ignore')
            if result.exit_code != 0:
                raise MCUException(f"MicroPython execution failed: {output}")
            
            return output.strip().split('\n') if output.strip() else []
            
        except Exception as e:
            log.error(f"Failed to run file: {e}")
            raise MCUException(str(e))
    
    def _soft_reset(self) -> List[str]:
        """Perform a soft reset by restarting the container."""
        try:
            log.info("Performing soft reset (restarting container)")
            self.container.restart()
            time.sleep(2)  # Wait for container to restart
            return ["Soft reset complete"]
        except Exception as e:
            raise MCUException(f"Soft reset failed: {e}")
    
    def _hard_reset(self) -> List[str]:
        """Perform a hard reset by recreating the container."""
        try:
            log.info("Performing hard reset (recreating container)")
            self.stop()
            self._container = None
            self._ensure_container()
            return ["Hard reset complete"]
        except Exception as e:
            raise MCUException(f"Hard reset failed: {e}")
    
    def run_cell(
        self,
        cell: str,
        *,
        timeout: Union[int, float] = TIMEOUT,
        follow: bool = True,
        mount: Optional[str] = None,
    ) -> List[str]:
        """Execute a cell of MicroPython code."""
        if mount:
            log.warning("Mount option not supported in Docker backend")
        
        return self._exec_micropython_code(cell, timeout)
    
    def copy_cell_to_mcu(self, cell: str, *, filename: str):
        """Copy cell content to a file in the container."""
        try:
            # Create temporary file with cell content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write("# Jupyter cell\n")
                f.write(cell)
                temp_file = f.name
            
            try:
                # Create tar archive
                import tarfile
                import io
                
                tar_data = io.BytesIO()
                with tarfile.open(fileobj=tar_data, mode='w') as tar:
                    tar.add(temp_file, arcname=filename)
                tar_data.seek(0)
                
                # Copy to container
                self.container.put_archive("/tmp", tar_data.getvalue())
                log.info(f"Cell copied to container file: {filename}")
                
            finally:
                os.unlink(temp_file)
                
        except Exception as e:
            raise MCUException(f"Failed to copy cell to container: {e}")
    
    def cell_from_mcu_file(self, filename: str) -> str:
        """Read a file from the container."""
        try:
            # Get file from container
            archive_data, _ = self.container.get_archive(f"/tmp/{filename}")
            
            # Extract file content
            import tarfile
            import io
            
            with tarfile.open(fileobj=io.BytesIO(archive_data.data)) as tar:
                member = tar.getmembers()[0]
                file_data = tar.extractfile(member)
                if file_data:
                    content = file_data.read().decode('utf-8')
                    return content
                else:
                    raise MCUException(f"Failed to read file {filename}")
                    
        except Exception as e:
            raise MCUException(f"Failed to read file from container: {e}")
    
    def select_device(self, port: Optional[str], verify: bool = False):
        """Select device (no-op for Docker, just ensure container is running)."""
        self._ensure_container()
        return f"Docker container: {self.container_name}"
    
    def get_fw_info(self, timeout: float):
        """Get firmware info from MicroPython."""
        try:
            info_code = """
import sys
import json
info = {
    'version': sys.version,
    'implementation': sys.implementation.name,
    'platform': sys.platform,
    'backend': 'docker'
}
print(json.dumps(info))
"""
            result = self._exec_micropython_code(info_code, timeout)
            if result and result[0].startswith('{'):
                return json.loads(result[0])
            return {"backend": "docker", "status": "running"}
        except Exception as e:
            log.error(f"Failed to get firmware info: {e}")
            return {"backend": "docker", "status": "error", "error": str(e)}
    
    @staticmethod
    def load_json_from_MCU(line: str):
        """Try to load JSON output from MicroPython."""
        result = DONT_KNOW
        if line.startswith(JSON_START) and line.endswith(JSON_END):
            line = line[7:-7]
            if line == "none":
                return None
            try:
                result = json.loads(line)
            except json.JSONDecodeError:
                try:
                    result = eval(line)
                except Exception:
                    pass
        return result
    
    def stop(self):
        """Stop and remove the container."""
        if self._container:
            try:
                log.info(f"Stopping container {self.container_name}")
                self._container.stop()
                self._container.remove()
                self._container = None
            except Exception as e:
                log.warning(f"Failed to stop container: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Don't automatically stop container to keep it alive between cells
        pass
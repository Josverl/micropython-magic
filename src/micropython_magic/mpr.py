""" Micropython Remote (MPR) magic for Jupyter Notebooks - Updated to use MPRemoteBoard
"""

import contextlib
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log
from mpflash.mpremoteboard import MPRemoteBoard

from micropython_magic.logger import MCUException
from micropython_magic.script_access import path_for_script

from .interactive import TIMEOUT

JSON_START = "<json~"
JSON_END = "~json>"
DONT_KNOW = "<~?~>"


class MCUInfo(dict):
    """A dict with MCU firmware attributes"""

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class MPRemote2:
    """Compatibility wrapper around MPRemoteBoard to maintain existing interface"""
    
    def __init__(
        self,
        shell: InteractiveShell,
        port: str = "auto",
        resume: bool = True,
    ):
        self.shell: InteractiveShell = shell
        self.port: str = port  # by default connect to the first device
        self.resume = resume  # by default resume the device to maintain state
        self.timeout = TIMEOUT
        
        # Initialize MPRemoteBoard with the specified port
        if port == "auto" or not port:
            # Get first available port
            available_ports = MPRemoteBoard.connected_boards()
            actual_port = available_ports[0] if available_ports else ""
        else:
            actual_port = port
            
        self._board = MPRemoteBoard(serialport=actual_port)
        
    @property
    def cmd_prefix(self) -> List[str]:
        """mpremote command prefix including port and resume according to options"""
        # This property is kept for compatibility but not used in new implementation
        prefix = ["python", "-m", "mpremote"] + self.connect_to
        if self.resume:
            prefix.append("resume")
        return prefix

    @property
    def connect_to(self) -> List[str]:
        "Creates mpremote 'connect to string' if port is specified."
        c = ["connect"]
        if self.port:
            c.append(self.port)
        return c

    def run_cmd(
        self,
        cmd: List[str],
        *,
        auto_connect: bool = True,
        stream_out: bool = True,
        shell=True,
        timeout: Union[int, float] = 0,
        follow: bool = True,
    ):
        """run a command on the device and return the output"""
        assert isinstance(cmd, list)
        
        try:
            # Use MPRemoteBoard's run_command method
            rc, result = self._board.run_command(
                cmd,
                timeout=int(timeout or self.timeout),
                resume=self.resume if auto_connect else False,
            )
            
            if rc != 0:
                raise MCUException(f"Command failed with code {rc}: {' '.join(result) if result else 'Unknown error'}")
                
            return result
            
        except Exception as e:
            log.error(f"Error running command {cmd}: {e}")
            raise MCUException(str(e)) from e

    def select_device(self, port: Optional[str], verify: bool = False):
        """try to select the device to connect to by specifying the serial port name."""
        _port = port.strip() if port else "auto"
        
        if not verify:
            self.port = _port
            # Update the underlying board object
            if _port == "auto" or not _port:
                available_ports = MPRemoteBoard.connected_boards()
                actual_port = available_ports[0] if available_ports else ""
            else:
                actual_port = _port
            self._board = MPRemoteBoard(serialport=actual_port)
            return _port
            
        try:
            # Try to connect and verify
            if _port == "auto" or not _port:
                available_ports = MPRemoteBoard.connected_boards()
                actual_port = available_ports[0] if available_ports else ""
            else:
                actual_port = _port
                
            test_board = MPRemoteBoard(serialport=actual_port)
            test_board.get_mcu_info()
            
            # If successful, update our board
            self.port = _port
            self._board = test_board
            return f"Connected to {actual_port}"
            
        except Exception as e:
            return f"Failed to connect: {e}"

    def run_cell(
        self,
        cell: str,
        *,
        timeout: Union[int, float] = TIMEOUT,
        follow: bool = True,
        mount: Optional[str] = None,
    ):
        """run a codeblock on the device and return the output"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            self._cell_to_file(f, cell)
            
            try:
                # Prepare run command
                run_cmd = ["run", f.name]
                if mount:
                    run_cmd = ["mount", mount] + run_cmd

                log.trace(f"running {run_cmd}")
                rc, result = self._board.run_command(
                    run_cmd,
                    timeout=int(timeout),
                    resume=self.resume,
                )
                
                if rc != 0:
                    error_msg = "\n".join(result) if result else "Unknown error"
                    raise MCUException(f"Cell execution failed: {error_msg}")
                    
                if result:
                    log.debug(f"result: {result}")
                return result
                
            finally:
                Path(f.name).unlink()

    def run_mcu_file(
        self,
        filename: str,
        *,
        stream_out: bool = True,
        timeout: Union[int, float] = 0,
        follow: bool = True,
        mount: Optional[str] = None,
    ):
        """run a file on the device and return the output"""
        exec_cmd = []
        if mount:
            exec_cmd = ["mount", mount]
        exec_cmd += ["exec", f"exec(open('{filename}').read(), globals())"]
        
        rc, result = self._board.run_command(
            exec_cmd, 
            timeout=int(timeout or self.timeout),
            resume=self.resume,
        )
        
        if rc != 0:
            error_msg = "\n".join(result) if result else "Unknown error"
            raise MCUException(f"File execution failed: {error_msg}")
            
        return result

    def copy_cell_to_mcu(self, cell, *, filename: str):
        """copy cell to a file to the MCU"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            self._cell_to_file(f, cell)
            
            try:
                # copy the file to the device
                copy_cmd = ["cp", f.name, f":{filename}"]
                rc, result = self._board.run_command(copy_cmd, timeout=60, resume=self.resume)
                
                if rc != 0:
                    error_msg = "\n".join(result) if result else "Unknown error"
                    raise MCUException(f"Failed to copy file: {error_msg}")
                    
            finally:
                Path(f.name).unlink()

    def _cell_to_file(self, f, cell):
        """Copy cell to a file, and close the file"""
        f.write("# Jupyter cell\n")
        f.write(cell)
        f.close()
        log.trace(f"copied cell to {f.name}")

    def cell_from_mcu_file(self, filename):
        """read a file from the device and return the contents"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            try:
                copy_cmd = ["cp", f":{filename}", f.name]
                rc, result = self._board.run_command(copy_cmd, timeout=60, resume=self.resume)
                
                if rc != 0:
                    error_msg = "\n".join(result) if result else "Unknown error"
                    raise MCUException(f"Failed to read file: {error_msg}")
                    
                return Path(f.name).read_text()
                
            finally:
                if Path(f.name).exists():
                    Path(f.name).unlink()

    @staticmethod
    def load_json_from_MCU(line: str):
        """try to load the output from the MCU transferred as json"""
        result = DONT_KNOW
        if line.startswith(JSON_START) and line.endswith(JSON_END):
            # remove the json wrapper
            line = line[7:-7]
            if line == "none":
                return None
            try:
                result = json.loads(line)
            except json.JSONDecodeError as e:
                with contextlib.suppress(Exception):
                    result = eval(line)
            except Exception as e:
                # result = None
                pass
        return result

    def get_fw_info(self, timeout: float):
        """Get firmware information from the MCU"""
        try:
            # Use MPRemoteBoard's built-in info gathering
            self._board.get_mcu_info(timeout=int(timeout))
            
            # Convert MPRemoteBoard info to the expected format
            fw_info = MCUInfo({
                'family': self._board.family,
                'version': self._board.version,
                'build': self._board.build,
                'port': self._board.port,
                'cpu': self._board.cpu,
                'arch': self._board.arch,
                'mpy': self._board.mpy,
                'description': self._board.description,
                'board': self._board.board,
                'board_id': self._board.board_id,
                'variant': self._board.variant,
            })
            fw_info.serial_port = self.port
            return fw_info
            
        except Exception as e:
            log.error(f"Failed to get firmware info: {e}")
            # Fallback to script-based approach
            try:
                cmd = ["run", str(path_for_script("fw_info.py"))]
                rc, result = self._board.run_command(cmd, timeout=int(timeout), resume=False)
                
                if rc != 0 or not result:
                    return {}
                    
                if not result[0].startswith("{"):
                    return result
                    
                fw_info = MCUInfo(eval(result[0]))
                fw_info.serial_port = self.port
                return fw_info
                
            except Exception as e2:
                log.error(f"Fallback firmware info failed: {e2}")
                return {}

"""Micropython Remote (MPR) magic for Jupyter Notebooks"""

import contextlib
import json
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log
from mpflash.mpremoteboard import MPRemoteBoard

from micropython_magic.logger import MCUException
from micropython_magic.script_access import path_for_script

from .interactive import TIMEOUT, ipython_run

JSON_START = "<json~"
JSON_END = "~json>"
DONT_KNOW = "<~?~>"


class MCUInfo(dict):
    """A dict with MCU firmware attributes"""

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class IPyRemoteBoard(MPRemoteBoard):
    def __init__(
        self,
        shell: InteractiveShell,
        port: str = "auto",
        resume: bool = True,
    ):
        self.shell: InteractiveShell = shell
        super().__init__(serialport=port)
        self.resume = resume  # by default resume the device to maintain state
        # self.timeout = TIMEOUT

    def select_device(self, port: Optional[str], verify: bool = False):
        """try to select the device to connect to by specifying the serial port name."""
        _port = port.strip() if port else "auto"
        if not verify:
            self.port = _port
            return _port
        # cmd = f"""eval \"'{_port}'\""""
        cmd = ["eval", f"\"'{_port}'\""]
        try:
            output = self.run_command_ipython(cmd)
            self.port = _port
        except Exception as e:
            output = e
        return output

    def run_cell(
        self,
        cell: str,
        *,
        timeout: Union[int, float] = TIMEOUT,
        follow: bool = True,
        mount: Optional[str] = None,
    ):
        """run a codeblock on the device and return the output
        copy cell to a file and run it on the MCU"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            self._cell_to_file(f, cell)
            # copy the file to the device
            run_cmd = ["run", f.name]  # TODO: may need to add quotes around f.name
            if mount:
                # prefix the run command with a mount command
                # run_cmd = f'mount "{Path(mount).as_posix()}" ' + run_cmd
                run_cmd = ["mount", mount] + run_cmd

            # TODO: detect / retry / report errors copying the file
            log.trace(f"running {run_cmd}")
            try:
                result = self.run_command_ipython(
                    run_cmd,
                    stream_out=True,
                    timeout=timeout,
                    follow=follow,
                )
                if result:
                    log.debug(f"result: {result}")
            except (MCUException, ConnectionError) as e:
                raise e
            # except Exception as e:

            #     log.error(f"Exception: {e}")
            #     result = e

            finally:
                Path(f.name).unlink()
        return result

    def copy_cell_to_mcu(self, cell, *, filename: str):
        """copy cell to a file to the MCU"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            self._cell_to_file(f, cell)
            # copy the file to the device
            copy_cmd = ["cp", f.name, f":{filename}"]
            # TODO: detect / retry / report errors copying the file
            # _ = self.run_command_ipython(copy_cmd, stream_out=False, timeout=60)
            _ = self.run_command_ipython(copy_cmd, timeout=60)
            # log.info(_)
            # log.info(f.name, "copied to device")
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
            # copy_cmd = f"cp :{filename} {f.name}"
            copy_cmd = ["cp", f":{filename}", f.name]
            # TODO: detect / retry / report errors copying the file
            # _ = self.run_command_ipython(copy_cmd, stream_out=False, timeout=60)
            _ = self.run_command_ipython(copy_cmd, timeout=60)

            return Path(f.name).read_text()

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

    def run_command_ipython(
        self,
        cmd: Union[str, List[str]],
        *,
        auto_connect: bool = True,
        stream_out: bool = True,
        shell=True,
        timeout: Union[int, float] = 0,
        follow: bool = True,
    ):
        """run a command on the device and return the output"""
        if isinstance(cmd, str) and " " in cmd:
            cmd = cmd.split(" ")
        elif isinstance(cmd, str):
            cmd = [cmd]
        if auto_connect:
            cmd = self.cmd_prefix() + cmd
            # if isinstance(cmd, str):
            #     cmd = f"""{self.cmd_prefix} {cmd}"""
            # else:
            #     log.warning(f"cmd is not a string: {cmd}")
        with log.contextualize(port=self.port):
            log.debug(cmd)
            return ipython_run(
                cmd,
                stream_out=stream_out,
                shell=shell,
                timeout=timeout,
                follow=follow,
            )

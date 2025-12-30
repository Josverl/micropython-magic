"""Micropython Remote magic for Jupyter Notebooks"""

import contextlib
import json
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log
from mpflash.mpremoteboard import RETRIES, MPRemoteBoard
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from micropython_magic.interactive import TIMEOUT, ipython_run
from micropython_magic.logger import MCUException

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
        serialport: str = "auto",
        resume: bool = True,
    ):
        self.shell: InteractiveShell = shell
        super().__init__(serialport=serialport)
        self.resume = resume  # by default resume the device to maintain state
        # self.timeout = TIMEOUT

    def select_device(self, serialport: Optional[str], verify: bool = False):
        """try to select the device to connect to by specifying the serial port name."""
        _comport = serialport.strip() if serialport else "auto"
        # update the serial port used by mpremote; keep MicroPython port info untouched
        self.serialport = _comport
        if not verify:
            return _comport

        # verify that there is indeed a device at that port
        cmd = ["eval", f"\"'{_comport}'\""]
        try:
            output = self.run_command_ipython(cmd)
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

    @retry(
        stop=stop_after_attempt(RETRIES),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def run_command_ipython(
        self,
        cmd: Union[str, List[str]],
        *,
        auto_connect: bool = True,
        stream_out: bool = True,
        shell=True,
        timeout: Union[int, float] = 0,
        follow: bool = True,
        resume: Optional[bool] = None,
        hide_meminfo: bool = False,
        store_output: bool = True,
    ):
        """run a command on the device and return the output"""
        if isinstance(cmd, str) and " " in cmd:
            cmd = cmd.split(" ")
        elif isinstance(cmd, str):
            cmd = [cmd]

        full_cmd = self.build_cmd(
            cmd,
            resume=resume if resume is not None else self.resume,
            auto_connect=auto_connect,
        )
        with log.contextualize(serialport=self.serialport):
            log.debug(full_cmd)
            return ipython_run(
                full_cmd,
                stream_out=stream_out,
                shell=shell,
                timeout=timeout,
                follow=follow,
                hide_meminfo=hide_meminfo,
                store_output=store_output,
            )

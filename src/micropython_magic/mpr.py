""" Micropython Remote (MPR) magic for Jupyter Notebooks
"""

import contextlib
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log

from .interactive import ipython_run

JSON_START = "<json~"
JSON_END = "~json>"
DONT_KNOW = "<~?~>"

import os

from .interactive import TIMEOUT


class MPRemote2:
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

    @property
    def cmd_prefix(self):
        """mpremote command prefix including port and resume according to options"""
        return f"mpremote {self.connect_to}{'resume' if self.resume else ''} "

    @property
    def connect_to(self):
        "Creates mpremote 'connect to string' if port is specified."
        return f"connect {self.port} " if self.port else ""

    def run_cmd(
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
        if auto_connect:
            if isinstance(cmd, str):
                cmd = f"""{self.cmd_prefix} {cmd}"""
            else:
                log.warning(f"cmd is not a string: {cmd}")
        log.debug(cmd)
        return ipython_run(
            cmd, stream_out=stream_out, shell=shell, timeout=timeout or self.timeout, follow=follow
        )

        # output = self.shell.getoutput(cmd, split=True)
        # assert isinstance(output, SList)
        # if len(output) > 0 and output[0].strip() == "no device found":
        #     raise ConnectionError("no device found")
        # return output

    def select_device(self, port: Optional[str], verify: bool = False):
        """try to select the device to connect to by specifying the serial port name."""
        _port = port.strip() if port else "auto"
        if not verify:
            self.port = _port
            return _port
        cmd = f"""eval \"'{_port}'\""""
        try:
            output = self.run_cmd(cmd)
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
        """run a codeblock on the device and return the output"""
        """copy cell to a file and run it on the MCU"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                "# Jupyter cell\n"
            )  # add a line to replace the cell magic to keep the line numbers aligned
            f.write(cell)
            f.close()
            # copy the file to the device
            log.trace(f"copied cell to {f.name}")
            file_attributes = os.stat(f.name)
            log.trace(f"{file_attributes=}")
            run_cmd = f"run {f.name}"
            if mount:
                # prefix the run command with a mount command
                run_cmd = f'mount "{Path(mount).as_posix()}" ' + run_cmd

            # TODO: detect / retry / report errors copying the file
            log.trace(f"running {run_cmd}")
            try:
                result = self.run_cmd(
                    run_cmd,
                    stream_out=True,
                    timeout=timeout,
                    follow=follow,
                )
                if result:
                    log.trace(f"result: {result}")
            except Exception as e:
                result = e

            finally:
                Path(f.name).unlink()
        return result

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
        exec_cmd = ""
        if mount:
            exec_cmd = f'mount "{mount}" '
        exec_cmd += f"exec \"exec( open('{filename}').read() , globals() )\""
        return self.run_cmd(exec_cmd, stream_out=stream_out, timeout=timeout, follow=follow)

    def copy_cell_to_mcu(self, cell, *, filename: str):
        """copy cell to a file to the MCU"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                "# Jupyter cell\n"
            )  # add a line to replace the cell magic to keep the line numbers aligned
            f.write(cell)
            f.close()
            # copy the file to the device
            copy_cmd = f"cp {f.name} :{filename}"
            # TODO: detect / retry / report errors copying the file
            _ = self.run_cmd(copy_cmd, stream_out=False, timeout=60)
            # log.info(_)
            # log.info(f.name, "copied to device")
            Path(f.name).unlink()

    def cell_from_mcu_file(self, filename):
        """read a file from the device and return the contents"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            copy_cmd = f"cp :{filename} {f.name}"
            # TODO: detect / retry / report errors copying the file
            _ = self.run_cmd(copy_cmd, stream_out=False, timeout=60)

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

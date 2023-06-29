""" Micropython Remote (MPR) magic for Jupyter Notebooks
"""

import contextlib
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Union

import IPython
from colorama import Style
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.text import LSString, SList
from loguru import logger as log

from .interactive import ipython_run

JSON_START = "<json~"
JSON_END = "~json>"
DONT_KNOW = "<~?~>"

from .interactive import TIMEOUT


class MPRemote2:
    def __init__(self, shell: InteractiveShell, port: str = "auto", resume: bool = True):
        self.shell: InteractiveShell = shell
        self.port: str = "auto"  # by default connect to the first device
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

    def run_cmd(self, cmd: str, *, auto_connect: bool = True, stream_out: bool = True, shell=True, timeout=0):
        """run a command on the device and return the output"""
        if auto_connect:
            cmd = f"""{self.cmd_prefix} {cmd}"""
        log.debug(cmd)
        return ipython_run(cmd, stream_out=stream_out, shell=shell, timeout=timeout or self.timeout)

        # output = self.shell.getoutput(cmd, split=True)
        # assert isinstance(output, SList)
        # if len(output) > 0 and output[0].strip() == "no device found":
        #     raise ConnectionError("no device found")
        # return output

    def select_device(self, line: Optional[str]):
        """try to select the device to connect to by specifying the serial port name."""
        _port = line.strip() if line else "auto"
        cmd = f"""eval \"'Checking connection to MCU on port {_port}.'\""""
        try:
            output = self.run_cmd(cmd)
            self.port = _port
        except Exception as e:
            output = e
        return output

    def run_cell(self, cell: str):
        """run a codeblock on the device and return the output"""
        #     # TODO: if the cell is small enough, concat the cell with \n an use exec instead of copy
        #     # - may need escaping quotes and newlines
        # copy the cell to a file on the device
        self.cell_to_mcu_file(cell, "__magic.py")
        # run the transferred cell/file
        result = self.run_mcu_file("__magic.py", stream_out=True)
        return

    def run_mcu_file(self, filename: str, stream_out: bool = True, timeout: int = 0):
        exec_cmd = f"exec \"exec( open('{filename}').read() , globals() )\""
        return self.run_cmd(exec_cmd, stream_out=stream_out, timeout=timeout)

    def cell_to_mcu_file(self, cell, filename):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# Jupyter cell\n")  # add a line to replace the cell magic to keep the line numbers aligned
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

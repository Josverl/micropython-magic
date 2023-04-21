"""
Run micropython code from a a notebook
 - connects to the first MCU connected on serial
 - uses resume to avoid soft-resetting the MCU
"""
# https://ipython.readthedocs.io/en/stable/config/custommagics.html
# https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.magic.html#IPython.core.magic.Magics
# https://nbviewer.org/github/rossant/ipython-minibook/blob/master/chapter6/602-cpp.ipynb

import json
import logging
import re
import sys
import tempfile
import warnings
from pathlib import Path
from typing import List, Optional, Union

from colorama import Style
from IPython.core.display import HTML, Javascript, Markdown, Pretty, TextDisplayObject, display
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import (
    Magics,
    cell_magic,
    line_magic,
    magics_class,
    needs_local_scope,
    output_can_be_silenced,
)
from IPython.utils.text import LSString, SList
from loguru import logger as log
from mpremote import pyboard, pyboardextended


def set_log_level(llevel: str):
    # format_str = "<level>{level: <8}</level> | <cyan>{module: <18}</cyan> - <level>{message}</level>"
    # format_str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    format_str = "<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    log.remove(0)
    log.add(sys.stdout, format=format_str, level=llevel, colorize=True)


DONT_KNOW = "<~?~>"
"""unknown type"""

set_log_level("INFO")


class PrettyOutput(object):
    """"""

    def __init__(self, data: Union[SList, LSString]):
        self.data = data

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __repr__(self):
        if isinstance(self.data, SList):
            return "\n".join(self.data.list)
        elif isinstance(self.data, LSString):
            return self.data
        else:
            self.data
            raise UsageError("Unexpected output type")


def just_text(output) -> str:
    """returns the text output of the command"""
    if isinstance(output, SList):
        return "\n".join(output.list)
    elif isinstance(output, LSString):
        return output
    else:
        return str(output)


class MPRemote2:
    def __init__(self, shell: InteractiveShell, port: str = "auto", resume: bool = True):
        self.shell: InteractiveShell = shell
        self.port: str = "auto"  # by default connect to the first device
        self.resume = True  # by default resume the device to maintain state

    @property
    def cmd_prefix(self):
        """mpremote command prefix including port and resume according to options"""
        return f"mpremote {self.connect_to}{'resume' if self.resume else ''} "

    @property
    def connect_to(self):
        "Creates mpremote 'connect to string' if port is specified."
        return f"connect {self.port} " if self.port else ""

    def run_cmd(self, cmd: str, auto_connect: bool = True):
        """run a command on the device and return the output"""
        if auto_connect:
            cmd = f"""{self.cmd_prefix} {cmd}"""
        log.debug(cmd)
        return self.shell.getoutput(cmd)

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

    def run_codeblock(self, cell: str):
        """run a codeblock on the device and return the output"""

        #     # TODO: if the cell is small enough, concat the cell with \n an use exec instead of copy
        #     # - may need escaping quotes and newlines

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(cell)
            f.close()
            # copy the file to the device
            copy_cmd = "cp {0:s} :__magic.py".format(f.name)
            # TODO: detect / retry / report errors copying the file
            _ = self.run_cmd(copy_cmd)
            # log.info(_)
            # log.info(f.name, "copied to device")
            Path(f.name).unlink()
            # run the transferred cell/file
            exec_cmd = "exec \"exec( open('__magic.py').read() , globals() )\""
        return self.run_cmd(exec_cmd)

    @staticmethod
    def load_json_from_MCU(line: str):
        """try to load the output from the MCU transferred as json"""
        result = DONT_KNOW
        if line.startswith("<json~") and line.endswith("~json>"):
            # remove the json wrapper
            line = line[7:-7]
            if line == "none":
                return None
            try:
                result = json.loads(line)
            except json.JSONDecodeError as e:
                try:
                    if line.startswith("{") and line.endswith("}"):
                        log.debug(" '{ }' detected - trying to eval the output")
                        result = eval(line)
                    elif "(" in line:  # perhaps this is wrapped in a type -(top level only?)
                        log.debug(" '(' detected - trying to eval the output")
                        result = eval(line)
                    else:
                        result = eval(line)
                except Exception as e:
                    result = None
            except Exception as e:
                result = None
        return result


@magics_class
class MpyMagics(Magics):
    """A class to define the magic functions for Micropython."""

    def __init__(self, shell: InteractiveShell):
        # first call the parent constructor
        super(MpyMagics, self).__init__(shell)
        self.shell: InteractiveShell
        self._MCUs: List[MPRemote2] = [MPRemote2(shell)]
        # self.port: str = "auto"  # by default connect to the first device
        # self.resume = True  # by default resume the device to maintain state

    @property
    def port(self) -> None:
        return None

    @property
    def MCU(self) -> MPRemote2:
        """Return the first/current/only MCU"""
        # to allow expansion to multiple MCUs in the future
        return self._MCUs[0]

    @line_magic("list_devices")
    def list_devices(self, line: str = "") -> list:
        """
        Return a SList or list of the Micropython devices connected to the computer through serial ports or USB.
        """
        if line:
            print("no arguments expected")
        cmd = "mpremote connect list"
        # output = self.shell.getoutput(cmd)
        output = self.MCU.run_cmd(cmd, auto_connect=False)
        if isinstance(output, SList):
            return output.list
        elif isinstance(output, list):
            return output
        else:
            return [output]
        # TODO: handle other output types #

    @line_magic("select")
    @output_can_be_silenced
    def select(self, line: Optional[str]):
        """
        Select the device to connect to by specifying the serial port name.
        """
        device = line.strip() if line else "auto"
        output = self.MCU.select_device(device)
        return just_text(output)

    @cell_magic("micropython")
    @cell_magic("mpy")
    def mpy_cell(self, line: str, cell: Optional[str] = None):
        """
        Run Micropython code on an attached device using mpremote.
        """
        if not cell:
            raise UsageError("Please specify some MicroPython code to execute")
        output = self.MCU.run_codeblock(cell)
        return PrettyOutput(output)

    @line_magic("micropython")
    @line_magic("mpy")
    @output_can_be_silenced
    def mpy_line(self, line: str):
        """
        Run Micropython code on an attached device using mpremote.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Assemble the command to run
        cmd = f'exec "{line}"'
        # print(exec_cmd)
        output = self.MCU.run_cmd(cmd)
        return PrettyOutput(output)

    @line_magic("eval")
    def eval(self, line: str):
        """
        Run a Micropython expression on an attached device using mpremote.
        Note that the expression
         * can only be a single expression
         * it cannot contain  comments or newlines.

        Runs the statement on the MCU and tries to convert the output to a python object.
        If that fails it returns the raw output as a string.
        """
        # Assemble the command to run
        statement = line.strip()
        cmd = f'''exec "import json; print('<json~',json.dumps({statement}),'~json>')"'''
        # print(cmd)
        output = self.MCU.run_cmd(cmd)
        matchers = [r"^.*Error:", r"^.*Exception:"]

        for ln in output.l:
            # check for errors and raise them
            if any(re.match(m, ln) for m in matchers):
                raise RuntimeError(ln) from eval(ln.split(":")[0])
            # check for json output and try to convert it
            if ln.startswith("<json~") and ln.endswith("~json>"):
                result = self.MCU.load_json_from_MCU(ln)
                if result != DONT_KNOW:
                    return result
        return output

    @line_magic("soft-reset")
    @output_can_be_silenced
    def soft_reset(self, line: str):
        """
        Perform a soft-reset on the current Micropython device.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Append an eval statement to avoid ending up in the repl
        output = self.MCU.run_cmd("soft-reset eval True")
        self.output = output
        return just_text(output)

    @line_magic("hard-reset")
    @output_can_be_silenced
    def hard_reset(self, line: str):
        """
        Perform a hard-reset on the current Micropython device.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        output = self.MCU.run_cmd("reset")
        self.output = output
        return just_text(output)

    @line_magic("mpremote")
    def mpremote(self, line: str):
        """Run a mpremote command with the commandline options"""
        cmd = f'mpremote "{line}"'
        output = self.MCU.run_cmd(cmd, auto_connect=False)
        self.output = output
        return output

    @line_magic("jv")
    def jv(self, line: str):
        """just something to test"""
        # log.warning("some warning")
        x = {"a": 1, "b": 2, "c": [1, 2, 3]}
        return Pretty(x)
        # output = ["['lib', 'temp.py', 'System Volume Information']", "OSError('boo')", "esp32"]
        # return Pretty("\n".join(output))

        # if isinstance(output, list):
        #     # ths is a multiline output from mpremote
        #     output_ = []
        #     for line in output:
        #         try:
        #             line_ = eval(line)
        #             output_.append(line_)
        #         except Exception as e:
        #             output_.append(line)
        #     # display(Pretty("\n".join(output)))
        #     return Pretty("\n".join(output))
        #     return
        # return x

    @line_magic("setvar")
    def setvars(self, line: str):
        """just something to test"""
        self.shell.user_ns["newvar"] = "just a brand new variable"
        # log.warning("some warning")

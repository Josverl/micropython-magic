"""
Run micropython code from a a notebook
 - connects to the first MCU connected on serial
 - uses resume to avoid soft-resetting the MCU
"""
# https://ipython.readthedocs.io/en/stable/config/custommagics.html
# https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.magic.html#IPython.core.magic.Magics
# https://nbviewer.org/github/rossant/ipython-minibook/blob/master/chapter6/602-cpp.ipynb

import re
import tempfile
from pathlib import Path
from typing import Optional, Union
from warnings import warn

from colorama import Style
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
from mpremote import pyboard, pyboardextended


def log(*args, **kwargs):
    print(Style.DIM, *args, **kwargs)


class PrettyOutput(object):
    """"""

    def __init__(self, output: Union[SList, LSString]):
        self.output = output

    def __getattr__(self, item):
        return getattr(self.output, item)

    def __repr__(self):
        if isinstance(self.output, SList):
            return "\n".join(self.output.list)
        elif isinstance(self.output, LSString):
            return self.output
        else:
            self.output
            raise UsageError("Unexpected output type")


def just_text(output) -> str:
    """returns the text output of the command"""
    if isinstance(output, SList):
        return "\n".join(output.list)
    elif isinstance(output, LSString):
        return output
    else:
        return str(output)


@magics_class
class MpyMagics(Magics):
    """A class to define the magic functions for Micropython."""

    def __init__(self, shell: InteractiveShell):
        # first call the parent constructor
        super(MpyMagics, self).__init__(shell)
        self.shell: InteractiveShell
        self.port: str = "auto"  # by default connect to the first device
        self.resume = True  # by default resume the device to maintain state

    @property
    def cmd_prefix(self):
        """mpremote command prefix including poert and resume according to options"""
        return f"mpremote {self.connect_to}{'resume' if self.resume else ''} "

    @property
    def connect_to(self):
        "creates connect to strign if port is specified"
        return f"connect {self.port} " if self.port else ""

    @line_magic("list_devices")
    def list_devices(self, line: str = "") -> list:
        """
        Return a SList or list of the Micropython devices connected to the computer through serial ports or USB.
        """
        if line:
            print("no arguments expected")
        exec_cmd = "mpremote resume connect list"
        output = self.shell.getoutput(exec_cmd)
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
        output = None
        if not line:
            # connect to the first/default
            self.port = "auto"
        else:
            self.port = line.strip()

        exec_cmd = (
            f"""{self.cmd_prefix}eval \"'Checking connection to MCU on port {self.port}.'\""""
        )
        # log.warn(exec_cmd)
        output = self.shell.getoutput(exec_cmd)
        return just_text(output)

    @cell_magic("mpy")
    def mpy_cell(self, line: str, cell: Optional[str] = None):
        """
        Run Micropython code on an attached device using mpremote.
        """
        # Assemble the command to run
        if not cell:
            raise UsageError("Please specify some MicroPython code to execute")
        if line:
            print("line specified", line)
        if False and len(cell) < 100:
            # TODO: if the cell is small enough, concat the cell with \n an use exec instead of copy
            # - may need escaping quotes and newlines
            raise NotImplementedError("pyboardextended exec not implemented yet")
            log("cell is small enough to use exec")

            exec_cmd = f'{self.cmd_prefix}exec "{cell}"'
            log(exec_cmd)

        else:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(cell)
                f.close()
                # copy the file to the device
                copy_cmd = self.cmd_prefix + "cp {0:s} :__magic.py".format(f.name)
                # TODO: detect / retry / report errors copying the file
                _ = self.shell.getoutput(copy_cmd)
                # log(_)
                # log(f.name, "copied to device")
                Path(f.name).unlink()
                # run the transferred cell/file
                exec_cmd = (
                    self.cmd_prefix + "exec \"exec( open('__magic.py').read() , globals() )\""
                )

        # log(exec_cmd)
        output = self.shell.getoutput(exec_cmd)
        return PrettyOutput(output)

    @line_magic("mpy")
    @output_can_be_silenced
    def mpy_line(self, line: str):
        """
        Run Micropython code on an attached device using mpremote.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Assemble the command to run
        exec_cmd = f'{self.cmd_prefix}exec "{line}"'
        # print(exec_cmd)
        output = self.shell.getoutput(exec_cmd)
        self.output = output
        return PrettyOutput(output)

    @line_magic("eval")
    @output_can_be_silenced
    def eval(self, line: str):
        """
        Run Micropython code on an attached device using mpremote.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Assemble the command to run
        cmd = f'{self.cmd_prefix}eval "{line}"'
        # print(cmd)
        output = self.shell.getoutput(cmd)
        self.output = output
        return just_text(output)

    @line_magic("soft-reset")
    @output_can_be_silenced
    def soft_reset(self, line: str):
        """
        Perform a soft-reset on the current Micropython device.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Assemble the command to run
        # Append an eval statement to avoid ending up in the repl
        cmd = f"{self.cmd_prefix} soft-reset eval True"
        # print(cmd)
        output = self.shell.getoutput(cmd)
        self.output = output
        return just_text(output)

    @line_magic("hard-reset")
    @output_can_be_silenced
    def hard_reset(self, line: str):
        """
        Perform a hard-reset on the current Micropython device.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        # Assemble the command to run
        # Append an eval statement to avoid ending up in the repl
        cmd = f"{self.cmd_prefix} reset"
        # print(cmd)
        output = self.shell.getoutput(cmd)
        self.output = output
        return just_text(output)

    @line_magic("mpremote")
    def mpremote(self, line: str):
        """Run a mpremote command with the commandline options"""
        cmd = f'mpremote "{line}"'
        output = self.shell.getoutput(cmd)
        self.output = output
        return output

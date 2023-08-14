"""Some magics to experiment with"""
import contextlib
import json
import logging
import re
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import List, Optional, Union

import IPython
from colorama import Style
from IPython.core.display import HTML, Javascript, Markdown, Pretty, ProgressBar, TextDisplayObject, display, update_display
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, cell_magic, line_magic, magics_class, needs_local_scope, output_can_be_silenced
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display
from IPython.utils.text import LSString, SList
from loguru import logger as log

from micropython_magic.octarine import MpyMagics, PrettyOutput


@magics_class
class ExpMagics(MpyMagics):
    # @cell_magic("cool")
    # def magic_cool(self, line, cell):
    #     """\
    #     A really cool magic command.
    #     """
    #     print(f"Magically cool ! {cell=}")

    # @line_magic("mpremote2")
    # def mpremote(self, line: str):
    #     """Run a mpremote command with the commandline options"""
    #     cmd = f'mpremote "{line}"'
    #     output = self.MCU.run_cmd(cmd, auto_connect=False)
    #     self.output = output
    #     return output

    @line_magic("slow")
    def slow(self, line: str):
        """just something to test"""

        output = ["line 1", "line 2", "line 3"]
        slow_did = display(Pretty("\n".join(output)), display_id=True)

        for i in range(10):
            time.sleep(1)
            output.append(f"line {i+3}")
            update_display(Pretty("\n".join(output)), display_id=slow_did.display_id)
        # # log.warning("some warning")
        # x = {"a": 1, "b": 2, "c": [1, 2, 3]}
        # return PrettyOutput(x)
        # # return Pretty(x)
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
        if self.shell:
            self.shell.user_ns["newvar"] = "just a brand new variable"
        else:
            log.warning("No shell found")

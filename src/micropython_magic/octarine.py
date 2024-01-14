"""
Run micropython code from a a notebook
 - connects to the first MCU connected on serial
 - uses resume to avoid soft-resetting the MCU
"""

# https://ipython.readthedocs.io/en/stable/config/custommagics.html
# https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.magic.html#IPython.core.magic.Magics
# https://nbviewer.org/github/rossant/ipython-minibook/blob/master/chapter6/602-cpp.ipynb

import argparse
import enum
import re
from typing import List, Optional

from colorama import Style
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, cell_magic, line_magic, magics_class, output_can_be_silenced
from IPython.core.magic_arguments import argument, argument_group, magic_arguments, parse_argstring
from IPython.utils.text import LSString, SList
from loguru import logger as log  # type: ignore
from traitlets import Float as Float_
from traitlets import UseEnum, observe

from micropython_magic.interactive import TIMEOUT
from micropython_magic.param_fixup import get_code

from .logger import set_log_level
from .mpr import DONT_KNOW, JSON_END, JSON_START, MPRemote2

# set the log level to WARNING
set_log_level("WARNING")


class MCUException(Exception):
    """Exception raised for errors on the MCU."""

    pass


class PrettyOutput(object):
    """"""

    def __init__(self, data):
        self.data = data

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __repr__(self):
        return repr(self.data)

    def _str_(self):
        return "\n".join(self.data.list)

    def _repr_json_(self):
        return self.data
        # return json.dumps(self.data, indent=2)


def just_text(output) -> str:
    """returns the text output of the command"""
    if isinstance(output, SList):
        return "\n".join(output.list)
    elif isinstance(output, LSString):
        return output
    else:
        return str(output)


class LogLevel(str, enum.Enum):
    """Log level"""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@magics_class
class MicroPythonMagic(Magics):
    """A class to define the magic functions for MicroPython."""

    # The default timeout
    timeout = Float_(TIMEOUT).tag(config=True, sync=True)  # type: ignore
    # verbose = Bool_(False).tag(config=True, sync=True)  # type: ignore
    loglevel = UseEnum(LogLevel, default_value=LogLevel.WARNING).tag(config=True)
    # .tag(config=True, sync=True)  # type: ignore

    def __init__(self, shell: InteractiveShell):
        # first call the parent constructor
        super(MicroPythonMagic, self).__init__(shell)
        self.shell: InteractiveShell
        self._MCUs: list[MPRemote2] = [MPRemote2(shell)]
        # self.port: str = "auto"  # by default connect to the first device
        # self.resume = True  # by default resume the device to maintain state

    @observe("loglevel")
    def _verbose_changed(self, change):
        # print(f"{change=}")
        if change["new"]:
            set_log_level(change["new"])
        else:
            set_log_level(LogLevel.WARNING)

    @property
    def port(self) -> None:
        return None

    @property
    def MCU(self) -> MPRemote2:
        """Return the first/current/only MCU"""
        # to allow expansion to multiple MCUs in the future
        return self._MCUs[0]

    # -------------------------------------------------------------------------
    # cell magics
    # -------------------------------------------------------------------------

    @cell_magic("micropython")
    @cell_magic("mpy")
    @magic_arguments("%micropython")  # add additional % to display two %% in help
    #
    @argument_group("Mount")
    @argument(
        "--mount",
        type=str,
        help="Host folder to mount on the MCU",
        metavar="A/FOLDER",
    )
    @argument_group("Code execution")
    @argument(
        "--writefile",
        "--save",
        "-wf",
        type=str,
        help="MCU [path/]filename to write to",
        metavar="PATH/FILE.PY",
    )
    @argument(
        "--readfile",
        "--load",
        "-rf",
        type=str,
        help="MCU [path/]filename to read from",
        metavar="PATH/FILE.PY",
    )
    @argument(
        "--new",
        action="store_true",
        help="new cell is added after the current cell instead of replacing it",
    )
    @argument("--timeout", default=-1, help="maximum timeout for the cell to run")
    @argument(
        "--follow",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="follow the output",
    )
    #
    @argument_group("Devices")
    @argument("--select", nargs="+", help="serial port to connect to", metavar="PORT")
    @argument(
        "--reset", "--soft-reset", action="store_true", help="Reset device (before running cell)."
    )
    @argument("--hard-reset", action="store_true", help="reset device.")
    def micropython(self, line: str, cell: str = ""):
        """
        Run Micropython code on an attached device using mpremote.
        """
        args = parse_argstring(self.micropython, line or "")

        if args.timeout == -1:
            args.timeout = self.timeout
        assert isinstance(args.timeout, float)

        if args.select:
            if len(args.select) > 1:
                # allow a list of ports to be specified
                log.warning(f"{args.select=} not yet implemented")
                return
            else:
                self.select(args.select[0])

        if line:
            log.debug(f"{args=}")
        # pre processing - these can be combined with the main processing

        if args.hard_reset:
            self.hard_reset()
        elif args.reset:
            self.soft_reset()

        if args.writefile:
            log.debug(f"{args.writefile=}")
            if args.new:
                log.warning(f"{args.new=} not implemented")
            self.MCU.copy_cell_to_mcu(cell, filename=args.writefile)
            return

        if args.readfile:
            log.debug(f"{args.readfile=},{args.new=}")
            code = self.MCU.cell_from_mcu_file(args.readfile)
            # if the first line contains a magic command, replace it with this magic command but with the options commented out
            if code.startswith("# %%"):
                code = "\n".join(code.split("\n")[1:])
            code = f"# %%micropython # {line}\n{code}"  # todo - use the same notation for the first line as the original command
            if args.new:
                self.shell.set_next_input(code, replace=False)
            else:
                self.shell.set_next_input(code, replace=True)
            return

        if not cell:
            raise UsageError("Please specify some MicroPython code to execute")
        log.trace(f"{cell=}")
        output = self.MCU.run_cell(
            cell, timeout=args.timeout, follow=args.follow, mount=args.mount
        )
        # return PrettyOutput(output)

    # -------------------------------------------------------------------------
    # line magics
    # -------------------------------------------------------------------------

    @line_magic("micropython")
    @line_magic("mpy")
    @magic_arguments("mpy")
    @argument_group("Code execution")
    @argument("statement", nargs="*", help="Micropython code to run.", metavar="STATEMENT(S)")
    @argument("--eval", "-e", nargs="*", help="Expression to evaluate", metavar="EXPRESSION")
    @argument("--timeout", default=-1, help="maximum timeout for the cell to run")
    @argument("--stream", action="store_true", help="stream each line of output as it is received")
    @argument_group("Devices")
    @argument("--list", "--devs", "-l", action="store_true", help="List available devices.")
    @argument("--select", "-s", nargs="+", help="serial port to connect to", metavar="PORT")
    @argument("--reset", "--soft-reset", action="store_true", help="reset device.")
    @argument("--hard-reset", action="store_true", help="reset device.")
    @argument("--info", action="store_true", help="get boardinfo from device")
    @argument("--bootloader", action="store_true", help="make the device enter its bootloader")
    @output_can_be_silenced
    def mpy_line(self, line: str):
        """
        Run Micropython code on an attached device using mpremote.

        - can be silenced with a trailing semicolon when used as a line magic
        """
        args = parse_argstring(self.mpy_line, line or "")
        if args.timeout == -1:
            args.timeout = self.timeout
        if not isinstance(args.timeout, float):
            args.timeout = float(args.timeout)  # type: ignore

        # try to fixup the expression after shell and argparse mangled it
        if args.statement and len(args.statement) >= 1:
            args.statement = get_code(line, args.statement[0])
        if args.eval and len(args.eval) >= 1:
            args.eval = get_code(line, args.eval[0])
        if isinstance(args.eval, list):
            args.eval = " ".join(args.eval)
        if args.hard_reset:  # avoid double resets
            args.reset = False
        #
        if line:
            log.debug(f"{args=}")
        # pre processing - these can be combined with the main processing
        if args.select:
            if len(args.select) > 1:
                log.warning(f"{args.select=} for multiple MCUs not yet implemented")
                return
            else:
                self.select(args.select[0])
        if args.hard_reset:
            self.hard_reset()
        elif args.reset:
            self.soft_reset()
        elif args.bootloader:
            self.MCU.run_cmd(["bootloader"])

        # processing
        if args.list:
            return self.list_devices()
        elif args.info:
            return self.get_fw_info(args.timeout)

        elif args.eval:
            return self.eval(args.eval)

        elif args.statement:
            # Assemble the command to run
            statement = "\n".join(args.statement)
            cmd = ["exec", statement]
            log.debug(f"{cmd=}")

            return self.MCU.run_cmd(
                cmd,
                stream_out=bool(args.stream),
                timeout=float(args.timeout),
            )

    # -------------------------------------------------------------------------
    # worker methods - these are called by the magics
    # -------------------------------------------------------------------------

    def list_devices(self) -> Optional[SList]:
        """
        Return a SList or list of the Micropython devices connected to the computer through serial ports or USB.
        """
        cmd = ["mpremote", "connect", "list"]
        # output = self.shell.getoutput(cmd)
        output = self.MCU.run_cmd(cmd, auto_connect=False, stream_out=False)
        return output

    def select(self, port: Optional[str]):
        """
        Select the device to connect to by specifying the serial port name.
        """
        device = port.strip() if port else "auto"
        output = self.MCU.select_device(device)
        return output

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
        cmd_old = (
            f'''exec "import json; print('{JSON_START}',json.dumps({statement}),'{JSON_END}')"'''
        )
        cmd = [
            "exec",
            # f'''"import json; print('{JSON_START}',json.dumps({statement}),'{JSON_END}')"''',
            f"""import json; print('{JSON_START}',json.dumps({statement}),'{JSON_END}')""",
        ]
        log.trace(repr(cmd))
        output = self.MCU.run_cmd(cmd, stream_out=False)
        if isinstance(output, SList):
            matchers = [r"^.*Error:", r"^.*Exception:"]
            for ln in output.l:
                # check for errors and raise them
                if any(re.match(m, ln) for m in matchers):
                    raise MCUException(ln) from eval(ln.split(":")[0])
                # check for json output and try to convert it
                if ln.startswith(JSON_START) and ln.endswith(JSON_END):
                    result = self.MCU.load_json_from_MCU(ln)
                    if result != DONT_KNOW:
                        return result
        return output

    def soft_reset(self):
        """
        Perform a soft-reset on the current Micropython device.
        """
        # Append an eval statement to avoid ending up in the repl
        output = self.MCU.run_cmd(["soft-reset", "eval", "True"])
        self.output = output
        return just_text(output)

    def hard_reset(self):
        """
        Perform a hard-reset on the current Micropython device.
        """
        output = self.MCU.run_cmd(["reset"])
        self.output = output
        return output

    def get_fw_info(self, timeout: float):
        return self.MCU.get_fw_info(timeout)

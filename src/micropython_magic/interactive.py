import contextlib
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from threading import Timer
from typing import List, Optional, Union

from IPython.core.getipython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.text import SList
from loguru import logger as log

TIMEOUT = 300
from .memoryinfo import RE_ALL


@dataclass
class LogTags:
    reset_tags: List[str]
    error_tags: List[str]
    warning_tags: List[str]
    success_tags: List[str]
    ignore_tags: List[str]
    trace_tags: List[str]
    trace_res: List[str]


DEFAULT_LOG_TAGS = LogTags(
    reset_tags=["rst cause:1, boot mode:"],
    error_tags=["Error: ", "Exception: ", "ERROR :", "CRIT  :"],  #
    warning_tags=["WARNING:", "WARN  :"],
    success_tags=["SUCCESS", "SUCCESS~"],
    ignore_tags=[],
    trace_tags=["Traceback (most recent call last)", '   File "<stdin>", '],
    trace_res=[r"\s+File \"[\w<>.]+\", line \d+, in .*"],
)


def ipython_run(
    cmd: List[str],
    stream_out=True,
    timeout: Union[int, float] = TIMEOUT,
    shell: bool = False,
    hide_meminfo: bool = False,
    store_output: bool = True,
    log_errors: bool = True,
    tags: LogTags = DEFAULT_LOG_TAGS,
    follow: bool = True,
    # port: Optional[str] = "",
) -> Optional[
    SList
]:  # sourcery skip: assign-if-exp, boolean-if-exp-identity, reintroduce-else, remove-unnecessary-cast, use-contextlib-suppress
    """Run an external command stream the output back to the Ipython console.
    args:
        cmd: the command to run, as a list of strings
        stream_out: stream the output back to the console as it is received (per line)
        timeout: the timeout in seconds, defaults to 300 seconds (5 mins)
        shell: run the command in a shell
        hide_meminfo: hide the output of  micropython.mem_info() from the console ( it will still be available in the execution value)
        store_output: store the output of the command in the ipython kernel namespace
        log_errors: log errors to the console
        tags: a LogTags object containing the tags to detect in the output
        follow: follow the output of the command until it finishes

    returns:
        (exit_code:int, output:List[str])
        a tuple of the exit code of the command and the output of the command
    """
    # Only implement line based reading and parsing for now
    # it is, faster, easier to implement and more useful for parsing regexes
    line_based = True
    interupted = False
    forever = timeout == 0
    timeout = abs(timeout)

    all_out = []
    output = ""

    def do_output(output: str) -> bool:
        """Assess a line of output, return True if the output should be displayed"""
        # detect board reset
        if any(tag in output for tag in tags.reset_tags):
            raise RuntimeError(f"Board reset detected : {output}")
        # detect errors
        if log_errors and any(tag in output for tag in tags.error_tags):
            log.error(output)
            return False
        # detect tracebacks
        if any(tag in output for tag in tags.trace_tags) or any(
            re.match(rx, output) for rx in tags.trace_res
        ):
            log.warning(output.rstrip())
            return False
        # detect warnings
        if any(tag in output for tag in tags.warning_tags):
            log.warning(output)
        # detect success
        if any(tag in output for tag in tags.success_tags):
            log.success(output)
        # ignore some tags
        if any(tag in output for tag in tags.ignore_tags):
            return False
        # do not output the line that matched a meminfo regex
        if hide_meminfo and output and any(rx.match(output) for rx in RE_ALL):
            return False
        return True

    log.debug(f"{'line' if line_based else 'char'} based, with timeout of {timeout} seconds")
    assert isinstance(cmd, list)
    try:
        process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=False,
        )  # ,  universal_newlines=True)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Failed to start {cmd[0]}") from e

    assert process.stdout is not None
    if follow == False:
        # we do not need to follow the output of the command
        # just return
        return None
    process_timer = None
    try:
        if not forever:
            # only if a timeout was specified start a timer to kill the process
            def timed_out():
                process.kill()
                log.warning(f"Command {cmd} timed out after {timeout} seconds")

            process_timer = Timer(interval=timeout, function=timed_out)
            process_timer.start()
        while forever or (process_timer and process_timer.is_alive()):
            if line_based:
                # TODO: Ctrl-C / KeyboardInterrupt is only detected at line-end (after \n)
                output_b = process.stdout.readline()
                output = output_b.decode("utf-8", errors="ignore")
                log.trace(f"output: {output}")
                if not do_output(output):
                    continue

            else:
                output_b = process.stdout.read(1)
                # ToDo # swallow the output if it matches a regex
                output = output_b.decode("utf-8", errors="ignore")

            if output == "" and process.poll() is not None:
                # process has finished, read the rest of the output before breaking out of the loop
                break
            if output:
                all_out.append(output)
                if stream_out:
                    print(output, end="")
                output = ""

        # rearrange the output to be a list of lines
        all_out = SList("".join(all_out).splitlines())
        if store_output:
            # update the ipython kernel namespace with the output of the command
            # this is useful for storing the output of a command in a variable
            # Normally the output of a command is not stored in the kernel namespace
            ipy: InteractiveShell = get_ipython()  # type: ignore
            ipy.displayhook.fill_exec_result(all_out)
            ipy.displayhook.update_user_ns(all_out)
        return all_out
    except KeyboardInterrupt:
        # if the user presses ctrl-c or stops the cell,
        # kill the process and raise a keyboard interrupt
        with contextlib.suppress(KeyboardInterrupt):
            interupted = True
            log.warning("Keyboard interrupt detected")
            if os.name == "nt":  # Windows
                os.kill(process.pid, signal.CTRL_C_EVENT)
            else:  # Unix-like
                os.kill(process.pid, signal.SIGINT)
            # kill the process
            process.kill()
            if process_timer:
                process_timer.cancel()
            if output:
                do_output(output)

    finally:
        # ignore unraisable exceptions
        def unraisable_hook(unraisable):
            # this is very crude , but seems to be the only way
            # to catch both  weakref deletions and keyboard interrupts
            return

        sys.unraisablehook = unraisable_hook

        try:
            if process.stderr and log_errors:
                for line in process.stderr:
                    log.warning(line)
            if not interupted and process_timer and process_timer.is_alive():
                process_timer.cancel()
        except Exception:
            pass

        # TODO: interrupt the script running on the MCU
        # if interupted:
        # assert port
        #     # ignore KeyboardInterrupt
        #     try:
        #         # subprocess.run(["mpremote", "connect", port, "eval", "'stop'"])
        #         conn = Pyboard("COM15")
        #         conn.serial.write(b"\x03\x03")
        #         conn.close()
        #     except KeyboardInterrupt:
        #         pass

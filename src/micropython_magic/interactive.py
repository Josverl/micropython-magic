import asyncio
import subprocess
from dataclasses import dataclass
from threading import Timer
from typing import List, Union

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


DEFAULT_LOG_TAGS = LogTags(
    reset_tags=["rst cause:1, boot mode:"],
    error_tags=["Error: ", "Exception: ", "ERROR :", "CRIT  :"],  # "Traceback ",
    warning_tags=["WARNING:", "WARN  :"],
    success_tags=["SUCCESS", "SUCCESS~"],
    ignore_tags=['  File "<stdin>",'],
)


def ipython_run(
    cmd: Union[list[str], str],
    stream_out=True,
    timeout: Union[int, float] = TIMEOUT,
    shell: bool = False,
    hide_meminfo: bool = False,
    store_output: bool = True,
    log_errors: bool = True,
    tags: LogTags = DEFAULT_LOG_TAGS,
) -> SList:
    """Run an external command stream the output back to the Ipython console.
    args:
        cmd: the command to run, as a list of strings or a single string
        stream_out: stream the output back to the console as it is received (per line)
        timeout: the timeout in seconds, defaults to 300 seconds (5 mins)
        shell: run the command in a shell
        hide_meminfo: hide the output of  micropython.mem_info() from the console ( it will still be available in the execution value)
        store_output: store the output of the command in the ipython kernel namespace

    returns:
        (exit_code:int, output:List[str])
        a tuple of the exit code of the command and the output of the command
    """
    # Only implement line based reading and parsing for now
    # it is, faster, easier to implement and more useful for parsing regexes
    line_based = True
    forever = timeout == 0
    timeout = abs(timeout)

    all_out = []
    # if stream_out:
    #     # InteractiveShell.ast_node_interactivity = "all"
    #     pass
    log.trace(f"per char , with timeout of {timeout} seconds")
    # assert timeout > 0
    try:
        process = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )  # ,  universal_newlines=True)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Failed to start {cmd[0]}") from e

    assert process.stdout is not None

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
                output = process.stdout.readline()
                output = output.decode("utf-8", errors="ignore")
                # detect board reset
                if any(tag in output for tag in tags.reset_tags):
                    raise RuntimeError(f"Board reset detected : {output}")
                # detect errors
                if log_errors and any(tag in output for tag in tags.error_tags):
                    log.error(output)
                # detect warnings
                if any(tag in output for tag in tags.warning_tags):
                    log.warning(output)
                # detect success
                if any(tag in output for tag in tags.success_tags):
                    log.success(output)
                # ignore some tags
                if any(tag in output for tag in tags.ignore_tags):
                    continue
                # do not output the line that matched a meminfo regex
                if hide_meminfo and output and any(re.match(output) for re in RE_ALL):
                    continue
            else:
                output = process.stdout.read(1)
                output = output.decode("utf-8", errors="ignore")
                # ToDo # swallow the output if it matches a regex

            if output == "" and process.poll() is not None:
                # process has finished, read the rest of the output before breaking out of the loop
                break
            if output:
                all_out.append(output)
                if stream_out:
                    print(output, end="")

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
    finally:
        if process.stderr and log_errors:
            for line in process.stderr:
                log.warning(line)
        if process_timer and process_timer.is_alive():
            process_timer.cancel()

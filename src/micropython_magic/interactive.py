import re
from typing import List, Optional, Union

from IPython.core.getipython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.text import SList
from loguru import logger as log
from mpflash.mpremoteboard.runner import IPYTHON_LOG_TAGS, LogTags, execute

from .logger import MCUException
from .memoryinfo import RE_ALL

TIMEOUT = 300
MPY_MAGIC = "mpy_magic"  # namespace key for micropython-magic variables


# todo : pass in the to detect in the output
def do_output(output: str, tags: LogTags, log_errors=True, hide_meminfo=False) -> bool:
    """Assess a line of output, return True if the output should be displayed"""
    # detect board reset
    if any(tag in output for tag in tags.reset_tags):
        raise RuntimeError(f"Board reset detected : {output}")
    # detect errors
    if log_errors and any(tag in output for tag in tags.error_tags):
        # just log the error , rather than trying to re-raise the MCU exception
        log.error(output)
        raise MCUException(output)
        # try:
        #     raise MCUException() from eval(output)
        # except Exception:
        #     raise MCUException(output)
        # return False
    # detect tracebacks
    if any(tag in output for tag in (tags.trace_tags or [])) or any(
        re.match(rx, output) for rx in (tags.trace_res or [])
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


def ipython_run(
    cmd: List[str],
    stream_out=True,
    timeout: Union[int, float] = TIMEOUT,
    shell: bool = False,
    hide_meminfo: bool = False,
    store_output: bool = True,
    log_errors: bool = True,
    tags: Optional[LogTags] = None,
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
        A populated SList of output lines when follow is True, otherwise None.
    """
    selected_tags = tags or IPYTHON_LOG_TAGS
    error_lines: List[str] = []
    in_error = False
    cell_no = "?"
    ipy = get_ipython()
    if ipy and getattr(ipy, "execution_count", None) is not None:
        cell_no = ipy.execution_count

    def _convert_stdin_trace(line: str) -> str:
        """Replace 'File "<stdin>", line X, in <module>' with 'Cell <N>, line X.'"""
        match = re.match(r"^(\s*)File \"<stdin>\", line (\d+), in <module>", line)
        if match:
            indent, lineno = match.groups()
            return f"{indent}Cell {cell_no}, line {lineno}. "
        return line

    def handler(line: str) -> Optional[str]:
        nonlocal in_error
        if "no device found" in line or "failed to access" in line:
            raise ConnectionError(line.strip())
        converted = _convert_stdin_trace(line)
        should_output = do_output(
            line,
            selected_tags,
            log_errors=False,
            hide_meminfo=hide_meminfo,
        )

        if log_errors and any(tag in line for tag in selected_tags.error_tags):
            in_error = True
            error_lines.append(converted.rstrip("\n"))
            log.error(converted.rstrip())
        elif in_error:
            error_lines.append(converted.rstrip("\n"))

        if in_error:
            should_output = True

        if should_output:
            if stream_out:
                print(converted, end="")
            return converted
        return None

    if not follow:
        execute(
            cmd,
            timeout=timeout,
            line_handler=handler,
            log_errors=log_errors,
            follow=False,
        )
        if log_errors and error_lines:
            raise MCUException("\n".join(error_lines))
        return None

    _, captured = execute(
        cmd,
        timeout=timeout,
        line_handler=handler,
        log_errors=log_errors,
        log_warnings=True,
        ignore_tags=selected_tags.ignore_tags,
        follow=True,
    )

    if log_errors and error_lines:
        raise MCUException("\n".join(error_lines))

    if not captured:
        return None

    all_out = SList("".join(captured).splitlines())
    if store_output:
        ipy: InteractiveShell = get_ipython()  # type: ignore
        ipy.displayhook.fill_exec_result(all_out)
        ipy.displayhook.update_user_ns(all_out)
    return all_out

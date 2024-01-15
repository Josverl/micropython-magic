""" Logging utilities for the micropython-magic package. """

from __future__ import annotations

import enum
import re
import sys
from typing import TYPE_CHECKING

from loguru import logger as log

if TYPE_CHECKING:
    from loguru import Record


class LogLevel(str, enum.Enum):
    """Log level"""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


RE_MCU_TRACEBACK = r"\s+File \"([\w<>.]+)\", line (\d+), in (.*)"

# TODO : the patching of the log record is not working as part of the magic
#        module.  It works fine when run from a cell in the notebook.


def patch_MCUlog(record: Record) -> None:
    """
    Patch the log record with module, line, and function information extracted from the MCU message.

    Args:
        record (dict): The log record to be patched.
    """
    if match := re.search(RE_MCU_TRACEBACK, record["message"]):
        record["module"] = match[1]
        record["line"] = int(match[2])
        record["function"] = match[3]
    record["extra"].update({"MCU": "WIO Terminal"})


def set_log_level(llevel: str):
    # format_str = "<level>{level: <8}</level> | <cyan>{module: <18}</cyan> - <level>{message}</level>"
    # format_str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    if llevel in {"DEBUG", "TRACE"}:
        format_str = "<level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {extra} | <level>{message}</level>"
    else:
        format_str = "<level>{level: <8}</level> | <level>{message}</level>"
    log.remove()
    log.add(sys.stdout, format=format_str, level=llevel, colorize=True)
    # log.patch(patch_MCUlog)


class MCUException(Exception):
    """Exception raised for errors on the MCU."""

    pass

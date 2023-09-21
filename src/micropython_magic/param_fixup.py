"""parmeter processing for micropython_magic"""

from typing import List, Optional

from loguru import logger as log


def get_code(line: str, partial: str) -> List[str]:
    """try recover the code from the commandline after argparse has mangled it"""
    log.debug(f"{line=}, {partial=}")
    while partial not in line:
        partial = partial[:-1]
    if not partial:
        return []
    full = line[line.find(partial) :]
    log.debug(f"{full=}")
    return [full]

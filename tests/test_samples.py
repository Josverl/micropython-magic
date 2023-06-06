import asyncio
import os
import re
from pathlib import Path

import pytest
from testbook import testbook
from testbook.client import TestbookNotebookClient

# avoid RuntimeWarning: Proactor event loop does not implement add_reader
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# parameterize the test to it for each notebook in the samples folder
@pytest.mark.parametrize(
    "fname",
    [
        "samples/install.ipynb",
        "samples/board_control.ipynb",
        "samples/board_selection.ipynb",
        "samples/multi_file.ipynb",
        "samples/mem_info.ipynb",
        "samples/micropython_binary.ipynb",
        # Unstable
        # "samples/network.ipynb",
        # "samples/rp2040.ipynb",
    ],
)
def test_samples(fname):
    print(f"Executing notebook {fname}")
    with testbook(fname, execute=True) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        assert tb.code_cells_executed > 0  # at least one cell executed

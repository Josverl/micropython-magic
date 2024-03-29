import asyncio
import os
import re

import pytest
from testbook import testbook
from testbook.client import TestbookNotebookClient

# avoid RuntimeWarning: Proactor event loop does not implement add_reader
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# fixture to execute the notebook once for all tests in this file
@pytest.fixture(scope="module")
def tb():
    fname = __file__.replace("_test.py", ".ipynb")
    print(f"Executing notebook {fname}")
    with testbook(fname, execute=True) as tb:
        yield tb


def test_transfers_from_MCU(tb: TestbookNotebookClient):
    # if any of the cells raised an assertion error, this will fail the test
    assert tb.code_cells_executed > 0  # at least one cell executed

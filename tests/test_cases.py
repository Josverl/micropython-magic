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


folder = Path("tests/testbook_cases")


# parameterize the test to it for each notebook in the samples folder
@pytest.mark.parametrize(
    "fname",
    [f.as_posix() for f in folder.glob("*.ipynb")],
)
def test_case(fname):
    print(f"Executing notebook {fname}")
    with testbook(fname, execute=True) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        assert tb.code_cells_executed > 0  # at least one cell executed

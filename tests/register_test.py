import asyncio
import os
import re

import pytest
from testbook import testbook

# avoid RuntimeWarning: Proactor event loop does not implement add_reader
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# fixturte to execute the notebook once for all tests in this file
@pytest.fixture(scope="module")
def tb():
    fname = __file__.replace("_test.py", ".ipynb")
    print(f"Executing notebook {fname}")
    with testbook(fname, execute=True) as tb:
        yield tb


def test_cell_magics_registered(tb):
    cellnum = 3
    assert "MpyMagics" in tb.cell_output_text(cellnum)
    assert "'Other'" in tb.cell_output_text(cellnum)


def test_line_magics_registered(tb):
    cellnum = 4
    assert "MpyMagics" in tb.cell_output_text(cellnum)
    assert "'Other'" in tb.cell_output_text(cellnum)

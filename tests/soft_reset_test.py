import asyncio
import os
import re

import pytest
from testbook import testbook

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


def test_value_retained(tb):
    cellnum = 2
    assert "persistent" in tb.cell_output_text(cellnum)


def test_value_cleared(tb):
    cellnum = 5
    # ugly \\\' is because of the way testbook handles output
    assert "\\'foo\\' isn\\'t defined" in tb.cell_output_text(cellnum)
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


def test_load_magic(tb):
    assert "micropython_magic extension is already loaded" in tb.cell_output_text(2)


def test_list_devices(tb):
    cellnum = 3
    windows_dev = re.search(r"COM\d+", tb.cell_output_text(cellnum))
    linux_dev = re.search(r"/dev/tty\d+", tb.cell_output_text(cellnum))
    assert windows_dev or linux_dev, "No device returned"


def test_mpy_cell(tb):
    cellnum = 4
    # unmame output
    assert re.search(r"sysname=", tb.cell_output_text(cellnum))
    assert re.search(r"nodename=", tb.cell_output_text(cellnum))
    #  plain print output
    assert re.search(r"hello from", tb.cell_output_text(cellnum))


def test_list_devices_2(tb):
    devices = tb.ref("devices")
    ports = tb.ref("ports")
    assert len(devices) > 0
    assert len(devices) == len(ports)


def test_eval(tb):
    cellnum = 7
    assert tb.cell_output_text(cellnum) == "14"


def test_mpy_line(tb):
    cellnum = 8
    assert "test mpy line magic" in tb.cell_output_text(cellnum)
    cellnum = 9
    assert "test micropython line magic" in tb.cell_output_text(cellnum)


def test_mpy_cell2(tb):
    cellnum = 10
    assert "test mpy cell magic" in tb.cell_output_text(cellnum)
    cellnum = 11
    assert "test micropython cell magic" in tb.cell_output_text(cellnum)

def test_notebook_ran_ok(tb: TestbookNotebookClient):
    # if any of the cells raised an assertion error, this will fail the test
    assert tb.code_cells_executed > 0  # at least one cell executed

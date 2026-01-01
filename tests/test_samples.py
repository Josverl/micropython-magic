import asyncio
import os
import re
import subprocess
from pathlib import Path

import pytest
from IPython.core.interactiveshell import InteractiveShell
from testbook import testbook
from testbook.client import CellExecutionError, TestbookNotebookClient

from micropython_magic.interactive import TIMEOUT
from micropython_magic.mpr import IPyRemoteBoard

# avoid RuntimeWarning: Proactor event loop does not implement add_reader
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


folder = Path("samples")


# parameterize the test to it for each notebook in the samples folder
@pytest.mark.parametrize(
    "notebook_name",
    [f.as_posix() for f in folder.glob("*.ipynb")],
)
def test_samples(notebook_name: Path):
    print(f"Executing notebook {notebook_name}")
    with testbook(notebook_name, execute=True, timeout=TIMEOUT) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        assert tb.code_cells_executed > 0  # at least one cell executed
        # count the code cells in the notebook with non-empty source
        cell_count = len(
            [
                c
                for c in tb.nb["cells"]
                if c["cell_type"] == "code" and c["source"].strip()
            ]
        )
        assert tb.code_cells_executed == cell_count, (
            f"All {cell_count} code cells should have executed."
        )

import asyncio
import os
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
    "notebook_file",
    [f.as_posix() for f in folder.glob("*.ipynb")],
)
def test_case(notebook_file):
    print(f"Executing notebook {notebook_file}")
    with testbook(notebook_file, execute=True) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        print(f"Executed {tb.code_cells_executed} cells")
        assert tb.code_cells_executed > 0  # at least one cell executed
        # count the code cells in the notebook with non-empty source
        cell_count = len([c for c in tb.nb["cells"] if c["cell_type"] == "code" and c["source"].strip()])
        assert tb.code_cells_executed == cell_count, f"All {cell_count} code cells should have executed."

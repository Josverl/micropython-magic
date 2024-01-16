import asyncio
import os
import re
import subprocess
from pathlib import Path

import pytest
from IPython.core.interactiveshell import InteractiveShell
from testbook import testbook
from testbook.client import TestbookNotebookClient

from micropython_magic.interactive import TIMEOUT
from micropython_magic.mpr import MPRemote2
from micropython_magic.script_access import path_for_script

# avoid RuntimeWarning: Proactor event loop does not implement add_reader
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


folder = Path("samples")


# parameterize the test to it for each notebook in the samples folder
@pytest.mark.parametrize(
    "fname",
    [f.as_posix() for f in folder.glob("*.ipynb")],
)
def test_samples(fname: Path):
    print(f"Executing notebook {fname}")
    # Check for correct port before running the test
    if "_" in Path(fname).stem:
        port = Path(fname).stem.split("_")[-1]
        if port in ["samd", "rp2"]:
            # check if a device with this port is connected
            cmd = ["mpremote", "run", str(path_for_script("fw_info.py"))]
            output = subprocess.check_output(cmd, timeout=TIMEOUT)

            if f"'port': '{port}'," not in output.decode("utf-8"):
                pytest.skip()(f"Test requires a {port} device connected")

    with testbook(fname, execute=True, timeout=TIMEOUT) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        assert tb.code_cells_executed > 0  # at least one cell executed

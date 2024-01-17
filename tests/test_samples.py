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
from micropython_magic.mpr import MPRemote2
from micropython_magic.script_access import path_for_script

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
    # Check for correct port before running the test
    if "_" in Path(notebook_name).stem:
        port = Path(notebook_name).stem.split("_")[-1]
        if port in ["samd", "rp2"]:
            # check if a device with this port is connected
            cmd = ["mpremote", "run", str(path_for_script("fw_info.py"))]
            output = subprocess.check_output(cmd, timeout=TIMEOUT)

            if f"'port': '{port}'," not in output.decode("utf-8"):
                pytest.xfail(f"Test requires a {port} device connected")
        if port in ["wokwi", "rfc2217"]:
            remoteport = "rfc2217://localhost:4000"
            cmd = ["mpremote", "connect", remoteport, "run", str(path_for_script("fw_info.py"))]
            try:
                output = subprocess.check_output(cmd, timeout=TIMEOUT)
                if "'family': 'micropython'" not in output.decode("utf-8"):
                    pytest.xfail(f"Test requires a device connected via {remoteport}")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pytest.xfail(f"Test requires a device connected via {remoteport}")

    with testbook(notebook_name, execute=True, timeout=TIMEOUT) as tb:
        # if any of the cells raised an assertion error, this will fail the test
        assert tb.code_cells_executed > 0  # at least one cell executed
        # count the code cells in the notebook with non-empty source
        cell_count = len([c for c in tb.nb["cells"] if c["cell_type"] == "code" and c["source"].strip()])
        assert tb.code_cells_executed == cell_count, f"All {cell_count} code cells should have executed."

import re

import pytest

from micropython_magic.logger import patch_MCUlog


@pytest.mark.parametrize(
    "message, module, line , function",
    [
        ("""  File "<stdin>", line 11, in <module>""", "<stdin>", 11, "<module>"),
        ("""  File "petstore.py", line 22, in is_stiff""", "petstore.py", 22, "is_stiff"),
    ],
)
def test_patch_MCUlog(message: str, module: str, line: int, function: str):
    record = {"message": message, "extra": {}}
    patch_MCUlog(record)  # type: ignore
    assert record["module"] == module
    assert record["line"] == line
    assert record["function"] == function
    assert record["extra"]["MCU"] == "WIO Terminal"

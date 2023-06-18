import pytest

from micropython_magic.magic_transformer import comment_magic_transformer


@pytest.mark.parametrize(
    "input, expected",
    [
        ["%%micropython", "%%micropython"],
        ["# %%micropython", "%%micropython"],
        ["#! %%micropython", "%%micropython"],
        ["#!%%micropython", "%%micropython"],
        ["#!  %%micropython", "%%micropython"],
        ["#!\t%%micropython", "%%micropython"],
        ["#!\t\t%%micropython", "%%micropython"],
        ["# ! %%micropython", "%%micropython"],
        ["# !%%micropython", "%%micropython"],
    ],
)
def test_comment_magic_transformer(input, expected):
    assert comment_magic_transformer([input]) == [expected]

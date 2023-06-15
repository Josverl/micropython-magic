"""
Transforms a cell with a commented cell magic into a cell without the comment, but with the %%celmagic.

`# %%micropython --> %%micropython`
This allows Pylance to only see python code and not the magic, 
which would otherwise confuse it, and cause it to be disabled.
"""
import re

re_comment_magic = r"#\s?(!)?\s?(%%(micropython|python|mypy|script))"  # matches `# %%micropython` or `#!%%micropython` with optional spaces in between
subst = "\\g<1>"


def comment_magic_transformer(lines: list[str]):
    """
    Transforms a cell with a commented cell magic into a cell without the comment, but with the %%celmagic.
    """
    if "%%" not in lines[0]:
        return lines
    return [re.sub(re_comment_magic, subst, lines[0])] + lines[1:]

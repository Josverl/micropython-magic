"""MicroPython magics for Jupyter Notebooks and JupyterLabs"""
__version__ = "0.7.0"
__author__ = "Jos Verlinde"


from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log

from .magic_transformer import comment_magic_transformer
from .octarine import MicropythonMagic

# from .exp_magics import ExpMagics


def load_ipython_extension(ipython: InteractiveShell):
    # register the input transformer to allow %%cell_magics in comments
    ipython.input_transformers_cleanup.append(comment_magic_transformer)
    # register the magics
    ipython.register_magics(MicropythonMagic)
    # ipython.register_magics(ExpMagics)


def unload_ipython_extension(ipython: InteractiveShell):
    # unregister the magics, allows to unload / reload the extension
    # ipython.magics_manager.magics["cell"].pop("mpy", None)
    # TODO
    pass

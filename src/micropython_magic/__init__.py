"""MicroPython magics for Jupyter Notebooks and Labs"""
__version__ = "0.2.0"
__author__ = "Jos Verlinde"


import IPython.core.magic as ipym
from IPython.core.events import available_events
from IPython.core.interactiveshell import InteractiveShell
from loguru import logger as log

from .magic_transformer import comment_magic_transformer
from .octarine import MpyMagics
from .test_magics import TestMagics


def load_ipython_extension(ipython: InteractiveShell):
    # register the magics and transformer
    ipython.register_magics(MpyMagics)
    ipython.input_transformers_cleanup.append(comment_magic_transformer)
    ipython.register_magics(TestMagics)


def unload_ipython_extension(ipython: InteractiveShell):
    # unregister the magics, allows to unload / reload the extension
    # ipython.magics_manager.magics["cell"].pop("mpy", None)
    # TODO 
    pass

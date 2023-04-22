"""An MicroPython magic for Jupyter Notebooks"""
__version__ = "0.1.0"

from warnings import warn

import IPython.core.magic as ipym
from IPython.core.interactiveshell import InteractiveShell

from .octarine import MpyMagics


def load_ipython_extension(ipython: InteractiveShell):
    # register the magics
    ipython.register_magics(MpyMagics)

    # register aliases - now directly defined in the class
    # if ipython.magics_manager and isinstance(ipython.magics_manager, ipym.MagicsManager):
    #     ipython.magics_manager.register_alias("micropython", "mpy", magic_kind="cell")
    #     ipython.magics_manager.register_alias("micropython", "mpy", magic_kind="line")
    # else:
    #     warn("No MagicsManager was found")


def unload_ipython_extension(ipython: InteractiveShell):
    # unregister the magics, allows to unload / reload the extension
    pass

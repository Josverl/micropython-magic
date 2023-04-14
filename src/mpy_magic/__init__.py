"""An MicroPython magic for Jupyter Notebooks"""
__version__ = '0.1.0'

from mpy_magic.magic import MpyMagics
import IPython.core.magic as ipym
from IPython.core.interactiveshell import InteractiveShell


def load_ipython_extension(ipython: InteractiveShell):
    # register the magics
    ipython.register_magics(MpyMagics)
    # register aliases
    if ipython.magics_manager and isinstance(ipython.magics_manager, ipym.MagicsManager):
        ipython.magics_manager.register_alias("mpr", "micropython")
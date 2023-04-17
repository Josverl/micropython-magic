"""
Run micropython code from a a notebook
 - connects to the first MCU connected on serial
 - uses resume to avoid soft-resetting the MCU
"""
# https://ipython.readthedocs.io/en/stable/config/custommagics.html
# https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.magic.html#IPython.core.magic.Magics
# https://nbviewer.org/github/rossant/ipython-minibook/blob/master/chapter6/602-cpp.ipynb


from typing import Optional
from warnings import warn

import IPython.core.magic as ipym
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.text import SList

# class ListOutput(object):
#     def __init__(self, slist: SList):
#         self.slist = slist
#     def _repr_markdown_(self):
#         return "\n".join([f" - {s}" for s in self.slist])
#     def __repr__(self):
#         return list(self.slist.list)


@ipym.magics_class
class MpyMagics(ipym.Magics):
    """A class to define the magic functions for Micropython."""

    def __init__(self, shell:InteractiveShell):
        # first call the parent constructor
        super(MpyMagics, self).__init__(shell)
        self.shell : InteractiveShell
        self.port: str = "" # by default connect to the first device
        self.resume = True # by default resume the device to maintain state

    @property
    def cmd_prefix(self):
        """mpremote command prefix including poert and resume according to options"""
        return f"mpremote {self.connect_to}{'resume' if self.resume else ''} "

    @property
    def connect_to(self):
        "creates connect to strign if port is specified"
        return f"connect {self.port} " if self.port else ""


    @ipym.line_magic("list_devices")
    def list_devices(self, line:str = ""):
        if line:
            print("no arguments expected")
        exec_cmd = "mpremote resume connect list"
        output= self.shell.getoutput(exec_cmd)
        return output.list

    @ipym.line_magic("connect")
    def connect(self, line: Optional[str]):
        output = SList()
        if not line:
            # TODO: connect to the first/default
            print("no device")
        else:
            self.port = line.strip()
            # exec_cmd =self.cmd_prefix +  f"mpremote connect {self.port} resume eval \"'Connected to MCU on port {self.port}.'\""
            exec_cmd = f"""{self.cmd_prefix}eval \"'Connected to MCU on port {self.port}.'\""""
            print(exec_cmd)
            output= self.shell.getoutput(exec_cmd)
        return output

    @ipym.line_cell_magic("mpy")
    def mpy(self, line: str, cell: Optional[str] = None):
        """Run Micropython code on an attached device using mpremote."""
        # Define the source and executable filenames.
        output = SList()
        if cell:
            source_filename = "temp.py"
            with open(source_filename, "w") as f:
                f.write(cell)
            # copy the file to the device
            copy_cmd = self.cmd_prefix + "cp {0:s} :".format(source_filename)
            exec_cmd = self.cmd_prefix + "exec \"exec( open('temp.py').read() , globals() )\""
            _ = self.shell.getoutput(copy_cmd)
            print(exec_cmd)
            output= self.shell.getoutput(exec_cmd)
        elif line:
            exec_cmd = f'{self.cmd_prefix}exec "{line}"'
            # print(exec_cmd)
            output= self.shell.getoutput(exec_cmd)
            self.output = output
        else:
            print("Error: Please specify some MicroPython code to execute")
        #
        return output.list

    @ipym.line_magic("exec")
    def exec(self, line: str):
        """Run Micropython code on an attached device using mpremote."""
        # Define the source and executable filenames.
        exec_cmd = f'{self.cmd_prefix}exec "{line}"'
        # print(exec_cmd)
        output= self.shell.getoutput(exec_cmd)
        self.output = output
        return output

    @ipym.line_magic("eval")
    def eval(self, line: str):
        """Run Micropython code on an attached device using mpremote."""
        # Define the source and executable filenames.
        cmd = f'{self.cmd_prefix}eval "{line}"'
        # print(cmd)
        output= self.shell.getoutput(cmd)
        self.output = output
        return output


    @ipym.line_magic("mpremote")
    def mpremote(self, line: str):
        """Run a mpremote command with the commandline options"""
        cmd = f'mpremote "{line}"'
        output= self.shell.getoutput(cmd)
        self.output = output
        return output




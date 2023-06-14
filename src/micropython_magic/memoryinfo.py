from __future__ import annotations

import re
import time
from dataclasses import InitVar, dataclass, field
from typing import Any, Iterable, List, Optional, Union

from colorama import Back, Fore, Style
from IPython.display import display, update_display
from IPython.lib.pretty import CallExpression, PrettyPrinter, pprint, pretty

re_head_1 = re.compile(r"GC: total: (\d+), used: (\d+), free: (\d+)")
re_head_2 = re.compile(r" No. of 1-blocks: (\d+), 2-blocks: (\d+), max blk sz: (\d+), max free sz: (\d+)")
re_stack = re.compile(r"stack: (\d+) out of (\d+)")
re_block = re.compile(r"^[0-9a-fA-F]*\: (.*)", flags=re.MULTILINE)
re_free = re.compile(r"\((.*) lines all free\)")

COL_WIDTH = 64


def info_str(mem_info) -> str:
    """convert the output of a %mpy command to a string that can be processed
    Accepts:
        - from SList
        - from list[str]
        - from str
        = PrettyPrint
    """
    if "data" in dir(mem_info):
        mem_info = mem_info.data

    if issubclass(type(mem_info), list):
        s = "\n".join(mem_info)
    elif issubclass(type(mem_info), str):
        s = str(mem_info)

    return s


@dataclass
class MemoryInfo:
    mmap: InitVar[Any] = ""
    name: str = ""
    datetime = None
    """Memory map"""
    rainbow: bool = False
    """Use Rainbow colors"""
    total: int = 0
    """Total memory"""
    used: int = 0
    """Used memory"""
    free: int = 0
    """Free memory"""
    one_blocks: int = 0
    """Number of 1-blocks"""
    two_blocks: int = 0
    """Number of 2-blocks"""
    max_block_size: int = 0
    """Largest available block"""
    max_free_size: int = 0
    """largest free block"""
    stack_used: int = 0
    """Stack used"""
    stack_total: int = 0
    """Stack total"""
    color = Fore.WHITE
    parent: MemoryInfoList = None
    show_free: bool = False

    def __post_init__(self, mmap: Any):
        if mmap:
            # self.mmap = info_str(mmap)
            self.parse(info_str(mmap))

    @property
    def columns(self):
        return self.parent.columns if self.parent else 3  # fixme

    @property
    def diff_with(self):
        return self.parent.diff_with if self.parent else None

    def _header(self):
        head = f"{Fore.WHITE}{Back.BLACK}"
        if self.diff_with:
            head += f"{self.parent.data[self.diff_with[0]].name} --> {self.name}\n"
        elif self.name:
            head += f"{self.name}\n"
        head += (
            f"Stack used:  0x{self.stack_used:04_x} of Total: 0x{self.stack_total:04x}  pct free: {(self.stack_total - self.stack_used)/self.stack_total if self.stack_total else 0:4.1%}\n"
            f"Memory used: 0x{self.used:08_x} of Total: 0x{self.total:08_x}  free: 0x{self.free:08_x} pct free: {(self.free/self.total)if self.total else 0:4.1%}\n"
            f"1-Blocks:       {self.one_blocks:5}  2-Blocks:      {self.two_blocks:5}\n"
            f"Max Block size: {self.max_block_size:5}  Max Free size: {self.max_free_size:5}\n"
        )
        return head

    def _repr_pretty_(self, pp, cycle=False):
        "print a colored version of the memory map"
        if cycle:
            pp.text("MemoryInfo(...)")
            return
        width = COL_WIDTH * self.columns
        text = self._header()
        color = Fore.WHITE

        for i in range(len(self.mmap)):
            # '=' keeps the same color
            if self.mmap[i] != "=":
                color = self.pcolor(self.mmap[i])
            text += color + self.mmap[i]
            # columns
            if (i + 1) % COL_WIDTH == 0:
                text += f"{Style.RESET_ALL} "
            # rows
            if (i + 1) % width == 0:
                text += Style.RESET_ALL + "\n"
        # now pretty print the memory map
        pp.text(text)

    def _repr_pretty_diff_(self, pp: PrettyPrinter, cycle, other: "MemoryInfo"):
        """print a colored version of a differential memory map
        the  maps list should contain the 2 memory maps to compare,
        indexes are in self.diff_with(A,B)
        """
        if cycle:
            pp.text("MemoryInfo(...)")
        width = COL_WIDTH * self.columns
        if not other:
            pp.text("MemoryInfo(...)")
            return
        pp.text(self._header())
        text = ""
        color = Fore.WHITE
        for i in range(len(self.mmap)):
            # '=' keeps the same color
            current = self.mmap[i] if i < len(self.mmap) else ""
            other_ = other.mmap[i] if i < len(other.mmap) else ""
            color = self.diff_color(current, other_)
            text += color + self.mmap[i]
            # columns
            if (i + 1) % COL_WIDTH == 0:
                text += f"{Style.RESET_ALL} "
            # rows
            if (i + 1) % width == 0:
                text += Style.RESET_ALL
                pp.text(text)
                pp.breakable("\n")
                text = ""
        # remainder
        pp.text(text)

    def diff_color(self, this: str, other: str):
        "Colors for the diff view"
        # BG = Filled for the changes ( Green for freed, Red for allocated)
        # FG = White for the changed, Magenta for the same
        changed = this != other
        freed = changed and this == "."
        allocated = changed and this != "."

        fg = Fore.BLUE
        bg = Back.BLACK
        if not changed:
            # same
            fg = Fore.MAGENTA
            bg = Back.BLACK

        else:
            fg = Fore.WHITE
            if freed:
                # freed
                bg = Back.GREEN
            elif allocated:
                # allocated
                bg = Back.RED
        return fg + bg

    def pcolor(self, c: str):
        # ====== =================
        # Symbol Meaning
        # ====== =================
        #    .   free block
        #    h   head block
        #    =   tail block
        #    m   marked head block
        #    T   tuple
        #    L   list
        #    D   dict
        #    F   float
        #    B   byte code
        #    M   module
        #    S   string or bytes
        #    A   bytearray
        # ====== =================
        BG_COLORS = [Back.BLUE, Back.RED, Back.MAGENTA, Back.CYAN]
        fg = Fore.BLACK
        bg = Back.RED
        if c == ".":
            fg = Fore.GREEN
            bg = Back.GREEN
        elif c.isupper():
            fg = Fore.WHITE
        else:
            fg = Fore.BLACK
        if c in "TSLDFABh":
            if self.rainbow:
                bg = BG_COLORS[self._color_num]
                self._color_num = (self._color_num + 1) % len(BG_COLORS)
            else:
                bg = Back.RED
        elif c == "M":
            fg = Fore.BLACK
            bg = Back.CYAN
        return fg + bg

    def parse(self, mem_info: Union[str, List[str]], name: Optional[str] = ""):
        """Parse the memory map store it in this MemoryInfo object"""
        # sourcery skip: use-named-expression
        if not isinstance(mem_info, str):
            mem_info = info_str(mem_info)

        match_head_1 = re_head_1.search(mem_info)
        if not match_head_1:
            raise ValueError("Not recognized as a valid Micropython memory info")
        self.total, self.used, self.free = [int(x) for x in match_head_1.groups()]
        # find the used blocks
        match_head_2 = re_head_2.search(mem_info)
        if match_head_2:
            self.one_blocks, self.two_blocks, self.max_block_size, self.max_free_size = [
                int(x) for x in match_head_2.groups()
            ]
        match_stack = re_stack.search(mem_info)
        if match_stack:
            self.stack_used, self.stack_total = [int(x) for x in match_stack.groups()]
        _raw_map = re_block.findall(mem_info)
        if self.show_free:
            match_free = re_free.search(mem_info)
            if match_free:
                # there can be multiple marks of free lines, so lets try to find them all
                # break the map into lines and find the free lines
                lines = mem_info.split("\n")
                l1 = 0
                for line in lines:
                    match_map = re_block.match(line)
                    if match_map:
                        l1 += 1
                        continue
                    match_free = re_free.search(line)
                    if match_free:
                        lines_free = int(match_free.groups(0)[0])
                        # insert the free lines in one go
                        _raw_map[l1:l1] = ["." * 64] * lines_free
                        l1 += lines_free
        self.mmap = "".join(_raw_map)
        return self

    def __sub__(self, other: MemoryInfo):
        """Subtract the other memory map from this one"""
        if not other:
            return ValueError("Other MemoryInfo object is empty")
        # new MemoryInfo , with just the diff of these two
        diff = MemoryInfoList([other, self])
        diff.diff_with = (0, -1)
        return diff


# -------------------------------------------------------------------------------------------
# MemoryInfoList
# -------------------------------------------------------------------------------------------


from collections import UserList


class MemoryInfoList(UserList):
    def __init__(self, iterable: Iterable = None, *, show_free: bool = False, rainbow: bool = False, columns: int = 4):
        self.show_free: bool = show_free  # show the free blocks - default True - currently ignored by code
        self.rainbow: bool = rainbow  # color the blocks in rainbow colors
        self.columns: int = columns

        self.diff_with: tuple = ()  # (other, current)
        if not iterable:
            iterable = []
        super().__init__(self._validate_mi(item) for item in iterable)

    def __setitem__(self, index, item):
        self.data[index] = self._validate_mi(item)

    def insert(self, index, item, name: Optional[str] = ""):
        self.data.insert(index, self._validate_mi(item, name=name))

    def append(self, item, name: Optional[str] = ""):
        self.data.append(self._validate_mi(item, name=name))

    def extend(self, other):
        if isinstance(other, type(self)):
            self.data.extend(other)
        else:
            self.data.extend(self._validate_mi(item) for item in other)

    def _validate_mi(self, value, name: Optional[str] = ""):
        # sourcery skip: extract-duplicate-method
        "Check if this is a memory Info object or can be converted to one"
        if isinstance(value, MemoryInfo):
            # no conversion needed
            value.parent = self
            if name:
                value.name = name
            return value
        if issubclass(type(value), list):
            # convert list to to a string with newlines
            value = "\n".join(value)
            info = MemoryInfo(value, name)
            info.parent = self
            return info
        elif issubclass(type(value), str):
            info = MemoryInfo(value, name)
            info.parent = self
            return info
        else:
            raise TypeError(f"MemoryInfo object or string value expected, got {type(value).__name__}")

    def play(self, start=None, end=None, step=1, delay=0.1, did=None):
        """Play the memory map as a movie, with a diff of n - 1"""
        self.diff_with = ()
        if not did:
            did = display(self, display_id=True)
        else:
            update_display(self, display_id=did.display_id)
        time.sleep(delay)
        # loop over the memory info objects - or a slice of them
        for idx, mi in enumerate(self[slice(start, end, step)]):
            self.diff_with = (idx - step, idx)
            update_display(self, display_id=did.display_id)
            time.sleep(delay)

    def _repr_pretty_(self, pp, cycle):
        """print a colored version of a memory map"""
        # Jupyter Pretty Printer
        self._color_num = 0
        if len(self.data):
            if self.diff_with and len(self.data) > 1:
                return self._repr_pretty_diff_(pp, cycle)
            else:
                return self.data[-1]._repr_pretty_(pp, cycle)

    def _repr_pretty_diff_(self, pp, cycle):
        """print a colored version of a differential memory map
        the  maps list should contain the 2 memory maps to compare,
        indexes are in self.diff_with(A,[B])
        # Jupyter Pretty Printer for diff comparisons of two maps
        """
        try:
            other_map = self.data[self.diff_with[0]]
            if len(self.diff_with) > 1:
                cur_map = self.data[self.diff_with[1]]
            else:
                cur_map = self.data[self._current]
        except IndexError:
            text = f"{Fore.RED}Not enough memory maps to compare - need 2, got {len(self.data)}"
            pp.text(text)
            return
        return cur_map._repr_pretty_diff_(pp, cycle, other=other_map)

    def map(self, action):
        return type(self)(action(item) for item in self)

    def filter(self, predicate):
        return type(self)(item for item in self if predicate(item))

    def for_each(self, func):
        for item in self:
            func(item)

    def parse_log(
        self,
        log_text: list[str],
    ) -> MemoryInfoList:
        """Parse a log file which may contain memoryinfo maps and append these to a MemoryInfoList"""

        # setup terminators
        RE_MEM_INFO_START = r"\*\*\* Memory info (.*) \*\*\*"
        MEM_INFO_END = "*********************"

        # init
        in_mem_info = False
        nr = 0
        mem_info_log = []
        # find the meory_info lines in the (console) log output
        while nr < len(log_text):
            # if the regex matches, start a new map
            if match := re.match(RE_MEM_INFO_START, log_text[nr]):
                # start a new map
                mem_info_log = []
                in_mem_info = True
                # get the name of the map
                map_name = match[1]
            if in_mem_info:
                if log_text[nr].startswith(MEM_INFO_END):
                    # At end of the map,
                    in_mem_info = False
                    # add it to the MemoryInfoList
                    if len(mem_info_log) > 0:
                        self.append(mem_info_log, name=map_name)
                else:
                    # add a line to the map
                    mem_info_log.append(log_text[nr])
            nr += 1
        return self

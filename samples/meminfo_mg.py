import copy
import re
from dataclasses import InitVar, dataclass, field
from typing import List, Optional, Union

from colorama import Back, Fore, Style
from IPython.lib.pretty import CallExpression, PrettyPrinter, pprint, pretty

re_head_1 = re.compile(r"GC: total: (\d+), used: (\d+), free: (\d+)")
re_head_2 = re.compile(r" No. of 1-blocks: (\d+), 2-blocks: (\d+), max blk sz: (\d+), max free sz: (\d+)")
re_stack = re.compile(r"stack: (\d+) out of (\d+)")
re_block = re.compile(r"^[0-9a-fA-F]*\: (.*)", flags=re.MULTILINE)
re_free = re.compile(r"\((.*) lines all free\)")

COL_WIDTH = 64


@dataclass
class Info:
    mmap: str = ""
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
    parent: "MemoryInfo" = None

    def __post_init__(self):
        if self.mmap:
            self.parse(self.mmap)

    def _header(self):
        head = f"{Fore.WHITE}{Back.BLACK}"
        if self.parent.diff_with:
            head += f"{self.parent.memory_maps[self.parent.diff_with[0]].name} --> {self.name}\n"
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
        width = COL_WIDTH * self.parent.columns
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

    def _repr_pretty_diff_(self, pp: PrettyPrinter, cycle, other: "Info"):
        """print a colored version of a differential memory map
        the  maps list should contain the 2 memory maps to compare,
        indexes are in self.diff_with(A,B)
        """
        if cycle:
            pp.text("Info(...)")
        width = COL_WIDTH * self.parent.columns
        if not other:
            pp.text("Info(...)")
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

    def parse(self, mem_info: Union[str, List[str]], name: Optional[str] = "", show_free=True):
        """Parse the memory map store it in this Info object"""
        # sourcery skip: use-named-expression

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
        if show_free:
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

    def __sub__(self, other: "Info"):
        """Subtract the other memory map from this one"""
        if not other:
            return ValueError("Other Info object is empty")
        # new MemoryInfo , with just the diff of these two
        diff = MemoryInfoList()
        diff.append(other)
        diff.append(self)
        diff.diff_with = (0, -1)
        return diff


@dataclass
class MemoryInfoList:
    """MicroPython Visual Memory Information Map"""

    show_free: bool = True
    rainbow: bool = False
    diff_with: tuple = ()
    "Tuple of Info indexes to compare (Other,Current)"
    columns: int = 4
    memory_maps: List["Info"] = field(default_factory=list)
    memory_info: InitVar[Union[str, List[str]] | None] = None
    _current = -1

    def __post_init__(self, memory_info):
        self.columns = max(1, self.columns)
        self._color_num = 0
        if memory_info:
            self.append(memory_info, self.name)

    def append(
        self,
        mem_info: Union[str, List[str]],
        name: Optional[str] = "",
    ):
        """Append a new memory map"""
        if issubclass(type(mem_info), list):
            mem_info = "\n".join(mem_info)
            info = Info(mem_info, name)
        elif issubclass(type(mem_info), str):
            mem_info = str(mem_info)
            info = Info(mem_info, name)
        elif issubclass(type(mem_info), Info):
            info = mem_info
        else:
            raise ValueError("Invalid type for mem_info")
        info.parent = self
        self.memory_maps.append(info)

    def _repr_pretty_(self, pp, cycle):
        self._color_num = 0
        if len(self.memory_maps):
            if self.diff_with and len(self.memory_maps) > 1:
                return self._repr_pretty_diff_(pp, cycle)
            else:
                return self.memory_maps[self._current]._repr_pretty_(pp, cycle)

    def _repr_pretty_diff_(self, pp, cycle):
        """print a colored version of a differential memory map
        the  maps list should contain the 2 memory maps to compare,
        indexes are in self.diff_with(A,[B])
        """
        try:
            other_map = self.memory_maps[self.diff_with[0]]
            if len(self.diff_with) > 1:
                cur_map = self.memory_maps[self.diff_with[1]]
            else:
                cur_map = self.memory_maps[self._current]
        except IndexError:
            text = f"{Fore.RED}Not enough memory maps to compare - need 2, got {len(self.memory_maps)}"
            pp.text(text)
            return
        return cur_map._repr_pretty_diff_(pp, cycle, other=other_map)

    # promote properties from the last memory map
    @property
    def used(self):
        return self.memory_maps[self._current].used

    @property
    def total(self):
        return self.memory_maps[self._current].total

    @property
    def free(self):
        return self.memory_maps[self._current].free

    @property
    def total(self):
        return self.memory_maps[self._current].total

    @property
    def one_blocks(self):
        return self.memory_maps[self._current].one_blocks

    @property
    def two_blocks(self):
        return self.memory_maps[self._current].two_blocks

    @property
    def max_block_size(self):
        return self.memory_maps[self._current].max_block_size

    @property
    def max_free_size(self):
        return self.memory_maps[self._current].max_free_size

    @property
    def stack_used(self):
        return self.memory_maps[self._current].stack_used

    @property
    def stack_total(self):
        return self.memory_maps[self._current].stack_total

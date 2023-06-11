import copy
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

from colorama import Back, Fore, Style

re_head_1 = re.compile(r"GC: total: (\d+), used: (\d+), free: (\d+)")
re_head_2 = re.compile(r" No. of 1-blocks: (\d+), 2-blocks: (\d+), max blk sz: (\d+), max free sz: (\d+)")
re_stack = re.compile(r"stack: (\d+) out of (\d+)")
re_block = re.compile(r"^[0-9a-fA-F]*\: (.*)", flags=re.MULTILINE)
re_free = re.compile(r"\((.*) lines all free\)")

COL_WIDTH = 64


@dataclass
class MemoryInfo:
    """MicroPython Visual Memory Information Map"""

    show_free: bool = True
    rainbow: bool = False
    diff_with: tuple = ()
    "Tuple of MemoryInfo.Info indexes to compare (Other,Current)"
    columns: int = 4
    memory_maps: List["MemoryInfo.Info"] = field(default_factory=list)

    @dataclass
    class Info:
        name: str = ""
        datetime = None
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
        mmap: str = ""
        """Memory map"""
        color = Fore.WHITE
        rainbow: bool = False

        def _header(self):
            return (
                f"{Fore.WHITE}{Back.BLACK}"
                f"{self.name}\n"
                f"Stack used:  0x{self.stack_used:04_x} of Total: 0x{self.stack_total:04x}  pct free: {(self.stack_total - self.stack_used)/self.stack_total if self.stack_total else 0:4.1%}\n"
                f"Memory used: 0x{self.used:08_x} of Total: 0x{self.total:08_x}  free: 0x{self.free:08_x} pct free: {(self.free/self.total)if self.total else 0:4.1%}\n"
                f"1-Blocks:       {self.one_blocks:5}  2-Blocks:      {self.two_blocks:5}\n"
                f"Max Block size: {self.max_block_size:5}  Max Free size: {self.max_free_size:5}\n"
            )

        def _repr_pretty_(self, pp, cycle=False):
            "print a colored version of the memory map"
            if cycle:
                pp.text("MemoryInfo(...)")
                return
            width = COL_WIDTH * 4  #  self.columns
            text = self._header()
            color = Fore.WHITE

            for i in range(len(self.mmap)):
                # '=' keeps the same color
                if self.mmap[i] != "=":
                    color = self.color(self.mmap[i])
                text += color + self.mmap[i]
                # columns
                if (i + 1) % COL_WIDTH == 0:
                    text += f"{Style.RESET_ALL} "
                # rows
                if (i + 1) % width == 0:
                    text += Style.RESET_ALL + "\n"
            # now pretty print the memory map
            pp.text(text)

        def color(self, c: str):
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

    def __init__(
        self,
        mem_info: Optional[Union[str, List[str]]] = "",
        name: Optional[str] = "",
        show_free: bool = False,
        columns: int = 4,
        rainbow: bool = False,
    ):
        """Parse the memory map"""
        self.columns = max(1, columns)
        self.rainbow = rainbow
        self.show_free = show_free
        self._color_num = 0
        self.memory_maps = []
        if mem_info:
            self.append(mem_info, name)

    def append(
        self,
        mem_info: Union[str, List[str]],
        name: Optional[str] = "",
    ):
        """Append a new memory map"""
        if issubclass(type(mem_info), list):
            mem_info = "\n".join(mem_info)
            info = self.parse(mem_info, name)
        elif issubclass(type(mem_info), str):
            mem_info = str(mem_info)
            info = self.parse(mem_info, name)

        self.memory_maps.append(info)

    def parse(self, mem_info: Union[str, List[str]], name: Optional[str] = ""):
        """Parse the memory map and return a MemoryInfo.Info object"""
        # sourcery skip: use-named-expression
        info = self.Info(name=name)

        match_head_1 = re_head_1.search(mem_info)
        if not match_head_1:
            raise ValueError("Not recognized as a valid Micropython memory info")
        info.total, info.used, info.free = [int(x) for x in match_head_1.groups()]
        # find the used blocks
        match_head_2 = re_head_2.search(mem_info)
        if match_head_2:
            info.one_blocks, info.two_blocks, info.max_block_size, info.max_free_size = [
                int(x) for x in match_head_2.groups()
            ]
        match_stack = re_stack.search(mem_info)
        if match_stack:
            info.stack_used, info.stack_total = [int(x) for x in match_stack.groups()]
        _raw_map = re_block.findall(mem_info)
        match_free = re_free.search(mem_info)
        if self.show_free and match_free:
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
        info.mmap = "".join(_raw_map)
        return info

    def _repr_pretty_(self, pp, cycle):
        self._color_num = 0
        if len(self.memory_maps):
            if self.diff_with and len(self.memory_maps) > 1:
                return self._repr_pretty_diff_(pp, cycle)
            else:
                return self.memory_maps[-1]._repr_pretty_(pp, cycle)

    def _repr_pretty_memmap_(self, pp, cycle):
        "print a colored version of the memory map"
        width = COL_WIDTH * self.columns
        FIRST = 0
        LAST = -1
        cur_map = self.memory_maps[LAST].mmap

        text = self._header(self.memory_maps[LAST])

        color = Fore.WHITE

        for i in range(len(cur_map)):
            # '=' keeps the same color
            if cur_map[i] != "=":
                color = self.color(cur_map[i])
            text += color + cur_map[i]
            # columns
            if (i + 1) % COL_WIDTH == 0:
                text += f"{Style.RESET_ALL} "
            # rows
            if (i + 1) % width == 0:
                text += Style.RESET_ALL + "\n"
        # now pretty print the memory map
        pp.text(text)

    def display_pretty(self, index=-1):
        """Display the memory map in a pretty way"""
        print(self)

    def _repr_pretty_diff_(self, pp, cycle):
        """print a colored version of a differential memory map
        the  maps list should contain the 2 memory maps to compare,
        indexes are in self.diff_with(A,B)
        """
        width = COL_WIDTH * self.columns
        try:
            OTHER = self.diff_with[0]
            CURRENT = self.diff_with[1]

            other_map = self.memory_maps[OTHER].mmap
            cur_map = self.memory_maps[CURRENT].mmap
        except IndexError:
            text = f"{Fore.RED}Not enough memory maps to compare - need 2, got {len(self.memory_maps)}"
            pp.text(text)
            return
        text = self.memory_maps[CURRENT]._header()
        color = Fore.WHITE
        for i in range(len(cur_map)):
            # '=' keeps the same color
            current = cur_map[i] if i < len(cur_map) else ""
            other = other_map[i] if i < len(other_map) else ""
            color = self.diff_color(current, other)
            text += color + cur_map[i]
            # columns
            if (i + 1) % COL_WIDTH == 0:
                text += f"{Style.RESET_ALL} "
            # rows
            if (i + 1) % width == 0:
                text += Style.RESET_ALL + "\n"
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

    # promote properties from the last memory map
    @property
    def used(self):
        return self.memory_maps[-1].used

    @property
    def total(self):
        return self.memory_maps[-1].total

    @property
    def free(self):
        return self.memory_maps[-1].free

    @property
    def total(self):
        return self.memory_maps[-1].total

    @property
    def one_blocks(self):
        return self.memory_maps[-1].one_blocks

    @property
    def two_blocks(self):
        return self.memory_maps[-1].two_blocks

    @property
    def max_block_size(self):
        return self.memory_maps[-1].max_block_size

    @property
    def max_free_size(self):
        return self.memory_maps[-1].max_free_size

    @property
    def stack_used(self):
        return self.memory_maps[-1].stack_used

    @property
    def stack_total(self):
        return self.memory_maps[-1].stack_total

    # def __sub__(self, other: "MemoryInfo"):
    #     # assume self is the newer / larger memory info
    #     diff = copy.deepcopy(self)
    #     diff.diff_with = True
    #     diff.used = self.used - other.used
    #     diff.free = self.free - other.free
    #     diff.one_blocks = self.one_blocks - other.one_blocks
    #     diff.two_blocks = self.two_blocks - other.two_blocks
    #     # diff.max_block_size = self.max_block_size - other.max_block_size
    #     # diff.max_free_size = self.max_free_size - other.max_free_size
    #     # diff.lines_free = self.lines_free - other.lines_free
    #     # diff.memory_map = self.memory_map

    #     # Just copy the last maps from both
    #     diff.memory_maps = [copy.deepcopy(self.memory_maps[-1]), copy.deepcopy(other.memory_maps[-1])]

    #     return diff

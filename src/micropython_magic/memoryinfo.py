from __future__ import annotations

import datetime
import re
import time
from dataclasses import InitVar, dataclass
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Union

import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
import numpy as np
from colorama import Back, Fore, Style
from IPython.display import display, update_display
from IPython.lib.pretty import PrettyPrinter
from loguru import logger as log
from matplotlib import ticker
from matplotlib.backend_bases import MouseEvent
from matplotlib.lines import Line2D

RE_HEAD_1 = re.compile(r"GC: total: (\d+), used: (\d+), free: (\d+)")
RE_HEAD_2 = re.compile(r"\s?No. of 1-blocks: (\d+), 2-blocks: (\d+), max blk sz: (\d+), max free sz: (\d+)")
RE_D_TIME = re.compile(r"time:\s?(\([\d|,|\s]+\))")
RE_STACK = re.compile(r"stack: (\d+) out of (\d+)")
RE_BLOCK = re.compile(r"^[0-9a-fA-F]*\: (.*)", flags=re.MULTILINE)
RE_FREE = re.compile(r"\((.*) lines all free\)")
# setup terminators
RE_MEM_INFO_START = re.compile(r"\*\*\* Memory info (.*) \*\*\*")
RE_MEM_INFO_END = re.compile(r"\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*")

RE_ALL = [RE_HEAD_1, RE_HEAD_2, RE_D_TIME, RE_STACK, RE_BLOCK, RE_FREE, RE_MEM_INFO_START, RE_MEM_INFO_END]

#  a numpy datatype to hold the memory info for a series of memory maps
DT_MEMINFO = np.dtype(
    {
        "names": [
            "description",  # U25
            "datetime",  # M
            "total",
            "used",
            "free",
            "max free",
            "1-blocks",
            "2-blocks",
            "max block",
            "stack",
            "stack used",
        ],
        "formats": ["U25", "datetime64[us]", "i4", "i4", "i4", "i4", "i4", "i4", "i4", "i4", "i4"],
    }
)


COL_WIDTH = 64


def info_str(mem_info) -> str:
    """convert the output of a %mpy command to a string that can be processed
    Accepts:
        - from SList
        - from list[str]
        - from str
        = PrettyPrint
    """
    s = ""
    if "data" in dir(mem_info):
        mem_info = mem_info.data

    if issubclass(type(mem_info), list):
        s = "\n".join(mem_info)
    elif issubclass(type(mem_info), str):
        s = str(mem_info)

    return s


@dataclass
class MemoryInfo:
    mmap: InitVar[str] = ""
    cols: InitVar[Optional[int]] = None  # type: ignore
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
    parent: Optional[MemoryInfoList] = None
    _columns: int = 4
    _show_free = False

    def __post_init__(self, mmap: str, cols):
        if mmap:
            # self.mmap = info_str(mmap)
            self.parse(mmap)
        if cols:
            self._columns = cols

    @property
    def columns(self):
        return self.parent.columns if self.parent else self._columns

    @columns.setter
    def columns(self, val: int):
        self._columns = val

    @property
    def diff_with(self):
        return self.parent.diff_with if self.parent else None

    @property
    def show_free(self):
        return self.parent.show_free if self.parent else self._show_free

    @show_free.setter
    def show_free(self, val: bool):
        self._show_free = val

    def _header(self):
        head = f"{Fore.WHITE}{Back.BLACK}"
        assert self.parent
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
        self._color_num = 0
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

        match_head_1 = RE_HEAD_1.search(mem_info)
        if not match_head_1:
            log.warning(f"mem_info record not recognized as a valid - {name}")
            return self
        self.total, self.used, self.free = [int(x) for x in match_head_1.groups()]
        # find the used blocks
        match_head_2 = RE_HEAD_2.search(mem_info)
        if match_head_2:
            self.one_blocks, self.two_blocks, self.max_block_size, self.max_free_size = [
                int(x) for x in match_head_2.groups()
            ]
        match_stack = RE_STACK.search(mem_info)
        if match_stack:
            self.stack_used, self.stack_total = [int(x) for x in match_stack.groups()]
        match_dt = RE_D_TIME.search(mem_info)
        if match_dt:
            dt = eval(match_dt.groups()[0])
            self.datetime = datetime.datetime(*dt[:-1])
        else:
            # use the local time
            self.datetime = datetime.datetime.now()

        _raw_map = RE_BLOCK.findall(mem_info)
        if self.show_free:
            match_free = RE_FREE.search(mem_info)
            if match_free:
                # there can be multiple marks of free lines, so lets try to find them all
                # break the map into lines and find the free lines
                lines = mem_info.split("\n")
                l1 = 0
                for line in lines:
                    match_map = RE_BLOCK.match(line)
                    if match_map:
                        l1 += 1
                        continue
                    match_free = RE_FREE.search(line)
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

    def as_np_array(self):
        """Return the memory object as a numpy array of a single row"""
        return np.array(
            [
                (
                    self.name[:25],
                    self.datetime,
                    self.total,
                    self.used,
                    self.free,
                    self.max_free_size,
                    self.one_blocks,
                    self.two_blocks,
                    self.max_block_size,
                    self.stack_total,
                    self.stack_used,
                )
            ],
            dtype=DT_MEMINFO,
        )


# -------------------------------------------------------------------------------------------
# MemoryInfoList
# -------------------------------------------------------------------------------------------


from collections import UserList


class MemoryInfoList(UserList):
    """A list of MemoryInfo objects that is used to store a series of memory map of the device"""

    def __init__(
        self, iterable: Optional[Iterable] = None, *, show_free: bool = True, rainbow: bool = False, columns: int = 4
    ):
        self.show_free: bool = show_free  # show the free blocks - default True
        self.rainbow: bool = rainbow  # color the blocks in rainbow colors
        self.columns: int = columns

        self.diff_with: tuple = ()  # (other, current)
        if not iterable:
            iterable = []
        super().__init__(self._validate_mi(item) for item in iterable)

    def __setitem__(self, index, item):
        self.data[index] = self._validate_mi(item)

    @cached_property
    def np_array(self):
        """Return the memory List as a numpy array to allow simple math operations"""
        return np.array(
            [
                (
                    i.name[:25],
                    i.datetime,
                    i.total,
                    i.used,
                    i.free,
                    i.max_free_size,
                    i.one_blocks,
                    i.two_blocks,
                    i.max_block_size,
                    i.stack_total,
                    i.stack_used,
                )
                for i in self.data
            ],
            dtype=DT_MEMINFO,
        )

    def insert(self, index, item, name: str = ""):
        new = self._validate_mi(item, name=name)
        self.data.insert(index, new)

    def append(self, item, name: str = ""):
        new = self._validate_mi(item, name=name)
        self.data.append(new)

    def extend(self, other):
        if isinstance(other, type(self)):
            self.data.extend(other)
        else:
            self.data.extend(self._validate_mi(item) for item in other)

    def _validate_mi(self, value, name: str = ""):
        # sourcery skip: extract-duplicate-method
        "Check if this is a memory Info object or can be converted to one"
        if isinstance(value, MemoryInfo):
            # no conversion needed
            value.parent = self
            if name:
                value.name = name
            return value
        if isinstance(value, list) and isinstance(value[0], str):
            # convert list to to a string with newlines to be parsed
            info = MemoryInfo("\n".join(value))
            info.name = name
            info.parent = self
            return info
        elif issubclass(type(value), str):
            info = MemoryInfo(value)
            info.name = name
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
        if not log_text:
            log.debug("No log text to parse")
            return self
        if not isinstance(log_text, list):
            raise TypeError("log_text should be a list of strings")
        if not isinstance(log_text[0], str):
            raise TypeError("log_text should be a list of strings")
        # init
        in_mem_info = False
        nr = 0
        mem_info_log = []
        # find the meory_info lines in the (console) log output
        while nr < len(log_text):
            # if the regex matches, start a new map
            if match := RE_MEM_INFO_START.match(log_text[nr]):
                # start a new map
                mem_info_log = []
                in_mem_info = True
                # get the name of the map
                map_name = match[1]
            if in_mem_info:
                # if log_text[nr].startswith(MEM_INFO_END):
                if RE_MEM_INFO_END.match(log_text[nr]):
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

    def plot(
        self,
        title: str = "Memory Info",
        # used: bool = True,
        free: bool = False,
        stack_total: bool = False,
        one_blocks: bool = False,
        two_blocks: bool = False,
        max_block_size: bool = False,
        max_free_size: bool = False,
        stack_used: bool = False,
        time_axis: bool = False,  # turn off for now due to limited time precision
        add_legend: bool = True,
        size=(12, 4),  # Figure dimension (width, height) in inches.
    ):  # sourcery skip: last-if-guard
        # only import if needed
        import warnings

        KB_DIVIDER = 1024
        LEGEND_L_BOX = (0.0, 0.0, 0.05, 1)
        LEGEND_R_BOX = (0.7, 0.0, 0.3, 1)

        fig, ax1 = plt.subplots(figsize=size)  # , layout="constrained")
        fig.set_label(title)

        # prep the x-axis
        DT_FORMAT = "%H:%M:%S.%f"
        if time_axis:
            ax1.set_xlabel("Time -->")
            x = self.np_array["datetime"]
            format_date = mpl_dates.DateFormatter(DT_FORMAT)
            ax1.xaxis.set_major_formatter(format_date)

        else:
            ax1.set_xlabel("snapshots -->")
            x = np.arange(len(self))
            ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins="auto", integer=True))

            def format_x_label(x_value, tick_pos):
                "formatter function to retrieve the label for the x-axis based onthe x_value that is passed in."
                try:
                    idx = int(x_value)  # convert float to int
                    return self.np_array["description"][idx]  # return the label from the list
                except IndexError:
                    return str(x_value)  #  out of range

            # nbins sets the number of major-ticks on the x-axis, integers only as these are used as index into the list
            ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins="auto", integer=True))
            # set the formatter function for the x-axis to replace the numbers with the labels
            ax1.xaxis.set_major_formatter(format_x_label)

        # use the memory info list to get the data
        a_free = self.np_array["free"]
        a_used = self.np_array["used"]
        self.np_array["stack"] = self.np_array["stack"]
        ##################################################################################
        # configure both axes
        ##################################################################################
        ax1.yaxis.set_major_formatter(lambda x, pos: f"{x/KB_DIVIDER:_.0f} Kb")  # integers in thousands notation
        ax1.set_ylabel("Memory (Kb)")
        ax1.set_xmargin(0)
        ax1.set_ymargin(0)
        ##################################################################################
        # Create twin Axes that shares the x-axis
        ax2 = ax1.twinx()
        ax2.yaxis.set_major_formatter("{x:_.0f}")
        ax2.set_ymargin(0)
        # Add grid for all axes with different styles
        ax1.grid(True, linestyle="dotted", color="olive")
        ax2.grid(True, axis="y", linestyle=":", color="fuchsia")
        ##################################################################################
        # show minor ticks
        ax1.minorticks_on()
        ax2.minorticks_on()
        ##################################################################################
        # adjust display of the x-axis labels
        for label in ax1.get_xticklabels():
            label.set_horizontalalignment("left")
            label.set_rotation(-10)
            label.set_fontsize("x-small")
            label.set_fontweight("light")
            label.set_y(label.get_position()[1] + 0.01)
        # make more room for the labels below  the figure
        fig.subplots_adjust(bottom=0.1)

        ##################################################################################
        # Add stackplot of free, used and stack memory if requested
        labels = ["heap used"]
        colors = ["orange"]
        data = [a_used]
        if free:
            labels.append("heap free")
            colors.append("green")
            data.append(a_free)
        if stack_total:
            labels.append("stack total")
            colors.append("purple")
            data.append(self.np_array["stack"])

        s_plot = ax1.stackplot(x, data, labels=labels, colors=colors, alpha=0.5)

        my_lines: List[Line2D] = []
        # Add line charts to 2nd axis
        if one_blocks:
            my_lines += ax2.plot(x, self.np_array["1-blocks"], label="1-Blocks", marker=".", linestyle="-.")
        if two_blocks:
            my_lines += ax2.plot(x, self.np_array["2-blocks"], label="2-Blocks", marker=".", linestyle="--")
        if max_block_size:
            my_lines += ax2.plot(x, self.np_array["max block"], label="Max Block Size", marker=".", linestyle="--")
        if max_free_size:
            my_lines += ax2.plot(x, self.np_array["max free"], label="Max Free Size", marker=".", linestyle="--")
        if stack_used:
            my_lines += ax2.plot(x, self.np_array["stack used"], label="Stack Used", marker=".", linestyle="--")

        if add_legend:
            # Add legend and show plot, best location left-ish top
            ax1.legend(loc="best", reverse=True, bbox_to_anchor=LEGEND_L_BOX, fontsize="small")
            #  bbox (x, y, width, height) - best location right-ish top
            ax2.legend(loc="best", bbox_to_anchor=LEGEND_R_BOX, fontsize="small")
        plt.tick_params(bottom="on")

        # create the annotations box, and hide it for now
        annot = ax2.annotate(
            "",
            xy=(0, 0),
            xytext=(-20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        annot.set_visible(False)

        def update_annot(line: Line2D, ind: Dict):
            """Update the annotation box with the data from the selected line."""
            x, y = line.get_data()
            # get the list index of the selected data point
            indx = ind["ind"][0]
            annot.xy = (x[indx], y[indx])
            ## get the text from the line object
            text = (
                f"@{self[indx].name}\n"
                f"time:{self[indx].datetime}\n"
                f"{line.get_label()} = {y[indx]:_.0f}\n"
                f"Memory used: {self[indx].used:_.0f} b, free {self[indx].free:_.0f} b"
            )
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.4)  # set the transparency of the box # type: ignore

        def hover(event: MouseEvent):
            """On mouse-hovewr over a line, display the corresponding data point value"""
            if event.inaxes in [ax1, ax2]:
                _visible = annot.get_visible()
                _contains = False
                for line in my_lines:
                    _contains, ind = line.contains(event)
                    if _contains:
                        update_annot(line, ind)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        break
                if not _contains and _visible:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        # connect the hover-function to the mouse
        fig.canvas.mpl_connect("motion_notify_event", hover)
        return fig

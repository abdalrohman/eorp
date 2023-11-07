#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edit_OEM_ROM_Project
Copyright (C) 2022 Abdalrohman Alnasier

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import builtins
import signal
import sys
from re import Pattern, compile
from shutil import get_terminal_size
from threading import Event, Thread
from typing import Iterable, Tuple, List, Dict, Union

from loguru import logger


class Color:
    """
    Holds representations for a 24-bit color value
    Attributes:
        hexa (str): 6 digit hexadecimal string "#RRGGBB"
        dec (Tuple[int, int, int]): Decimal RGB as a tuple of integers (0-255)
        red (int): Red component of the color (0-255)
        green (int): Green component of the color (0-255)
        blue (int): Blue component of the color (0-255)
        depth (str): "fg" or "bg"
        escape (str): Escape sequence to set color
        default (bool): Whether to use default color
    Methods:
        __init__(color: str, depth: str = "fg", default: bool = False) -> None:
            Initializes a new Color object with the given color, depth, and default values.
        __str__() -> str:
            Returns the escape sequence to set the color.
        __repr__() -> str:
            Returns the escape sequence to set the color.
        __iter__() -> Iterable:
            Returns an iterator over the red, green, and blue components of the color.
        __call__(*args: str) -> str:
            Joins the given string arguments and applies the color.
        truecolor_to_256(rgb: Tuple[int, int, int], depth: str = "fg") -> str:
            Converts the given true color RGB value to a 256-color value.
        escape_color(hexa: str = "", r: int = 0, g: int = 0, b: int = 0, depth: str = "fg") -> str:
            Returns the escape sequence to set the color based on the given hexadecimal or decimal RGB values.
        fg(*args) -> str:
            Returns the escape sequence to set the foreground color based on the given hexadecimal or decimal RGB values.
        bg(*args) -> str:
            Returns the escape sequence to set the background color based on the given hexadecimal or decimal RGB values.
    """

    hexa: str
    dec: Tuple[int, int, int]
    red: int
    green: int
    blue: int
    depth: str
    escape: str
    default: bool

    def __init__(self, color: str, depth: str = "fg", default: bool = False) -> None:
        """
        Initializes a new Color object with the given color, depth, and default values.
        Args:
            color (str): The color value as a 6 digit hexadecimal string "#RRGGBB", 2 digit hexadecimal string "#FF", or decimal RGB as a string "255 255 255".
            depth (str, optional): The depth of the color, either "fg" (foreground) or "bg" (background). Defaults to "fg".
            default (bool, optional): Whether to use the default color. Defaults to False.
        """
        self.depth = depth
        self.default = default
        try:
            if not color:
                self.dec = (-1, -1, -1)
                self.hexa = ""
                self.red = self.green = self.blue = -1
                self.escape = "\033[49m" if depth == "bg" and default else ""
                return

            elif color.startswith("#"):
                self.hexa = color
                if len(self.hexa) == 3:
                    self.hexa += self.hexa[1:3] + self.hexa[1:3]
                    c = int(self.hexa[1:3], base=16)
                    self.dec = (c, c, c)
                elif len(self.hexa) == 7:
                    self.dec = (
                        int(self.hexa[1:3], base=16),
                        int(self.hexa[3:5], base=16),
                        int(self.hexa[5:7], base=16),
                    )
                else:
                    raise ValueError(
                        f"Incorrectly formatted hexadecimal rgb string: {self.hexa}"
                    )

            else:
                c_t = tuple(map(int, color.split(" ")))
                if len(c_t) == 3:
                    self.dec = c_t  # type: ignore
                else:
                    raise ValueError('RGB dec should be "0-255 0-255 0-255"')

            if not all(0 <= c <= 255 for c in self.dec):
                raise ValueError(f"One or more RGB values are out of range: {color}")

        except ValueError as e:
            logger.exception(str(e))
            self.escape = ""
            return

        if self.dec and not self.hexa:
            self.hexa = f'{hex(self.dec[0]).lstrip("0x").zfill(2)}{hex(self.dec[1]).lstrip("0x").zfill(2)}{hex(self.dec[2]).lstrip("0x").zfill(2)}'

        if self.dec and self.hexa:
            self.red, self.green, self.blue = self.dec
            self.escape = f'\033[{38 if self.depth == "fg" else 48};2;{";".join(str(c) for c in self.dec)}m'

    def __str__(self) -> str:
        """Returns the escape sequence to set the color."""
        return self.escape

    def __repr__(self) -> str:
        """Returns the escape sequence to set the color."""
        return self.escape

    def __iter__(self) -> Iterable:
        """Returns an iterator over the red, green, and blue components of the color."""
        for c in self.dec:
            yield c

    def __call__(self, *args: str) -> str:
        """Joins the given string arguments and applies the color."""
        if len(args) < 1:
            return ""
        return f"{self.escape}{''.join(args)}\033[0m"

    @staticmethod
    def truecolor_to_256(rgb: Tuple[int, int, int], depth: str = "fg") -> str:
        """
        Converts the given true color RGB value to a 256-color value.

        Args:
            rgb: Tuple of RGB values
            depth: Color depth ("fg" for foreground, "bg" for background)

        Return:
            256-color value
        """
        if depth not in ("fg", "bg"):
            raise ValueError("Invalid depth value")

        if not all(0 <= value <= 255 for value in rgb):
            raise ValueError("Invalid RGB value")

        r, g, b = rgb
        if r == g == b:
            # grayscale
            index = round(r / 255 * 23)
            code = 232 + index
        else:
            # color
            r_index = round(r / 255 * 5)
            g_index = round(g / 255 * 5)
            b_index = round(b / 255 * 5)
            code = 16 + (r_index * 36) + (g_index * 6) + b_index

        return f"\033[{38 if depth == 'fg' else 48};5;{code}m"

    @staticmethod
    def escape_color(
            hexa: str = "", r: int = 0, g: int = 0, b: int = 0, depth: str = "fg"
    ) -> str:
        """
        Converts the given hexadecimal RGB value or RGB values to an ANSI escape code.

        Args:
            hexa: Hexadecimal RGB value
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            depth: Color depth ("fg" for foreground, "bg" for background)

        Return:
            ANSI escape code
        """
        if hexa:
            hexa = hexa.lstrip("#")  # remove '#' if present
            if len(hexa) == 2:
                color = int(hexa, base=16)
                c = f"\033[{38 if depth == 'fg' else 48};2;{color};{color};{color}m"
            elif len(hexa) == 3:
                r = int(hexa[0] * 2, base=16)
                g = int(hexa[1] * 2, base=16)
                b = int(hexa[2] * 2, base=16)
                c = f"\033[{38 if depth == 'fg' else 48};2;{r};{g};{b}m"
            elif len(hexa) == 6:
                r = int(hexa[:2], base=16)
                g = int(hexa[2:4], base=16)
                b = int(hexa[4:], base=16)
                c = f"\033[{38 if depth == 'fg' else 48};2;{r};{g};{b}m"
            else:
                raise ValueError(
                    f"Incorrectly formatted hexadecimal rgb string: #{hexa}"
                )
        else:
            c = f"\033[{38 if depth == 'fg' else 48};2;{r};{g};{b}m"

        return c

    @classmethod
    def fg(cls, *args) -> str:
        """
        Converts the given hexadecimal RGB value or RGB values to a foreground ANSI escape code.

        Args:
            args: Hexadecimal RGB value or RGB values

        Return:
            Foreground ANSI escape code
        """
        if len(args) == 1 and isinstance(args[0], str):
            return cls.escape_color(hexa=args[0], depth="fg")
        elif len(args) == 3 and all(isinstance(arg, int) for arg in args):
            return cls.escape_color(r=args[0], g=args[1], b=args[2], depth="fg")
        else:
            raise ValueError("Invalid arguments")

    @classmethod
    def bg(cls, *args) -> str:
        """
        Converts the given hexadecimal RGB value or RGB values to a background ANSI escape code.

        Args:
            args: Hexadecimal RGB value or RGB values

        Return:
            Background ANSI escape code
        """
        if len(args) == 1 and isinstance(args[0], str):
            return cls.escape_color(hexa=args[0], depth="bg")
        elif len(args) == 3 and all(isinstance(arg, int) for arg in args):
            return cls.escape_color(r=args[0], g=args[1], b=args[2], depth="bg")
        else:
            raise ValueError("Invalid arguments")


class Colors:
    """Standard colors"""

    default = Color("#cc")
    white = Color("#ff")
    red = Color("#bf3636")
    green = Color("#68bf36")
    blue = Color("#0fd7ff")
    yellow = Color("#db8b00")
    black_bg = Color("#00", depth="bg")
    null = Color("")


class Mv:
    """Class with a collection of cursor movement functions: .to | .right | .left | .up | .down | .save() | .restore()"""

    @staticmethod
    def to(line: int, col: int) -> str:
        """Move the cursor to the specified line and column."""
        return f"\033[{line};{col}f"

    @staticmethod
    def right(x: int) -> str:
        """Move the cursor right by the specified number of columns."""
        return f"\033[{x}C"

    @staticmethod
    def left(x: int) -> str:
        """Move the cursor left by the specified number of columns."""
        return f"\033[{x}D"

    @staticmethod
    def up(x: int) -> str:
        """Move the cursor up by the specified number of lines."""
        return f"\033[{x}A"

    @staticmethod
    def down(x: int) -> str:
        """Move the cursor down by the specified number of lines."""
        return f"\033[{x}B"

    save: str = "\033[s"  # Save cursor position
    restore: str = "\033[u"  # Restore saved cursor position

    # Alias methods for easier usage
    t: staticmethod = to
    r: staticmethod = right
    l: staticmethod = left
    u: staticmethod = up
    d: staticmethod = down


class Fx:
    """Class for applying text effects and colors in a terminal."""

    # Escape sequence start, separator, and end
    start = "\033["
    sep = ";"
    end = "m"

    # Reset foreground/background color and text effects
    reset = rs = "\033[0m"

    # Bold on and off
    bold = b = "\033[1m"
    unbold = ub = "\033[22m"

    # Dark on and off
    dark = d = "\033[2m"
    undark = ud = "\033[22m"

    # Italic on and off
    italic = i = "\033[3m"
    unitalic = ui = "\033[23m"

    # Underline on and off
    underline = u = "\033[4m"
    ununderline = uu = "\033[24m"

    # Blink on and off
    blink = bl = "\033[5m"
    unblink = ubl = "\033[25m"

    # Strike / crossed-out on and off
    strike = s = "\033[9m"
    unstrike = us = "\033[29m"

    # Precompiled regex for finding a 24-bit color escape sequence in a string
    color_re: Pattern[str] = compile(r"\033\[\d+;\d?;?\d*;?\d*;?\d*m")

    @staticmethod
    def trans(string: str) -> str:
        """Replace whitespace characters in a string with an escape code that moves the cursor to the right without overwriting the background."""
        return string.replace(" ", "\033[1C")

    @classmethod
    def uncolor(cls, string: str) -> str:
        """Remove all 24-bit color escape codes from a string."""
        return cls.color_re.sub("", string)


class Term:
    """Class for managing terminal information and commands."""

    # Terminal dimensions
    width: int = 0
    height: int = 0

    # Flags for terminal resize events
    resized: bool = False
    _w: int = 0
    _h: int = 0

    # Default foreground and background colors
    fg: str = ""
    bg: str = ""

    # Hide and show terminal cursor
    hide_cursor: str = "\033[?25l"
    show_cursor: str = "\033[?25h"

    # Switch to alternate and normal screen
    alt_screen: str = "\033[?1049h"
    normal_screen: str = "\033[?1049l"

    # Clear screen and set cursor to position 0,0
    clear: str = "\033[2J\033[0;0f"

    # Enable and disable reporting of mouse position on click and release
    mouse_on: str = "\033[?1002h\033[?1015h\033[?1006h"
    mouse_off: str = "\033[?1002l"

    # Enable and disable reporting of mouse position at any movement
    mouse_direct_on: str = "\033[?1003h"
    mouse_direct_off: str = "\033[?1003l"

    # Event for window change signal
    winch: Event = Event()

    # List of old boxes for redrawing
    old_boxes: List = []

    # Minimum terminal dimensions
    min_width: int = 0
    min_height: int = 0

    @classmethod
    def terminal_resize(cls, width: int, height: int) -> None:
        """Callback function for terminal resize events."""
        cls._w = width
        cls._h = height
        cls.resized = True
        cls.winch.set()

    @classmethod
    def initialize(cls) -> None:
        """Initialize the terminal."""
        # Set up terminal resize signal handler
        signal.signal(signal.SIGWINCH, cls.terminal_resize)

        # Get terminal dimensions
        cls.update_terminal_dimensions()

    @classmethod
    def update_terminal_dimensions(cls) -> None:
        """Update the terminal dimensions."""
        cls.width, cls.height = get_terminal_size()


class Key:
    """Class for handling the threaded input reader for keypresses and mouse events."""

    # List of keypresses
    list: List[str] = []

    # Dictionary containing information about mouse events
    mouse: Dict[str, List[List[int]]] = {}

    # Current mouse position
    mouse_pos: Tuple[int, int] = (0, 0)

    # Threading events for managing the input reader
    new: Event = Event()
    idle: Event = Event()
    mouse_move: Event = Event()

    # Flag indicating whether mouse reporting is enabled
    mouse_report: bool = False

    # Set the idle event
    idle.set()

    # Flags indicating the state of the input reader
    stopping: bool = False
    started: bool = False

    # Threading.Thread object representing the input reader thread
    reader: Thread = Thread()

    # Dictionary that maps escape sequences to their corresponding key names
    escape: Dict[Union[str, Tuple[str, str]], str] = {
        "\n": "enter",  # Enter key
        ("\x7f", "\x08"): "backspace",  # Backspace key
        ("[A", "OA"): "up",  # Up arrow key
        ("[B", "OB"): "down",  # Down arrow key
        ("[D", "OD"): "left",  # Left arrow key
        ("[C", "OC"): "right",  # Right arrow key
        "[2~": "insert",  # Insert key
        "[3~": "delete",  # Delete key
        "[H": "home",  # Home key
        "[F": "end",  # End key
        "[5~": "page_up",  # Page Up key
        "[6~": "page_down",  # Page Down key
        "\t": "tab",  # Tab key
        "[Z": "shift_tab",  # Shift + Tab keys
        "OP": "f1",  # F1 key
        "OQ": "f2",  # F2 key
        "OR": "f3",  # F3 key
        "OS": "f4",  # F4 key
        "[15": "f5",  # F5 key
        "[17": "f6",  # F6 key
        "[18": "f7",  # F7 key
        "[19": "f8",  # F8 key
        "[20": "f9",  # F9 key
        "[21": "f10",  # F10 key
        "[23": "f11",  # F11 key
        "[24": "f12",  # F12 key
    }

    @classmethod
    def start(cls) -> None:
        """Starts the input reader thread."""
        if not cls.started:
            cls.reader = Thread(target=cls._read_input)
            cls.reader.start()
            cls.started = True

    @classmethod
    def stop(cls) -> None:
        """Stops the input reader thread."""
        if cls.started:
            cls.stopping = True
            cls.reader.join()
            cls.stopping = False
            cls.started = False

    @classmethod
    def _read_input(cls) -> None:
        """Reads input from the user and adds it to the list of keypresses."""
        while not cls.stopping:
            key = input()
            if not cls.stopping:
                cls.list.append(key)
                cls.new.set()
                cls.idle.clear()
                cls.mouse_move.clear()

    @classmethod
    def add_mouse_event(cls, event: str, x: int, y: int) -> None:
        """Adds a mouse event to the dictionary of mouse events."""
        if event not in cls.mouse:
            cls.mouse[event] = []

        cls.mouse[event].append([x, y])
        cls.new.set()
        cls.idle.clear()
        cls.mouse_move.set()

    @classmethod
    def clear(cls) -> None:
        """Clears all data and resets the state of the input reader."""
        cls.list.clear()
        cls.mouse.clear()
        cls.mouse_pos = (0, 0)
        cls.new.clear()
        cls.idle.set()
        cls.mouse_move.clear()


class Banner:
    """Class for drawing a banner in the terminal."""

    out: List[str] = []  # List of strings representing the banner
    c_color: str = ""  # Current color
    length: int = 0  # Length of the longest line in the banner
    banner_src = ""

    def __init__(self, banner_src: List[Tuple[str, str, str]]) -> None:
        self.banner_src: List[Tuple[str, str, str]] = banner_src

        # Generate the banner if it hasn't been generated yet
        if not self.out:
            # Iterate over each line in the banner source
            for num, (color, color2, line) in enumerate(self.banner_src):
                # Update the length of the longest line
                self.length = max(self.length, len(line))

                # Initialize the output string for this line
                out_var = ""

                # Set the colors for this line
                line_color = Color.fg(color)
                line_color2 = Color.fg(color2)
                line_dark = Color.fg(f"#{80 - num * 6}")

                # Iterate over each character in the line
                for n, letter in enumerate(line):
                    # If the character is a block and the current color is not the line color
                    if letter == "█" and self.c_color != line_color:
                        # Set the current color to the appropriate line color
                        self.c_color = line_color2 if 5 < n < 25 else line_color

                        # Add the current color to the output string
                        out_var += self.c_color

                    # If the character is a space
                    elif letter == " ":
                        # Replace the space with an escape code that moves the cursor to the right
                        letter = f"{Mv.r(1)}"

                        # Reset the current color
                        self.c_color = ""

                    # If the character is not a block or space and the current color is not dark
                    elif letter != "█" and self.c_color != line_dark:
                        # Set the current color to dark
                        self.c_color = line_dark

                        # Add the current color to the output string
                        out_var += line_dark

                    # Add the character to the output string
                    out_var += letter

                # Add this line to the list of lines in the banner
                self.out.append(out_var)

    @classmethod
    def draw(cls, line: int, col: int = 0, center: bool = False) -> str:
        """Draws a banner at a specific position in the terminal.

        Args:
            line: The row position where the banner will be drawn.
            col: The column position where the banner will be drawn. Default is 0.
            center: Whether to center the banner horizontally. Default is False.

        Returns:
            The formatted string representation of the banner.
        """
        out: str = ""  # Initialize an empty string for storing the output

        # If centering is enabled, calculate the column position for centering
        if center:
            col = Term.width // 2 - cls.length // 2

        # Iterate over each line in the banner
        for n, o in enumerate(cls.out):
            # Add an escape code to move the cursor to the appropriate position and add this line to the output string
            out += f"{Mv.to(line + n, col)}{o}\n"

        return out + f"{Term.fg}"  # Reset foreground color and add it to output string


class PrintClass:
    """Wrapper class for the print method to display colored text in the terminal.

    Example usage:
    printer = PrintClass()
    printer.print('Hello World!', color='red', tag='[ERROR]', tag_color='yellow', fmt=['bold'])
    """

    # Dictionary of color codes
    __colors: Dict[str, str] = {
        "purple": "\033[95m",
        "blue": "\033[94m",
        "green": "\033[92m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "black": "\033[30m",
        "white": "\033[37m",
    }

    # Dictionary of format codes
    __formats: Dict[str, str] = {
        "bold": "\033[1m",
        "underline": "\033[4m",
        "blink": "\033[5m",
    }

    @staticmethod
    def __get_color_escape_code(color: str) -> str:
        """Return the escape code for the given color or the default color if the color is not found."""
        return PrintClass.__colors.get(color, "\033[0m")

    @staticmethod
    def __get_format_escape_code(fmt: str) -> str:
        """Return the escape code for the given format or the default format if the format is not found."""
        return PrintClass.__formats.get(fmt, "\033[0m")

    @staticmethod
    def print(
            *args: Union[str, int, float],
            color: str = None,
            tag: str = None,
            tag_color: str = None,
            fmt: List[str] = None,
            **kwargs,
    ) -> None:
        """Print method that prints colored and formatted text to the terminal.

        Args:
            *args (Union[str, int, float]): The arguments to print.
            color (str, optional): The color of the text. Defaults to None.
            tag (str, optional): The tag to add before the text. Defaults to None.
            tag_color (str, optional): The color of the tag. Defaults to None.
            fmt (List[str], optional): The list of formats to apply to the text. Defaults to None.
            **kwargs: Additional keyword arguments to pass to the built-in print function.

        Example usage:
            printer = PrintClass()
            printer.print('Hello World!', color='red', tag='[ERROR]', tag_color='yellow', fmt=['bold'])
        """

        # Initialize an empty string for storing the result
        result = ""

        # Concatenate all arguments into a single string
        for arg in args:
            result += str(arg)

        # Apply color to the result if specified
        if color:
            result = PrintClass.__get_color_escape_code(color) + result

        # Add tag to the result if specified
        if tag:
            result = f"{tag} {result}"

        # Apply tag color to the result if specified
        if tag_color:
            result = PrintClass.__get_color_escape_code(tag_color) + result

        # Apply formats to the result if specified
        if fmt:
            for f in fmt:
                builtins.print(
                    PrintClass.__get_format_escape_code(f), file=sys.stdout, end=""
                )

        # Reset color and add it to result string
        result += "\033[0m"

        # Print the result with remaining keyword arguments
        builtins.print(result, **kwargs)

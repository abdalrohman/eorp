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
import argparse
import ctypes
import os
import platform
from pathlib import Path

GIBIBYTE = 1024 ** 3  # 1 GiB = 1024 MiB
MEBIBYTE = 1024 ** 2  # 1 MiB = 1024 KiB
KIBIBYTE = 1024  # 1 KiB = 1024 Bytes


class DiskUsage:
    """
    DiskUsage class is used to calculate the disk usage of files and directories.

    Attributes:
        human_readable (bool): If True, the sizes will be printed in a human-readable format (e.g., KB, MB, GB).
        display_bytes (bool): If True, the sizes will be printed in bytes when not using human-readable format.
        display_regular_files_also (bool): If True, the sizes for all files will be printed.
        display_directories_also (bool): If True, the sizes for all directories will be printed.
    """

    def __init__(
            self,
            human_readable: bool = False,
            display_bytes: bool = True,
            display_regular_files_also: bool = False,
            display_directories_also: bool = False,
    ):
        """
        The constructor for DiskUsage class.

        Parameters:
            human_readable (bool): If True, the sizes will be printed in a human-readable format (e.g., KB, MB, GB).
            display_bytes (bool): If True, the sizes will be printed in bytes when not using human-readable format.
            display_regular_files_also (bool): If True, the sizes for all files will be printed.
            display_directories_also (bool): If True, the sizes for all directories will be printed.
        """
        self.human_readable = human_readable
        self.display_bytes = display_bytes
        self.display_regular_files_also = display_regular_files_also
        self.display_directories_also = display_directories_also

    def write_last_error(self, error_code: int, message: str, name: str) -> None:
        """
        Prints an error message for a given error code.

        Parameters:
            - error_code (int): The error code.
            - message (str): The error message.
            - name (str): The name of the file or directory.
        """
        if platform.system() == "Windows":
            print(f"{message} {name}: {ctypes.FormatError(error_code)}")
        else:
            print(f"{message} {name}: {os.strerror(error_code)}")

    def format_file_size(
            self, path: Path, size: int, suppress_print: bool = False
    ) -> None:
        """
        Formats the file size in a human-readable format or bytes and prints it.

        Parameters:
            path (Path): The path of the file.
            size (int): The size of the file in bytes.
            suppress_print (bool): If True, suppresses the print of the file size and returns it instead.
        """
        hr_size = 0.0
        if self.human_readable:
            if size >= GIBIBYTE:
                hr_size = size / GIBIBYTE
                output = f"{hr_size:.1f}G\t{path}"
            elif size >= MEBIBYTE:
                hr_size = size / MEBIBYTE
                output = f"{hr_size:.1f}M\t{path}"
            elif size >= KIBIBYTE:
                hr_size = size / KIBIBYTE
                output = f"{hr_size:.1f}K\t{path}"
            else:
                output = f"{size}\t{path}"
        else:
            if not self.display_bytes:
                if size > 0:
                    size = round(size / 1024.0)  # Convert to KB and round
                    if size == 0:
                        # Don't allow zero to display if there are bytes in the file
                        size = 1
            output = f"{size:7}\t{path}"

        if suppress_print:
            return size
        else:
            print(output)

    def calc_disk_usage(self, path: Path, is_top_level: bool = True) -> int:
        """
        Calculates the disk usage of a file or directory and prints the size if is_top_level is True.

        Parameters:
            path (Path): The path of the file or directory.
            is_top_level (bool): If True, prints the size of the file or directory. Default is True.

        Returns:
            int: The size of the file or directory in bytes.
        """
        if isinstance(path, str):
            path = Path(path)

        size = 0
        entries = []

        if Path(path).is_file():
            size = path.stat().st_size
            if self.display_regular_files_also or is_top_level:
                self.format_file_size(path, size)
        elif Path(path).is_dir() and not Path(path).is_symlink():
            try:
                entries = os.listdir(path)
                for entry in entries:
                    entry_path = Path(path, entry)
                    size += self.calc_disk_usage(entry_path, False)
                if self.display_directories_also or is_top_level:
                    self.format_file_size(path, size)
            except OSError as e:
                self.write_last_error(e.errno, "Failed to list directory", str(path))
                # exit(e.errno)
            except KeyboardInterrupt:
                print("\nTermination...")
                exit(1)

        if self.human_readable:
            if size >= GIBIBYTE:
                return f"{size / GIBIBYTE:.1f}G"
            elif size >= MEBIBYTE:
                return f"{size / MEBIBYTE:.1f}M"
            elif size >= KIBIBYTE:
                return f"{size / KIBIBYTE:.1f}K"
            else:
                return size
        return size

    @staticmethod
    def main():
        """
        Main function to parse the command-line arguments and calculate the disk usage of the specified paths.

        It parses the command-line arguments, creates a DiskUsage object for each path, and calculates the disk usage of the path.
        """
        parser = argparse.ArgumentParser(
            description="Calculate disk usage of files and directories."
        )
        parser.add_argument(
            "paths",
            metavar="PATH",
            type=str,
            nargs="+",
            help="Path to file or directory",
        )
        parser.add_argument(
            "-hr",
            "--human-readable",
            action="store_true",
            help="Print sizes in human-readable format (e.g., KB, MB, GB)",
        )
        parser.add_argument(
            "-b",
            "--bytes",
            action="store_true",
            help="Print sizes in bytes when not using human-readable format",
        )
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="Print sizes for all files and directories",
        )
        parser.add_argument(
            "-s",
            "--suppress-print",
            action="store_true",
            help="Suppress printing and return the sizes instead",
        )

        try:
            args = parser.parse_args()
            for path in args.paths:
                disk_usage = DiskUsage(
                    human_readable=args.human_readable,
                    display_bytes=not args.bytes,
                    display_regular_files_also=args.all,
                    display_directories_also=args.all,
                )
                disk_usage.calc_disk_usage(path, True)
        except KeyboardInterrupt:
            print("\nTermination...")


if __name__ == "__main__":
    DiskUsage().main()

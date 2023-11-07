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
from platform import machine, platform, system


class SystemDetector:
    """
    A class used to detect the system and provide system information.

    Attributes:
        system (str): The name of the operating system.
        machine (str): The machine architecture.
        platform (str): The platform information.

    Methods:
        get_architecture() -> str: Returns the system architecture.
        get_os_type() -> str: Returns the operating system type.
        detect_wsl_version() -> str or None: Returns the version of Windows Subsystem for Linux (WSL) if detected, otherwise returns None.
        get_system_info() -> tuple[str, str, str]: Returns a tuple containing the system architecture, operating system type, and platform information.
    """

    def __init__(self):
        """
        Constructs all the necessary attributes for the SystemDetector object.
        """
        self.system: str = system()
        self.machine: str = machine()
        self.platform: str = platform()

    def get_architecture(self) -> str:
        """
        Returns the system architecture.

        Returns:
            str: The system architecture.
        """
        return "Amd64" if self.machine == "x86_64" else self.machine

    def get_os_type(self) -> str:
        """
        Returns the operating system type.

        Returns:
            str: The operating system type.
        """
        if self.system == "Linux":
            if "Microsoft" in self.platform:
                wsl_version: str = self.detect_wsl_version()
                if wsl_version:
                    return f"WSL {wsl_version}"
                else:
                    return "Linux"
            elif "CYGWIN" in self.platform:
                return "Cygwin"
            elif "Android" in self.platform:
                return "Termux"
            else:
                return "Linux"
        elif self.system == "Windows":
            return "Windows"
        elif self.system == "Darwin":
            return "macOS"
        else:
            return "Unknown system"

    def detect_wsl_version(self):
        """
        Detects and returns the version of Windows Subsystem for Linux (WSL) if detected.

        Returns:
            str: The WSL version (1 or 2) if WSL is detected, otherwise returns None.
        """
        try:
            with open("/proc/version", "r", encoding="utf-8") as version_file:
                version_info: str = version_file.read()
                if "microsoft" in version_info.lower():
                    if "wsl2" in version_info.lower():
                        return "2"
                    else:
                        return "1"
                return "Not WSL"
        except FileNotFoundError:
            pass

    def get_system_info(self) -> tuple[str, str, str]:
        """
        Returns a tuple containing the system architecture, operating system type, and platform information.

        Returns:
            tuple[str, str, str]: A tuple containing the system architecture, operating system type, and platform information.
        """
        architecture: str = self.get_architecture()
        os_type: str = self.get_os_type()

        return architecture, os_type, self.platform

# USE SystemDetector
# decorator = SystemDetector()

# print(decorator.get_os_type())

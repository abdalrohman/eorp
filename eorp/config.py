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
import os
from configparser import ConfigParser
from pathlib import Path
from platform import machine
from typing import Dict, Optional, Union

from loguru import logger

from .errors import UnsupportedArchitectureError
from .variables import CONFIG_FILE, ROOT_DIR


class Configs:
    """
    A class used to generate and manage the config file.

    Attributes:
        config_file (Path): The path to the config file.

    Methods:
        check_arch() -> str: Returns the system architecture.
        write_config(section: str, data: Dict[str, str]) -> None: Writes a section with key-value pairs to the config file.
        load_config(section: str, key: str) -> str: Loads a value from a key in a section from the config file.
        update_config(section: str, data: Union[str, Dict[str, str]], value: str = None) -> None: Updates a section with key-value pairs or a single key-value pair in the config file.
        delete_config(section: str, key: str = None) -> None: Deletes a section or key from the config file.
        print_config() -> None: Prints the config in a readable and visually appealing format.
        has_option(section: str, option: str) -> bool: Returns True if the specified section has the specified option, otherwise returns False.
        write_default_config() -> None: Writes default values for each section in the config file.
    """

    def __init__(self, config_file: Path) -> None:
        """
        Constructs all the necessary attributes for the Configs object.

        Parameters:
            config_file (Path): The path to the config file.
        """
        if isinstance(config_file, str):
            self.config_file = Path(config_file)
        elif isinstance(config_file, Path):
            self.config_file = config_file
        else:
            raise TypeError("config_file must be a str or a Path object.")

        # Load config file
        self.config = ConfigParser(delimiters=":")
        self.config.read(self.config_file)

        # check if config file is not exist and generate it
        if not self.config_file.exists():
            if not self.config_file.parent.exists():
                os.makedirs(self.config_file.parent)
            self.config_file.touch()
            print(f"\nGenerating {self.config_file}")
            self.write_default_config()

    def check_arch(self) -> str:
        """
        Returns the system architecture.

        Returns:
            str: The architecture name, either "ARM64" or "AMD64".
            If neither, raises an UnsupportedArchitectureError.

        Raises:
            UnsupportedArchitectureError: If the architecture is not supported.
        """
        arch = machine()
        if arch == "aarch64":
            return "ARM64"
        elif arch == "x86_64":
            return "AMD64"
        else:
            raise UnsupportedArchitectureError(f"Unsupported architecture: {arch}")

    def write_config(self, section: str, data: Dict[str, str]) -> None:
        """
        Writes a section with key-value pairs to the config file.

        Parameters:
            section (str): The section name to write in the config file.
            data (Dict[str, str]): The key-value pairs to write in the section.

        Raises:
            Exception: If an error occurs while writing to the config file.
        """
        try:
            self.config[section] = data
            with open(self.config_file, "w", encoding="UTF-8") as config_file:
                self.config.write(config_file)
        except Exception as e:
            logger.info(
                f"Error: Failed to write section '{section}' to config file. Error: {e}"
            )

    def load_config(self, section: str, key: str) -> str:
        """
        Loads and returns a value from a key in a section from the config file.

        Parameters:
            section (str): The section name to load from the config file.
            key (str): The key name to load from the section.

        Returns:
            str or None: The value of the key in the section. If not found, returns None.

        Raises:
            KeyError: If either the section or key is not found in the config file.
        """
        try:
            return self.config[section].get(key)
        except KeyError:
            logger.error(
                f"Error: Section '{section}' or key '{key}' not found in config file."
            )
            return None

    def update_config(
            self,
            section: str,
            data: Union[str, Dict[str, str]],
            value: Optional[str] = None,
    ) -> None:
        """
        Updates a section with key-value pairs or a single key-value pair in the config file.

        Parameters:
            section (str): The section name to update in the config file.
            data (Union[str, Dict[str, str]]): The key name or dictionary of key-value pairs to update in the section.
            value (str or None): The value to update if data is a single key name. Defaults to None.

        Raises:
            ValueError: If data is a single key name and value is not provided.
            Exception: If an error occurs while updating the config file.
        """
        try:
            # Check if data is a dictionary
            if isinstance(data, dict):
                # Update section with key-value pairs
                for key, value in data.items():
                    self.config.set(
                        section, key, str(value)
                    )  # value must be string to write to config file
            else:
                # Check if value is provided
                if value is None:
                    raise ValueError(
                        "Value must be provided when updating a single key"
                    )

                # Update section with single key-value pair
                self.config.set(section, data, str(value))

            # Write updated config to file
            with open(self.config_file, "w", encoding="UTF-8") as config_file:
                self.config.write(config_file)
        except Exception as e:
            logger.error(
                f"Error: Failed to update section '{section}' in config file. Error: {e}"
            )

    def delete_config(self, section: str, key: Optional[str] = None) -> None:
        """
        Deletes a section or key from the config file.

        Parameters:
            section (str): The section name to delete from the config file.
            key (str or None): The key name to delete from the section. If not provided, the entire section will be deleted. Defaults to None.

        Raises:
            KeyError: If either the section or key is not found in the config file.
            Exception: If an error occurs while deleting from the config file.
        """
        try:
            # Check if key is provided
            if key is not None:
                # Delete the specified key from the section
                self.config.remove_option(section, key)
            else:
                # Delete the entire section
                self.config.remove_section(section)

            # Write updated config to file
            with self.config_file.open("w", encoding="UTF-8") as config_file:
                self.config.write(config_file)
        except KeyError:
            logger.error(
                f"Error: Section '{section}' or key '{key}' not found in config file."
            )
        except Exception as e:
            logger.error(
                f"Error: Failed to delete section '{section}' or key '{key}' from config file. Error: {e}"
            )

    def print_config(self) -> None:
        """
        Prints the config in a readable and visually appealing format.

        This method iterates over each section and its keys and values in the config file and prints them in a visually appealing format.
        """
        for section in self.config.sections():
            print(f"[{section}]")
            for key, value in self.config.items(section):
                print(f"  {key} = {value}")
            print()

    def has_option(self, section: str, option: str) -> bool:
        """
        Returns True if the specified section has the specified option, otherwise returns False.

        Parameters:
            section (str): The section name to check.
            option (str): The option name to check.

        Returns:
            bool: True if the specified section has the specified option, otherwise returns False.
        """
        return self.config.has_option(section, option)

    def write_default_config(self) -> None:
        """
        Writes default values for each section in the config file.

        This method checks the system architecture and writes default values for each supported tool based on it.
        """
        arch = self.check_arch()
        linux = {
            "brotli": f"{ROOT_DIR}/bin/{arch.lower()}/brotli",
            "payload": f"{ROOT_DIR}/bin/{arch.lower()}/payload-dumper-go",
            "mke2fs": f"{ROOT_DIR}/bin/{arch.lower()}/mke2fs",
            "mke2fs_conf": f"{ROOT_DIR}/bin/{arch.lower()}/mke2fs.conf",
            "e2fsdroid": f"{ROOT_DIR}/bin/{arch.lower()}/e2fsdroid",
            "img2simg": f"{ROOT_DIR}/bin/{arch.lower()}/img2simg",
            "simg2img": f"{ROOT_DIR}/bin/{arch.lower()}/simg2img",
            "lpunpack": f"{ROOT_DIR}/bin/{arch.lower()}/lpunpack",
            "lpmake": f"{ROOT_DIR}/bin/{arch.lower()}/lpmake",
            "erofs": f"{ROOT_DIR}/bin/{arch.lower()}/extract.erofs",
        }
        if arch == "AMD64":
            linux.update(
                {
                    "fastboot": f"{ROOT_DIR}/bin/amd64/fastboot",
                    "fastboot_wsl": f"{ROOT_DIR}/bin/amd64/fastboot.exe",
                    "dump.erofs": f"{ROOT_DIR}/bin/amd64/dump.erofs",
                    "fsck.erofs": f"{ROOT_DIR}/bin/amd64/fsck.erofs",
                    "zstd": f"{ROOT_DIR}/bin/amd64/zstd.exe",
                }
            )

        configs = {
            "MAIN": {
                "main_project": f"{ROOT_DIR}/Projects/",
                "partitions": "super payload odm system vendor product system_ext system_dlkm cust mi_ext odm_a vendor_a product_a system_ext_a system_a odm_dlkm vendor_dlkm my_bigball my_carrier my_engineering my_heytap my_manifest my_product my_region my_stock odm_dlkm_a vendor_dlkm_a my_bigball_a my_carrier_a my_engineering_a my_heytap_a my_manifest_a my_product_a my_region_a my_stock_a",
                "proj_folders": "Config Build Backup Source Output",
                "excluded_partitions": "boot dtbo",
                "valid_extensions": ".raw .img .bin .br .dat .new .simg .sparse .erofs .zst .zstd .gz .gzip .lz4 .lzma .7z .zip",
                "log_level": "DEBUG",
            },
            "LINUX": linux,
            "DEVICE_INFO": {
                "METADATA_SIZE": "65536",
                "METADATA_SLOT": "2",
                "SUPER_PARTITION_NAME": "super",
                "SUPER_PARTITION_SIZE": "9126805504",
                "SUPER_PARTITION_GROUPS": "qti_dynamic_partitions",
                "QTI_DYNAMIC_PARTITIONS_PARTITION_LIST": "odm product system system_ext vendor mi_ext",
            },
            "EXTRA_INODE": {
                "odm": "2000",
                "vendor": "30000",
                "system": "30000",
                "system_ext": "30000",
                "product": "30000",
            },
            "EXTRA_SIZE": {
                "odm": "20485760",
                "vendor": "219430400",
                "system": "419430400",
                "system_ext": "104857600",
                "product": "104857600",
            },
        }

        for config_name, config in configs.items():
            self.write_config(config_name, config)


# create config instance
config = Configs(CONFIG_FILE)
# config.load_config("MAIN", "main_project")

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
import gzip
import lzma
import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import lz4.frame as lz4f
import py7zr
import zstandard
from loguru import logger
from tqdm import tqdm

from .ext4_extractor.ext4_info import ReadExt4
from .ext4_extractor.extract_ext4 import ExtractExt4
from .sdat2img.sdat2img import sdat2img

# Import necessary modules and handle ImportError
try:
    from .disk_usage import DiskUsage
    from .file_type import (
        validate_compression_type,
        validate_file_system,
        validate_zip_file,
        validate_7z_file,
    )
    from .config import Configs
    from .variables import CONFIG_FILE
    from .utils import copy_file, remove, run_command
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Ensure that the 'disk_usage', 'file_type', and 'utils' modules are located in the same directory as this file."
    ) from exc

# Load the configuration file
config_file_path = Path(CONFIG_FILE)
config = Configs(config_file_path)


class ExtractFirmware:
    """A class for extracting firmware from various file formats."""

    def __init__(
            self,
            main_project: Union[str, Path],
            input_firmware_path: Union[str, Path] = None,
            firmware_files: Union[str, List[str]] = None,
            valid_extensions: Union[str, List[str]] = None,
            bin_directory_path: Optional[Union[str, Path]] = None,
            excluded_partitions: Union[str, List[str]] = None,
            valid_partitions: Union[str, List[str]] = None,
            verbose: bool = False,
    ):
        """
        Initializes the ExtractFirmware object.

        Parameters:
            input_firmware_path (str or Path): The path to the input firmware file.
            main_project (str or Path, optional): The path to the main project directory.
                If this is None (the default), the output directory will be a subdirectory named "Source" in the main project directory.
            firmware_files (str or list, optional): The name or list of names of files to be extracted from the firmware file.
            valid_extensions (str or list, optional): Give the valid extensions of the firmware file.
                If this is None (the default), all files in the firmware file will be extracted.
            bin_directory_path (str or Path, optional): The path to the directory containing binary files used for extraction.
            verbose (bool): If True, print progress messages. Default is False.
            excluded_partitions (str or list, optional): The name or list of names of partitions to be excluded from extraction.
            valid_partitions (str or list, optional): The name or list of names of partitions to be included in extraction.

        Note:
            If input_firmware_path is not provided or empty, it will extract the files from output_directory.

        """
        # Initialize instance variables
        self.config = config

        self.verbose = verbose

        # check if main_project is a sub-project
        if str(main_project).endswith("Projects"):
            raise ValueError(
                f"Your working on main project folder, not sub-project! {main_project}"
            )

        self.main_project_directory = Path(main_project)

        # Convert input paths to Path objects if they are not None
        self.input_firmware_path = (
            Path(input_firmware_path) if input_firmware_path else None
        )
        self.bin_directory_path = (
            Path(bin_directory_path) if bin_directory_path else None
        )

        # If firmware_files is a single string, convert it to a list
        if isinstance(firmware_files, str):
            firmware_files = [firmware_files]

        # Load binary files for extraction from either the provided bin directory or the configuration
        if bin_directory_path is None:
            self.brotli = self.config.load_config("LINUX", "brotli")
            self.simg2img = self.config.load_config("LINUX", "simg2img")
            self.lpunpack = self.config.load_config("LINUX", "lpunpack")
            self.payload = self.config.load_config("LINUX", "payload")
        else:
            bin_path = Path(bin_directory_path)
            self.brotli = bin_path.joinpath("brotli").resolve()
            self.simg2img = bin_path.joinpath("simg2img").resolve()
            self.lpunpack = bin_path.joinpath("lpunpack").resolve()
            self.payload = bin_path.joinpath("payload").resolve()

        # Load excluded partitions from config.ini or from arguments
        self.excluded_partitions_config = self.config.load_config(
            "MAIN", "excluded_partitions"
        )

        if excluded_partitions is not None:
            self.EXCLUDED_PARTITIONS = set(excluded_partitions)
        elif self.excluded_partitions_config is not None:
            self.EXCLUDED_PARTITIONS = set(self.excluded_partitions_config.split(" "))
        else:
            logger.warning("WARNING!: No excluded partitions found")
            self.EXCLUDED_PARTITIONS = (
                set()
            )  # Initialize as an empty set instead of None

        # Load valid extensions from config.ini or from arguments
        self.valid_extensions = self.config.load_config("MAIN", "valid_extensions")

        if valid_extensions is not None:
            self.VALID_EXTENTIONS = set(valid_extensions)
        elif self.valid_extensions is not None:
            self.VALID_EXTENTIONS = set(self.valid_extensions.split(" "))
        else:
            logger.warning("WARNING!: No valid partitions found")
            self.VALID_EXTENTIONS = set()  # Initialize as an empty set instead of None

        # Load valid partitions from config.ini or from arguments
        self.valid_partitions_config = self.config.load_config("MAIN", "partitions")
        if valid_partitions is not None:
            self.VALID_PARTITIONS = set(valid_partitions)
        elif self.valid_partitions_config is not None:
            self.VALID_PARTITIONS = set(self.valid_partitions_config.split(" "))
        else:
            logger.warning("WARNING!: No valid partitions found")
            self.VALID_PARTITIONS = set()  # Initialize as an empty set instead of None

        # Set source directory path
        self.source_directory = self.main_project_directory.joinpath("Source")

        # Check if the output directory exists
        if not self.source_directory.exists():
            logger.warning(
                f"WARNING!: Output directory: {self.source_directory} not found"
            )
            return None

        # If input_firmware_path is provided and it's a non-empty file, proceed with extraction
        if (
                self.input_firmware_path
                and self.input_firmware_path.is_file()
                and not self.input_firmware_path.stat().st_size == 0
        ):
            # If it's a valid zip file, extract it
            if validate_zip_file(self.input_firmware_path):
                if firmware_files is None:
                    self.extract_zip_file(
                        self.input_firmware_path, self.source_directory
                    )
                else:
                    self.extract_zip_file(
                        self.input_firmware_path,
                        self.source_directory,
                        firmware_files,
                    )
            # FIXME extract 7z rom
            elif validate_7z_file(self.input_firmware_path):
                self.extract_7z_file(self.input_firmware_path, self.source_directory)
            else:
                # If the file type is not supported for extraction, copy the file to the output directory
                if self.source_directory is not None:
                    copy_file(
                        self.input_firmware_path,
                        self.source_directory.joinpath(self.input_firmware_path.name),
                    )
                else:
                    raise FileNotFoundError(
                        f"Input file: {self.input_firmware_path} or Output directory: {self.source_directory} not found"
                    )

        # Check if the output directory is not empty
        if not any(self.source_directory.iterdir()):
            raise ValueError(f"Output directory: {self.source_directory} is empty")

        # Define a dictionary to map compression types to their corresponding extraction methods
        compression_methods = {
            "gzip": self.extract_gz_file,
            "zstd": self.extract_zstd_file,
            "7z": self.extract_7z_file,
            "zip": self.extract_zip_file,
            "lzma": self.extract_lzma_file,
            "lz4": self.extract_lz4_file,
            "brotli": self.extract_brotli_file,
        }

        # Define a dictionary to map file system types to their corresponding extraction methods
        filesystem_methods = {
            "ext4": self.extract_ext4_file,
            "erofs": self.extract_erofs_file,
            "super": self.extract_super_file,
            "payload": self.extract_payload_file,
            "sparse": self.extract_sparse_file,
            # Add other file system types here
        }

        # Initialize a set to hold the previous iteration's files
        previous_files = set()

        # Initialize a counter for the number of iterations
        iteration_count = 0
        max_iterations = 100  # Set a limit for the maximum number of iterations

        # Loop until there are no more files to extract
        while iteration_count < max_iterations:
            # Increment the iteration counter
            iteration_count += 1

            # Validate the files to extract and convert the list to a set for efficient operations
            files_to_extract = set(
                self.validate_files_to_extract(self.source_directory)
            )

            # If there are no more files to extract or the set of files hasn't changed, break the loop
            if not files_to_extract or files_to_extract == previous_files:
                break

            # Initialize a set to hold the files that couldn't be extracted in this iteration
            remaining_files = set()

            # Iterate over each file in the list of files to extract
            for file_name in files_to_extract:
                file_name_path = file_name

                # Extract compressed files if the file's compression type is supported
                compression_type = validate_compression_type(file_name_path)
                if compression_type in compression_methods:
                    compression_methods[compression_type](
                        file_name_path, Path(file_name_path).parent
                    )
                else:
                    # If the file's compression type is not supported, add it to the list of remaining files
                    remaining_files.add(file_name_path)

                # Extract file systems if the file's system type is supported
                filesystem_type = validate_file_system(file_name_path)
                if filesystem_type in filesystem_methods:
                    filesystem_methods[filesystem_type](file_name_path)
                else:
                    # If the file's system type is not supported, remove it from the list of remaining files
                    remaining_files.discard(file_name_path)

            # Update the previous_files set for the next iteration
            previous_files = files_to_extract.copy()

            # Update the list of files to extract with the remaining files
            files_to_extract = remaining_files

        # If the maximum number of iterations was reached, print a warning message
        if iteration_count == max_iterations:
            logger.warning(
                "WARNING!: Maximum number of iterations reached. Some files may not have been extracted."
            )

    def validate_files_to_extract(
            self,
            output_directory: Union[str, Path],
            excluded_files: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Validates the files to extract based on their extensions and names.

        Parameters:
            output_directory (str or Path): The directory where the files are located.
            excluded_files (list, optional): The names of the files to be excluded from extraction.

        Returns:
            set: A set of valid files to extract.
        """

        # Initialize a set to store the valid files to extract
        partitions_to_extract = set()

        # Define a list of valid extensions if not provided
        if self.VALID_EXTENTIONS:
            # VALID_EXTENTIONS is a class variable that contains the valid extensions
            valid_extensions = self.VALID_EXTENTIONS

        else:
            valid_extensions = {
                ".bin",
                ".br",
                ".dat",
                ".new",
                ".simg",
                ".sparse",
                ".erofs",
                ".img",
                ".zst",
                ".zstd",
                ".gz",
                ".gzip",
                ".lz4",
                ".lzma",
                ".7z",
                ".zip",
                ".raw",
            }

        # Define a helper function to check if a file extension is valid
        def is_valid_extension(file_ext: str) -> bool:
            return file_ext in valid_extensions

        # EXCLUDED_PARTITIONS is a class variable that contains the partitions to be excluded
        excluded_partitions = self.EXCLUDED_PARTITIONS

        # VALID_PARTITIONS is a class variable that contains the valid partitions
        valid_partitions = self.VALID_PARTITIONS

        # Extend the EXCLUDED list if user specifies files to be excluded
        if excluded_files is not None:
            excluded_partitions.update(excluded_files)

        # Initialize a list to store the directory contents
        dir_contents = []

        # Walk through the output directory and add all non-hidden files to dir_contents
        for dirpath, dirnames, filenames in os.walk(output_directory):
            for file in filenames:
                if file.startswith("."):
                    continue
                if Path(os.path.join(dirpath, file)).stat().st_size != 0:
                    dir_contents.append(os.path.join(dirpath, file))

        # Iterate over each file in dir_contents
        for file in dir_contents:
            file_path = file
            file_name, file_exts = os.path.splitext(os.path.basename(file_path))

            # Initialize a list to store the extensions of a multi-extension file
            extentions = [file_exts]

            # Check for multi-extension files and add all extensions to extentions
            while file_name.count(".") > 0:
                file_name, ext = os.path.splitext(file_name)
                extentions.append(ext)

            # If the filename is not excluded and is a valid partition, check its extensions
            if file_name not in excluded_partitions and file_name in valid_partitions:
                for ext in extentions:
                    # If an extension is valid, add the filepath to partitions_to_extract
                    if is_valid_extension(ext):
                        partitions_to_extract.add(file_path)

        if not partitions_to_extract:
            logger.warning(
                f"WARNING!: Check parititions list and excluded partitions in {CONFIG_FILE} ignore it if images extracted."
            )

        return partitions_to_extract

    def list_zip_info(self, input_zip_file: Union[str, Path]) -> Dict[str, int]:
        """
        This function takes in a path to a zip file and returns a dictionary containing
        information about the files within the zip file. The keys of the dictionary are the
        names of the files and the values are their sizes in bytes.

        Parameters:
            input_zip_file (Union[str, Path]): The path to the input zip file. This can be a string or a Path object.

        Raises:
            FileNotFoundError: This exception is raised if the input file does not exist.

        Returns:
            dict: A dictionary where the keys are the names of the files in the zip file and the values are their sizes in bytes.

        """

        # Convert input to Path object to ensure compatibility with different input types
        input_zip_file = Path(input_zip_file)

        # Check if input file exists, raise a FileNotFoundError if it does not
        if not input_zip_file.exists():
            raise FileNotFoundError(f"Input file: {input_zip_file} not found")

        # Initialize an empty dictionary to store the file information. Each key-value pair will represent a file and its size
        zip_info = {}

        # Open the zip file in read mode to access its contents
        with zipfile.ZipFile(input_zip_file, "r") as zf:
            # Iterate over the information of all files in the zip file
            for info in zf.infolist():
                # Exclude directories from the dictionary
                if not info.filename.endswith("/"):
                    # Add the name and size of each file to the dictionary
                    zip_info[info.filename] = info.file_size

        # Return the dictionary of file information
        return zip_info

    def extract_zip_file(
            self,
            input_zip_file: Union[str, Path],
            output_directory: Union[str, Path],
            file_names: Optional[Union[str, List[str]]] = None,
    ) -> None:
        """
        Extracts specified files from a zip archive and displays a progress bar.

        Parameters:
            input_zip_file (Union[str, Path]): The path to the input zip file.
            output_directory (Union[str, Path]): The path to the output directory where the decompressed data will be saved.
            file_names (Optional[Union[str, List[str]]]): The name or list of names of files to be extracted.
                If this is None (the default), all files in the zip archive will be extracted.

        Raises:
            FileNotFoundError: If the input file does not exist, is empty, or is a directory.
            ValueError: If the input file is not a valid zip file.
            KeyError: If any of the specified files do not exist in the zip archive.
            KeyboardInterrupt: If the extraction process is interrupted manually.
        """

        # Convert input arguments to Path objects for easier manipulation
        input_zip_file = Path(input_zip_file)
        output_directory = Path(output_directory)

        # Print the names of the input and output files if verbose mode is enabled
        if self.verbose:
            logger.info(f"Detected an installer zip file.")
            logger.info(f"\tFile name: [{input_zip_file.name}]")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_zip_file, False)}]"
            )

        # Initialize an empty list to store the names of files to be extracted
        files_to_extract = []

        # Get information about all files in the zip archive
        file_info_dict = self.list_zip_info(input_zip_file)

        # Check if any specific files are provided for extraction
        if file_names is not None:
            # If a single filename is provided as a string, convert it to a list
            if isinstance(file_names, str):
                file_names = [file_names]

            # Go through all files in the zip archive and add any matching filenames to the list of files to extract
            for filename in file_info_dict:
                if os.path.basename(filename) in file_names:
                    files_to_extract.append(filename)
        else:
            # If no specific files are provided, extract all files in the archive
            files_to_extract = list(file_info_dict.keys())

        # Calculate the total size of all files to be extracted for progress tracking
        total_size = sum(file_info_dict[filename] for filename in files_to_extract)

        # Initialize a progress bar with the total size of all files to be extracted
        with tqdm(
                total=total_size,
                desc="Extracting",
                ncols=shutil.get_terminal_size().columns,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
        ) as progress_bar:
            # Open the zip archive
            with zipfile.ZipFile(input_zip_file, "r") as zip_archive:
                # Go through all files to be extracted
                for filename in files_to_extract:
                    try:
                        # Ensure directory exists before extracting
                        output_directory.joinpath(os.path.dirname(filename)).mkdir(
                            parents=True, exist_ok=True
                        )

                        # Update the description of the progress bar with the name of the extracted file
                        progress_bar.set_description(
                            f"Extracted ({os.path.basename(filename)})"
                        )

                        # Open the source file in the zip archive and the destination file on disk
                        with zip_archive.open(filename) as source_file, open(
                                output_directory.joinpath(filename), "wb"
                        ) as destination_file:
                            # Read from the source file and write to the destination file in chunks of 10MB
                            for chunk in iter(
                                    lambda: source_file.read(10 * 1024 * 1024), b""
                            ):
                                destination_file.write(chunk)
                                # Update the progress bar by the size of the chunk
                                progress_bar.update(len(chunk))

                    except KeyboardInterrupt:
                        # If a keyboard interrupt is detected during extraction,
                        # delete any partially-extracted files and exit.
                        os.remove(output_directory.joinpath(filename))
                        logger.error(
                            f"\nExtraction interrupted. Removed {output_directory.joinpath(filename)}"
                        )
                        return False

                    except KeyError:
                        # If a specified file does not exist in the zip archive, print an error message and exit.
                        logger.error(f"Can't extract {file_names} from archive")
                        return False

        # If all files were extracted successfully, return True
        return True

    def extract_gz_file(
            self,
            input_gzip_file: Union[str, Path],
            output_file: Union[str, Path],
    ) -> bool:
        """
        This method is used to decompress a gzip file to a given output file.

        Parameters:
            input_gzip_file (Union[str, Path]): This is the path to the input gzip file.
            output_file (Union[str, Path]): This is the path to the output file where the decompressed data will be saved.

        Raises:
            FileNotFoundError: This error is raised if the input file does not exist or is empty.
            IsADirectoryError: This error is raised if the output file is a directory.
            KeyboardInterrupt: This error is raised if the extraction process is interrupted manually.

        Returns:
            bool: This method returns True if extraction was successful, False otherwise.
        """

        # Convert input arguments to Path objects for easier manipulation
        input_gzip_file = Path(input_gzip_file)
        output_file = Path(output_file)

        # If verbose mode is enabled, print details about the detected gzip file
        if self.verbose:
            logger.info("Detected a gz file, commonly used for GSI.")
            logger.info(f"\tFile name: [{input_gzip_file.name}].")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_gzip_file, False)}]"
            )

        # ensure do not write on the same file
        if input_gzip_file.suffix in [".gz", ".gzip"]:
            # If the file has a .gz or .gzip extension, remove it
            input_gzip_file = input_gzip_file
            # Check if the file already has a .img extension
            if Path(input_gzip_file.stem).suffix != ".img":
                # If not, set the output file with .img extension
                output_file = output_file / Path(input_gzip_file.stem).with_suffix(
                    ".img"
                )
            else:
                # If yes, just remove the .gz or .gzip extension
                output_file = output_file / input_gzip_file.stem
        else:
            # If the file doesn't have a .gz or .gzip extension, store the previous extension,
            # rename the file with a .gz extension and set it as the input file,
            # and set the output file with the previous extension
            previous_suff = input_gzip_file.suffix
            input_gzip_file.rename(input_gzip_file.with_suffix(".gz"))
            input_gzip_file = input_gzip_file.with_suffix(".gz")
            output_file = output_file / Path(input_gzip_file.stem).with_suffix(
                previous_suff
            )

        # Check if output file is a directory. If yes, append the input file name to the output directory path
        if output_file.is_dir():
            output_file = output_file.joinpath(input_gzip_file.name).with_suffix("")

        # If verbose mode is enabled, print the names of the input and output files
        if self.verbose:
            logger.info(f"Extracting [{input_gzip_file.name}] to [{output_file}]")

        # Try to open the input gzip file in read mode and the output file in write mode
        try:
            with gzip.open(input_gzip_file, "rb") as in_gzip_file, open(
                    output_file, "wb"
            ) as out_file:
                # Initialize a progress bar with the total size of the input file
                with tqdm(
                        total=input_gzip_file.stat().st_size,
                        desc=f"Extracting ({input_gzip_file.name})",
                        ncols=shutil.get_terminal_size().columns,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                ) as progress_bar:
                    # Read from the input file and write to the output file in chunks of 10MB
                    for chunk in iter(
                            lambda: in_gzip_file.read(10 * 1024 * 1024), b""
                    ):  # 10MB chunks
                        out_file.write(chunk)
                        # Update the progress bar by the size of the chunk
                        progress_bar.update(len(chunk))
                remove(input_gzip_file)
                return True
        except KeyboardInterrupt:
            # If a keyboard interrupt is detected during extraction, delete any partially-extracted files and exit
            os.remove(output_file)
            logger.error(f"\nExtraction interrupted. Removed {output_file}")
            return False

    def extract_zstd_file(
            self,
            input_zstd_file: Union[str, Path],
            output_file: Union[str, Path],
    ) -> None:
        """
        Decompresses a zstd compressed file to a given output file.

        Parameters:
            input_zstd_file (str): The path to the input zstd compressed file.
            output_file (str): The path to the output file where the decompressed data will be saved.
            verbose (bool): If True, print progress messages. Default is False.

        Raises:
            KeyboardInterrupt: If the extraction process is interrupted manually.
        """

        input_zstd_file = Path(input_zstd_file)
        output_file = Path(output_file)

        if self.verbose:
            logger.info("Detected a zstd file, commonly used to compress [super.img].")
            logger.info(f"\tFile name: [{input_zstd_file.name}].")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_zstd_file, False)}]"
            )

        # ensure do not write on the same file
        if input_zstd_file.suffix in [".zst", ".zstd"]:
            # If the file has a .zst or .zstd extension, remove it
            input_zstd_file = input_zstd_file
            # Check if the file already has a .img extension
            if Path(input_zstd_file.stem).suffix != ".img":
                # If not, set the output file with .img extension
                output_file = output_file / Path(input_zstd_file.stem).with_suffix(
                    ".img"
                )
            else:
                # If yes, just remove the .zst or .zstd extension
                output_file = output_file / input_zstd_file.stem
        else:
            # If the file doesn't have a .zst or .zstd extension, store the previous extension,
            # rename the file with a .zst extension and set it as the input file,
            # and set the output file with the previous extension
            previous_suff = input_zstd_file.suffix
            input_zstd_file.rename(input_zstd_file.with_suffix(".zst"))
            input_zstd_file = input_zstd_file.with_suffix(".zst")
            output_file = output_file / Path(input_zstd_file.stem).with_suffix(
                previous_suff
            )

        if output_file.is_dir():
            output_file = output_file.joinpath(input_zstd_file.name).with_suffix("")

        # Get the total size of the input file for the progress bar
        total_size = input_zstd_file.stat().st_size

        try:
            # Open the input zstd file in read mode and the output file in write mode
            with zstandard.open(input_zstd_file, "rb") as in_zstd_file, open(
                    output_file, "wb"
            ) as out_file:
                # Initialize a progress bar with the total size of the input file
                with tqdm(
                        total=total_size,
                        desc=f"Extracting ({input_zstd_file.name})",
                        ncols=shutil.get_terminal_size().columns,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                ) as progress_bar:
                    # Read from the input file and write to the output file in chunks of 10MB
                    for chunk in iter(
                            lambda: in_zstd_file.read(10 * 1024 * 1024), b""
                    ):  # 10MB chunks
                        out_file.write(chunk)
                        # Update the progress bar by the size of the chunk
                        progress_bar.update(len(chunk))
            remove(input_zstd_file)
            return True
        except KeyboardInterrupt:
            # If a keyboard interrupt is detected during extraction, delete any partially-extracted files and exit
            os.remove(output_file)
            logger.error(f"\nExtraction interrupted. Removed {output_file}")
            return False

    def extract_7z_file(
            self,
            input_7z_file: Union[str, Path],
            output_directory: Union[str, Path],
    ) -> None:
        """
        This function extracts a 7z compressed file to a specified output directory.

        Args:
            input_7z_file (Union[str, Path]): The path to the input 7z compressed file.
            output_directory (Union[str, Path]): The path to the output directory where the decompressed data will be saved.

        Returns:
            None

        Raises:
            KeyboardInterrupt: If the extraction process is interrupted manually.
        """

        # Convert input arguments to Path objects for easier manipulation
        input_7z_file = Path(input_7z_file)
        output_directory = Path(output_directory)

        # If verbose mode is enabled, print details about the detected 7z file
        if self.verbose:
            logger.info("Detected a 7z file, not commonly used.")
            logger.info(f"\tFile name: [{input_7z_file.name}].")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_7z_file, False)}]"
            )

        try:
            # Open the 7z file in read mode
            with py7zr.SevenZipFile(input_7z_file, mode="r") as archive:
                # Get the total number of files in the archive
                total_files = len(archive.getnames())

                # Initialize a progress bar for the extraction process
                with tqdm(
                        total=total_files,
                        desc=f"Extracting ({input_7z_file.name})",
                        ncols=shutil.get_terminal_size().columns,
                        unit="file",
                ) as progress_bar:
                    # Loop through each file in the archive
                    for filename in archive.getnames():
                        try:
                            # Extract the current file to the output directory
                            archive.extract(targets=[filename], path=output_directory)
                            # Update the progress bar
                            progress_bar.update(1)
                        except KeyboardInterrupt:
                            # If a keyboard interrupt is detected during extraction, delete any partially-extracted files and raise the exception
                            for file in Path(output_directory).rglob(filename):
                                os.remove(file)
                            return False
            return True  # Return True after successful extraction

        except py7zr.exceptions.Bad7zFile as e:
            # Print an error message if there was an issue with the 7z file
            logger.error(f"Can't extract {input_7z_file} due to error: {str(e)}")
            return False  # Return False if there was an error during extraction

    def extract_lzma_file(
            self,
            input_lzma_file: Union[str, Path],
            output_file: Union[str, Path],
    ) -> None:
        """
        Method to extract an LZMA compressed file to a given output file.

        Parameters:
            input_lzma_file (Union[str, Path]): The path to the input LZMA compressed file.
            output_file (Union[str, Path]): The path to the output file where the decompressed data will be saved.

        Raises:
            KeyboardInterrupt: If the extraction process is interrupted manually.
            lzma.LZMAError: If there is an error during the extraction process.
        """

        # Convert input arguments to Path objects for easier manipulation
        input_lzma_file = Path(input_lzma_file)
        output_file = Path(output_file)

        # If verbose mode is enabled, print details about the detected lzma file
        if self.verbose:
            logger.info("Detected a lzma file, not commonly used.")
            logger.info(f"\tFile name: [{input_lzma_file.name}].")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_lzma_file, False)}]"
            )

        # If the output file is a directory, join the input file name to it
        if output_file.is_dir():
            output_file = output_file.joinpath(input_lzma_file.with_suffix("").name)

        try:
            # Open the input LZMA file in read mode
            with lzma.open(input_lzma_file, mode="rb") as archive:
                # Get the total size of the input LZMA file for the progress bar
                total_size = os.path.getsize(input_lzma_file)

                # Initialize a progress bar with the total size of the input LZMA file
                with tqdm(total=total_size, unit="B", unit_scale=True) as pbar:
                    # Open the output file in write mode
                    with open(output_file, "wb") as outfile:
                        try:
                            # Extract the file in chunks and update the progress bar
                            for chunk in iter(lambda: archive.read(1024), b""):
                                outfile.write(chunk)
                                pbar.update(len(chunk))
                        except KeyboardInterrupt:
                            # If a keyboard interrupt is detected during extraction,
                            # delete any partially-extracted files and exit.
                            os.remove(output_file)
                            logger.error(
                                f"\nExtraction interrupted. Removed {output_file}"
                            )
                            return False

            return True  # Return True after successful extraction

        except lzma.LZMAError as e:
            logger.error(f"Can't extract {input_lzma_file} due to error: {str(e)}")
            return False  # Return False if there was an error during extraction

    def extract_lz4_file(
            self,
            input_lz4_file: Union[str, Path],
            output_file: Union[str, Path],
    ) -> None:
        """
        Method to extract an LZ4 compressed file to a given output file.

        Parameters:
            input_lz4_file (Union[str, Path]): The path to the input LZ4 compressed file.
            output_file (Union[str, Path]): The path to the output file where the decompressed data will be saved.

        Raises:
            KeyboardInterrupt: If the extraction process is interrupted manually.
            RuntimeError: If there is an error during the extraction process.
        """

        # Convert input arguments to Path objects for easier manipulation
        input_lz4_file = Path(input_lz4_file)
        output_file = Path(output_file)

        # If verbose mode is enabled, print details about the detected lz4 file
        if self.verbose:
            logger.info("Detected a lz4 file, not commonly used.")
            logger.info(f"\tFile name: [{input_lz4_file.name}].")
            logger.info(
                f"\tSize: [{DiskUsage(human_readable=True).calc_disk_usage(input_lz4_file, False)}]"
            )

        # If the output file is a directory, join the input file name to it
        if output_file.is_dir():
            output_file = output_file.joinpath(input_lz4_file.with_suffix("").name)

        try:
            # Open the input LZ4 file in read mode
            with lz4f.open(input_lz4_file, mode="rb") as archive:
                # Get the total size of the input LZ4 file for the progress bar
                total_size = os.path.getsize(input_lz4_file)

                # Initialize a progress bar with the total size of the input LZ4 file
                with tqdm(total=total_size, unit="B", unit_scale=True) as pbar:
                    # Open the output file in write mode
                    with open(output_file, "wb") as outfile:
                        try:
                            # Extract the file in chunks and update the progress bar
                            for chunk in iter(lambda: archive.read(1024), b""):
                                outfile.write(chunk)
                                pbar.update(len(chunk))
                        except KeyboardInterrupt:
                            # If a keyboard interrupt is detected during extraction,
                            # delete any partially-extracted files and exit.
                            os.remove(output_file)
                            logger.error(
                                f"\nExtraction interrupted. Removed {output_file}"
                            )
                            return False

            return True  # Return True after successful extraction

        except RuntimeError as e:
            logger.error(f"Can't extract {input_lz4_file} due to error: {str(e)}")
            return False  # Return False if there was an error during extraction

    def extract_brotli_file(
            self, input_brotli_file: Union[str, Path], output_dir: Union[str, Path]
    ) -> None:
        # Convert the input file to a Path object for easier manipulation
        input_brotli_file = Path(input_brotli_file)

        # Define the output directory for extraction
        output_dir = Path(output_dir)

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(
                f"Initiating extraction of {input_brotli_file} to the directory {output_dir}."
            )

        img_name = str(input_brotli_file.name).split(".", maxsplit=1)[0]
        sdat_img = output_dir / f"{img_name}.new.dat"
        transfer_list = output_dir / f"{img_name}.transfer.list"
        img_output = output_dir / f"{img_name}.img"

        if self.verbose:
            logger.info(f"Converting {img_name}.new.dat.br to {img_name}.new.dat")

        cmd = [str(self.brotli), "-df", str(input_brotli_file)]
        _, ret = run_command(cmd, verbose=True)

        if ret == 0:
            remove(input_brotli_file)  # cleanup after extract

        if self.verbose:
            logger.info(f"Converting {img_name}.new.dat to {img_name}.img")

        if sdat2img(transfer_list, sdat_img, img_output, verbose=self.verbose):
            remove(sdat_img)  # cleanup after extract
            remove(transfer_list)  # cleanup after extract
            return True

        return False

    def extract_super_file(self, input_super_file: Union[str, Path]) -> bool:
        """
        Extracts the super image file if it is valid and exists.

        Args:
            input_super_file (Union[str, Path]): The input super image file to be extracted.

        Raises:
            CalledProcessError: If there is an error during the extraction process.

        Returns:
            bool: True if the extraction is successful, False otherwise.
        """

        # Convert the input file to a Path object for easier manipulation
        input_super_file = Path(input_super_file)

        # Define the output directory for extraction
        output_dir = self.source_directory

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(
                f"Initiating extraction of {input_super_file} to the directory {output_dir}."
            )

        # Run the command to extract the super image
        cmd = [str(self.lpunpack), str(input_super_file), str(output_dir)]
        _, ret = run_command(cmd)

        # If the extraction is successful, remove the input file and return True
        if ret == 0:
            remove(input_super_file)  # cleanup after extract
            return True

        # If the extraction fails, return False
        return False

    def extract_payload_file(self, input_payload_file: Union[str, Path]) -> bool:
        """
        Extracts a payload file and saves the output in the project directory.

        Parameters:
            input_payload_file (Union[str, Path]): The path to the input payload file. This can be a string or a Path object.

        Raises:
            CalledProcessError: If there is an error during the extraction process.

        Returns:
            bool: True if extraction was successful, False otherwise.
        """

        # Convert the input argument to a Path object for easier manipulation
        input_payload_file = Path(input_payload_file)

        # Define the directory path where the extracted files will be saved
        output_dir = self.source_directory

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(
                f"Initiating extraction of {input_payload_file} to the directory {output_dir}."
            )

        # Define the command for extraction
        cmd = [str(self.payload), "-o", str(output_dir), str(input_payload_file)]

        # Run the command and capture the return code
        _, ret = run_command(cmd, verbose=self.verbose)

        # If extraction was successful, remove the input image and return True
        if ret == 0:
            remove(input_payload_file)
            return True

        # If extraction failed, return False
        return False

    def extract_ext4_file(self, input_ext4_file: Union[str, Path]) -> bool:
        """
        This function extracts an ext4 file and saves the output in the project directory.

        Parameters:
            input_ext4_file (Union[str, Path]): The path to the input ext4 file.

        Raises:
            FileNotFoundError: If the required Python scripts are not found in the config file.
            CalledProcessError: If there is an error during extraction.

        Returns:
            bool: True if extraction was successful, False otherwise.
        """

        # Convert input argument to Path object for easier manipulation
        input_ext4_file = Path(input_ext4_file)

        # Define paths for extraction
        filename = input_ext4_file.stem
        input_img = input_ext4_file
        out_dir = self.main_project_directory / "Output" / filename
        info_dir = self.main_project_directory / "Config"

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(f"Identified file system type for {input_img} as ext4.")
            logger.info(f"Initiating extraction of information from {filename}.")

        if not ReadExt4(image_path=input_img, out_dir=info_dir).read_ext4():
            return False

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(
                f"Initiating extraction of {input_img} to the directory {out_dir}."
            )

        if ExtractExt4(image_name=input_img, out_dir=out_dir).extract_ext4():
            remove(input_img)
            return True

        return False

    def extract_erofs_file(self, input_erofs_file: Union[str, Path]) -> None:
        """
        Extracts an erofs file and saves the output in the project directory.

        Parameters:
            input_erofs_file (Union[str, Path]): The path to the input erofs file.

        Raises:
            CalledProcessError: If there is an error during extraction.

        Returns:
            bool: True if extraction was successful, False otherwise.
        """

        # Convert input argument to Path object for easier manipulation
        input_erofs_file = Path(input_erofs_file)

        # Load configuration values from the config file
        erofs = Path(self.config.load_config("LINUX", "erofs"))

        # Prepare the paths for the input image file, output directory and info directory
        input_img = self.main_project_directory / "Source" / input_erofs_file.name
        output_dir = self.main_project_directory / "Output"
        info_dir = self.main_project_directory / "Config"

        # Print information about the extraction process if verbose mode is enabled
        if self.verbose:
            logger.info(f"Identified file system type for {input_img} as erofs")
            logger.info(
                f"Initiating extraction of {input_erofs_file} to the directory {output_dir}."
            )

        # Prepare the command to be run for extraction
        cmd = [
            str(erofs),
            "-i",
            str(input_img),
            "-o",
            str(output_dir),
            "-f",
            "-x",
            "-C",
            str(info_dir),
        ]

        # Run command and capture return code
        _, ret = run_command(cmd, verbose=True)

        # If extraction was successful, remove the input image and return True
        if ret == 0:
            remove(input_img)
            return True

        # If the extraction was not successful, return False
        return False

    def extract_f2fs_file(self, input_f2fs_file: Union[str, Path]) -> None:
        # TODO
        pass

    def extract_sparse_file(self, input_sparse_file: Union[str, Path]) -> bool:
        input_sparse_file = Path(input_sparse_file)
        total_chunks = 20
        chunk_list = []
        is_splited = False

        basename = input_sparse_file.parent
        filename = input_sparse_file.stem
        suffix = input_sparse_file.suffix.lstrip('.')
        if suffix.isdigit() and 0 <= int(suffix) < total_chunks:
            split_files = [basename / f"{filename}.{i}" for i in range(total_chunks)]
            chunk_list = [file for file in split_files if file.exists()]
            is_splited = bool(chunk_list)

        output_dir = self.main_project_directory / "Source"
        img_name = str(input_sparse_file.name).split(".", maxsplit=1)[0]
        img_output = output_dir / f"{img_name}.raw"

        if self.verbose:
            logger.info(
                f"Initiating extraction of {' '.join(map(str, chunk_list)) if is_splited else input_sparse_file} to the directory {output_dir}."
            )

        cmd = [self.simg2img] + (chunk_list + [img_output] if is_splited else [input_sparse_file, img_output])
        _, ret = run_command(cmd)

        if ret == 0:
            for file in (chunk_list if is_splited else [input_sparse_file]):
                remove(file)
            return True

        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Firmware")
    parser.add_argument(
        "input_zip_firmware", nargs="?", default="", help="Input ZIP firmware"
    )
    parser.add_argument(
        "output_directory", nargs="?", default="", help="Output directory"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode"
    )

    args = parser.parse_args()

    input_zip_firmware = args.input_zip_firmware
    output_directory = args.output_directory
    verbose = True

    EF = ExtractFirmware(input_zip_firmware, output_directory, verbose=verbose)

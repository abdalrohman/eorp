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
import gc
import gzip
import os
import platform
import re
import shlex
import shutil
import struct
import subprocess
import time
from datetime import datetime
from functools import partial, wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from warnings import warn

import pytz
import zstandard
from loguru import logger

from .disk_usage import DiskUsage
from .config import config


def get_local_time_timezone(timezone="Asia/Riyadh"):
    # Get the current time in UTC
    current_time_utc = datetime.now(pytz.utc)

    # Convert to San Francisco's time zone (PST/PDT)
    sf_time_zone = pytz.timezone(timezone)
    local_time = current_time_utc.astimezone(sf_time_zone)

    # You may format it as you desire, including AM/PM
    formatted_time = local_time.strftime("%Y-%m-%d %I:%M:%S %p %Z%z")

    return formatted_time


def get_local_time(timezone=None):
    if timezone is not None:
        return get_local_time_timezone(timezone)
    else:
        # Get the current time, which will be in the local timezone of the computer
        local_time = datetime.now()

        # You may format it as you desire, including AM/PM
        formatted_time = local_time.strftime("%Y-%m-%d %I:%M:%S %p %Z%z")

        return formatted_time


def force_free_memory():
    """Forces Python's garbage collector to free unused memory.

    Returns:
        int: The number of bytes freed.
    """

    gc.collect()
    return gc.get_stats()[0]


def deprecated(func=None, *, message=None):
    """This is a decorator which can be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used."""

    if func is None:
        return partial(deprecated, message=message)

    @wraps(func)
    def new_func(*args, **kwargs):
        if message:
            warn(
                message,
                category=DeprecationWarning,
                stacklevel=2,
            )
        else:
            warn(
                f"Call to deprecated function {func.__name__}.",
                category=DeprecationWarning,
                stacklevel=2,
            )
        return func(*args, **kwargs)

    return new_func


def run_command(
        arg: List[Union[str, Path]],
        env: Optional[Dict[str, str]] = None,
        verbose: bool = True,
        capture_output: bool = True,
        **kwargs: Any,
) -> Tuple[str, int]:
    """
    Runs the given command and returns the output.

    Parameters:
        arg (List[Union[str, Path]]): The command represented as a list of strings or Path objects.
        verbose (bool): Whether the commands should be shown. Default True.
        capture_output (bool): Whether to capture the command's output. Default True.
        env (Dict[str, str]): A dictionary of additional environment variables. Default None.
        kwargs (Any): Any additional arguments to be passed to subprocess.run(), such as stdin, etc. stdout and stderr will default to subprocess.PIPE unless the caller specifies any of them.

    Returns:
        Tuple[str, int]: A tuple containing two elements:
            - The output of the command if capture_output is True, else an empty string.
            - The exit code of the command.

    Raises:
        subprocess.CalledProcessError: If the command exits with a non-zero return code.
        KeyboardInterrupt: If the execution is interrupted by Ctrl+C.
        Exception: If any other exception occurs.
    """
    start_time = time.time()

    # Convert all elements in arg to string
    arg = [str(a) for a in arg]

    if env is not None:
        logger.info("Env: {}", env)
        env_copy = os.environ.copy()
        env_copy.update(env)
        kwargs.setdefault("env", env_copy)

    if verbose:
        logger.info(f"Running: {shlex.join(arg)}")

    if capture_output:
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.PIPE)
        kwargs.setdefault("universal_newlines", True)

    try:
        proc = subprocess.run(arg, **kwargs, check=True)
        output = proc.stdout if capture_output else ""
    except subprocess.CalledProcessError as exc:
        logger.error(
            f"Failed to run command '{arg}' (exit code {exc.returncode}):\n{exc.output}"
        )
        raise
    except KeyboardInterrupt as exc:
        logger.info("\nTerminating...")
        raise SystemExit(1) from exc
    except Exception as exc:
        logger.exception(f"Failed to run command '{arg}': {exc}")
        raise SystemExit(1) from exc

    runtime = time.time() - start_time
    if verbose:
        logger.info(f"Execution time: {runtime} seconds")

    return output, proc.returncode


def get_environment_variable(name: str) -> Tuple[Optional[str], List[str]]:
    """
    Retrieves the value of the specified environment variable. This function is compatible with both Windows and Unix-based systems.

    Parameters:
        name (str): The name of the environment variable to retrieve.

    Returns:
        Tuple[Optional[str], List[str]]: A tuple containing two elements:
            - The value of the environment variable if it exists, None otherwise.
            - A list of error messages, if any occurred during the retrieval process.

    Raises:
        Exception: If there is a failure in retrieving the environment variable on Windows due to reasons other than the variable not being found.
    """
    error_messages = []

    if platform.system() == "Windows":
        from ctypes import FormatError, wintypes

        value = ""
        req_size = wintypes.DWORD()
        gev_failure = 0
        win32_api_error = 0

        def write_last_error(error_code: int, message: str, name: str) -> None:
            """Prints an error message for a given error code."""
            error_messages.append(f"{message} {name}: {FormatError(error_code)}")

        # Try to get the size of the environment variable value
        if ctypes.windll.kernel32.GetEnvironmentVariableW(name, None, 0) == gev_failure:
            win32_api_error = ctypes.GetLastError()
            if win32_api_error == 203:  # ERROR_ENVVAR_NOT_FOUND
                error_messages.append(f"No environment variable by the name '{name}'")
                return None, error_messages
            else:
                write_last_error(
                    win32_api_error, "Failed to get size for environment variable", name
                )
                raise Exception(f"Failed to get environment variable: {name}")
        else:
            # Get the value of the environment variable
            req_size = ctypes.windll.kernel32.GetEnvironmentVariableW(name, None, 0)
            value = ctypes.create_unicode_buffer(req_size)
            if (
                    ctypes.windll.kernel32.GetEnvironmentVariableW(name, value, req_size)
                    == gev_failure
            ):
                write_last_error(
                    ctypes.GetLastError(), "Failed to get environment variable", name
                )
                raise Exception(f"Failed to get environment variable: {name}")
        return value.value, error_messages
    else:
        # Get the value of the environment variable on Unix-based systems
        value = os.environ.get(name)
        if value is None:
            error_messages.append(f"No environment variable by the name '{name}'")
        return value, error_messages


def create_directory(dir_name: Path) -> int:
    """
    Creates a directory and its parent directories if they do not exist.

    Parameters:
        dir_name (Path): The name of the directory to create.

    Returns:
        int: 0 if the directory was created successfully, 1 if it already exists, -1 if an error occurred.

    Raises:
        PermissionError: If the user does not have permission to create the directory.
        OSError: If an error occurs while creating the dire
    """
    # if isinstance(dir_name, str):
    dir_name = Path(dir_name)

    try:
        if dir_name.exists():
            logger.info(f"Directory already exists: {dir_name}")
            return 1

        os.makedirs(dir_name)
        logger.info(f"Directory created: {dir_name}")
        return 0
    except FileExistsError:
        logger.info(f"Directory already exists: {dir_name}")
        return 1
    except PermissionError as e:
        logger.error(f"Permission denied while creating directory: {dir_name}")
        logger.exception(str(e))
        return -1
    except OSError as e:
        logger.error(f"Error creating directory: {dir_name}")
        logger.exception(str(e))
        return -1


def remove(path: Path) -> int:
    """
    Removes a file or directory.

    Parameters:
        path (Path): The path of the file or directory to be removed.

    Returns:
        int: 0 if the file or directory was successfully removed, 1 if it does not exist, -1 if an error occurred.

    Raises:
        PermissionError: If the user does not have permission to remove the file or directory.
        OSError: If an error occurs while removing the file or directory.
    """
    # if isinstance(path, str):
    path = Path(path)

    try:
        if path.is_file():
            # Remove a file
            if path.exists():
                os.remove(path)
                logger.info(f"File '{path}' successfully removed.")
                return 0
            else:
                logger.info(f"File '{path}' does not exist.")
                return 1
        elif path.is_dir():
            # Remove a directory
            if path.exists():
                shutil.rmtree(path)
                logger.info(f"Directory '{path}' successfully removed.")
                return 0
            else:
                logger.info(f"Directory '{path}' does not exist.")
                return 1
        else:
            logger.info(f"Path '{path}' is neither a file nor a directory.")
            return 1
    except FileNotFoundError:
        logger.info(f"File or directory '{path}' does not exist.")
        return 1
    except PermissionError as e:
        logger.error(f"Permission denied while removing '{path}': {e}")
        return -1
    except OSError as e:
        logger.error(f"Error while removing '{path}': {e}")
        return -1


def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    Copies a file from the source path to the destination path while displaying a progress bar.
    If the user interrupts the process (e.g., by pressing ctrl + c), the program exits gracefully and removes the partially copied file.

    Parameters:
        src (Path): The source file path.
        dst (Path): The destination file path.

    Returns:
        None

    Raises:
        KeyboardInterrupt: If the user interrupts the process, it raises this exception to exit gracefully and remove the partially copied file.
    """
    src = Path(src)
    dst = Path(dst)

    try:
        # Get the size of the source file
        file_size = src.stat().st_size
        # Open the source file in binary mode for reading
        with src.open("rb") as fsrc:
            # Open the destination file in binary mode for writing
            with dst.open("wb") as fdst:
                # Create a progress bar using tqdm
                with tqdm(
                        total=file_size,
                        unit="B",
                        desc=f"Copying ({src.name})",
                        unit_scale=True,
                        unit_divisor=1024,
                        ncols=shutil.get_terminal_size().columns,
                ) as pbar:
                    # Read the source file in chunks of 1024 bytes
                    while True:
                        buf = fsrc.read(1024)
                        # If we have reached the end of the file, stop reading
                        if not buf:
                            break
                        # Write the chunk to the destination file
                        fdst.write(buf)
                        # Update the progress bar
                        pbar.update(len(buf))
    except KeyboardInterrupt:
        # If the user presses ctrl + c, exit gracefully
        print("\nTerminating...")
        remove(dst)
        exit(0)


def copy_folder(src: Path, dst: Path) -> None:
    """
    Copies a folder and its contents from the source path to the destination path while displaying a progress bar.
    If the user interrupts the process (e.g., by pressing ctrl + c), the program exits gracefully.

    Parameters:
        src (Path): The source folder path.
        dst (Path): The destination folder path.

    Returns:
        None

    Raises:
        KeyboardInterrupt: If the user interrupts the process, it raises this exception to exit gracefully.
    """
    src = Path(src)
    dst = Path(dst)

    try:
        # Calculate the total size of all files in the source folder
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(src):
            for f in filenames:
                fp = Path(dirpath, f)
                total_size += fp.stat().st_size

        # Create a progress bar using tqdm
        with tqdm(
                total=total_size, unit="B", unit_scale=True, unit_divisor=1024
        ) as pbar:
            # Walk through all subdirectories and files in the source folder
            for dirpath, dirnames, filenames in os.walk(src):
                # Create the corresponding destination directory path
                dst_dirpath = Path(dst, os.path.relpath(dirpath, src))
                # If the destination directory does not exist, create it
                if not dst_dirpath.exists():
                    os.makedirs(dst_dirpath)
                # Copy each file from the source to the destination directory
                for f in filenames:
                    src_file = Path(dirpath, f)
                    dst_file = Path(dst_dirpath, f)
                    # Open the source file in binary mode for reading
                    with src_file.open("rb") as fsrc:
                        # Open the destination file in binary mode for writing
                        with dst_file.open("wb") as fdst:
                            # Read the source file in chunks of 1024 bytes
                            while True:
                                buf = fsrc.read(1024)
                                # If we have reached the end of the file, stop reading
                                if not buf:
                                    break
                                # Write the chunk to the destination file
                                fdst.write(buf)
                                # Update the progress bar
                                pbar.update(len(buf))
    except KeyboardInterrupt:
        # If the user presses ctrl + c, exit gracefully
        print("\nTerminating...")
        exit(0)


def dir_size(path: str, verbose_mode: bool = False) -> int:
    """
    Calculates the size of a directory or file in bytes.

    This function uses the `DiskUsage` class to calculate the size of a directory or file on the host system. The size is calculated based on a 1K block size.

    Parameters:
        path (str): The path of the directory or file to calculate the size of.
        verbose_mode (bool): If True, prints the path being calculated. Default is False.

    Returns:
        int: The size of the directory or file in bytes.
    """
    if verbose_mode:
        logger.info(f"Calculating size of {path}")

    return int(DiskUsage().calc_disk_usage(path=path, is_top_level=False))


def count(directory: Path) -> int:
    """
    Returns the count of files and directories in the specified directory.

    Parameters:
        directory (Path): The directory to calculate the count on.

    Returns:
        int: The number of files and directories.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"The specified directory '{directory}' does not exist."
        )

    count = sum([len(files) + len(dirs) for _, dirs, files in os.walk(directory)])
    return count


def cat(
        in_file: Optional[str] = None, msg: Optional[str] = None, out_file: str = None
) -> None:
    """
    Writes the contents of the input file or a message into the output file.

    Parameters:
        in_file (str, optional): The path to the input file. Default is None.
        msg (str, optional): The message to write to the file. Default is None.
        out_file (str): The path to the output file.

    Raises:
        FileNotFoundError: If the input file does not exist.
        PermissionError: If the program does not have permission to read from the input file or write to the output file.
        OSError: If an error occurs while reading from the input file or writing to the output file.
    """
    if out_file is None:
        raise FileNotFoundError("The output file must be specified.")

    try:
        with open(out_file, "a", encoding="UTF-8") as output_file:
            if in_file is not None:
                with open(in_file, "r", encoding="UTF-8") as input_file:
                    output_file.write(input_file.read())
            if msg is not None:
                output_file.write(f"{msg}\n")
    except FileNotFoundError as e:
        print(f"Input file not found: {e}")
    except PermissionError as e:
        print(
            f"Permission denied while reading from input file or writing to output file: {e}"
        )
    except OSError as e:
        print(
            f"Error occurred while reading from input file or writing to output file: {e}"
        )


def init_folders(project: str) -> None:
    """
    Initialize project folders.

    This function creates a set of folders for a given project, as specified in the configuration file.

    Parameters:
        project (str): The name of the project for which to create the folders.

    Raises:
        FileNotFoundError: If the configuration file could not be found.
        PermissionError: If the program does not have permission to create the directories.
        OSError: If an error occurs while creating the directories.
    """
    try:
        # Load the list of folders to create from the configuration file
        folders: List[str] = config.load_config("MAIN", "proj_folders").split(" ")

        # Iterate over each folder in the list
        for folder in folders:
            # Create the full path to the folder by joining the project and folder names
            folder_path = Path(project).joinpath(folder)

            # Create the directory and its parents if they do not exist
            create_directory(folder_path)
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}")
    except PermissionError as e:
        print(f"Permission denied while creating directories: {e}")
    except OSError as e:
        print(f"Error occurred while creating directories: {e}")


def list_folder(folder_name: Path) -> dict:  # type: ignore
    """
    Lists the contents of a folder.

    This function returns a dictionary containing the contents of the specified folder.

    Parameters:
        folder_name (Path): The name of the folder to list.

    Returns:
        dict: A dictionary containing the contents of the specified folder, where the keys are integers and the values are strings representing the names of the files or directories in the folder.

    Raises:
        FileNotFoundError: If the specified folder does not exist.
        PermissionError: If the program does not have permission to access the specified folder.
        OSError: If an error occurs while accessing the specified folder.
    """
    folder_name = Path(folder_name)

    try:
        if not folder_name.exists():
            logger.error("No Projects directory found.")
            raise FileNotFoundError(f"No such directory: {folder_name}")

        directory_list = os.listdir(folder_name)
        # Create a dictionary from the list of projects
        dict_projects = {}
        for i, proj in enumerate(directory_list):
            dict_projects[i + 1] = proj
        logger.info(
            "List of projects:\n"
            + "\n".join(
                [f"\t{key:<4}: {value}" for key, value in dict_projects.items()]
            )
        )
        return dict_projects
    except FileNotFoundError as e:
        print(f"Folder not found: {e}")
    except PermissionError as e:
        print(f"Permission denied while accessing directory: {e}")
    except OSError as e:
        print(f"Error occurred while accessing directory: {e}")


def init_project(prj_name: str) -> None:
    """
    Initialize a project with the given name.

    This function creates a new project with the given name, or overwrites an existing project with the same name if the user confirms.

    Parameters:
        prj_name (str): The name of the project to create.

    Raises:
        FileNotFoundError: If the configuration file could not be found.
        PermissionError: If the program does not have permission to create or delete directories.
        OSError: If an error occurs while creating or deleting directories.
    """
    try:
        # Log the project name
        logger.info(f"Project Name: {prj_name}")

        # Update the configuration file with the main project path
        data = {"main_project": Path("Projects", prj_name)}
        config.update_config("MAIN", data)

        # Construct the full path to the project directory
        project_path = Path("Projects", prj_name)

        # Check if the project directory already exists
        if project_path.is_dir():
            # Log a warning message
            logger.warning("This project exists")

            # Prompt the user for confirmation to overwrite the existing project
            choice = input(
                "If you want to continue, this will delete the existing project [y/n]: "
            )

            # If the user confirms, delete the existing project and initialize a new one
            if choice.lower() == "y":
                logger.info(f"Removing project {project_path}")
                remove(project_path)
                init_folders(config.load_config("MAIN", "main_project"))

            # If the user does not confirm, initialize a new project without deleting the existing one
            else:
                init_folders(config.load_config("MAIN", "main_project"))

        # If the project directory does not exist, initialize a new project
        else:
            init_folders(config.load_config("MAIN", "main_project"))

        # Update the configuration file with the main project path
        data = {"main_project": Path("Projects", prj_name)}
        config.update_config("MAIN", data)
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}")
    except PermissionError as e:
        print(f"Permission denied while creating or deleting directories: {e}")
    except OSError as e:
        print(f"Error occurred while creating or deleting directories: {e}")


def replace_in_file(filename: Path, pattern: str, repl: str) -> None:
    """
    Replaces occurrences of a pattern in a file with a replacement string.

    Parameters:
        filename (Path): The name of the file to perform the replacement on.
        pattern (str): The pattern to search for in the file.
        repl (str): The string to replace the pattern with.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the program does not have permission to read from or write to the specified file.
        OSError: If an error occurs while reading from or writing to the specified file.
    """
    # Ensure that filename is a Path object
    # if isinstance(filename, str):
    filename = Path(filename)

    try:
        with open(filename, encoding="UTF-8") as file:
            lines = file.readlines()

        with open(filename, "w", encoding="UTF-8") as file:
            for line in lines:
                file.write(re.sub(pattern, repl, line))
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except PermissionError as e:
        print(f"Permission denied while reading from or writing to file: {e}")
    except OSError as e:
        print(f"Error occurred while reading from or writing to file: {e}")


def find_text_in_file(filename: Path, text: str, sep: str = ":", level: int = 1) -> str:
    """
    Find a specific text in a file and return a specific part of the line where the text is found.

    Parameters:
        filename (Path): The path of the file to search in.
        text (str): The text to search for in the file.
        sep (str, optional): The separator used to split the line. Defaults to ':'.
        level (int, optional): The index of the split part to return. Defaults to 1.

    Returns:
        str or None: The specified part of the line where the text is found, or None if the text is not found.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IndexError: If the level index is out of range for the split line.
        UnicodeDecodeError: If the file cannot be decoded using UTF-8.
    """
    # Ensure that filename is a Path object
    # if isinstance(filename, str):
    filename = Path(filename)

    try:
        # Check if the file exists
        if not filename.is_file():
            raise FileNotFoundError(f"No such file: '{filename}'")

        # Open the file using a context manager
        with filename.open("r", encoding="UTF-8") as file:
            # Iterate over each line in the file
            for line in file:
                # Check if the text is present in the line
                if text in line:
                    # Split the line and return the specified level of the split
                    return line.split(sep)[level].strip()

        # Return None if the text is not found
        return None
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except IndexError as e:
        print(f"Level index out of range for split line: {e}")
    except UnicodeDecodeError as e:
        print(f"File cannot be decoded using UTF-8: {e}")


def check_sparse(input_img: Path) -> bool:
    """
    Check if the image is sparse.

    Parameters:
        input_img (Path): The path to the image file.

    Returns:
        bool: True if the image is sparse, False otherwise.

    Raises:
        FileNotFoundError: If the specified image file does not exist.
        PermissionError: If the program does not have permission to read from the specified image file.
        OSError: If an error occurs while reading from the specified image file.
    """
    # if isinstance(input_img, str):
    input_img = Path(input_img)

    try:
        # Read the first 28 bytes of the image file
        with input_img.open("rb") as f:
            header_bin = f.read(28)

        # Unpack the binary data into variables
        header = struct.unpack("<I4H4I", header_bin)
        magic = header[0]

        # Check if the magic number matches the expected value
        if magic == 0xED26FF3A:
            return True
        else:
            return False
    except FileNotFoundError as e:
        print(f"Image file not found: {e}")
    except PermissionError as e:
        print(f"Permission denied while reading from image file: {e}")
    except OSError as e:
        print(f"Error occurred while reading from image file: {e}")


def create_gzip(input_file: Path, out_gzip: Path) -> None:
    """
    Create a gzip file from an existing file.

    Parameters:
        input_file (Path): The path to the input file.
        out_gzip (Path): The path to the output gzip file.

    Raises:
        FileNotFoundError: If the input file does not exist.
        PermissionError: If the program does not have permission to read from the input file or write to the output gzip file.
        OSError: If an error occurs while reading from the input file or writing to the output gzip file.
    """
    # if isinstance(input_file, str):
    input_file = Path(input_file)
    # elif isinstance(out_gzip, str):
    out_gzip = Path(out_gzip)

    try:
        # Ensure that the output file has a .gz extension
        out_gzip = out_gzip if out_gzip.suffix == ".gz" else f"{out_gzip}.gz"

        # Compress the input file to the output gzip file
        with input_file.open("rb") as f_in, gzip.open(out_gzip, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    except FileNotFoundError as e:
        print(f"Input file not found: {e}")
    except PermissionError as e:
        print(
            f"Permission denied while reading from input file or writing to output gzip file: {e}"
        )
    except OSError as e:
        print(
            f"Error occurred while reading from input file or writing to output gzip file: {e}"
        )


def create_zstd(input_file: Path, out_zstd: Path) -> None:
    """
    Compresses a file with zstd.

    Parameters:
        input_file (Path): The path to the input file.
        out_zstd (Path): The path to the output file.

    Raises:
        FileNotFoundError: If the input file does not exist.
        PermissionError: If the program does not have permission to read from the input file or write to the output file.
        OSError: If an error occurs while reading from the input file or writing to the output file.
    """
    # if isinstance(input_file, str):
    input_file = Path(input_file)
    # elif isinstance(out_zstd, str):
    out_zstd = Path(out_zstd)

    try:
        # Add .zst to the previous suffix of the output file
        out_zstd = out_zstd.with_suffix(out_zstd.suffix + ".zst")

        logger.info(f"Compress [{input_file}] to [{out_zstd}]")

        # create a zstd compressor object with multithreading enabled
        cctx = zstandard.ZstdCompressor(threads=-1)

        # open the input and output files in binary mode
        with input_file.open("rb") as input_f, out_zstd.open("wb") as output_f:
            # create a stream reader object that compresses data on the fly
            reader = cctx.stream_reader(input_f)
            # copy the data from the reader to the output file
            shutil.copyfileobj(reader, output_f)
    except FileNotFoundError as e:
        print(f"Input file not found: {e}")
    except PermissionError as e:
        print(
            f"Permission denied while reading from input file or writing to output file: {e}"
        )
    except OSError as e:
        print(
            f"Error occurred while reading from input file or writing to output file: {e}"
        )


def get_rom_info(output_dir: Path) -> Tuple[str, str, str]:
    """
    Returns the ROM type, incremental version, and security patch level of a ROM.

    This method reads the build.prop files in the output directory to determine the ROM type, incremental version, and security patch level of a ROM.

    Parameters:
        output_dir (Path): The path to the output directory containing the build.prop files.

    Returns:
        tuple: A tuple containing the ROM type (str), incremental version (str), and security patch level (str) of the ROM.

    Raises:
        FileNotFoundError: If any of the build.prop files are not found.
        ValueError: If the ROM type, incremental version, or security patch level cannot be determined.

    """
    # Define the path to the system build.prop file
    build_prop_file = Path(output_dir, "system", "system", "build.prop")

    # Attempt to open and read the system build.prop file
    try:
        with build_prop_file.open() as f:
            lines = f.readlines()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Could not find file: {build_prop_file}") from exc

    # Initialize variables for storing the extracted incremental version and security patch level
    incremental = None
    security_patch = None

    # Extract incremental version and security patch level
    for line in lines:
        if line.startswith("ro.system.build.version.incremental="):
            incremental = line.split("=")[1].strip()
        elif line.startswith("ro.build.version.security_patch="):
            security_patch = line.split("=")[1].strip()

        if incremental and security_patch:
            break

    # If either the incremental version or security patch level could not be determined, raise an error
    if not incremental or not security_patch:
        raise ValueError(
            "Could not determine incremental version or security patch level"
        )

    # Define a dictionary mapping build properties to ROM types
    rom_types = {
        "ro.miui.ui.version.name": "MIUI",
        "ro.build.version.opporom": "ColorOS",
        "ro.build.version.EMUI": "EMUI",
        "ro.build.version.samsung": "One UI",
        "ro.build.version.release": "AOSP",
        "lineageos": "LineageOS",
    }

    # Define a list of paths to other build.prop files to search for the ROM type
    build_prop_files = [
        Path(output_dir, "product", "etc", "build.prop"),
        Path(output_dir, "vendor", "build.prop"),
        Path(output_dir, "system", "system", "build.prop"),
        Path(output_dir, "system_ext", "etc", "build.prop"),
        Path(output_dir, "odm", "etc", "build.prop"),
    ]

    # Initialize a variable for storing the detected ROM type
    rom_type = None

    # Iterate over each build.prop file in the list of paths
    for file in build_prop_files:
        # Attempt to open and read the current build.prop file
        try:
            with open(file, encoding="utf-8") as f:
                for line in f:
                    for prop, name in rom_types.items():
                        if line.startswith(prop):
                            rom_type = name
                            break
                    if rom_type:
                        break
        except FileNotFoundError:
            continue
        if rom_type:
            break

    # If no ROM type could be determined, raise an error
    if not rom_type:
        raise ValueError("Could not determine ROM type")

    return rom_type, incremental, security_patch

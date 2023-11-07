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
from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from eorp.config import Configs
from eorp.create_ext4 import CreateExt4
from eorp.create_super import CreateSuper
from eorp.debloater import Debloater
from eorp.extract_firmware import ExtractFirmware
from eorp.interface import (
    Banner,
    Color,
    Colors,
    Fx,
    Mv,
    Term,
)
from eorp.logging import Log
from eorp.system_info import SystemDetector
from eorp.utils import (
    count,
    dir_size,
    find_text_in_file,
    init_project,
    list_folder,
    remove,
    replace_in_file,
    run_command,
)
from eorp.variables import CONFIG_FILE, CONFIG_DIR, LOG_FILE, ROOT_DIR


def check_pip() -> Optional[bool]:
    """
    Check if pip is installed on the system. If not, try to install it.

    Returns:
        True if pip is found or installed successfully, False otherwise.
    """
    try:
        # Check if pip is already installed by running "pip --version"
        python_executable = sys.executable
        subprocess.run(
            [python_executable, "-m", "pip", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        print("pip is already installed.")
        return True
    except subprocess.CalledProcessError:
        # If pip is not found, try to install it
        print("pip is not installed. Installing pip...")
        try:
            # Try to install pip using the ensurepip module
            subprocess.run([sys.executable, "-m", "ensurepip", "--default-pip"], check=True)
            print("pip installed successfully.")
            return True
        except subprocess.CalledProcessError:
            # If ensurepip fails, try to install pip using the package manager for the current Linux distribution
            distro_name = None
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as os_release:
                    for line in os_release:
                        if line.startswith("ID="):
                            distro_name = line.split("=")[1].strip().lower()
            except:
                pass

            if distro_name in ["ubuntu", "debian", "kali"]:
                install_command = ["sudo", "apt", "install", "-y", "python3-pip"]
            elif distro_name == "arch":
                install_command = ["sudo", "pacman", "-S", "python-pip"]
            else:
                print(
                    f"Unsupported Linux distribution: {distro_name}. Please install pip manually."
                )
                return False

            try:
                subprocess.run(install_command, check=True)
                print("pip installed successfully.")
                return True
            except subprocess.CalledProcessError:
                print("Error installing pip. Please install it manually.")
                return False


def install_missing_module(module_name: str) -> Optional[bool]:
    """
    Install a missing Python module and the requirements from a requirements.txt file using pip.

    Args:
        module_name: The name of the module to install.

    Returns:
        True if the module and requirements are installed successfully, False otherwise.
    """
    try:
        python_executable = sys.executable
        # Install the missing module
        subprocess.run(
            [python_executable, "-m", "pip", "install", "--user", module_name],
            check=True,
        )
        print(f"Module '{module_name}' installed successfully.")

        # Install the requirements from the requirements.txt file
        if Path(ROOT_DIR).joinpath("./requirements.txt").exists():
            subprocess.run(
                [python_executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=True,
            )
            print("Requirements installed successfully.")

        return True
    except subprocess.CalledProcessError:
        print(
            f"Error installing module '{module_name}' or requirements. Please install them manually."
        )
        return False


def restart_script():
    """
    Restart the current script.
    """
    print("Restarting script...")
    os.execv(sys.executable, ["python"] + sys.argv)


try:
    from loguru import logger
except (ImportError, ModuleNotFoundError) as e:
    # Extracting module name from error message
    module_name = str(e).split()[-1].strip("'")
    print(
        f"Error: Module '{module_name}' not found. Make sure you have all required modules installed."
    )

    if check_pip():
        if install_missing_module(module_name):
            restart_script()
        else:
            exit(1)
    else:
        print("Error installing pip. Please install it manually.")
        exit(1)

# ? Variables ------------------------------------------------------------------------------------->

# Banner source data: list of tuples containing foreground color, background color, and text
BANNER_SRC: List[Tuple[str, str, str]] = [
    ("#1976d2", "#42a5f5", "███████╗ ██████╗ ██████╗ ██████╗"),
    ("#1976d2", "#42a5f5", "██╔════╝██╔═══██╗██╔══██╗██╔══██╗"),
    ("#1976d2", "#42a5f5", "█████╗  ██║   ██║██████╔╝██████╔╝"),
    ("#1976d2", "#42a5f5", "██╔══╝  ██║   ██║██╔══██╗██╔═══╝"),
    ("#1976d2", "#42a5f5", "███████╗╚██████╔╝██║  ██║██║"),
    ("#FFFFFF", "#000000", "╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝"),
]

# Project version
VERSION: str = "1.1"
# Project name
PROJECT_NAME: str = "EORP"

# ? Setup ----------------------------------------------------------------------------------------->
# TODO
try:
    os.makedirs(f"{CONFIG_DIR}/logs", exist_ok=True)
except PermissionError:
    print(f'ERROR!\nNo permission to write to "{CONFIG_DIR}" directory!')
    raise SystemExit(1)

# Initiate the Configs instance
config_file_path = Path(CONFIG_FILE)
config = Configs(config_file_path)

# set log level
LOG_LEVEL: str = config.load_config("MAIN", "log_level")

# Instantiate the Log class with a log file path
log = Log(log_file_path=LOG_FILE, loglevel=LOG_LEVEL)


# ? args ------------------------------------------------------------------------------------------>


def create_parser() -> argparse.ArgumentParser:
    """Create an argument parser for the command line interface.

    Returns:
        argparse.ArgumentParser: An argument parser object that can parse the command line arguments.
    """
    # TODO: Add argument to ZipCreator
    parser = argparse.ArgumentParser(
        description="Command line arguments",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--project-name",
        dest="name",
        metavar="PROJECT",
        help="Specify project name and init folder project",
    )

    parser.add_argument(
        "-f",
        "--input-firmware",
        dest="input",
        metavar="FILE",
        required=False,
        help="Input firmware file (e.g. payload.bin, super.img, ext4.img)",
    )

    parser.add_argument(
        "-u",
        "--update-project",
        dest="project",
        action="store_true",
        help="Update project name in config.ini",
    )
    parser.add_argument(
        "-ep",
        "--extract-project",
        dest="extract_project",
        action="store_true",
        help="Extract images inside Source dir without [-f]",
    )
    parser.add_argument(
        "-l", "--list-projects", dest="lst", action="store_true", help="Projects List"
    )
    parser.add_argument(
        "-w",
        "--write-config",
        dest="write_config",
        action="store_true",
        help="Write config.ini",
    )

    parser.add_argument(
        "-b",
        "--build-image",
        dest="build_image",
        metavar="TYPE",
        type=lambda s: [t.strip() for t in s.split(",")],
        help="""Build image of type [raw:r, sparse:s, brotli:b] (Linux only).
             Multiple values can be passed separated by commas.
             raw:     This will build an ext4 filesystem.
             sparse:  This will build a sparse filesystem.
             brotli:  This will compress the sparse image with brotli.
             These options must be used in the following order: first raw, then sparse, then brotli.""",
    )

    parser.add_argument(
        "--flash",
        nargs="?",
        const="",
        dest="flash",
        metavar="FLASH",
        type=lambda s: [t.strip() for t in s.split(",")],
        help="""Flash images to devices using fastboot [recovery:r, system:s, wipe:w].
             Multiple values can be passed separated by commas.
             wipe:     This will delete all your files and photos stored on internal storage.
             recovery: This will reboot the device to recovery mode after finishing the flashing process.
             system:   This will reboot the device to system mode after finishing the flashing process.""",
    )

    parser.add_argument(
        "-s",
        "--super-image",
        nargs="?",
        const="",
        dest="super_image",
        metavar="METHOD",
        type=lambda s: [t.strip() for t in s.split(",")],
        help="""Build super partition and compress with:
            none:no - no compression
            sparse:s - sparse compression
            zstd:zst - zstd compression
            gzip:gz - gzip compression
            brotli:br - brotli compression""",
    )

    # parser.add_argument(
    #     '--debloat',
    #     nargs="?",
    #     const="",
    #     dest='debloat',
    #     metavar="DEBLOAT",
    #     type=lambda s: [t.strip() for t in s.split(',')],
    #     help='''Debloat project with:
    #         path_to_debloating_list - debloat using file_name.txt
    #         project_path - debloat using project_path'''
    # )

    parser.add_argument(
        "--debloat",
        nargs="*",
        dest="debloat",
        metavar=("DEBLOAT_LIST_PATH", "PROJECT_PATH"),
        help="Debloat project using DEBLOAT_LIST_PATH and PROJECT_PATH",
    )

    parser.add_argument(
        "-ui",
        "--update-info",
        dest="update_info",
        action="store_true",
        help="Update project info inside _filesystem_features.txt",
    )
    parser.add_argument("--clean", dest="clean", action="store_true", help="Clean up projects dir")
    parser.add_argument("-v", "--version", action="store_true", help="show version info and exit")

    return parser


# ? Main ------------------------------------------------------------------------------------------>


def update_images_info(specified_proj: Path) -> None:
    """Update the size and inode count of the images in the project.

    Args:
        specified_proj (Path): The path to the project directory.

    Returns:
        None
    """
    if isinstance(specified_proj, str):
        specified_proj = Path(specified_proj)

    # Load configurations
    configs = config

    # Set default values for extra_size and extra_inode
    default_extra_size: int = 104857600
    default_extra_inode: int = 2000

    # Create a dictionary to store the new size and inode count of each image
    image_info: dict = {}

    # Iterate over the output directory to calculate the new size and inode count of each image
    for extracted_image in os.listdir(Path(specified_proj, "Output")):
        new_size = dir_size(Path(specified_proj, "Output", extracted_image))
        new_inode_count = count(Path(specified_proj, "Output", extracted_image))
        image_info[extracted_image] = (new_size, new_inode_count)

    # Iterate over the file features files to update the size and inode count of each image
    for file_features in Path(specified_proj, "Config").rglob("*_filesystem_features.txt"):
        extracted_image = re.search(r"(.+)_filesystem_.*", file_features.name).group(1)
        if extracted_image in image_info:
            new_size, new_inode_count = image_info[extracted_image]
            old_size = find_text_in_file(file_features, "Partition Size:")
            old_inode_count = find_text_in_file(file_features, "Inode count:")

            # Load extra size and inode values for different images from config.ini
            extra_size_config = configs.load_config("EXTRA_SIZE", extracted_image)
            if extra_size_config is not None:
                extra_size = int(extra_size_config)
            else:
                extra_size = default_extra_size

            extra_inode_config = configs.load_config("EXTRA_INODE", extracted_image)
            if extra_inode_config is not None:
                extra_inode = int(extra_inode_config)
            else:
                extra_inode = default_extra_inode

            # Log the update of the size and inode count of the image
            logger.info(
                f"Updating the size of [{extracted_image}] from [{old_size}] to [{new_size + extra_size}]"
            )
            replace_in_file(
                file_features,
                "^Partition Size:.*",
                f'Partition Size:{" " * 12}{new_size + extra_size}',
            )
            logger.info(
                f"Updating the inode count of [{extracted_image}] from "
                f"[{old_inode_count}] to [{new_inode_count + extra_inode}]"
            )
            replace_in_file(
                file_features,
                "^Inode count:.*",
                f'Inode count:{" " * 12}{new_inode_count + extra_inode}',
            )

            # Print a separator line
            print(f"{Colors.green}----------------------------------------------------------------")


def list_projects():
    """List all available projects in the Projects directory."""
    projects_dir: Path = Path(ROOT_DIR).joinpath("Projects")

    return list_folder(projects_dir)


def get_fastboot_path() -> str:
    """Get the path to the fastboot executable depending on the current platform.

    Returns:
        str: The path to the fastboot executable.
    """
    os_type: str = SystemDetector().get_os_type()

    if "WSL" in os_type.upper():
        print("Running on WSL")
        return config.load_config("LINUX", "fastboot_wsl")
    elif "Linux" in os_type.upper():
        print("Running on Linux")
        return config.load_config("LINUX", "fastboot")
    elif "Windows" in os_type.upper():
        print("Not supported on Windows. Install WSL and try to run on WSL")
        sys.exit(1)
    else:
        raise Exception("Unsupported platform")


def flash_device(fastboot: Path, flash: List[str]) -> None:
    """Flash the device with the given images.

    Args:
        fastboot (Path): The path to the fastboot executable.
        flash (List[str]): A list of options for flashing the device.
    """
    if isinstance(fastboot, str):
        fastboot = Path(fastboot)

    # Load configurations
    main_project = config.load_config("MAIN", "main_project")
    source_dir = Path(main_project, "source")
    build_dir = Path(main_project, "Build")
    partitions = config.load_config("MAIN", "partitions").split(" ")
    other_part = "boot dtbo vbmeta vbmeta_system logo".split()

    # Check if fastboot executable exists
    if not fastboot.is_file():
        sys.exit(1)

    # Flash partitions
    choose_part = list_folder(build_dir)
    if choose_part is not None:
        print(f"Choose partition to flash: {choose_part}")
        print("Choose a/all to flash all partitions.")
        ans = input("Enter partition: ")
        if ans not in ("a", "all"):
            part = build_dir / f"{choose_part[int(ans)]}"
            run_command([fastboot, "flash", str(choose_part[int(ans)]).removesuffix(".img"), part], verbose=True,
                        stdout=sys.stdout)
        else:
            for part in partitions:
                for path in Path(build_dir).rglob(f"{part}.img"):
                    run_command([fastboot, "flash", part, str(path)], verbose=True, stdout=sys.stdout)

    # Install boot and dtbo if 'r' is present in flash list
    ans = input("Do you want to install boot and dtbo? [y/n]: ")
    if ans.lower() == "y":
        for part in other_part:
            for path in Path(source_dir).rglob(f"{part}.img"):
                run_command(
                    [fastboot, "flash", part, str(path)],
                    verbose=True,
                    stdout=sys.stdout,
                )

    # Erase metadata and userdata if 'w' is present in flash list
    if "w" in flash:
        print("WARNING: This will delete all your files and photos stored on internal storage.")
        ans = input("Are you sure you want to proceed? [y/n]: ")
        if ans.lower() == "y":
            run_command([fastboot, "erase", "metadata"], verbose=True)
            run_command([fastboot, "erase", "userdata"], verbose=True)

    # Reboot device if 's' is present in flash list
    if "s" in flash:
        ans = input("Do you want to reboot the device? [y/n]: ")
        if ans.lower() == "y":
            run_command([fastboot, "reboot"], verbose=True)

    if "r" in flash:
        ans = input("Do you want to reboot the recovery? [y/n]: ")
        if ans.lower() == "y":
            run_command([fastboot, "reboot", "recovery"], verbose=True)


if __name__ == "__main__":
    # check_terminal_size(80, 25)
    # print banner
    banner = (
        f'{Term.clear}{Banner(BANNER_SRC).draw(Term.height // 2 - 10, center=True)}{Mv.l(46)}{Color("#17e364")}{Fx.b}BY: ABDULRAHMAN'
        f"{Mv.r(5)}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{Term.bg}{Term.fg}{Mv.d(1)}"
    )
    print(banner)
    time.sleep(0.5)

    os_type = SystemDetector().get_os_type()
    if os_type == "WSL 2":
        print("Recommended to run this script must be run on WSL 1, (WSL 2 make the script slower).")
    elif os_type == "Windows":
        print("Not supported on Windows yet.")

    start_time = time.time()

    # Parse the command line arguments using the create_parser() function
    parser = create_parser()
    args = parser.parse_args()

    # Check if at least one argument is provided
    if len(sys.argv) < 2:
        logger.error("You must enter at least one argument!!!")
        parser.print_usage()
        raise SystemExit(1)

    # Print version information if the --version flag is provided
    if args.version:
        print(f"{PROJECT_NAME} version: {VERSION}")
        raise SystemExit(0)

    # Initialize a new project if the --project-name flag is provided
    if args.name:
        data = {"main_project": Path(ROOT_DIR, "Projects", args.name)}
        config.update_config("MAIN", data)
        init_project(args.name)

    # Update project name in config.ini if the --update-project flag is provided
    if args.project:
        dict_projects = list_projects()

        try:
            logger.info("Choose Project: ")
            ans = int(input("Enter the project number: "))
            logger.info(f"Your choice is [{dict_projects[ans]}].")
            specified_proj = dict_projects[ans]
            data = {"main_project": Path(ROOT_DIR, "Projects", specified_proj)}
            config.update_config("MAIN", data)
            logger.info(f"Updated project to [{config.load_config('MAIN', 'main_project')}]")
        except (KeyboardInterrupt, KeyError, ValueError):
            logger.exception(f"Aborting Your choice [{ans}] not found.")
            sys.exit(1)

    # Write config.ini if the --write-config flag is provided
    if args.write_config:
        logger.info(f"Update {CONFIG_FILE}")
        config.write_default_config()

    # List projects if the --list-projects flag is provided
    if args.lst:
        list_projects()
        sys.exit(0)

    main_project = config.load_config("MAIN", "main_project")

    # Extract firmware if the --input-firmware flag is provided
    if args.input:
        # ExtractFirmware(main_project).ext_fw(args.input, Path(main_project, "Source"))
        # ExtractFirmware(main_project).extract_img()
        ExtractFirmware(
            input_firmware_path=args.input,
            main_project=main_project,
            verbose=True,
        )

    # Extract images if the --extract-project flag is provided
    if args.extract_project:
        try:
            # ExtractFirmware(main_project).extract_img()
            ExtractFirmware(main_project=main_project, verbose=True)
        except FileNotFoundError:
            logger.error("Project folder not exist try update project with [-u]")

    if args.update_info:
        dict_projects = list_projects()

        try:
            logger.info("Choose Project: ")
            ans = int(input("Enter the project number: "))
            logger.info(f"Your choice is [{ans}].")
            specified_proj = Path(ROOT_DIR, "Projects", dict_projects[ans])
        except (KeyboardInterrupt, KeyError, ValueError):
            logger.exception(f"Aborting Your choice [{ans}] not found.")
            sys.exit(1)

        update_images_info(specified_proj)

    # Build super partition and compress it with different methods if the --super-image flag is provided
    # Loop through the values of args.super_image and call CreateSuper for each method
    if args.super_image:
        for method in args.super_image:
            if method not in ["none", "no", "sparse", "s"]:
                CreateSuper(compression_type=method).create_super_img()
            else:
                CreateSuper(sparse_super_partition=True, compression_type=method).create_super_img()

    # Build image with different types if the --build-image flag is provided
    # Loop through the values of args.build_image and set the corresponding flags for CreateExt4
    if args.build_image:
        build_image_set = set(args.build_image)
        raw = "raw" in build_image_set or "r" in build_image_set
        sparse = "sparse" in build_image_set or "s" in build_image_set
        brotli = "brotli" in build_image_set or "b" in build_image_set

        if raw or sparse or brotli:
            CreateExt4().main(raw, sparse, brotli)

    if args.flash:
        # Get path to fastboot executable
        fastboot = get_fastboot_path()

        # Flash device
        flash_device(fastboot, args.flash)

    if args.debloat is not None:
        if len(args.debloat) == 0:
            project = list_projects()
            logger.info("Choose Project: ")
            ans = int(input("Enter the project number: "))
            project_path = Path(ROOT_DIR, "Projects", project[ans])

            debloater_list = list_folder(Path(ROOT_DIR, "debloat_lists"))
            logger.info("Choose debloat file list: ")
            ans = int(input("Enter the file number: "))
            debloat_list_path = Path("debloat_lists", debloater_list[ans])

            if debloat_list_path.exists() and project_path.exists():
                Debloater(
                    debloating_list=debloat_list_path, project_path=project_path
                ).backup_and_debloat()
            else:
                logger.error(
                    f"Debloat list path '{debloat_list_path}' or project path '{project_path}' does not exist"
                )

        elif len(args.debloat) == 1:
            # One argument was passed to the --debloat option
            project = list_projects()
            logger.info("Choose Project: ")
            ans = int(input("Enter the project number: "))
            project_path: Path = Path(ROOT_DIR, "Projects", project[ans])
            debloat_list_path: Path = Path(args.debloat[0])

            if debloat_list_path.exists() and project_path.exists():
                Debloater(
                    debloating_list=debloat_list_path, project_path=project_path
                ).backup_and_debloat()
            else:
                logger.error(
                    f"Debloat list path '{debloat_list_path}' or project path '{project_path}' does not exist"
                )

        elif len(args.debloat) == 2:
            # Two arguments were passed to the --debloat option
            debloat_list_path: Path = Path(args.debloat[0])
            project_path = args.debloat[1]

            if debloat_list_path.exists() and project_path.exists():
                Debloater(
                    debloating_list=debloat_list_path, project_path=project_path
                ).backup_and_debloat()
            else:
                logger.error(
                    f"Debloat list path '{debloat_list_path}' or project path '{project_path}' does not exist"
                )

    # Clean up projects directory if the --clean flag is provided
    if args.clean:
        dict_projects = list_projects()
        logger.info("Choose Project to delete: ")
        ans = input("Enter the project number: [1, 2 ...] or 'c' to cancel: ")

        if ans.lower() in ["c", "cancel"]:
            logger.info("Deletion canceled.")
            sys.exit(0)
        else:
            try:
                ans = {int(x) for x in ans.split(",")}
                for prj_num in ans:
                    specified_proj = dict_projects[prj_num]
                    logger.info(f"Clean Project {Path(ROOT_DIR, 'Projects', dict_projects[prj_num])}")
                    remove(Path(ROOT_DIR, "Projects", dict_projects[prj_num]))
            except (KeyboardInterrupt, KeyError, ValueError):
                logger.exception(f"Aborting Your choice {ans} not found.")
                sys.exit(1)

    runtime = time.time() - start_time

    print(f"{Mv.d(3)}")
    print(
        f"{Fx.italic}{Colors.green}[SUCCESS] {Colors.default}Total Excution time: {runtime} seconds{Fx.ui}{Fx.ub}{Term.bg}{Term.fg}"
    )

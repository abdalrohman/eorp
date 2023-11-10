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
import os
import shutil
from pathlib import Path

from loguru import logger

from .variables import ROOT_DIR
from .utils import list_folder


class Debloater:
    """
    This class is responsible for debloating a specified project. It reads a list of files and directories to remove from a file, backs up these files and directories, then removes them from the project.
    """

    def __init__(self, debloating_list: str, project_path: str):
        """
        Constructs all the necessary attributes for the Debloater object.

        Parameters:
            debloating_list (str): The name of the file containing the list of items to debloat.
            project_path (str): The path to the project directory.
        """
        self.debloating_list = debloating_list
        self.project_path = project_path
        self.debloat_set = self.read_set()

    def read_set(self) -> set:
        """
        Reads and returns a set of strings representing the non-empty, non-comment lines in the debloating_list file.

        Returns:
            set: A set of strings representing the non-empty, non-comment lines in the debloating_list file.
        """
        debloat_set = set()

        # Use a context manager to handle closing the file
        logger.info(
            f"Reading the list of debloating files from [{self.debloating_list}]."
        )
        with open(self.debloating_list, "r", encoding="UTF-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    debloat_set.add(line)

        return debloat_set

    def backup_and_debloat(self) -> None:
        """
        This function backs up files before they are debloated and removes files and directories from the specified project based on the list in the specified file.
        """

        # Create a backup directory
        backup_dir = os.path.join(self.project_path, "Backup")
        os.makedirs(backup_dir, exist_ok=True)
        for item in self.debloat_set:
            item_path = os.path.join(self.project_path, "Output", item)
            if os.path.isfile(item_path):
                item_backup_dir = os.path.join(backup_dir, os.path.dirname(item))
                logger.info(f"Create backup for {item}")
                os.makedirs(item_backup_dir, exist_ok=True)
                shutil.copy2(item_path, item_backup_dir)
                logger.info(f"Debloat {item_path}")
                os.remove(item_path)
            elif os.path.isdir(item_path):
                item_backup_dir = os.path.join(backup_dir, item)
                logger.info(f"Create backup for {item}")
                shutil.copytree(item_path, item_backup_dir)
                logger.info(f"Debloat {item_path}")
                shutil.rmtree(item_path)
            else:
                logger.warning(f"File not found: {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debloater")
    parser.add_argument(
        "--debloat",
        nargs="*",
        dest="debloat",
        metavar=("DEBLOAT_LIST_PATH", "PROJECT_PATH"),
        help="Debloat project using DEBLOAT_LIST_PATH and PROJECT_PATH",
    )

    args = parser.parse_args()

    if args.debloat is not None:
        # Check the number of arguments passed to the --debloat option
        if len(args.debloat) == 0:
            # If no arguments were passed, prompt the user to choose a project and a debloat list
            project = list_folder(Path(ROOT_DIR, "Projects"))
            logger.info("Choose Project: ")
            ans = int(input("Enter the project number: "))
            project_path = Path("Projects", project[ans])

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
            project = list_folder(Path(ROOT_DIR, "Projects"))
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

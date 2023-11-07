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
from typing import Union

from eorp.ext4_extractor.ext4 import Volume


class ExtractExt4:
    def __init__(self, image_name: Union[str, os.PathLike], out_dir: Union[str, os.PathLike]):
        """
        Initialize the ExtractExt4 object.

        Parameters:
            image_name (str or os.PathLike): The path to the image file.
            out_dir (str or os.PathLike): The path to the output directory.
        """
        self.image_name = os.path.realpath(image_name)
        self.file_name = self.__extract_file_name(os.path.basename(self.image_name))
        self.out_dir = os.path.realpath(out_dir)

        # If output directory exists, remove it and create a new one
        if os.path.isdir(self.out_dir):
            print(f"Output directory {self.out_dir} already exists. Removing and recreating it.")
            shutil.rmtree(self.out_dir)
            os.makedirs(self.out_dir)
        else:
            os.makedirs(self.out_dir)

        self.num_files = 0
        self.num_dirs = 0
        self.num_links = 0

    def __extract_file_name(self, file_path: str) -> str:
        """
        Extract the file name from the file path.

        Parameters:
            file_path (str): The file path.

        Returns:
            str: The file name.
        """
        name = os.path.basename(file_path).split(".")[0]
        return name

    def extract_ext4(self):
        """
        Extract the ext4 filesystem from the image file.

        This method uses the ext4 library to extract the filesystem. It counts the number of files,
        directories, and links that are extracted.

        Note: The actual extraction code has been omitted for brevity.

        Raises:
            Exception: If an error occurs during extraction.
        """

        try:

            def scan_dir(root_inode, root_path=""):
                for entry_name, entry_inode_idx, entry_type in root_inode.open_dir():
                    # exclude '.', '..'
                    if entry_name in [".", "..", "lost+found"]:
                        continue

                    entry_inode = root_inode.volume.get_inode(entry_inode_idx, entry_type)
                    entry_inode_path = root_path + "/" + entry_name

                    if entry_inode.is_dir:
                        self.num_dirs += 1
                        dir_target = self.out_dir + entry_inode_path.replace(
                            '"permissions"', "permissions"
                        )

                        if not os.path.isdir(dir_target):
                            os.makedirs(dir_target)

                        scan_dir(entry_inode, entry_inode_path)  # loop inside the directory

                    elif entry_inode.is_file:
                        self.num_files += 1
                        # extract files
                        raw = entry_inode.open_read().read()

                        file_target = os.path.join(self.out_dir + entry_inode_path)

                        if os.path.isfile(file_target):
                            os.remove(file_target)

                        # write to new file
                        with open(file_target, "wb") as out:
                            out.write(raw)

                    elif entry_inode.is_symlink:
                        self.num_links += 1
                        try:
                            link_target = entry_inode.open_read().read().decode()
                            # check if file exist and remove it
                            target = self.out_dir + entry_inode_path

                            if os.path.islink(target) or os.path.isfile(target):
                                os.remove(target)

                            if "\0" not in link_target and "\0" not in target:
                                os.symlink(link_target, target)
                            else:
                                print(
                                    f"Found a null byte in the link target {link_target} or target {target}"
                                )
                        except UnicodeDecodeError:
                            print(f"Could not decode the link target of {entry_inode}.")

            # open image
            with open(self.image_name, "rb") as file:
                root = Volume(file).root
                scan_dir(root)

            print(
                f"Extraction completed. Total directories: {self.num_dirs}, total files: {self.num_files}, total links: {self.num_links}."
            )
            return True  # Return True if everything was successful
        except Exception as e:
            print(f"An error occurred: {e}")
            return False  # Return False if an error occurred


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract ext4 filesystem.")
    parser.add_argument("image_path", type=str, help="Path to the image file.")
    parser.add_argument("out_path", type=str, help="Path to the output directory.")
    args = parser.parse_args()

    extractor = ExtractExt4(args.image_path, args.out_path)
    print(
        f":: Starting extraction of {extractor.file_name}.img...",
        f":: Image path: {extractor.image_name}",
        f":: Output directory: {extractor.out_dir}",
        sep="\n",
        end="\n\n",
    )

    if not extractor.extract_ext4():
        print("Extraction failed due to an error.")

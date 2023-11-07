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
from pathlib import Path
from typing import Union

from eorp.ext4_extractor.ext4 import Volume


class ReadExt4:
    """
    A class to read Ext4 file system.
    """

    def __init__(self, image_path: Union[str, Path], out_dir: Union[str, Path]):
        """
        Initialize the class with necessary parameters.
        """
        self.image_name: Path = Path(image_path).resolve()
        self.out_dir = Path(out_dir).resolve()
        self.fs_context = []
        self.fs_config = []
        self.fetures = []
        self.file_name = self.__file_name(self.image_name.name)

        # Define output file paths
        self.fs_context_file = self.out_dir / f"{self.file_name}_file_contexts.txt"
        self.fs_config_file = self.out_dir / f"{self.file_name}_filesystem_config.txt"
        self.file_features = self.out_dir / f"{self.file_name}_filesystem_features.txt"

        # Initialize counters
        self.num_files = 0
        self.num_dirs = 0
        self.num_links = 0

    def __file_name(self, file_path: Path):
        """
        Extract the base name from the file path.
        """
        file_path = Path(file_path)
        name = str(file_path.name).split(".", maxsplit=1)[0]
        return name

    def __get_octal_perm(self, arg):
        """
        Convert permission string to octal.
        """
        if len(arg) < 9 or len(arg) > 10:
            return None
        if len(arg) == 10:
            arg = arg[1:]

        # Define permission mapping
        perm_map = {"r": 4, "w": 2, "x": 1, "S": 0, "s": 1, "T": 0, "t": 1}

        # Calculate octal permission
        o, g, w = [sum(perm_map.get(x, 0) for x in arg[i : i + 3]) for i in range(0, len(arg), 3)]

        return f"0{o}{g}{w}"

    def __appendf(self, msg, out_file):
        """
        Append a message to a file.
        """
        with open(out_file, "w", encoding="UTF-8") as file:
            file.write(f"{msg}\n")

    def __write_context(self):
        """
        Write context from fs_context list to file.
        """
        # Define common strings
        context_strings = {
            "vendor": "/ u:object_r:vendor_file:s0",
            "odm": "/ u:object_r:vendor_file:s0",
            "system": "/ u:object_r:system_file:s0",
        }

        # Add context strings based on file_name
        self.fs_context.append(context_strings.get(self.file_name, "/ u:object_r:system_file:s0"))
        self.fs_context.append(f"/{self.file_name}(/.*)? u:object_r:{self.file_name}_file:s0")

        # Add lost+found string
        lost_found_string = (
            "/lost+found        u:object_r:rootfs:s0"
            if self.file_name == "system"
            else f"/{self.file_name}/lost+found        u:object_r:rootfs:s0"
        )
        self.fs_context.append(lost_found_string)

        # Replace . and + with \. and \+ in list
        self.fs_context = [ele.replace(".", r"\.").replace("+", r"\+") for ele in self.fs_context]

        self.fs_context.sort()

        # Write contexts to file
        self.__appendf("\n".join(self.fs_context), self.fs_context_file)

    def __write_config(self):
        """
        Write config from fs_config list to file.
        """
        # Define common strings
        config_strings = {
            "vendor": "/ 0 2000 0755",
            "odm": "/ 0 2000 0755",
            "system": "/ 0 0 0755",
        }

        # Add config strings based on file_name
        self.fs_config.append(config_strings.get(self.file_name, "/ 0 0 0755"))
        self.fs_config.append(f"{self.file_name} 0 0 0755")

        self.fs_config.sort()

        # Write config list to file
        self.__appendf("\n".join(self.fs_config), self.fs_config_file)

    def __write_fetures(self):
        """
        Write features to file.
        """

        with open(self.image_name, "rb") as file:
            volume = Volume(file)  # Read the volume once and reuse it

            # Append features to the list
            self.fetures.extend(
                [
                    f"Filesystem volume name:   {volume.superblock.s_volume_name.decode()}",
                    f"Last mounted on:          {volume.superblock.s_last_mounted.decode()}",
                    f"Filesystem UUID:          {volume.uuid.lower()}",
                    f"Filesystem magic number:  {hex(volume.superblock.s_magic)}",
                    f"Reserved block count:     {str(volume.superblock.s_reserved_pad)}",
                    f"Inode size:               {str(volume.superblock.s_inode_size)}",
                    f"Block size:               {str(volume.block_size)}",
                    f"Inode count:              {str(volume.superblock.s_inodes_count)}",
                    f"Partition Size:           {self.image_name.stat().st_size}",
                    f"Inodes per group:         {str(volume.superblock.s_inodes_per_group)}",
                ]
            )

            # Write to file
            self.__appendf("\n".join(self.fetures), self.file_features)

    def read_ext4(self):
        try:

            def scan_dir(root_inode, root_path=""):
                for entry_name, entry_inode_idx, entry_type in root_inode.open_dir():
                    # exclude '.', '..'
                    if entry_name in [".", "..", "lost+found"]:
                        continue

                    entry_inode = root_inode.volume.get_inode(entry_inode_idx, entry_type)
                    entry_inode_path = root_path + "/" + entry_name
                    mode = self.__get_octal_perm(entry_inode.mode_str)
                    uid = entry_inode.inode.i_uid
                    gid = entry_inode.inode.i_gid
                    con = ""

                    # loop over xattr ('security.selinux', b'u:object_r:vendor_file:s0\x00')
                    for i in list(entry_inode.xattrs()):
                        if i[0] == "security.selinux":
                            con = i[1].decode("utf-8")  # decode context
                            con = con[:-1]  # remove last car from context '\x00'
                        else:
                            pass

                    file_name_context = "/" + self.file_name + entry_inode_path
                    file_name_config = self.file_name + entry_inode_path

                    if self.file_name in ("system"):
                        file_name_context = entry_inode_path
                        file_name_config = entry_inode_path[
                            entry_inode_path.startswith("/") and len("/") :
                        ]

                    if entry_inode.is_dir:
                        self.num_dirs += 1
                        scan_dir(entry_inode, entry_inode_path)  # loop inside the directory
                        self.fs_config.append(f"{file_name_config} {uid} {gid} {mode}")
                        self.fs_context.append(f"{file_name_context} {con}")

                    elif entry_inode.is_file:
                        self.num_files += 1
                        self.fs_config.append(f"{file_name_config} {uid} {gid} {mode}")
                        self.fs_context.append(f"{file_name_context} {con}")

                    elif entry_inode.is_symlink:
                        self.num_links += 1
                        try:
                            link_target = entry_inode.open_read().read().decode("utf-8")
                            if '\0' not in link_target:
                                self.fs_config.append(
                                    f"{file_name_config} {uid} {gid} {mode} {link_target}"
                                )
                                self.fs_context.append(f"{file_name_context} {con}")
                            else:
                                print(f"Found a null byte in the link target {link_target}")
                        except UnicodeDecodeError:
                            print(f"Could not decode the link target of {entry_inode}.")

            # open image
            with open(self.image_name, "rb") as file:
                root = Volume(file).root
                scan_dir(root)

            self.__write_context()
            self.__write_config()
            self.__write_fetures()
            print(
                f"Processed {self.num_dirs} directories, {self.num_files} files, and {self.num_links} links."
            )

            return True  # Return True if everything was successful
        except Exception as e:
            print(f"An error occurred: {e}")
            return False  # Return False if an error occurred


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process an ext4 image.")
    parser.add_argument("image_path", type=str, help="Path to the ext4 image file.")
    parser.add_argument("info_path", type=str, help="Path to the output directory for info files.")
    args = parser.parse_args()

    reader = ReadExt4(args.image_path, args.info_path)

    print(
        f":: Saving information from {reader.file_name}.img...",
        f":: Image path -> {reader.image_name}",
        f":: Info dir   -> {reader.out_dir}",
        sep="\n",
        end="\n\n",
    )

    reader.read_ext4()

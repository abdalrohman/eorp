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
import re
import sys
from pathlib import Path
from typing import List, Tuple

from loguru import logger

from .config import Configs
from .img2sdat.img2sdat import img2sdat
from .interface import Colors, Fx, Mv
from .utils import (
    cat,
    list_folder,
    remove,
    run_command,
)
from .variables import CONFIG_FILE

# Check if the config file exists and write default values if not
config_file_path = Path(CONFIG_FILE)
config = Configs(config_file_path)


class CreateExt4:
    """
    Class for creating ext4 images.

    Attributes:
        configs (Configs): The Configs class instance.
        mke2fs (str): The path to the mke2fs executable.
        mke2fs_conf (str): The path to the mke2fs configuration file.
        e2fsdroid (str): The path to the e2fsdroid executable.
        img2simg (str): The path to the img2simg executable.
        brotli_tool (str): The path to the brotli executable.
        main_project (str): The main project path loaded from the configuration file.
        config_dir (Path): The path to the configuration directory.
        build_dir (Path): The path to the build directory.
        out_dir (Path): The path to the output directory.

    Methods:
        dump_data(file: str) -> Tuple[str, str, str, str, str, str]: Extracts specific data from the output of the tune2fs command.
        make_ext4(raw: bool = False, sparse: bool = False, brotli: bool = False, active: bool = True, list_build: list = "") -> None: Make ext4 filesystem.
        correct_contexts(self, fs_context_file: str) -> None: Correct the file contexts and add additional ones.
        define_file_contexts(self, fs_context_file: str) -> None: Define the file contexts.
    """

    def __init__(self):
        """
        Construct all the necessary attributes.
        """
        # Load configuration values from the configuration file
        self.configs = config
        self.mke2fs = self.configs.load_config("LINUX", "mke2fs")
        self.mke2fs_conf = self.configs.load_config("LINUX", "mke2fs_conf")
        self.e2fsdroid = self.configs.load_config("LINUX", "e2fsdroid")
        self.img2simg = self.configs.load_config("LINUX", "img2simg")
        self.brotli_tool = self.configs.load_config("LINUX", "brotli")

        # Load main project path from the configuration file
        self.main_project = self.configs.load_config("MAIN", "main_project")

        # Construct paths to the config, build, and output directories
        self.config_dir = Path(self.main_project, "Config")
        self.build_dir = Path(self.main_project, "Build")
        self.out_dir = Path(self.main_project, "Output")

    def dump_data(self, file: str) -> Tuple[str, str, str, str, str, str]:
        """Extracts specific data from the output of the tune2fs command.

        Parameters:
            file: The path to the file containing the output of the tune2fs command.

        Returns:
            A tuple containing the extracted data in the following order:
            - UUID
            - Inode size
            - Inode count
            - Block size
            - Reserved percent
            - Partition size
        """
        # Define the search patterns to extract specific data from the file
        search_patterns = {
            "uuid": r"Filesystem UUID:\s*(\S+)",
            "inode_size": r"Inode size:\s*(\d+)",
            "reserved_percent": r"Reserved block count:\s*(\d+)",
            "block_size": r"Block size:\s*(\d+)",
            "inode_count": r"Inode count:\s*(\d+)",
            "part_size": r"Partition Size:\s*(\d+)",
        }
        # Create an empty dictionary to store the extracted data
        data = {}
        # Read the entire file
        with open(file, "r", encoding="UTF-8") as f:
            file_content = f.read()
        # Extract data using regular expressions
        for key, pattern in search_patterns.items():
            match = re.search(pattern, file_content)
            if match:
                data[key] = match.group(1)
        # Return the extracted data as a tuple
        return (
            data.get("uuid", ""),
            data.get("inode_size", ""),
            data.get("inode_count", ""),
            data.get("block_size", ""),
            data.get("reserved_percent", ""),
            data.get("part_size", ""),
        )

    def __print_images(self) -> List[str]:
        """Return a list of images to build.

        Returns:
            list_build (List[str]): A list of images to build.
        """
        dict_build = list_folder(self.out_dir)
        logger.info(f"Images list in {self.main_project}: ")
        logger.info(f"{Fx.bold}{Colors.yellow}Type [all/a] to choose all images")
        logger.info(f"{Fx.bold}{Colors.yellow}Type [exit/e] to exit{Mv.d(1)}")
        try:
            logger.info("Choose partition(s) to build: ")
            ans = input("Enter the partition number(s) [1, 2, ...]: ").split(",")
            logger.info(f"Your choice is {ans}.")
            if ans == ["all"] or ans == ["a"]:
                return list(dict_build.values())
            elif ans == ["exit"] or ans == ["e"]:
                logger.info("Exiting...")
                raise SystemExit(0)
            else:
                return [dict_build[int(num_part)] for num_part in ans]
        except KeyboardInterrupt:
            logger.info("Terminating...")
            sys.exit(1)
        except (KeyError, ValueError) as e:
            logger.exception(f"Terminating. Invalid input {e}.")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"An error occurred {e}.")
            sys.exit(1)

    def make_ext4(
            self,
            raw: bool = False,
            sparse: bool = False,
            brotli: bool = False,
            active: bool = True,
            list_build: list = "",
    ) -> None:
        """Make ext4 filesystem.

        Parameters:
            raw (bool, optional): If True, create a raw ext4 image. Defaults to False.
            sparse (bool, optional): If True, create a sparse ext4 image. Defaults to False.
            brotli (bool, optional): If True, compress the ext4 image using brotli. Defaults to False.
            active (bool, optional): If True, use the images returned by the __print_images() method. Defaults to True.
            list_build (str, optional): A list of images to build. Defaults to "".
        """
        images_build = self.__print_images() if active else list_build
        for partition in images_build:
            if raw:
                part_path = os.path.join(self.out_dir, partition)
                filesystem_config = os.path.join(
                    self.config_dir, partition + "_filesystem_config.txt"
                )
                file_contexts = os.path.join(
                    self.config_dir, partition + "_file_contexts.txt"
                )
                if not os.path.exists(part_path):
                    continue
                file_features = os.path.join(
                    self.config_dir, partition + "_filesystem_features.txt"
                )
                try:
                    (
                        uuid,
                        inode_size,
                        inode_count,
                        block_size,
                        reserved_percent,
                        part_size,
                    ) = self.dump_data(file_features)
                except UnboundLocalError:
                    logger.exception(f"Check {file_features}")
                    sys.exit(1)
                # Truncate output file since mke2fs will keep verity section in existing file
                with open(
                        os.path.join(self.build_dir, partition + ".img"), "w"
                ) as output_file:
                    output_file.truncate()
                label = partition
                last_mounted_directory = "/" + partition
                # run mke2fs
                if partition in ("system", "system_a"):
                    last_mounted_directory = "/"
                # FIXME delete this after fix extract_erofs to write inode_size to info file
                inode_size = 256
                reserved_percent = 0
                block_size = 4096
                mke2fs_cmd = [
                    self.mke2fs,
                    "-O",
                    "^has_journal",
                    "-L",
                    label,
                    "-N",
                    str(inode_count),
                    "-I",
                    str(inode_size),
                    "-M",
                    last_mounted_directory,
                    "-m",
                    str(reserved_percent),
                    "-U",
                    uuid,
                    "-t",
                    "ext4",
                    "-b",
                    str(block_size),
                    os.path.join(self.build_dir, partition + ".img"),
                    str(int(part_size) // int(block_size)),
                ]
                mke2fs_env = {
                    "MKE2FS_CONFIG": self.mke2fs_conf,
                    "E2FSPROGS_FAKE_TIME": "1230768000",
                }
                output, ret = run_command(mke2fs_cmd, mke2fs_env)
                if ret != 0:
                    logger.error(f"Failed to run mke2fs: {output}")
                    sys.exit(4)
                # Run e2fsdroid
                e2fsdroid_env = {"E2FSPROGS_FAKE_TIME": "1230768000"}
                file_con_cmd = []
                if os.path.exists(filesystem_config) and os.path.exists(file_contexts):
                    file_con_cmd = ["-C", filesystem_config] + ["-S", file_contexts]
                else:
                    logger.warning(
                        f"Try without ({filesystem_config}) and {file_contexts}"
                    )
                    filesystem_config = ""
                    file_contexts = ""
                # The options must be ordered
                e2fsdroid_cmd = (
                        [
                            self.e2fsdroid,
                            "-e",
                            "-T",
                            "1230768000",
                        ]
                        + file_con_cmd
                        + ["-S", os.path.join(self.config_dir, "file_contexts.txt")]
                        + ["-f", os.path.join(self.out_dir, partition)]
                        + ["-a", last_mounted_directory]
                        + [os.path.join(self.build_dir, partition + ".img")]
                )
                output, ret = run_command(e2fsdroid_cmd, e2fsdroid_env)
                if ret != 0:
                    logger.error(f"Failed to run e2fsdroid_cmd: {output}")
                    remove(os.path.join(self.build_dir, partition + ".img"))
                    sys.exit(4)
                print("")
            if sparse:
                raw_img = os.path.join(self.build_dir, partition + ".img")
                sparse_img = os.path.join(self.build_dir, partition + ".sparse")
                if not os.path.exists(raw_img):
                    continue
                logger.info("Convert raw image to sparse...")
                cmd = [self.img2simg, raw_img, sparse_img]
                run_command(cmd, verbose=True)
                if os.path.isfile(sparse_img):
                    remove(raw_img)
            if brotli:
                sparse_img = os.path.join(self.build_dir, partition + ".sparse")
                sdat_img = os.path.join(self.build_dir, partition + ".new.dat")
                if not os.path.exists(sparse_img):
                    continue
                logger.info("Convert sparse image to sdat...")

                img2sdat(
                    input_image=sparse_img,
                    prefix=partition,
                    cache_size=402653184,
                    out_dir=self.build_dir,
                    version=4,
                )

                if os.path.isfile(sdat_img):
                    remove(sparse_img)
                logger.info("Compress with brotli...")
                cmd = [self.brotli_tool, "-q", "6", "-v", "-f", sdat_img]
                run_command(cmd, verbose=True)
                if os.path.isfile(sdat_img + ".br"):
                    remove(sdat_img)

    def correct_contexts(self, fs_context_file: str) -> None:
        """Correct the file contexts and add additional ones.

        Parameters:
            fs_context_file (str): The path to the file containing the file contexts.
        """
        logger.info(f"Correcting {fs_context_file}")
        fs_context = []
        # Define a regular expression to match custom prefixes
        my_str = "(my_(engineering|version|product|company|preload|bigball|carrier|region|stock|heytap|manifest|custom)|special_preload)"
        # Define another regular expression to match specific prefixes
        my_str2 = "(my_version|odm)"
        # Add the corrected file contexts to the list
        fs_context.extend(
            [
                f"/{my_str}(/.*)?           u:object_r:system_file:s0",
                f"/{my_str}/overlay(/.*)?   u:object_r:vendor_overlay_file:s0",
                f"/{my_str}/non_overlay/overlay(/.*)?   u:object_r:vendor_overlay_file:s0",
                f"/{my_str}/vendor_overlay/[0-9]+/.*   u:object_r:vendor_file:s0",
                f"/{my_str}/vendor/etc(/.*)?    u:object_r:vendor_configs_file:s0",
                f"/{my_str2}/build.prop                                             u:object_r:vendor_file:s0",
                f"/{my_str2}/vendor_overlay/[0-9]+/lib(64)?(/.*)?    u:object_r:same_process_hal_file:s0",
                f"/{my_str2}/vendor_overlay/[0-9]+/etc/camera(/.*)?  u:object_r:same_process_hal_file:s0",
                f"/{my_str2}/vendor_overlay/[0-9]+/camera(/.*)?      u:object_r:vendor_file:s0",
                f"/{my_str2}/lib64/camera(/.*)?                      u:object_r:vendor_file:s0",
                f"/{my_str2}/vendor_overlay/lib?(/.*)?         u:object_r:same_process_hal_file:s0",
                f"/{my_str2}/vendor_overlay/lib(64)?(/.*)?     u:object_r:same_process_hal_file:s0",
                "/my_manifest/build.prop u:object_r:vendor_file:s0",
                "/my_company/theme_bak(/.*)? u:object_r:oem_theme_data_file:s0",
                "/my_product/etc/project_info.txt                                   u:object_r:vendor_file:s0",
                "/my_product/product_overlay/framework(/.*)?          u:object_r:system_file:s0",
                "/my_product/product_overlay/etc/permissions(/.*)?    u:object_r:system_file:s0",
                "/(vendor|my_engineering|system/vendor)/bin/factory	u:object_r:factory_exec:s0",
                "/(vendor|my_engineering|system/vendor)/bin/pcba_diag	u:object_r:pcba_diag_exec:s0",
                "/my_product/lib(64)?/libcolorx-loader\\.so                         u:object_r:same_process_hal_file:s0",
                "/my_product/vendor/firmware(/.*)      u:object_r:vendor_file:s0",
                "/my_version/vendor/firmware(/.*)?      u:object_r:vendor_file:s0",
                '/my_bigball(/.*)?                    u:object_r:rootfs:s0"',
                "/my_carrier(/.*)?                    u:object_r:rootfs:s0",
                "/my_company(/.*)?                    u:object_r:rootfs:s0",
                "/my_engineering(/.*)?                u:object_r:rootfs:s0",
                "/my_heytap(/.*)?                     u:object_r:rootfs:s0",
                "/my_manifest(/.*)?                   u:object_r:rootfs:s0",
                "/my_preload(/.*)?                    u:object_r:rootfs:s0",
                "/my_product(/.*)?                    u:object_r:rootfs:s0",
                "/my_region(/.*)?                     u:object_r:rootfs:s0",
                "/my_stock(/.*)?                      u:object_r=rootfs=s0",
                "/special_preload(/.*)?               u=object_r=rootfs=s0",
                "/firmware(/.*)?         u=object_r=firmware_file=s0",
                "/bt_firmware(/.*)?      u=object_r=bt_firmware_file=s0",
                "/persist(/.*)?          u=object_r=mnt_vendor_file=s0",
                "/dsp                    u=object_r=system_file=s0",
                "/oem                    u=object_r=system_file=s0",
                "/op1                    u=object_r=system_file=s0",
                "/op2                    u=object_r=system_file=s0",
                "/charger_log            u=object_r=system_file=s0",
                "/audit_filter_table     u=object_r=system_file=s0",
                "/keydata                u=object_r=system_file=s0",
                "/keyrefuge              u=object_r=system_file=s0",
                "/omr                    u=object_r=system_file=s0",
                "/publiccert.pem         u=object_r=system_file=s0",
                "/sepolicy_version       u=object_r=system_file=s0",
                "/cust                   u=object_r=system_file=s0",
                "/donuts_key             u=object_r=system_file=s0",
                "/v_key                  u=object_r=system_file=s0",
                "/carrier                u=object_r=system_file=s0",
                "/dqmdbg                 u=object_r=system_file=s0",
                "/ADF                    u=object_r=system_file=s0",
                "/APD                    u=object_r=system_file=s0",
                "/asdf                   u:object_r:system_file:s0",
                "/batinfo                u:object_r:system_file:s0",
                "/voucher                u:object_r:system_file:s0",
                "/xrom                   u:object_r:system_file:s0",
                "/custom                 u:object_r:system_file:s0",
                "/cpefs                  u:object_r:system_file:s0",
                "/modem                  u:object_r:system_file:s0",
                "/module_hashes          u:object_r:system_file:s0",
                "/pds                    u:object_r:system_file:s0",
                "/tombstones             u:object_r:system_file:s0",
                "/factory                u:object_r:system_file:s0",
                "/oneplus(/.*)?          u:object_r:system_file:s0",
                "/addon.d                u:object_r:system_file:s0",
                "/op_odm                 u:object_r:system_file:s0",
                "/avb                    u:object_r:system_file:s0",
                "/opconfig               u:object_r:system_file:s0",
                "/opcust                 u:object_r:system_file:s0",
                "/mi_ext(/.*)?           u:object_r:system_file:s0",
                "/(odm|vendor/odm)(/.*)?                       u:object_r:vendor_file:s0",
            ]
        )

        # Sort the list alphabetically
        fs_context.sort()
        # Write the list to the file
        cat(msg="\n".join(fs_context), out_file=fs_context_file)

    def define_file_contexts(self) -> None:
        """
        Defines the file contexts by checking the existence of specific file paths and writing them to a file.
        """

        # Define paths to the vendor, system, product, and system_ext file contexts
        vendor_context = os.path.join(
            self.out_dir, "vendor/etc/selinux/vendor_file_contexts"
        )
        system_context = os.path.join(
            self.out_dir, "system/system/etc/selinux/plat_file_contexts"
        )
        product_context = os.path.join(
            self.out_dir, "product/etc/selinux/product_file_contexts"
        )
        system_ext_context = os.path.join(
            self.out_dir, "system_ext/etc/selinux/system_ext_file_contexts"
        )
        file_context = os.path.join(self.config_dir, "file_contexts.txt")

        # Check if the file contexts file exists
        file_context_exists = os.path.exists(file_context)

        if not file_context_exists:
            # If the file contexts file does not exist, check if the vendor, system, product, and system_ext file contexts exist and write them to the file
            if os.path.exists(system_context):
                logger.info(f"Writing from {system_context}")
                cat(in_file=system_context, out_file=file_context)
            if os.path.exists(vendor_context):
                logger.info(f"Writing from {vendor_context}")
                cat(in_file=vendor_context, out_file=file_context)
            if os.path.exists(system_ext_context):
                logger.info(f"Writing from {system_ext_context}")
                cat(in_file=system_ext_context, out_file=file_context)
            if os.path.exists(product_context):
                logger.info(f"Writing from {product_context}")
                cat(in_file=product_context, out_file=file_context)

        file_context_exists = os.path.exists(file_context)

        if file_context_exists:
            # If the file contexts file exists, correct the file contexts
            self.correct_contexts(file_context)
        else:
            # If the file contexts file does not exist, log an error and exit
            logger.error(f"{file_context} not found!!")
            sys.exit(1)

    def main(
            self, raw: bool = False, sparse: bool = False, brotli: bool = False
    ) -> None:
        """Main method for creating ext4 images.

        Parameters:
            raw (bool, optional): If True, create a raw ext4 image. Defaults to False.
            sparse (bool, optional): If True, create a sparse ext4 image. Defaults to False.
            brotli (bool, optional): If True, compress the ext4 image using brotli. Defaults to False.
        """
        # ensure file_context.txt exist
        self.define_file_contexts()

        # Make the ext4 images
        self.make_ext4(raw, sparse, brotli)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create ext4 images")
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
            These options must be used in the following order: first raw, then sparse, then brotli.
        """,
    )

    args = parser.parse_args()

    if args.build_image:
        build_image_set = set(args.build_image)
        raw = "raw" in build_image_set or "r" in build_image_set
        sparse = "sparse" in build_image_set or "s" in build_image_set
        brotli = "brotli" in build_image_set or "b" in build_image_set

        if raw or sparse or brotli:
            CreateExt4().main(raw, sparse, brotli)

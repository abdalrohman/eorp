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
from pathlib import Path

from loguru import logger

from .config import Configs
from .create_ext4 import CreateExt4
from .img2sdat.img2sdat import img2sdat
from .utils import (
    create_gzip,
    create_zstd,
    remove,
    run_command,
)
from .variables import CONFIG_FILE

# Check if the config file exists and write default values if not
config_file_path = Path(CONFIG_FILE)
config = Configs(config_file_path)


class CreateSuper:
    """
    This class is used to create a super partition.

    Attributes:
        sparse (bool): Whether to create a sparse super partition.
        compression_type (str): The type of compression to use. Can be one of ['zstd', 'gz', 'brotli'].
        config (Config): An instance of the Config class.
        metadata_size (int): The size of the metadata.
        metadata_slot (int): The number of metadata slots.
        super_partition_size (int): The size of the super partition.
        super_partition_groups (list): The groups in the super partition.
        super_partition_name (str): The name of the super partition.
        partition_list (list): The list of partitions in the super partition.
        main_project (str): The path to the main project directory.
        config_dir (str): The path to the configuration directory.
        build_dir (str): The path to the build directory.
        lpmake_path (str): The path to the lpmake tool.
        img2simg_path (str): The path to the img2simg tool.
        simg2img_path (str): The path to the simg2img tool.
        brotli_tool (str): The path to the brotli tool.
        file_context (str): The path to the file_contexts.txt file.

    Methods:
        check_image_files_existence(): Checks if all image files exist and builds missing ones if necessary.
        get_image_file_sizes(): Returns a dictionary containing the sizes of all image files in bytes.
        create_super_img(): Creates the super.img file.
        compress_with_brotli(super_img): Compresses the super image with brotli.
    """

    def __init__(
            self, sparse_super_partition: bool = False, compression_type: str = None
    ):
        """
        Constructs all the necessary attributes for th CreateSuper object.

        Parameters:
            sparse_super_partition (bool): Whether to create a sparse super partition.
            compression_type (str): The type of compression to use. Can be one of ['zstd', 'gz', 'brotli'].
        """
        self.sparse = sparse_super_partition
        self.compression_type = compression_type
        self.config = config
        self.metadata_size = self.config.load_config("DEVICE_INFO", "metadata_size")
        self.metadata_slot = self.config.load_config("DEVICE_INFO", "metadata_slot")
        self.super_partition_size = self.config.load_config(
            "DEVICE_INFO", "super_partition_size"
        )
        self.super_partition_groups = self.config.load_config(
            "DEVICE_INFO", "super_partition_groups"
        )
        self.super_partition_name = self.config.load_config(
            "DEVICE_INFO", "super_partition_name"
        )
        self.partition_list = self.config.load_config(
            "DEVICE_INFO", "qti_dynamic_partitions_partition_list"
        ).split(" ")
        self.main_project = self.config.load_config("MAIN", "main_project")
        self.config_dir = os.path.join(self.main_project, "Config")
        self.build_dir = os.path.join(self.main_project, "Build")
        self.lpmake_path = self.config.load_config("LINUX", "lpmake")
        self.img2simg_path = self.config.load_config("LINUX", "img2simg")
        self.simg2img_path = self.config.load_config("LINUX", "simg2img")
        self.brotli_tool = self.config.load_config("LINUX", "brotli")
        self.file_context = os.path.join(self.config_dir, "file_contexts.txt")

    def check_image_files_existence(self):
        """
        Checks if all image files exist and builds missing ones if necessary.

        If any image files are missing, this method will attempt to build them using the `CreateExt4` class. If the file contexts file is missing, this method will also attempt to define it using the `CreateExt4` class.
        """
        list_builds = []
        for image_file in self.partition_list:
            img_path = os.path.join(self.build_dir, f"{image_file}.img")
            if not os.path.exists(img_path):
                logger.error(f"{image_file} missing try to build it first")
                list_builds.append(image_file)

        if os.path.exists(self.file_context):
            pass
        else:
            CreateExt4().define_file_contexts()

        logger.info("Start building missing images")
        CreateExt4().make_ext4(raw=True, active=False, list_build=list_builds)

    def get_image_file_sizes(self):
        """
        Returns a dictionary containing the sizes of all image files in bytes.

        Returns:
            dict: A dictionary mapping image file names to their sizes.
        """
        sizes = {}
        for image_file in self.partition_list:
            img_path = os.path.join(self.build_dir, f"{image_file}.img")
            sizes[image_file] = os.path.getsize(img_path)
        return sizes

    def create_super_img(self):
        """
        Creates a super partition image.

        This method first checks if all image files exist and builds missing ones if necessary. It then creates a super partition image using the `lpmake` tool. If a compression type is specified, this method will also attempt to compress the super partition image using the specified compression type.
        """
        self.check_image_files_existence()
        sizes = self.get_image_file_sizes()

        partition_commands = []
        for image_file, img_size in sizes.items():
            partition_commands.extend(
                [
                    "--partition",
                    f"{image_file}:readonly:{img_size}:{self.super_partition_groups}",
                    "--image",
                    f'{image_file}={os.path.join(self.build_dir, f"{image_file}.img")}',
                ]
            )

        super_commands = [
            self.lpmake_path,
            "--metadata-size",
            f"{str(self.metadata_size)}",
            "--metadata-slots",
            f"{str(self.metadata_slot)}",
            "--device",
            f"{self.super_partition_name}:{self.super_partition_size}",
            "--group",
            f"{self.super_partition_groups}:{self.super_partition_size}",
        ]
        out_put = ["-o", os.path.join(self.build_dir, "super.img")]
        cmd = (
                super_commands
                + (["--sparse"] if self.sparse else [])
                + partition_commands
                + out_put
        )
        run_command(cmd, verbose=True)

        if self.compression_type is not None:
            compression_mapping = {
                "gz": create_gzip,
                "gzip": create_gzip,
                "zstd": create_zstd,
                "zst": create_zstd,
                "brotli": self.compress_with_brotli,
                "br": self.compress_with_brotli,
            }
            compression_func = compression_mapping.get(self.compression_type)
            if compression_func is not None:
                compression_func(
                    os.path.join(self.build_dir, "super.img"),
                    os.path.join(self.build_dir, "super.img"),
                )
                # TODO remove super.img file after compressed
            else:
                logger.info("Not supported compression type!")

        logger.info(
            f"Successfully created super.img file at {os.path.join(self.build_dir)}"
        )

    def compress_with_brotli(self, super_img):
        """
        Compresses a super partition image using the brotli tool.

        This method first converts the super partition image to an sdat file using the `img2sdat` tool. It then compresses the sdat file using the brotli tool.

        Parameters:
            super_img (str): The path to the super partition image to compress.
        """
        sdat_img = os.path.join(self.build_dir, "super.new.dat")
        if os.path.exists(super_img):
            logger.info("Convert super image to sdat...")

            img2sdat(
                input_image=super_img,
                prefix=super,
                cache_size=402653184,
                out_dir=self.build_dir,
                version=4,
            )

            if os.path.isfile(sdat_img):
                remove(super_img)
            logger.info("Compress with brotli...")
            cmd = [self.brotli_tool, "-q", "6", "-v", "-f", sdat_img]
            run_command(cmd, verbose=True)
            if os.path.isfile(sdat_img + ".br"):
                remove(sdat_img)
        else:
            logger.error(f"{super_img} does not exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build super partition and compress with: sparse, zstd, gzip, brotli"
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

    args = parser.parse_args()

    if args.super_image:
        for method in args.super_image:
            if method not in ["none", "no", "sparse", "s"]:
                CreateSuper(compression_type=method).create_super_img()
            else:
                CreateSuper(
                    sparse_super_partition=True, compression_type=method
                ).create_super_img()

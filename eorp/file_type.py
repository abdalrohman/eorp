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
import io
import struct
import sys
from pathlib import Path

# [constant_section]----------------------------------------------------------------->
# Super image constant

LP_PARTITION_RESERVED_BYTES = 4096
LP_METADATA_GEOMETRY_SIZE = 4096
LP_METADATA_HEADER_MAGIC = 0x414C5030
LP_METADATA_GEOMETRY_MAGIC = 0x616C4467

# Sparse image constant
SPARSE_HEADER_MAGIC = 0xED26FF3A

# Erofs image constant
EROFS_SUPER_MAGIC_V1 = 0xE0F5E1E2
EROFS_SUPER_OFFSET = 1024

# f2fs image constant
F2FS_SUPER_MAGIC = 0xF2F52010  # F2FS Magic Number
F2FS_SUPER_OFFSET = 1024  # byte-size offset

# Ext4 image constant
EXT4_SUPER_MAGIC = 0xEF53
EXT4_SUPER_OFFSET = 0x400

# Payload.bin constant
PAYLOAD_MAGIC_HEADER = b"CrAU"  # 0x55417243

# lzma constant
LZMA_MAGIC = 0x5D

# lz4 constant
LZ4_MAGIC = 0x184D2204

# gzip constant
GZIP_MAGIC = b"\x1f\x8b"  # \037\213

# zstd constant
ZSTD_MAGIC_NUMBER = 0xFD2FB528

# Android constant
BOOT_MAGIC = b"ANDROID!"
BOOT_ARGS_SIZE = 512
BOOT_EXTRA_ARGS_SIZE = 1024
BOOT_NAME_SIZE = 16

FORMATS = [
    "8s10I{}s{}s8I{}s".format(
        BOOT_NAME_SIZE, BOOT_ARGS_SIZE, BOOT_EXTRA_ARGS_SIZE
    ),  # Version 0
    "8s10I{}s{}s8I{}sI".format(
        BOOT_NAME_SIZE, BOOT_ARGS_SIZE, BOOT_EXTRA_ARGS_SIZE
    ),  # Version 1
    "8s10I{}s{}s8I{}sII".format(
        BOOT_NAME_SIZE, BOOT_ARGS_SIZE, BOOT_EXTRA_ARGS_SIZE
    ),  # Version 2
    "8s4I4I{}s{}s".format(BOOT_ARGS_SIZE, BOOT_EXTRA_ARGS_SIZE),  # Version 3
    "8s4I4I{}s{}sI".format(BOOT_ARGS_SIZE, BOOT_EXTRA_ARGS_SIZE),  # Version 4
]

# zip constant
ZIP_HEADER_MAGIC = 0x504B0304  # b"\x50\x4B\x03\x04"
ZIP_EMPTY_END_MAGIC = 0x504B0506  # b"\x50\x4B\x05\x06"
ZIP_SPLIT_END_MAGIC = 0x504B0102  # b"\x50\x4B\x01\x02"

# 7z constant
MAGIC_7Z = b"7z\xBC\xAF\x27\x1C"  # ==  "37 7A BC AF 27 1C"


# [end_constant_section]----------------------------------------------------------------->


# [img_file_check]------------------------------------------------------------------->
def validate_super_partition(
        file_path: Path, slot_number: int = 0, verbose: bool = False
) -> bool:
    """Validate the super partition."""
    try:
        # Open the file in binary read mode
        with open(file_path, "rb") as fd:
            # Define the format strings for struct.unpack
            header_fmt = "<I2H2I32sI32s"
            geometry_fmt = "<II32s3I"

            # Seek to the start of the geometry metadata and read it
            fd.seek(LP_PARTITION_RESERVED_BYTES, io.SEEK_SET)
            geometry_buffer = fd.read(struct.calcsize(geometry_fmt))
            # Unpack the geometry metadata
            (
                geometry_magic,
                _,
                _,
                metadata_max_size,
                metadata_slot_count,
                _,
            ) = struct.unpack(geometry_fmt, geometry_buffer)

            # Validate the geometry magic number
            if geometry_magic != LP_METADATA_GEOMETRY_MAGIC:
                return False

            # Calculate the offsets for the header metadata based on slot number
            base = LP_PARTITION_RESERVED_BYTES + (LP_METADATA_GEOMETRY_SIZE * 2)
            _tmp_offset = metadata_max_size * slot_number

            offsets = [
                base + _tmp_offset,
                base + metadata_max_size * metadata_slot_count + _tmp_offset,
            ]

            # For each offset, seek to it and read and check the header magic number
            for index, offset in enumerate(offsets):
                fd.seek(offset, io.SEEK_SET)
                header_buffer = fd.read(struct.calcsize(header_fmt))
                header_magic, _, _, _, _, _, _, _ = struct.unpack(
                    header_fmt, header_buffer
                )

                if header_magic == LP_METADATA_HEADER_MAGIC:
                    return True

            if verbose:
                print(
                    f"Geometry magic -> {geometry_magic} and Header magic -> {header_magic}"
                )
        return False
    except struct.error:
        return False


def validate_sparse_partitions(file_path: Path) -> bool:
    """

    """
    try:
        # Open the file in binary read mode
        with open(file_path, "rb") as fd:
            # Define the format string for struct.unpack
            # This format string corresponds to the sparse_header_t struct in C
            sparse_fmt = "<I2H2HI3I"

            # Read from the file the number of bytes specified by calcsize
            header_bin = fd.read(struct.calcsize(sparse_fmt))

            # Unpack the binary data according to the format string
            (
                magic,
                major_version,
                minor_version,
                file_hdr_sz,
                chunk_hdr_sz,
                _,  # blk_sz,
                _,  # total_blks,
                _,  # total_chunks,
                _,  # image_checksum,
            ) = struct.unpack(sparse_fmt, header_bin)

            # Validate the header values
            if magic != SPARSE_HEADER_MAGIC:
                return False

            if major_version != 1 or minor_version != 0:
                return False

            if file_hdr_sz != 28:
                return False

            if chunk_hdr_sz != 12:
                return False

        return True
    except struct.error:
        return False


def validate_erofs_superblock(file_path: Path) -> bool:
    """Validate the EROFS superblock."""
    try:
        with open(file_path, "rb") as fd:
            struct_format = "<I"
            fd.seek(EROFS_SUPER_OFFSET, io.SEEK_SET)

            (magic,) = struct.unpack(
                struct_format, fd.read(struct.calcsize(struct_format))
            )

            # Check if the magic number matches the expected value
            if magic != EROFS_SUPER_MAGIC_V1:
                return False

        return True
    except struct.error:
        return False


def validate_ext4_superblock(file_path: Path) -> bool:
    """Validate the EXT4 superblock."""
    try:
        with open(file_path, "rb") as fd:
            struct_fmt = "<13IHhH"
            fd.seek(EXT4_SUPER_OFFSET, io.SEEK_SET)

            header_bin = fd.read(struct.calcsize(struct_fmt))

            _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, s_magic = struct.unpack(
                struct_fmt, header_bin
            )

            # Check if the magic number matches the expected value
            if s_magic != EXT4_SUPER_MAGIC:
                return False

        return True
    except struct.error:
        return False


def validate_f2fs_superblock(file_path: Path) -> bool:
    """Validate the F2FS superblock."""
    try:
        with open(file_path, "rb") as fd:
            struct_format = "<I"
            fd.seek(F2FS_SUPER_OFFSET, io.SEEK_SET)

            (magic,) = struct.unpack(
                struct_format, fd.read(struct.calcsize(struct_format))
            )

            # Check if the magic number matches the expected value
            if magic != F2FS_SUPER_MAGIC:
                return False

        return True
    except struct.error:
        return False


def validate_payload(filepath: Path) -> bool:
    """Validate the payload header."""
    try:
        with open(filepath, "rb") as fd:
            struct_fmt = ">4sQQL"  # 8 bytes for version, 8 bytes for manifest length, 4 bytes for metadata signature length

            header_bin = fd.read(struct.calcsize(struct_fmt))

            magic, _, _, _ = struct.unpack(struct_fmt, header_bin)

            # Check if the magic number matches the expected value
            if magic != PAYLOAD_MAGIC_HEADER:
                return False

        return True
    except struct.error:
        return False


def validate_file_system(file_path: Path) -> str:
    """Validate the file system type of a given file."""

    file_path = Path(file_path)
    if not file_path.is_file() or file_path.stat().st_size == 0:
        return "Unknown"

    if validate_super_partition(file_path):
        return "super"
    elif validate_sparse_partitions(file_path):
        return "sparse"
    elif validate_erofs_superblock(file_path):
        return "erofs"
    elif validate_ext4_superblock(file_path):
        return "ext4"
    elif validate_f2fs_superblock(file_path):
        return "f2fs"
    elif validate_payload(file_path):
        return "payload"
    else:
        return "Unknown"


# [end_img_file_check]----------------------------------------------------------------->


# [compress_file_check_section]----------------------------------------------------------------->
def validate_lz4(filepath: Path) -> bool:
    """Validate the LZ4."""
    with open(filepath, "rb") as fd:
        struct_fmt = "<I"  # 4 bytes for magic

        header_bin = fd.read(struct.calcsize(struct_fmt))

        (magic,) = struct.unpack(struct_fmt, header_bin)

        # Check if the magic number matches the expected value
        if magic != LZ4_MAGIC:
            return False

    return True


def validate_lzma(filepath: Path) -> bool:
    """Validate the LZMA."""
    with open(filepath, "rb") as fd:
        struct_fmt = "<B"  # 1 byte for magic

        header_bin = fd.read(struct.calcsize(struct_fmt))

        (magic,) = struct.unpack(struct_fmt, header_bin)

        # Check if the magic number matches the expected value
        if magic != LZMA_MAGIC:
            return False

    return True


def validate_gzip(filepath: Path) -> bool:
    """Validate the GZIP header."""
    with open(filepath, "rb") as fd:
        struct_fmt = "<2s"  # 2 bytes for magic

        header_bin = fd.read(struct.calcsize(struct_fmt))

        (magic,) = struct.unpack(struct_fmt, header_bin)

        # Check if the magic number matches the expected value
        if magic != GZIP_MAGIC:
            return False

    return True


def validate_zstd(filepath: Path) -> bool:
    """Validate the Zstd."""
    with open(filepath, "rb") as fd:
        struct_fmt = "<I"  # 4 bytes for magic

        header_bin = fd.read(struct.calcsize(struct_fmt))

        (magic,) = struct.unpack(struct_fmt, header_bin)

        # Check if the magic number matches the expected value
        if magic != ZSTD_MAGIC_NUMBER:
            return False

    return True


def validate_zip_file(filepath: Path, verbose: bool = False) -> str:
    """Validate the zip file."""
    ZIP_MAGICS = [ZIP_HEADER_MAGIC, ZIP_EMPTY_END_MAGIC, ZIP_SPLIT_END_MAGIC]
    with open(filepath, "rb") as fd:
        struct_fmt = ">I"

        header_bin = fd.read(struct.calcsize(struct_fmt))

        magic = struct.unpack(struct_fmt, header_bin)[0]

        if verbose:
            if magic == ZIP_HEADER_MAGIC:
                return "Good zip file"
            elif magic == ZIP_EMPTY_END_MAGIC:
                return "Empty zip file"
            elif magic == ZIP_SPLIT_END_MAGIC:
                return "Split zip file"

        if magic not in ZIP_MAGICS:
            return False

    return True


def validate_7z_file(filepath: Path) -> bool:
    """Validate the 7z file."""
    with open(filepath, "rb") as fd:
        struct_fmt = "6B"
        header_bin = fd.read(struct.calcsize(struct_fmt))
        magic = struct.pack(struct_fmt, *header_bin)

        # Check if the magic number matches the expected value
        if magic != MAGIC_7Z:
            return False

    return True


def validate_compression_type(file_path: Path) -> str:
    """Validate the compression type of a given file."""

    file_path = Path(file_path)
    if not file_path.is_file() or file_path.stat().st_size == 0:
        return "Unknown"

    if validate_gzip(file_path):
        return "gzip"
    elif validate_zip_file(file_path):
        return "zip"
    elif validate_7z_file(file_path):
        return "7z"
    elif validate_lzma(file_path):
        return "lzma"
    elif validate_zstd(file_path):
        return "zstd"
    elif validate_lz4(file_path):
        return "lz4"
    elif file_path.suffix == ".br":
        return "brotli"
    else:
        return "Unknown"


# [end_compress_file_check_section]----------------------------------------------------------------->


# [validate_android_boot_section]----------------------------------------------------------------->
def remove_null_bytes(data):
    return tuple(
        value.rstrip(b"\x00") if isinstance(value, bytes) else value for value in data
    )


def validate_boot_img(filepath: Path, verbose: bool = False) -> bool:
    with open(filepath, "rb") as fd:
        struct_fmt = "8s"

        header_bin = fd.read(struct.calcsize(struct_fmt))

        magic = struct.unpack(struct_fmt, header_bin)[0]

        # Check if the magic number matches
        if magic != BOOT_MAGIC:
            return False

        if verbose:
            # Try each format to see which one fits
            for version, fmt in enumerate(FORMATS):
                fd.seek(0)  # Go back to the start of the file
                try:
                    data = struct.unpack(fmt, fd.read(struct.calcsize(fmt)))
                    cleaned_data = remove_null_bytes(data)
                    print("Boot Info:")
                    print(f"This is a version {version} boot.img file.")

                    if version == 0:
                        names = [
                            "magic",
                            "kernel size",
                            "kernel addresses",
                            "ramdisk size",
                            "ramdisk addresses",
                            "second_size",
                            "second addresses",
                            "tags addresses",
                            "page size",
                            "unused",
                            "os_version",
                            "Boot Name",
                            "cmdline",
                            "id_0",
                            "id_1",
                            "id_2",
                            "id_3",
                            "id_4",
                            "id_5",
                            "id_6",
                            "id_7",
                            "extra_cmdline",
                        ]
                    elif version == 1:
                        names = [
                            "magic",
                            "kernel size",
                            "kernel addresses",
                            "ramdisk size",
                            "ramdisk addresses",
                            "second_size",
                            "second addresses",
                            "tags addresses",
                            "page size",
                            "header_version",
                            "os_version",
                            "Boot Name",
                            "cmdline",
                            "id_0",
                            "id_1",
                            "id_2",
                            "id_3",
                            "id_4",
                            "id_5",
                            "id_6",
                            "id_7",
                            "extra_cmdline",
                            "recovery_[dtbo|acpio]_size",
                            "recovery_[dtbo|acpio]_offset",
                            "header_size",
                        ]
                    elif version == 2:
                        names = [
                            "magic",
                            "kernel size",
                            "kernel addresses",
                            "ramdisk size",
                            "ramdisk addresses",
                            "second_size",
                            "second addresses",
                            "tags addresses",
                            "page size",
                            "header_version",
                            "os_version",
                            "Boot Name",
                            "cmdline",
                            "id_0",
                            "id_1",
                            "id_2",
                            "id_3",
                            "id_4",
                            "id_5",
                            "id_6",
                            "id_7",
                            "extra_cmdline",
                            "recovery_[dtbo|acpio]_size",
                            "recovery_[dtbo|acpio]_offset",
                            "header_size",
                            "dtb_size",
                            "dtb_addr",
                        ]
                    elif version == 3:
                        names = [
                            "magic",
                            "kernel size",
                            "ramdisk size",
                            "os_version",
                            "header_size",
                            "reserved",
                            "header_version",
                            "cmdline",
                        ]
                    elif version == 4:
                        names = [
                            "magic",
                            "kernel size",
                            "ramdisk size",
                            "os_version",
                            "header_size",
                            "reserved",
                            "header_version",
                            "cmdline",
                            "signature_size",
                        ]

                    id_values = []
                    addr_values = []
                    size_values = []
                    cmdlines = []
                    other = []

                    for name, value in zip(names, cleaned_data):
                        if "id" in name:
                            id_values.append(f"0x{value:08x}")
                            continue
                        if "addresses" in name:
                            addr_values.append(f"{name} 0x{value:08x}")
                            continue
                        if "size" in name:
                            size_values.append(f"{name} 0x{value:08x}")
                            continue
                        if "cmdline" in name:
                            cmdlines.append(f"{name} : {value}")
                            continue
                        else:
                            other.append(f"{name} : {value}")

                    print("Sizes:")
                    for value in size_values:
                        print(f"\t{value}")
                    print("Addresses:")
                    for value in addr_values:
                        print(f"\t{value}")
                    print("Cmdlines:")
                    for value in cmdlines:
                        print(f"\t{value}")
                    print(f"id : {' '.join(id_values)}")
                    print("\n")
                    for value in other:
                        print(f"{value}")

                    break
                except struct.error:
                    continue

    return True


# [end_validate_android_boot_section]----------------------------------------------------------------->


if __name__ == "__main__":
    file_type = validate_file_system(Path(sys.argv[1]))

    print(file_type)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import re
import signal
import sys
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import Configs
from .utils import (
    copy_file,
    copy_folder,
    create_directory,
    get_rom_info,
    list_folder,
)
from .variables import CONFIG_FILE, ROOT_DIR

# Check if the config file exists and write default values if not
config_file_path = Path(CONFIG_FILE)
config = Configs(config_file_path)

super_gz = """#!/sbin/sh

OUTFD=/proc/self/fd/$2
ZIPFILE=$3

ui_print() {
  echo -e "ui_print $1\nui_print " >>$OUTFD
}

package_extract_file() {
  unzip -o -p "$ZIPFILE" $1 >$2
}

package_extract_gzip() {
  unzip -o -p "$ZIPFILE" $1 | tmp/gzip -d -c >$2
}

mkdir -p tmp
unzip -o -p "$ZIPFILE" bin/gzip > tmp/gzip
unzip -o -p "$ZIPFILE" bin/busybox > tmp/busybox
chmod 0755 tmp/gzip
chmod 0755 tmp/busybox


ui_print " "
ui_print "************************************************"
ui_print "   Base Port        :               "
ui_print "   Android version  : 13                          "
ui_print "   Security patch   :                   "
ui_print "   Device           : vayu                        "
ui_print "   By               : @abdularahman_alnassier     "
ui_print "************************************************"
ui_print " "

start_time=$(date +%s)

ui_print " :: Start Installation..."
ui_print " "
ui_print " :: Flashing firmware..."
ui_print " "

run_program "tmp/busybox", "mount", "/cache"
run_program "tmp/busybox", "mount", "/cust"
run_program "tmp/busybox", "rm", "-rf", "/cust"
run_program "tmp/busybox", "rm", "-rf", "/data/dalvik-cache"

package_extract_file "images/cmnlib64.mbn" "/dev/block/bootdevice/by-name/cmnlib64"
package_extract_file "images/imagefv.elf" "/dev/block/bootdevice/by-name/imagefv"
package_extract_file "images/cmnlib.mbn" "/dev/block/bootdevice/by-name/cmnlib"
package_extract_file "images/hyp.mbn" "/dev/block/bootdevice/by-name/hyp"
package_extract_file "images/BTFM.bin" "/dev/block/bootdevice/by-name/bluetooth"
package_extract_file "images/tz.mbn" "/dev/block/bootdevice/by-name/tz"
package_extract_file "images/aop.mbn" "/dev/block/bootdevice/by-name/aop"
package_extract_file "images/xbl_config.elf" "/dev/block/bootdevice/by-name/xbl_config"
package_extract_file "images/storsec.mbn" "/dev/block/bootdevice/by-name/storsec"
package_extract_file "images/uefi_sec.mbn" "/dev/block/bootdevice/by-name/uefisecapp"
package_extract_file "images/NON-HLOS.bin" "/dev/block/bootdevice/by-name/modem"
package_extract_file "images/qupv3fw.elf" "/dev/block/bootdevice/by-name/qupfw"
package_extract_file "images/abl.elf" "/dev/block/bootdevice/by-name/abl"
package_extract_file "images/dspso.bin" "/dev/block/bootdevice/by-name/dsp"
package_extract_file "images/devcfg.mbn" "/dev/block/bootdevice/by-name/devcfg"
package_extract_file "images/km41.mbn" "/dev/block/bootdevice/by-name/keymaster"
package_extract_file "images/xbl.elf" "/dev/block/bootdevice/by-name/xbl"
package_extract_file "images/cmnlib64.mbn" "/dev/block/bootdevice/by-name/cmnlib64bak"
package_extract_file "images/cmnlib.mbn" "/dev/block/bootdevice/by-name/cmnlibbak"
package_extract_file "images/hyp.mbn" "/dev/block/bootdevice/by-name/hypbak"
package_extract_file "images/tz.mbn" "/dev/block/bootdevice/by-name/tzbak"
package_extract_file "images/aop.mbn" "/dev/block/bootdevice/by-name/aopbak"
package_extract_file "images/xbl_config.elf" "/dev/block/bootdevice/by-name/xbl_configbak"
package_extract_file "images/uefi_sec.mbn" "/dev/block/bootdevice/by-name/uefisecappbak"
package_extract_file "images/qupv3fw.elf" "/dev/block/bootdevice/by-name/qupfwbak"
package_extract_file "images/abl.elf" "/dev/block/bootdevice/by-name/ablbak"
package_extract_file "images/devcfg.mbn" "/dev/block/bootdevice/by-name/devcfgbak"
package_extract_file "images/km41.mbn" "/dev/block/bootdevice/by-name/keymasterbak"
package_extract_file "images/xbl.elf" "/dev/block/bootdevice/by-name/xblbak"
package_extract_file "images/dtbo.img" "/dev/block/bootdevice/by-name/dtbo"
package_extract_file "images/logo.img" "/dev/block/bootdevice/by-name/logo"
package_extract_file "images/vbmeta.img" "/dev/block/bootdevice/by-name/vbmeta"
package_extract_file "images/vbmeta_system.img" "/dev/block/bootdevice/by-name/vbmeta_system"

ui_print " :: Flashing boot partition..."
ui_print " "
package_extract_file "images/boot.img" "/dev/block/bootdevice/by-name/boot"


ui_print " :: Flashing super partition..."
ui_print " "
# package_extract_file "images/cust.img" "/dev/block/bootdevice/by-name/cust"
package_extract_gzip "images/super.img.zst" "/dev/block/bootdevice/by-name/super"


ui_print " :: Cleaning..."
ui_print " "
run_program "/sbin/sh", "-c", "rm -rf /data/system/package_cache"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.miui.yellowpage"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.miui.aod"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.google.android.gms/app_dg_cache"
run_program "tmp/busybox", "rm", "-rf", "tmp/gzip"
run_program "tmp/busybox", "rm", "-rf", "tmp/busybox"

finish_time=$(($(date +%s) - "$start_time"))

ui_print "************************************************"
ui_print " :: Finish installation at $finish_time S       "
ui_print " :: Flashing successfully                       "
ui_print "************************************************"
ui_print " :: This work need for Donation to contenue     "
ui_print "************************************************"

exit 0

"""

super_zst = """#!/sbin/sh

OUTFD=/proc/self/fd/$2
ZIPFILE=$3

ui_print() {
  echo -e "ui_print $1\nui_print " >>$OUTFD
}

package_extract_file() {
  unzip -o -p "$ZIPFILE" $1 >$2
}

package_extract_zstd() {
  unzip -o -p "$ZIPFILE" $1 | tmp/zstd -d -c >$2
}

mkdir -p tmp
unzip -o -p "$ZIPFILE" bin/zstd > tmp/zstd
unzip -o -p "$ZIPFILE" bin/busybox > tmp/busybox
chmod 0755 tmp/zstd
chmod 0755 tmp/busybox


ui_print " "
ui_print "************************************************"
ui_print "   Base Port        :               "
ui_print "   Android version  : 13                          "
ui_print "   Security patch   :                   "
ui_print "   Device           : vayu                        "
ui_print "   By               : @abdularahman_alnassier     "
ui_print "************************************************"
ui_print " "

start_time=$(date +%s)

ui_print " :: Start Installation..."
ui_print " "
ui_print " :: Flashing firmware..."
ui_print " "

run_program "tmp/busybox", "mount", "/cache"
run_program "tmp/busybox", "mount", "/cust"
run_program "tmp/busybox", "rm", "-rf", "/cust"
run_program "tmp/busybox", "rm", "-rf", "/data/dalvik-cache"

package_extract_file "images/cmnlib64.mbn" "/dev/block/bootdevice/by-name/cmnlib64"
package_extract_file "images/imagefv.elf" "/dev/block/bootdevice/by-name/imagefv"
package_extract_file "images/cmnlib.mbn" "/dev/block/bootdevice/by-name/cmnlib"
package_extract_file "images/hyp.mbn" "/dev/block/bootdevice/by-name/hyp"
package_extract_file "images/BTFM.bin" "/dev/block/bootdevice/by-name/bluetooth"
package_extract_file "images/tz.mbn" "/dev/block/bootdevice/by-name/tz"
package_extract_file "images/aop.mbn" "/dev/block/bootdevice/by-name/aop"
package_extract_file "images/xbl_config.elf" "/dev/block/bootdevice/by-name/xbl_config"
package_extract_file "images/storsec.mbn" "/dev/block/bootdevice/by-name/storsec"
package_extract_file "images/uefi_sec.mbn" "/dev/block/bootdevice/by-name/uefisecapp"
package_extract_file "images/NON-HLOS.bin" "/dev/block/bootdevice/by-name/modem"
package_extract_file "images/qupv3fw.elf" "/dev/block/bootdevice/by-name/qupfw"
package_extract_file "images/abl.elf" "/dev/block/bootdevice/by-name/abl"
package_extract_file "images/dspso.bin" "/dev/block/bootdevice/by-name/dsp"
package_extract_file "images/devcfg.mbn" "/dev/block/bootdevice/by-name/devcfg"
package_extract_file "images/km41.mbn" "/dev/block/bootdevice/by-name/keymaster"
package_extract_file "images/xbl.elf" "/dev/block/bootdevice/by-name/xbl"
package_extract_file "images/cmnlib64.mbn" "/dev/block/bootdevice/by-name/cmnlib64bak"
package_extract_file "images/cmnlib.mbn" "/dev/block/bootdevice/by-name/cmnlibbak"
package_extract_file "images/hyp.mbn" "/dev/block/bootdevice/by-name/hypbak"
package_extract_file "images/tz.mbn" "/dev/block/bootdevice/by-name/tzbak"
package_extract_file "images/aop.mbn" "/dev/block/bootdevice/by-name/aopbak"
package_extract_file "images/xbl_config.elf" "/dev/block/bootdevice/by-name/xbl_configbak"
package_extract_file "images/uefi_sec.mbn" "/dev/block/bootdevice/by-name/uefisecappbak"
package_extract_file "images/qupv3fw.elf" "/dev/block/bootdevice/by-name/qupfwbak"
package_extract_file "images/abl.elf" "/dev/block/bootdevice/by-name/ablbak"
package_extract_file "images/devcfg.mbn" "/dev/block/bootdevice/by-name/devcfgbak"
package_extract_file "images/km41.mbn" "/dev/block/bootdevice/by-name/keymasterbak"
package_extract_file "images/xbl.elf" "/dev/block/bootdevice/by-name/xblbak"
package_extract_file "images/dtbo.img" "/dev/block/bootdevice/by-name/dtbo"
package_extract_file "images/logo.img" "/dev/block/bootdevice/by-name/logo"
package_extract_file "images/vbmeta.img" "/dev/block/bootdevice/by-name/vbmeta"
package_extract_file "images/vbmeta_system.img" "/dev/block/bootdevice/by-name/vbmeta_system"

ui_print " :: Flashing boot partition..."
ui_print " "
package_extract_file "images/boot.img" "/dev/block/bootdevice/by-name/boot"


ui_print " :: Flashing super partition..."
ui_print " "
# package_extract_file "images/cust.img" "/dev/block/bootdevice/by-name/cust"
package_extract_zstd "images/super.img.zst" "/dev/block/bootdevice/by-name/super"


ui_print " :: Cleaning..."
ui_print " "
run_program "/sbin/sh", "-c", "rm -rf /data/system/package_cache"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.miui.yellowpage"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.miui.aod"
run_program "/sbin/sh", "-c", "rm -rf /data/data/com.google.android.gms/app_dg_cache"
run_program "tmp/busybox", "rm", "-rf", "tmp/zstd"
run_program "tmp/busybox", "rm", "-rf", "tmp/busybox"

finish_time=$(($(date +%s) - "$start_time"))

ui_print "************************************************"
ui_print " :: Finish installation at $finish_time S       "
ui_print " :: Flashing successfully                       "
ui_print "************************************************"
ui_print " :: This work need for Donation to contenue     "
ui_print "************************************************"

exit 0
"""


class ZipCreator:
    """A class for creating a zip file for a given project.

    This class provides methods to prepare the necessary files and directories,
    create a zip file with the desired content, and generate an updater script
    for the zip file.

    Attributes:
        config_dir (str): The path to the config directory.
        build_dir (str): The path to the build directory.
        output_dir (str): The path to the output directory.
        zip_tmp (str): The path to the temporary zip directory.
        zip_installer_path (str): The path to the zip installer.
        images_dir (str): The path to the images directory.
        installer_type (str): The type of installer used in the zip file.

    Methods:
        __init__(config_dir: str, build_dir: str, output_dir: str, zip_tmp: str,
                 zip_installer_path: str, images_dir: str):
            Initializes an instance of the ZipCreator class.

        prepare_zip():
            Prepares the zip file by copying necessary files and directories.

        prepare_installer():
            Prepares the installer by copying necessary files and directories.

        create_zip():
            Creates a zip file with the given name and content.

        create_dyn_op_list():
            Creates a dynamic operation list.

        create_updater_script():
            Creates an updater script for the zip file.
    """

    def __init__(self):
        """Constructs all the necessary attributes for the ZipCreator class."""
        self.config = config
        self.main_project = self.config.load_config("MAIN", "main_project")
        self.config_dir = os.path.join(self.main_project, "Config")
        self.build_dir = os.path.join(self.main_project, "Build")
        self.output_dir = os.path.join(self.main_project, "Output")
        self.zip_tmp = os.path.join(self.build_dir, "zip_tmp")
        self.zip_installer_path = os.path.join(ROOT_DIR, "zip_installer")
        self.images_dir = os.path.join(self.zip_tmp, "images")
        self.installer_type = "br"

        if not os.path.exists(self.images_dir):
            create_directory(self.images_dir)

    def prepare_zip(self):
        """Prepares the zip file by copying necessary files and directories.

        This method copies the required files and directories from the zip installer
        path to the images directory in the temporary zip directory.
        """
        copy_folder(self.zip_installer_path, self.zip_tmp)

        for dir_name in ["firmware", "vbmeta", "boot"]:
            copy_folder(os.path.join(self.zip_installer_path, dir_name), self.images_dir)
        logos_path = os.path.join(self.zip_installer_path, "logo")
        logo_dict = list_folder(logos_path)
        logo_choice = logo_dict[int(input("Which logo do you want? "))]

        copy_file(
            os.path.join(os.path.join(logos_path, logo_choice)),
            os.path.join(self.images_dir, "logo.img"),
        )

    def prepare_installer(self):
        """Prepares the installer by copying necessary files and directories.

        This method identifies the installer type based on the available images in the
        build directory. It copies the required files and directories to the temporary
        zip directory.
        """
        images = os.listdir(os.path.join(self.build_dir))
        super_installer_type: Optional[str] = None
        installer_type: Optional[str] = None
        partition_list = ["system", "system_ext", "odm", "vendor", "product"]

        for image in images:
            source = os.path.join(self.build_dir, image)
            if image.startswith("super") and image.endswith((".zst", ".gz", ".br")):
                super_installer_type = image.rsplit(".", 1)[1]
                destination = os.path.join(self.images_dir, image)
                copy_file(source, destination)
                if image.endswith(".br"):
                    copy_file(
                        os.path.join(self.build_dir, "super.patch.dat"),
                        os.path.join(self.zip_tmp, "super.patch.dat"),
                    )
                    copy_file(
                        os.path.join(self.build_dir, "super.transfer.list"),
                        os.path.join(self.zip_tmp, "super.transfer.list"),
                    )
                    pass
                break

            for partition in partition_list:
                if image.startswith(partition) and image.endswith(".br"):
                    installer_type = "br"
                    destination = os.path.join(self.zip_tmp, image)
                    copy_file(source, destination)
                    copy_file(
                        os.path.join(self.build_dir, f"{partition}.patch.dat"),
                        os.path.join(self.zip_tmp, f"{partition}.patch.dat"),
                    )
                    copy_file(
                        os.path.join(self.build_dir, f"{partition}.transfer.list"),
                        os.path.join(self.zip_tmp, f"{partition}.transfer.list"),
                    )
                    break

        if installer_type:
            copy_folder(os.path.join(self.zip_installer_path, installer_type), self.zip_tmp)

        if super_installer_type:
            copy_folder(
                os.path.join(self.zip_installer_path, "super", super_installer_type),
                self.zip_tmp,
            )
            installer_type = super_installer_type

        if input("Do you want the fastboot installer inside the zip? (y/n) ").lower() == "y":
            copy_folder(os.path.join(self.zip_installer_path, "super", "fastboot"), self.zip_tmp)

        self.installer_type = installer_type

    def create_zip(self):
        """Creates a zip file with the given name and content.

        This method creates a zip file with the desired name and content by iterating
        through the files and directories in the temporary zip directory and adding them
        to the zip file.
        """

        def signal_handler(sig, frame):
            logger.info("Exiting gracefully...")
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # Remove date from zip_name if present
        # Format: YYYY.MM.DD_HH.MM
        # Example: 2023.09.05_14.10
        # Regex: \d{4}[-._]\d{2}[-._]\d{2}[-._]\d{2}[-._]\d{2}

        # Remove .zip extension from zip_name if present
        # Example: rom_2023.09.05_14.10.zip -> rom_2023.09.05_14.10

        # Add current date and time to zip_name
        # Format: YYYY.MM.DD_HH.MM
        # Example: rom_2023.09.05_14.10

        rom_type, incremental = get_rom_info(self.output_dir)
        zip_name = input("Enter the name of zip file: ") or f"{rom_type}_{incremental}"
        zip_name = re.sub(
            r"\d{4}[-._]\d{2}[-._]\d{2}[-._]\d{2}[-._]\d{2}",
            "",
            zip_name.split(".zip")[0],
        )
        zip_name = f'{zip_name}_{datetime.datetime.now().strftime("%Y.%m.%d_%H.%M")}.zip'

        zip_file_path = os.path.join(self.build_dir, zip_name)
        with zipfile.ZipFile(zip_file_path, "w") as my_zip:
            for root, dirs, files in os.walk(self.zip_tmp):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.zip_tmp)
                    with open(file_path, "rb") as f:
                        my_zip.writestr(arcname, f.read())

    def create_dyn_op_list(self):
        """Creates a dynamic operation list.

        This method creates a dynamic operation list for the zip file.
        """
        pass

    def create_updater_script(self) -> None:
        """Creates an updater script for the zip file.

        This method generates an updater script for the zip file based on the installer
        type. The updater script is written to the META-INF/com/google/android/update-binary
        file in the temporary zip directory.
        """
        meta_inf_dir = os.path.join(self.zip_tmp, "META-INF")

        if not os.path.isdir(meta_inf_dir):
            os.makedirs(meta_inf_dir, exist_ok=True)
            os.makedirs(os.path.join(meta_inf_dir, "com", "google", "android"), exist_ok=True)

        update_script_path = os.path.join(
            self.zip_tmp, "META-INF", "com", "google", "android", "update-binary"
        )

        if self.installer_type == "zst":
            logger.info(f"Write update-binary file for {self.installer_type}")
            with open(update_script_path, "w", encoding="UTF-8") as updater:
                updater.write(super_zst)
        if self.installer_type == "gz":
            logger.info(f"Write update-binary file for {self.installer_type}")
            with open(update_script_path, "w", encoding="UTF-8") as updater:
                updater.write(super_gz)


if __name__ == "__main__":
    zip_creator = ZipCreator()

    zip_creator.prepare_zip()
    zip_creator.prepare_installer()
    zip_creator.create_updater_script()
    # zip_creator.create_zip()

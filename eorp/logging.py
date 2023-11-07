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
import sys
from typing import Optional

from loguru import logger


class Log:
    """
    A class used to generate log files.

    Attributes:
        log_file_path (Path): The path to the log file. If None, no log file will be created.
        level (str): The log level. Defaults to "DEBUG".

    Methods:
        configure_logger(): Configures the logger to write logs to file and stdout.
    """

    def __init__(
            self, log_file_path: Optional[str] = None, loglevel: str = "DEBUG"
    ) -> None:
        """
        Constructs all the necessary attributes for the Log object.

        Parameters:
            log_file_path (str, optional): The path to the log file. If None, no log file will be created. Defaults to None.
            level (str, optional): The log level. Defaults to "DEBUG".
        """
        self.log_file_path = log_file_path
        self.level = loglevel
        self.configure_logger()

    def configure_logger(self) -> None:
        """
        Configures the logger to write logs to file and stdout.

        This method first removes any existing handlers, then adds a handler for stdout. If `log_file_path` is not None, it also adds a handler for the log file. The log file is set to rotate every 24 hours.
        """
        # Remove any existing handlers
        logger.remove()

        # Add a handler for stdout
        logger.add(
            sink=sys.stdout,
            format="<g>[{time:HH:mm}]</g> <level>{message}</level>",
            level=self.level,
        )

        # If log_file_path is not None, add a handler for the log file
        if self.log_file_path is not None:
            logger.add(
                sink=self.log_file_path,
                format="[{time:YYYY-MM-DD HH:mm:ss.SSS}] [{level}] [{file}:{line}] - {message}",
                level=self.level,
                rotation="24h",  # Rotate the log file every 24 hours
                enqueue=True,
            )

# USE Logging
# try:
#     os.makedirs(f"{CONFIG_DIR}/logs", exist_ok=True)
# except PermissionError:
#     print(f'ERROR!\nNo permission to write to "{CONFIG_DIR}" directory!')
#     raise SystemExit(1)

# # Initiate the Configs instance
# config_file_path = Path(CONFIG_FILE)
# config = Configs(config_file_path)

# # set log level
# LOG_LEVEL: str = config.load_config("MAIN", "log_level")

# # Instantiate the Log class with a log file path
# log = Log(log_file_path=LOG_FILE, loglevel=LOG_LEVEL)

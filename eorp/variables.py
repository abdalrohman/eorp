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
from pathlib import Path

ROOT_DIR: Path = Path(__file__).parent.resolve().parent

CONFIG_DIR: Path = Path(ROOT_DIR, ".config", "eorp")
# Configuration file path
CONFIG_FILE: Path = CONFIG_DIR.joinpath("config.ini")
# Log file path
LOG_FILE: Path = CONFIG_DIR.joinpath("logs", "eorp.log")


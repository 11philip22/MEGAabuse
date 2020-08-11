#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  Copyright Philip Woldhek 2020
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""" Makes backups of your mega.nz urls

Make a backup of your MEGAabuse uploads
and then make a backup of your backup. Don't worry mega.nz is a public service.

"""

import json
import sys
from os import path
import chromedriver_autoinstaller
from pathlib import Path

from megaabuse.accountfactory import AccountFactory

# Automatically install chromedriver
chromedriver_autoinstaller.install()

# Get script path
if getattr(sys, "frozen", False):
    SCRIPT_DIR = path.dirname(path.realpath(sys.executable))
else:
    SCRIPT_DIR = path.dirname(path.realpath(__file__))

# Get megatools path
BIN_PATH = Path(SCRIPT_DIR, "binaries")
if sys.platform == "win32":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_win", "megatools.exe")

elif sys.platform == "darwin":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_mac", "megatools")
    CMD_SERVER_PATH = Path()

elif sys.platform == "linux":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_linux", "megatools")

else:
    print("OS not supported")
    sys.exit(1)

AF = AccountFactory(MEGATOOLS_PATH)

OUT_FILE = Path(SCRIPT_DIR, "out.json")
with open(OUT_FILE) as file:
    OUT_DATA = json.load(file)

for folder, urls in OUT_DATA.items():
    required_accounts = len(urls)
    accounts = AF.guerrilla_gen_bulk(required_accounts, False, False)
    print(accounts)
    break

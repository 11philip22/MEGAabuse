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
from pathlib import Path

from megaabuse.accountfactory import AccountFactory
from megaabuse.selenium import Selenium
from megaabuse.megacmd import MegaCmd

# Get script path
# if getattr(sys, "frozen", False):
#     SCRIPT_DIR = path.dirname(path.realpath(sys.executable))
# else:
#     SCRIPT_DIR = path.dirname(path.realpath(__file__))
SCRIPT_DIR = "V:/MEGAabuse"

# Get megatools path
BIN_PATH = Path(SCRIPT_DIR, "binaries")
if sys.platform == "win32":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_win", "megatools.exe")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_windows")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "MEGAcmdServer.exe")

elif sys.platform == "darwin":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_mac", "megatools")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_mac")
    CMD_SERVER_PATH = Path()

elif sys.platform == "linux":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_linux", "megatools")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_linux")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "mega-cmd-server")
else:
    print("OS not supported")
    sys.exit(1)

AF = AccountFactory(MEGATOOLS_PATH)
SEL = Selenium()
CMD = MegaCmd(MEGACMD_PATH, CMD_SERVER_PATH)

OUT_FILE = Path(SCRIPT_DIR, "out.json")
with open(OUT_FILE) as file:
    OUT_DATA = json.load(file)

for folder, urls in OUT_DATA.items():
    folder_name = Path(folder).stem

    required_accounts = len(urls)
    print(f"Generating {required_accounts} accounts")
    accounts = AF.guerrilla_gen_bulk(required_accounts, False, False)

    print(folder_name)
    for url, credentials in zip(urls, accounts.items()):
        username = credentials[0]
        password = credentials[1]

        SEL.login(username, password)
        SEL.import_(url)
        SEL.logout()
        export_url = CMD.export_folder(username, password, f"/{folder_name}")
        print(url)
        print(export_url)
        print()
    break

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

"""" Uploads files to MEGA. without limits (except speed lol)

This Part of the program mostly contains spaghetti code for passing
the right parameters to the main class and managing the size of the
thread pool depending how many proxies are being used. No proxies is 1 thread.

"""

import argparse
import multiprocessing
import sys
from operator import not_
from os import linesep, listdir, path
from pathlib import Path

from megaabuse import MegaAbuse, get_logger
from megaabuse.macqueue import Queue

# Parse arguments
PARSER = argparse.ArgumentParser(description="MEGAabuse")

PARSER.add_argument(
    "-s", "--upload-subdirs",
    required=False,
    type=str,
    nargs='+',
    metavar="<dir>",
    help="Uploads all sub-folders of specified folder"
)
PARSER.add_argument(
    "-d", "--upload-dirs",
    required=False,
    type=str,
    nargs='+',
    metavar="<dir>",
    help="Upload one or multiple folders"
)
PARSER.add_argument(
    "-k", "--keep-alive",
    required=False,
    action="store_true",
    help="Reads from accounts.txt and keeps the accounts active"
)
PARSER.add_argument(
    "-c", "--check-urls",
    required=False,
    action="store_true",
    help="Checks if urls are still up"
)
PARSER.add_argument(
    "-v",
    required=False,
    action="store_true",
    help="Output logs"
)
PARSER.add_argument(
    "-vv",
    required=False,
    action="store_true",
    help="Output debug logs"
)
PARSER.add_argument(
    "-vvv",
    required=False,
    action="store_true",
    help="Output super debug logs"
)
PARSER.add_argument(
    "-n", "--no-write",
    required=False,
    action="store_true",
    help="Dont read or write any file"
)
PARSER.add_argument(
    "-p", "--proxy",
    required=False,
    action="store_true",
    help="Use socks5 proxies defined in proxy.txt"
)

SCRIPT_ARGS = PARSER.parse_args()
# Exit if help argument has been passed.
# To prevent writing empty log files
try:
    if SCRIPT_ARGS.h:
        sys.exit(0)
except AttributeError:
    # -h or --help has not been passed continue
    pass

# Get script location.
# Used for addressing MEGAcmd & megatools, writing resume files and writing logs.
if getattr(sys, "frozen", False):
    SCRIPT_DIR = path.dirname(path.realpath(sys.executable))
else:
    SCRIPT_DIR = path.dirname(path.realpath(__file__))

if SCRIPT_ARGS.vv:  # Enable debug mode
    level = 10
elif SCRIPT_ARGS.v:  # Enable console log output
    level = 20
elif SCRIPT_ARGS.vvv:  # Enable super verbose output
    level = 0
else:
    level = 40

# Get a logger
LOGGER = get_logger(
    "MEGAabuse",
    Path(SCRIPT_DIR, "logs"),
    level=level,
    write=not_(SCRIPT_ARGS.no_write)
)

if SCRIPT_ARGS.keep_alive and SCRIPT_ARGS.no_write:  # These two options are not compatible and keep_alive will not run
    LOGGER.warning("keep alive will not be performed since MEGAabuse is not reading or writing any files")

# Get the right megatools for your system
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

if not MEGATOOLS_PATH.is_file():
    raise FileNotFoundError("No megatools found!")

# PROXY_STORE = multiprocessing.Queue()  # Available proxies
proxy_store = Queue()  # Available proxies

if SCRIPT_ARGS.proxy:
    # If --proxy is passed load proxies from proxy file
    PROXY_FILE_PATH = Path(SCRIPT_DIR, "proxies.txt")
    if not PROXY_FILE_PATH.is_file():
        PROXY_FILE_PATH.touch()

    with open(PROXY_FILE_PATH) as proxy_file:
        for proxy_line in proxy_file:
            prox = proxy_line.strip("\n")
            LOGGER.debug("Loaded: %s", prox)
            proxy_store.put(prox)
    LOGGER.info("%s proxies loaded", proxy_store.qsize())

    # 1 thread for each proxy
    THREADS = proxy_store.qsize()
else:
    # No proxies. Use 1 thread
    THREADS = 1

# Counter of all the active workers. Used for logging purposes.
worker_count = multiprocessing.Value("i", 0)

# Init main class
ABUSE = MegaAbuse(
    MEGATOOLS_PATH,
    MEGACMD_PATH,
    Path(SCRIPT_DIR, "resume"),        # Optional
    Path(SCRIPT_DIR, "accounts.txt"),  # Optional
    Path(SCRIPT_DIR, "done.txt"),      # Optional
    CMD_SERVER_PATH,                   # Optional
    logger=LOGGER,
    write_files=not_(SCRIPT_ARGS.no_write)
)


def worker(folder_path):
    """" This is actually just a wrapper around
         upload_folder to handle the proxies """

    worker_count.value += 1  # Add to active worker counter. Used for logging purposes.
    LOGGER.debug("Worker spawned. Total workers: %s", worker_count.value)

    proxy = False
    if SCRIPT_ARGS.proxy:
        # Get proxy
        proxy = proxy_store.get()
        LOGGER.debug("Using proxy: %s", proxy)
        LOGGER.debug("Proxies in store: %s", proxy_store.qsize())

    exported_urls = ABUSE.upload_folder(folder_path, proxy)
    LOGGER.info("Done uploading: %s", folder_path)

    if SCRIPT_ARGS.proxy:
        # Return proxy
        proxy_store.put(proxy)
        LOGGER.debug("Returning proxy: %s", proxy)
        LOGGER.debug("Proxies in store: %s", proxy_store.qsize())

    worker_count.value -= 1  # Subtract to active worker counter. Used for logging purposes.
    LOGGER.debug("Worker finished. Total workers: %s", worker_count.value)

    return {folder_path: exported_urls}


# Create output file
if not SCRIPT_ARGS.no_write:
    OUTPUT_FILE = Path(SCRIPT_DIR, "out.txt")
    if not OUTPUT_FILE.is_file():
        OUTPUT_FILE.touch()


def urls_to_file(urls: list, folder_path):
    """" Write results to output file """

    LOGGER.log(0, "urls_to_file function called")

    LOGGER.debug("Writing to file")

    with open(OUTPUT_FILE, "a") as out_file:
        out_file.write(folder_path + linesep)
        for url in urls:
            LOGGER.debug("Writing to results file: %s", url)
            out_file.write(url + linesep)
        out_file.write(linesep)


def upload_manager(queue):
    """" Starts upload process and processes results """

    try:
        multiprocessing.freeze_support()  # todo: Does this do anything
        with multiprocessing.Pool(processes=THREADS) as pool:  # todo: Find fix for windows exe
            results = pool.map(worker, queue)  # Map pool to upload queue
    except RuntimeError as exc:
        traceback = sys.exc_info()[2]
        LOGGER.error(exc.with_traceback(traceback))
        return

    all_export_urls = {}
    for res in results:
        all_export_urls.update(res)

    LOGGER.info("Processed %s files", ABUSE.total_files_count.value)

    # Print results
    print()
    # Print folder path and export urls
    for e_file_path, res in all_export_urls.items():
        # Write to file
        if not SCRIPT_ARGS.no_write:
            urls_to_file(res, e_file_path)
        # Print folder path
        print(linesep + e_file_path)
        for e_url in res:
            # Print export url
            print(e_url)
    print()


upload_queue = []  # To be downloaded

# Upload sub dirs
if SCRIPT_ARGS.upload_subdirs:
    LOGGER.debug("Uploading sub-directories")

    for folder in SCRIPT_ARGS.upload_subdirs:
        d_path = Path(folder)

        for sub_folder in listdir(d_path):  # Append target folders to upload list
            upload_queue.append(Path(d_path, sub_folder))

# Upload multiple dirs
elif SCRIPT_ARGS.upload_dirs:
    LOGGER.debug("Uploading multiple directories")

    for folder in SCRIPT_ARGS.upload_dirs:  # Append target folders to upload list
        upload_queue.append(folder)

if SCRIPT_ARGS.upload_dirs or SCRIPT_ARGS.upload_subdirs:
    upload_manager(upload_queue)  # Start Upload process

# Keeps accounts active
if SCRIPT_ARGS.keep_alive and not SCRIPT_ARGS.no_write:  # Does not run if --no-write has been passed
    LOGGER.debug("Keeping accounts alive")

    with open(ABUSE.account_file) as account_f:
        # Read accounts from file
        for file_line in account_f:
            line = file_line.strip("\n")
            usern, passwd = line.split(";")

            # Log in and log out using megacmd
            LOGGER.info("Logging into: %s %s", usern, passwd)
            ABUSE.keep_alive(usern, passwd)

LOGGER.info("Done")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""" Uploads files to MEGA. without limits (except speed lol)

This Part of the program mostly contains spaghetti code for passing
the right parameters to the main class and managing the size of the
thread pool depending how many proxies are being used. No proxies is 1 thread.

"""

import json
import argparse
import multiprocessing
import sys
import time
from operator import not_
from os import linesep, listdir, path
from pathlib import Path

from megaabuse import MegaAbuse, get_logger
from megaabuse.macqueue import Queue

print("""
______  __________________________       ______                     
___   |/  /__  ____/_  ____/__    |_____ ___  /_____  _____________ 
__  /|_/ /__  __/  _  / __ __  /| |  __ `/_  __ \  / / /_  ___/  _ \\
_  /  / / _  /___  / /_/ / _  ___ / /_/ /_  /_/ / /_/ /_(__  )/  __/
/_/  /_/  /_____/  \____/  /_/  |_\__,_/ /_.___/\__,_/ /____/ \___/    
""")

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
    "-sf", "--skip",
    required=False,
    type=str,
    nargs='+',
    metavar="<.file extension>",
    help="Skip files by specifying one or more file extensions"
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
PARSER.add_argument(
    "-o", "--overwrite",
    required=False,
    action="store_true",
    help="Overwrite resume file. This will do an upload from scratch"
)
PARSER.add_argument(
    "-id", "--ignore-done",
    required=False,
    action="store_true",
    help="Ignores the done file"
)
PARSER.add_argument(
    "--generate-accounts",
    required=False,
    type=int,
    metavar="<amount of accounts>",
    help="Generate any number of mega accounts"
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
    mega_tools_path=MEGATOOLS_PATH,
    mega_cmd_path=MEGACMD_PATH,
    resume_dir=Path(SCRIPT_DIR, "resume"),           # Optional
    accounts_file=Path(SCRIPT_DIR, "accounts.txt"),  # Optional
    done_file=Path(SCRIPT_DIR, "done.txt"),          # Optional
    cmd_server_path=CMD_SERVER_PATH,                 # Optional
    logger=LOGGER,
    write_files=not_(SCRIPT_ARGS.no_write)
)

WRONG_EXTENSIONS = []


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

    start = time.time()  # Begin counter

    exported_urls = ABUSE.upload_folder(folder_path, WRONG_EXTENSIONS, proxy)
    LOGGER.info("Done uploading: %s", folder_path)

    end = time.time()
    elapsed_time_s = int(end - start)
    if elapsed_time_s >= 3600:  # If upload took longer than an hour
        sleep_time_s = elapsed_time_s / 4  # Wait 25% of tasks completion time
        if sleep_time_s >= 10800:  # Dont sleep longer than 3 hours
            sleep_time_s = 10800
        LOGGER.info("Sleeping for %is", sleep_time_s)
        time.sleep(sleep_time_s)

    if SCRIPT_ARGS.proxy:
        # Return proxy
        proxy_store.put(proxy)
        LOGGER.debug("Returning proxy: %s", proxy)
        LOGGER.debug("Proxies in store: %s", proxy_store.qsize())

    worker_count.value -= 1  # Subtract to active worker counter. Used for logging purposes.
    LOGGER.debug("Worker finished. Total workers: %s", worker_count.value)

    return {folder_path: exported_urls}


if not SCRIPT_ARGS.no_write:
    # Create output file
    OUTPUT_FILE = Path(SCRIPT_DIR, "out.txt")
    if not OUTPUT_FILE.is_file():
        OUTPUT_FILE.touch()

    # Create json output file
    JSON_OUTPUT_FILE = Path(SCRIPT_DIR, "out.json")
    if not JSON_OUTPUT_FILE.is_file():
        JSON_OUTPUT_FILE.touch()


def urls_to_file(urls: list, folder_path):
    """" Write results to output file """

    LOGGER.log(0, "urls_to_file function called")

    LOGGER.debug("Writing to file")

    # Write to outfile
    with open(OUTPUT_FILE, "a") as out_file:
        out_file.write(folder_path + linesep)
        for url in urls:
            LOGGER.debug("Writing to results file: %s", url)
            out_file.write(url + linesep)
        out_file.write(linesep)

    # Write to json out
    out_data = {}
    with open(JSON_OUTPUT_FILE, "r+") as json_file:
        try:
            out_data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            pass

    out_data.update({folder_path: urls})
    ABUSE.update_json_file(JSON_OUTPUT_FILE, out_data)


def upload_manager(queue):
    """" Starts upload process and processes results """
    with multiprocessing.Pool(processes=THREADS) as pool:
        results = pool.map(worker, queue)  # Map pool to upload queue

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


if __name__ == "__main__":
    """" Init
    On Windows multiprocessing.Pool.map will import the main module at start.
    This if statement is to avoid the pool being mapped recursively.
    """

    multiprocessing.freeze_support()

    upload_queue = []  # To be downloaded

    if not SCRIPT_ARGS.no_write:  # Not applicable if files are ignored
        if SCRIPT_ARGS.overwrite:
            ABUSE.overwrite = True

        if SCRIPT_ARGS.ignore_done:
            ABUSE.ignore_done = True

    # Generate Mega.nz accounts
    if SCRIPT_ARGS.generate_accounts:
        for user, passwd in ABUSE.get(SCRIPT_ARGS.generate_accounts).items():
            print(user, passwd)

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
        if SCRIPT_ARGS.skip:
            WRONG_EXTENSIONS = SCRIPT_ARGS.skip

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

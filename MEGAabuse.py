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

"""" Uploads files to MEGA. without limits (except speed lol) """

import argparse
import atexit
import json
import logging
import multiprocessing
import multiprocessing.queues
import re
import subprocess
import sys
import time
from os import linesep, listdir, path, walk
from pathlib import Path
from random import choice

from bs4 import BeautifulSoup
from names import get_first_name

import guerrillamail

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

# Create logger
LOGGER = logging.getLogger('MEGAabuse')
LOGGER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if not SCRIPT_ARGS.no_write:  # Dont bother with log files if --no-write is passed
    # Create logs folder
    LOG_DIR = Path(SCRIPT_DIR, "logs")
    if not LOG_DIR.is_dir():
        LOG_DIR.mkdir()

    # Create log file
    LOG_FILE = Path(LOG_DIR, "log.txt")
    # If log file exists rename old one before creating the file
    if LOG_FILE.is_file():
        count = 0
        while True:
            new_file_name = f"log.txt.{count}"
            new_file_path = Path(LOG_DIR, new_file_name)
            if new_file_path.is_file():
                count += 1
            else:
                LOG_FILE.rename(new_file_path)
                break
    LOG_FILE.touch()

    FILE_HANDLER = logging.FileHandler(str(LOG_FILE))
    if SCRIPT_ARGS.vvv:  # Enable super verbose output
        FILE_HANDLER.setLevel(logging.NOTSET)
    else:
        FILE_HANDLER.setLevel(logging.DEBUG)
    FILE_HANDLER.setFormatter(FORMATTER)
    LOGGER.addHandler(FILE_HANDLER)

STREAM_HANDLER = logging.StreamHandler()
if SCRIPT_ARGS.vv:  # Enable debug mode
    STREAM_HANDLER.setLevel(logging.DEBUG)
elif SCRIPT_ARGS.v:  # Enable console log output
    STREAM_HANDLER.setLevel(logging.INFO)
elif SCRIPT_ARGS.vvv:  # Enable super verbose output
    STREAM_HANDLER.setLevel(logging.NOTSET)
else:
    STREAM_HANDLER.setLevel(logging.ERROR)

STREAM_HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(STREAM_HANDLER)

if SCRIPT_ARGS.keep_alive and SCRIPT_ARGS.no_write:  # These two options are not compatible and keep_alive will not run
    LOGGER.warning("keep alive will not be performed since MEGAabuse is not reading or writing any files")

# Found solution for mac os not implemented error here: https://github.com/keras-team/autokeras/issues/368


class SharedCounter:
    """" A synchronized shared counter.

    The locking done by multiprocessing.Value ensures that only a single
    process or thread may read or write the in-memory ctypes object. However,
    in order to do n += 1, Python performs a read followed by a write, so a
    second process may read the old value before the new one is written by the
    first process. The solution is to use a multiprocessing.Lock to guarantee
    the atomicity of the modifications to Value.

    This class comes almost entirely from Eli Bendersky's blog:
    http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/

    """

    def __init__(self, val=0):
        self.count = multiprocessing.Value('i', val)

    def increment(self, incr=1):
        """" Increment the counter by n (default = 1) """
        with self.count.get_lock():
            self.count.value += incr

    @property
    def value(self):
        """" Return the value of the counter """
        return self.count.value


class Queue(multiprocessing.queues.Queue):
    """" A portable implementation of multiprocessing.Queue.

    Because of multithreading / multiprocessing semantics, Queue.qsize() may
    raise the NotImplementedError exception on Unix platforms like Mac OS X
    where sem_getvalue() is not implemented. This subclass addresses this
    problem by using a synchronized shared counter (initialized to zero) and
    increasing / decreasing its value every time the put() and get() methods
    are called, respectively. This not only prevents NotImplementedError from
    being raised, but also allows us to implement a reliable version of both
    qsize() and empty().

    """

    def __init__(self, *args, **kwargs):
        super(Queue, self).__init__(*args, **kwargs, ctx=multiprocessing.get_context())
        self.size = SharedCounter(0)

    def put(self, obj, block=True, timeout=None):
        self.size.increment(1)
        super(Queue, self).put(obj, block, timeout)

    def get(self, block=True, timeout=None):
        self.size.increment(-1)
        return super(Queue, self).get(block, timeout)

    def qsize(self):
        """" Reliable implementation of multiprocessing.Queue.qsize() """
        return self.size.value

    def empty(self):
        """" Reliable implementation of multiprocessing.Queue.empty() """
        return not self.qsize()


class AccountFactory:
    """" Creates mega.nz accounts using guerrillamail """

    total_accounts_created = 0  # Total accounts created

    def __init__(self, tools_path):
        self.megareg_dir = f"{tools_path} reg"

    @staticmethod
    def random_text(length):
        """" Returns a random string with specified length """
        return ''.join(
            [choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for i in range(length)])

    @staticmethod
    def random_mail():
        """" Returns a 30 character string """
        return ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789') for i in range(30)])

    @staticmethod
    def guerrilla_wait_for_mail():
        """" Wait for welcome mail """
        wait_time = 0
        while True:
            if wait_time > 120:
                LOGGER.info("Waiting for mail time exceeded 2 minutes. Aborting")
                return False
            mail_str = str(guerrillamail.cli("list"))
            if "welcome@mega.nz" in mail_str:
                return mail_str
            wait_time += 2
            time.sleep(2)

    @staticmethod
    def extract_url(mail_str):
        """" Extracts url from mail """
        soup = BeautifulSoup(mail_str, "html.parser")
        for link in soup.findAll("a"):
            if link.get("href") is not None and "#confirm" in link.get("href"):
                return link.get("href").replace('3D"', "").replace('"', "")
        return None

    def guerrilla_gen_bulk(self, accounts_number, fixed_pass, proxy):
        """" Creates mega.nz accounts using guerrilla mail """
        start = time.time()
        LOGGER.info("Starting a new bulk")
        email_code_pairs = {}
        email_pass_pairs = {}
        confirm_commands = []
        name = get_first_name()
        needed = accounts_number

        # Register a bulk of size "needed"
        LOGGER.info("Registering accounts")
        while needed > 0:
            email_text = self.random_mail()
            # guerrillamail.cli("setaddr",email_text)
            email = email_text + "@guerrillamailblock.com"
            if fixed_pass:
                email_password = fixed_pass
            else:
                email_password = self.random_text(21)
            cmd = f"{self.megareg_dir} -n {name} -e {email} -p {email_password} --register --scripted"
            if proxy:
                cmd += f" --proxy={proxy}"
            LOGGER.log(0, cmd)
            confirm_text = subprocess.check_output(cmd, shell=True).decode('UTF-8')
            confirm_text = confirm_text[confirm_text.find("-"):]
            email_code_pairs[email] = confirm_text
            email_pass_pairs[email] = email_password
            needed -= 1
        LOGGER.info("Done registering")

        # Wait for mail and read it
        for address in email_pass_pairs:
            address = address[0:30]
            guerrillamail.cli("setaddr", address)
            mail_id = self.guerrilla_wait_for_mail()[6:15]
            mail_str = str(guerrillamail.cli("get", mail_id))
            current_link = self.extract_url(mail_str)
            current_email = address + "@guerrillamailblock.com"
            current_command = email_code_pairs[current_email].replace(
                "@LINK@", current_link)
            confirm_commands.append("{} {}".format(self.megareg_dir, current_command.replace("megareg.exe", "")))

        # Confirm accounts
        LOGGER.info("Confirming accounts")
        for command in confirm_commands:
            subprocess.check_output(command, shell=True)

        self.total_accounts_created += accounts_number
        LOGGER.info(
            "Bulk done. Generated %s accounts in %ss. Currently: %s",
            accounts_number,
            round(time.time() - start, 1),
            self.total_accounts_created
        )
        return email_pass_pairs


# Get the right megatools for your system
BIN_PATH = Path(SCRIPT_DIR, "binaries")
if sys.platform == "win32":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_win", "megatools.exe")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_windows")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "MEGAcmdServer.exe")

elif sys.platform == "darwin":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_mac", "megatools")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_mac")

elif sys.platform == "linux":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_linux", "megatools")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_linux")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "mega-cmd-server")
else:
    print("OS not supported")
    sys.exit(1)

if not MEGATOOLS_PATH.is_file():
    raise FileNotFoundError("No megatools found!")

# Start MEGA cmd server
if sys.platform == "linux" or sys.platform == "win32":
    if not CMD_SERVER_PATH.is_file():
        raise FileNotFoundError("No megacmd found!")

    CMD_SERVER_PROC = subprocess.Popen(
        str(CMD_SERVER_PATH),
        shell=True,
        stdout=subprocess.PIPE,
        cwd=MEGACMD_PATH
    )

    def exit_handler():
        """"Stop MEGA cmd server when program exits"""
        logging.debug("Killing MEGA cmd server")
        if CMD_SERVER_PROC:
            CMD_SERVER_PROC.terminate()
    atexit.register(exit_handler)

# Create accounts.txt
if not SCRIPT_ARGS.no_write:
    account_file = Path(SCRIPT_DIR, "accounts.txt")
    if not account_file.is_file():
        account_file.touch()

# Lock used for locking the pool when creating an account at the moment accounts can nut be created simultaneously
ACC_LOCK = multiprocessing.Lock()
ACC_FACTORY = AccountFactory(MEGATOOLS_PATH)


# todo: Support multiprocessing. confirm_command or something when you do two at once
def get_account(amount, proxy=False):
    """"" Wrapper for guerrilla_gen_bulk """
    with ACC_LOCK:
        accounts = ACC_FACTORY.guerrilla_gen_bulk(amount, False, proxy)
    # Write credentials to file
    if not SCRIPT_ARGS.no_write:
        with open(account_file, "a") as file:
            for user, password in accounts.items():
                file.write(f"{user};{password}" + linesep)
    return accounts


def update_json_file(file, data):
    """" Updates a json file with new data """
    with open(file, "w") as json_file:
        json.dump(data, json_file, indent=4)


def logout():
    """" Logs out of megacmd """
    LOGGER.log(0, "Logout function called")

    cmd_path = Path(MEGACMD_PATH, "mega-logout")
    cmd = str(cmd_path)
    LOGGER.log(0, cmd)

    subprocess.Popen(cmd, shell=True, cwd=MEGACMD_PATH).wait()


def login(username, password):
    """" Logs in to megacmd """
    LOGGER.log(0, "Login function called")

    cmd_path = Path(MEGACMD_PATH, "mega-login")
    cmd = f"{cmd_path} \"{username}\" \"{password}\""
    LOGGER.log(0, cmd)

    subprocess.Popen(cmd, shell=True, cwd=MEGACMD_PATH).wait()


# Regex for extracting export url from export command output
URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
EXPORT_LOCK = multiprocessing.Lock()  # Used for locking the pool while exporting.


def export_folder(username, password, folder_name):
    """" Exports a folder """
    LOGGER.log(0, "Export function called")

    with EXPORT_LOCK:
        logout()
        login(username, password)

        cmd_path = Path(MEGACMD_PATH, "mega-export")
        cmd = f"{cmd_path} -a {folder_name}"
        LOGGER.log(0, cmd)

        output = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=MEGACMD_PATH
        ).communicate(b"yes")  # Set to 'no' if you are a pirate

    std_out_text = output[0].decode("utf-8")

    # Return url
    url = URL_REGEX.findall(std_out_text)[0]
    LOGGER.info("Exported: %s", url)
    return url


def create_folder(user_name, password, folder_name, proxy=False):
    """" Create a folder om a mega account """
    LOGGER.log(0, "Create folder function called")

    cmd = f"{MEGATOOLS_PATH} mkdir {folder_name} -u {user_name} -p {password}"
    if proxy:
        cmd += f" --proxy={proxy}"
    LOGGER.log(0, cmd)

    subprocess.Popen(cmd, shell=True).wait()


def upload_file(username, password, remote_path, file_path, proxy=False):
    """" Uploads a file to mega """
    LOGGER.log(0, "Upload file function called")

    cmd = f"{MEGATOOLS_PATH} put -u {username} -p {password} --path {remote_path} {file_path}"
    if proxy:
        cmd += f" --proxy={proxy}"
    LOGGER.log(0, cmd)

    return bool(subprocess.Popen(cmd, shell=True).wait() == 0)


# Create resume dir
if not SCRIPT_ARGS.no_write:
    resume_dir = Path(SCRIPT_DIR, "resume")
    if not resume_dir.is_dir():
        resume_dir.mkdir()


def upload_chunks(chunks, dir_name, proxy):  # Proxy can be str or False
    """" Uploads the chunks to mega.nz """
    LOGGER.log(0, "Upload chunks function called")

    resume_data = []
    if not SCRIPT_ARGS.no_write:
        # Create resume file
        resume_file = Path(resume_dir, f"{dir_name}.json")
        if not resume_file.is_file() and not SCRIPT_ARGS.no_write:
            resume_file.touch()

        # Try to load data from resume file if fails create empty resume data var
        with open(resume_file, "r+") as json_file:
            try:
                resume_data = json.load(json_file)
            except json.decoder.JSONDecodeError:
                pass

    # The chunk we are working with
    c_counter = 0
    export_urls = []
    for chunk in chunks:
        # If chunk is not in resume data create it and try again
        while True:
            try:
                r_data = resume_data[c_counter]
                LOGGER.debug("Found chunk in resume data %s", r_data)
                break
            except IndexError:
                chunk_resume = {
                    "credentials": get_account(1, proxy),
                    "folder name": chunk["folder name"],
                    "uploaded files": []
                }
                resume_data.append(chunk_resume)

        credentials = resume_data[c_counter]["credentials"]
        user_name = list(credentials.keys())[0]
        password = credentials[user_name]

        folder_name = resume_data[c_counter]["folder name"]
        uploaded_files = resume_data[c_counter]["uploaded files"]

        # Create folder
        create_folder(user_name, password, f"/Root/{folder_name}", proxy)

        for file in chunk["files"]:
            if file not in uploaded_files:
                LOGGER.info("Uploading: %s", file)

                file_path = Path(file)
                extension = file.split(".")[-1]
                file_name = f"{file_path.stem}.{extension}"

                # Returns True on a successful upload
                if upload_file(user_name, password, f"/Root/{folder_name}/{file_name}", file, proxy):

                    # Update resume data
                    uploaded_files.append(file)
                    if not SCRIPT_ARGS.no_write:
                        update_json_file(resume_file, resume_data)
                else:
                    LOGGER.error("Error uploading: %s", file)
            else:
                LOGGER.info("Skipping: %s", file)

        # Folder path is with / instead of /Root because the export folder function
        # uses megacmd instead of megatools.
        export_url = export_folder(user_name, password, f"/{folder_name}")
        export_urls.append(export_url)

        # Write export url to resume file
        resume_data[c_counter].update({"export url": export_url})
        if not SCRIPT_ARGS.no_write:
            update_json_file(resume_file, resume_data)

        c_counter += 1
    return export_urls


def find_files(search_path, wrong_extensions: list):
    """" Outputs a dict of all file paths and their sizes """
    file_paths = {}
    for root, _, files in walk(search_path):
        files.sort()
        for file in files:
            extension = path.splitext(file)[1]
            if extension not in wrong_extensions:
                file_path = path.join(root, file)
                file_paths.update({file_path: path.getsize(file_path)})
    return file_paths


def divide_files(paths: dict, max_size):  # Max size is in bits
    """" Input is {path: size in bytes dict}.
         divides files in lists of no more than 50GB """
    file_chunks = []
    file_list = []
    chunk_size = 0
    for file_path, size in paths.items():
        if chunk_size + size > max_size:
            file_chunks.append(file_list)
            file_list = []
            chunk_size = 0
        chunk_size += size
        file_list.append(file_path)
    if file_list:
        file_chunks.append(file_list)
    return file_chunks


# Read done file
done = []
if not SCRIPT_ARGS.no_write:
    DONE_FILE = Path(SCRIPT_DIR, "done.txt")
    if not DONE_FILE.is_file():
        DONE_FILE.touch()
    else:
        with open(DONE_FILE) as f:
            done = [line.rstrip() for line in f]

# Counter for all the files being processed. Used for logging purposes.
total_files_count = multiprocessing.Value("i", 0)


def upload_folder(folder_path, proxy=False):
    """" Uploads a folder to mega.nz returns download urls """
    LOGGER.log(0, "Upload folder function called")

    if folder_path in done and not SCRIPT_ARGS.no_write:
        LOGGER.info("Skipping: %s", folder_path)
        return []
    LOGGER.info("Uploading %s", folder_path)

    paths = find_files(folder_path, [".json", ])
    LOGGER.info("%s: Found %s files", folder_path, len(paths))
    total_files_count.value += len(paths)
    file_lists = divide_files(paths, 15000000000)
    folder_name = Path(folder_path).parts[-1]

    chunks = []
    # A chunk is a set of files that fits in a mega account (50GB)
    for file_list in file_lists:
        chunks.append({
            "folder name": folder_name,
            "files": file_list
        })

    LOGGER.info("Uploading: %s chunks", len(chunks))
    export_urls = upload_chunks(chunks, folder_name, proxy)

    done.append(folder_path)
    if not SCRIPT_ARGS.no_write:
        with open(DONE_FILE, "a") as file:
            file.write(folder_path + linesep)

    return export_urls


# PROXY_STORE = multiprocessing.Queue()  # Available proxies
PROXY_STORE = Queue()  # Available proxies

if SCRIPT_ARGS.proxy:
    # If --proxy is passed load proxies from proxy file
    PROXY_FILE_PATH = Path(SCRIPT_DIR, "proxies.txt")
    if not PROXY_FILE_PATH.is_file():
        PROXY_FILE_PATH.touch()

    with open(PROXY_FILE_PATH) as proxy_file:
        for proxy_line in proxy_file:
            prox = proxy_line.strip("\n")
            LOGGER.debug("Loaded: %s", prox)
            PROXY_STORE.put(prox)
    LOGGER.info("%s proxies loaded", PROXY_STORE.qsize())

    # 1 thread for each proxy
    THREADS = PROXY_STORE.qsize()
else:
    # No proxies. Use 1 thread
    THREADS = 1

# Counter of all the active workers. Used for logging purposes.
worker_count = multiprocessing.Value("i", 0)


def worker(folder_path):
    """" This is actually just a wrapper around
         upload_folder to handle the proxies """
    worker_count.value += 1  # Add to active worker counter. Used for logging purposes.
    LOGGER.debug("Worker spawned. Total workers: %s", worker_count.value)

    proxy = False
    if SCRIPT_ARGS.proxy:
        # Get proxy
        proxy = PROXY_STORE.get()
        LOGGER.debug("Using proxy: %s", proxy)
        LOGGER.debug("Proxies in store: %s", PROXY_STORE.qsize())

    exported_urls = upload_folder(folder_path, proxy)
    LOGGER.info("Done uploading: %s", folder_path)

    if SCRIPT_ARGS.proxy:
        # Return proxy
        PROXY_STORE.put(proxy)
        LOGGER.debug("Returning proxy: %s", proxy)
        LOGGER.debug("Proxies in store: %s", PROXY_STORE.qsize())

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

    LOGGER.info("Processed %s files", total_files_count.value)

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


UPLOAD_QUEUE = []  # To be downloaded

# Upload sub dirs
if SCRIPT_ARGS.upload_subdirs:
    LOGGER.debug("Uploading sub-directories")

    for folder in SCRIPT_ARGS.upload_subdirs:
        d_path = Path(folder)

        for sub_folder in listdir(d_path):  # Append target folders to upload list
            UPLOAD_QUEUE.append(Path(d_path, sub_folder))

# Upload multiple dirs
elif SCRIPT_ARGS.upload_dirs:
    LOGGER.debug("Uploading multiple directories")

    for folder in SCRIPT_ARGS.upload_dirs:  # Append target folders to upload list
        UPLOAD_QUEUE.append(folder)

if SCRIPT_ARGS.upload_dirs or SCRIPT_ARGS.upload_subdirs:
    upload_manager(UPLOAD_QUEUE)  # Start Upload process

# Keeps accounts active
if SCRIPT_ARGS.keep_alive and not SCRIPT_ARGS.no_write:  # Does not run if --no-write has been passed
    LOGGER.debug("Keeping accounts alive")

    with open(account_file) as account_f:
        # Read accounts from file
        for file_line in account_f:
            line = file_line.strip("\n")
            usern, passwd = line.split(";")

            # Log in and log out using megacmd
            LOGGER.info("Logging into: %s %s", usern, passwd)
            logout()
            login(usern, passwd)
            logout()

LOGGER.info("Done")

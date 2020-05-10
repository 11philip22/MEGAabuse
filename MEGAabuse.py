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

import argparse
import atexit
import json
import logging
import multiprocessing
import re
import subprocess
import time
from os import linesep, listdir, path, walk
from pathlib import Path
from random import choice
import sys

from bs4 import BeautifulSoup
from names import get_first_name

import guerrillamail

if getattr(sys, 'frozen', False):
    script_dir = path.dirname(path.realpath(sys.executable))
else:
    script_dir = path.dirname(path.realpath(__file__))

# Parse arguments
parser = argparse.ArgumentParser(description="MEGAabuse")

parser.add_argument(
    "-s", "--upload-subdirs",
    required=False,
    type=str,
    nargs='+',
    metavar="<dir>",
    help="Uploads all sub-folders of specified folder"
)
parser.add_argument(
    "-d", "--upload-dirs",
    required=False,
    type=str,
    nargs='+',
    metavar="<dir>",
    help="Upload one or multiple folders"
)
parser.add_argument(
    "-k", "--keep-alive",
    required=False,
    action="store_true",
    help="Reads from accounts.txt and keeps the accounts active"
)
parser.add_argument(
    "-c", "--check-urls",
    required=False,
    action="store_true",
    help="Checks if urls are still up"
)
parser.add_argument(
    "-v",
    required=False,
    action="store_true",
    help="Output logs"
)
parser.add_argument(
    "-vv",
    required=False,
    action="store_true",
    help="Output debug logs"
)
parser.add_argument(
    "-vvv",
    required=False,
    action="store_true",
    help="Output super debug logs"
)
parser.add_argument(
    "-n", "--no-write",
    required=False,
    action="store_true",
    help="Dont read or write any file"
)
parser.add_argument(
    "-p", "--proxy",
    required=False,
    action="store_true",
    help="Use socks5 proxies defined in proxy.txt"
)

script_args = parser.parse_args()
# Exit if help argument has been passed.
# To prevent writing empty log files
try:
    if script_args.h:
        sys.exit(0)
except AttributeError:
    # -h or --help has not been passed continue
    pass

# Create logger
logger = logging.getLogger('MEGAabuse')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if not script_args.no_write:  # Dont bother with log files if --no-write is passed
    # Create logs folder
    log_dir = Path(script_dir, "logs")
    if not log_dir.is_dir():
        log_dir.mkdir()

    # Create log file
    log_file = Path(log_dir, "log.txt")
    # If log file exists rename old one before creating the file
    if log_file.is_file():
        count = 0
        while True:
            new_file_name = f"log.txt.{count}"
            new_file_path = Path(log_dir, new_file_name)
            if new_file_path.is_file():
                count += 1
            else:
                log_file.rename(new_file_path)
                break
    log_file.touch()

    fh = logging.FileHandler(str(log_file))
    if script_args.vvv:  # Enable super verbose output
        fh.setLevel(logging.NOTSET)
    else:
        fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

ch = logging.StreamHandler()
if script_args.vv:  # Enable debug mode
    ch.setLevel(logging.DEBUG)
elif script_args.v:  # Enable console log output
    ch.setLevel(logging.INFO)
elif script_args.vvv:  # Enable super verbose output
    ch.setLevel(logging.NOTSET)
else:
    ch.setLevel(logging.ERROR)

ch.setFormatter(formatter)
logger.addHandler(ch)

if script_args.keep_alive and script_args.no_write:  # These two options are not compatible and keep_alive will not run
    logger.warning("keep alive will not be performed since MEGAabuse is not reading or writing any files")

# #################################### Begin mac os workaround #########################################################
# Found selution for macos not implemented error here: https://github.com/keras-team/autokeras/issues/368


# class SharedCounter:
#     """ A synchronized shared counter.
#
#     The locking done by multiprocessing.Value ensures that only a single
#     process or thread may read or write the in-memory ctypes object. However,
#     in order to do n += 1, Python performs a read followed by a write, so a
#     second process may read the old value before the new one is written by the
#     first process. The solution is to use a multiprocessing.Lock to guarantee
#     the atomicity of the modifications to Value.
#
#     This class comes almost entirely from Eli Bendersky's blog:
#     http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing/
#
#     """
#
#     def __init__(self, val=0):
#         self.count = multiprocessing.Value('i', val)
#
#     def increment(self, incr=1):
#         """ Increment the counter by n (default = 1) """
#         with self.count.get_lock():
#             self.count.value += incr
#
#     @property
#     def value(self):
#         """ Return the value of the counter """
#         return self.count.value
#
#
# class Queue(multiprocessing.Queue):
#     """ A portable implementation of multiprocessing.Queue.
#
#     Because of multithreading / multiprocessing semantics, Queue.qsize() may
#     raise the NotImplementedError exception on Unix platforms like Mac OS X
#     where sem_getvalue() is not implemented. This subclass addresses this
#     problem by using a synchronized shared counter (initialized to zero) and
#     increasing / decreasing its value every time the put() and get() methods
#     are called, respectively. This not only prevents NotImplementedError from
#     being raised, but also allows us to implement a reliable version of both
#     qsize() and empty().
#
#     """
#
#     def __init__(self, *args, **kwargs):
#         super(Queue, self).__init__(*args, **kwargs)
#         self.size = SharedCounter(0)
#
#     def put(self, *args, **kwargs):
#         self.size.increment(1)
#         super(Queue, self).put(*args, **kwargs)
#
#     def get(self, *args, **kwargs):
#         self.size.increment(-1)
#         return super(Queue, self).get(*args, **kwargs)
#
#     def qsize(self):
#         """ Reliable implementation of multiprocessing.Queue.qsize() """
#         return self.size.value
#
#     def empty(self):
#         """ Reliable implementation of multiprocessing.Queue.empty() """
#         return not self.qsize()


# #################################### End mac os workaround ###########################################################
# #################################### Begin account creator ###########################################################
ac = 0  # Total accounts created


def random_text(length):
    """"Returns a random string with specified length"""
    return ''.join([choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for i in range(length)])


def random_mail():
    """"Returns a 30 character string"""
    return ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789') for i in range(30)])


def guerrilla_wait_for_mail():
    """"Wait for welcome mail"""
    wait_time = 0
    while True:
        if wait_time > 120:
            logger.info("Waiting for mail time exceeded 2 minutes. Aborting")
            return False
        mail_str = str(guerrillamail.cli("list"))
        if "welcome@mega.nz" in mail_str:
            return mail_str
        time.sleep(2)


def extract_url(mail_str):
    """"Extracts url from mail"""
    soup = BeautifulSoup(mail_str, "html.parser")
    for link in soup.findAll("a"):
        if link.get("href") is not None and "#confirm" in link.get("href"):
            return link.get("href").replace('3D"', "").replace('"', "")


def guerrilla_gen_bulk(accounts_number, fixed_pass, megareg_dir, proxy):
    """"Creates mega.nz accounts using guerrilla mail"""
    start = time.time()
    logger.info("Starting a new bulk")
    email_code_pairs = {}
    email_pass_pairs = {}
    confirm_commands = []
    name = get_first_name()
    n = accounts_number
    global ac

    # Register a bulk of size n
    logger.info("Registering accounts")
    while n > 0:
        email_text = random_mail()
        # guerrillamail.cli("setaddr",email_text)
        email = email_text + "@guerrillamailblock.com"
        if fixed_pass:
            email_password = fixed_pass
        else:
            email_password = random_text(21)
        cmd = f"{megareg_dir} -n {name} -e {email} -p {email_password} --register --scripted"
        if proxy:
            cmd += f" --proxy={proxy}"
        logger.log(0, cmd)
        confirm_text = subprocess.check_output(cmd, shell=True).decode('UTF-8')
        confirm_text = confirm_text[confirm_text.find("-"):]
        email_code_pairs[email] = confirm_text
        email_pass_pairs[email] = email_password
        n -= 1
    logger.info("Done registering")

    # Wait for mail and read it
    for address in email_pass_pairs:
        address = address[0:30]
        guerrillamail.cli("setaddr", address)
        mail_id = guerrilla_wait_for_mail()[6:15]
        mail_str = str(guerrillamail.cli("get", mail_id))
        current_link = extract_url(mail_str)
        current_email = address + "@guerrillamailblock.com"
        current_command = email_code_pairs[current_email].replace(
            "@LINK@", current_link)
        confirm_commands.append("{} {}".format(megareg_dir, current_command.replace("megareg.exe", "")))

    # Confirm accounts
    logger.info("Confirming accounts")
    for command in confirm_commands:
        subprocess.check_output(command, shell=True)

    ac += accounts_number
    logger.info(
        "Bulk done. Generated %s accounts in %ss. Currently: %s", accounts_number, round(time.time() - start, 1), ac)
    return email_pass_pairs


# #################################### End account creator #############################################################
# #################################### MEGAabuse!!! ####################################################################

# Get the right megatools for your system
bin_path = Path(script_dir, "binaries")
if sys.platform == "win32":
    megatools_path = Path(bin_path, "megatools_win", "megatools.exe")
    megacmd_path = Path(bin_path, "megacmd_windows")
    cmd_server_path = Path(megacmd_path, "MEGAcmdServer.exe")

elif sys.platform == "darwin":
    megatools_path = Path(bin_path, "megatools_mac", "megatools")
    megacmd_path = Path(bin_path, "megacmd_mac")

elif sys.platform == "linux":
    megatools_path = Path(bin_path, "megatools_linux", "megatools")
    megacmd_path = Path(bin_path, "megacmd_linux")
    cmd_server_path = Path(megacmd_path, "mega-cmd-server")
else:
    print("OS not supported")
    sys.exit(1)

if not megatools_path.is_file():
    raise FileNotFoundError("No megatools found!")

# Start MEGA cmd server
if sys.platform == "linux" or sys.platform == "win32":
    if not cmd_server_path.is_file():
        raise FileNotFoundError("No megacmd found!")

    mcmd_p = subprocess.Popen(
        str(cmd_server_path),
        shell=True,
        stdout=subprocess.PIPE,
        cwd=megacmd_path
    )

    # Stop MEGA cmd server when program exits
    def exit_handler():
        logging.debug("Killing MEGA cmd server")
        if mcmd_p:
            mcmd_p.terminate()
    atexit.register(exit_handler)

# Create accounts.txt
if not script_args.no_write:
    account_file = Path(script_dir, "accounts.txt")
    if not account_file.is_file():
        account_file.touch()

# Lock used for locking the pool when creating an account at the moment accounts can nut be created simultaneously
a_lock = multiprocessing.Lock()


# todo: Support multiprocessing. confirm_command or something when you do two at once
def get_account(amount, proxy=False):
    """""Wrapper for guerrilla_gen_bulk"""
    with a_lock:
        accounts = guerrilla_gen_bulk(amount, False, f"{megatools_path} reg", proxy)
    # Write credentials to file
    if not script_args.no_write:
        with open(account_file, "a") as file:
            for user, password in accounts.items():
                file.write(f"{user};{password}" + linesep)
    return accounts


def update_json_file(file, data):
    """"Updates a json file with new data"""
    with open(file, "w") as json_file:
        json.dump(data, json_file, indent=4)


def logout():
    """"Logs out of megacmd"""
    logger.log(0, "Logout function called")

    cmd_path = Path(megacmd_path, "mega-logout")
    cmd = str(cmd_path)
    logger.log(0, cmd)

    subprocess.Popen(cmd, shell=True, cwd=megacmd_path).wait()


def login(username, password):
    """"Logs in to megacmd"""
    logger.log(0, "Login function called")

    cmd_path = Path(megacmd_path, "mega-login")
    cmd = f"{cmd_path} \"{username}\" \"{password}\""
    logger.log(0, cmd)

    subprocess.Popen(cmd, shell=True, cwd=megacmd_path).wait()


# Regex for extracting export url from export command output
url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


def export_folder(username, password, folder_name):
    """"Exports a folder"""
    logger.log(0, "Export function called")

    logout()
    login(username, password)

    cmd_path = Path(megacmd_path, "mega-export")
    cmd = f"{cmd_path} -a {folder_name}"
    logger.log(0, cmd)

    output = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=megacmd_path
    ).communicate(b"yes")  # Set to 'no' if you are a pirate

    std_out_text = output[0].decode("utf-8")

    # Return url
    url = url_regex.findall(std_out_text)[0]
    logger.info("Exported: %s", url)
    return url


def create_folder(user_name, password, folder_name, proxy=False):
    """"Create a folder om a mega account"""
    logger.log(0, "Create folder function called")

    cmd = f"{megatools_path} mkdir {folder_name} -u {user_name} -p {password}"
    if proxy:
        cmd += f" --proxy={proxy}"
    logger.log(0, cmd)

    subprocess.Popen(cmd, shell=True).wait()


def upload_file(username, password, remote_path, file_path, proxy=False):
    """"Uploads a file to mega"""
    logger.log(0, "Upload file function called")

    cmd = f"{megatools_path} put -u {username} -p {password} --path {remote_path} {file_path}"
    if proxy:
        cmd += f" --proxy={proxy}"
    logger.log(0, cmd)

    return bool(subprocess.Popen(cmd, shell=True).wait() == 0)


# Create resume dir
if not script_args.no_write:
    resume_dir = Path(script_dir, "resume")
    if not resume_dir.is_dir():
        resume_dir.mkdir()


def upload_chunks(chunks, dir_name, proxy):  # Proxy can be str or False
    """"Uploads the chunks to mega.nz"""
    logger.log(0, "Upload chunks function called")

    resume_data = []
    if not script_args.no_write:
        # Create resume file
        resume_file = Path(resume_dir, f"{dir_name}.json")
        if not resume_file.is_file() and not script_args.no_write:
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
                a = resume_data[c_counter]
                logger.debug("Found chunk in resume data %s", a)
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
                logger.info("Uploading: %s", file)

                file_path = Path(file)
                extension = file.split(".")[-1]
                file_name = f"{file_path.stem}.{extension}"

                # Returns True on a successful upload
                if upload_file(user_name, password, f"/Root/{folder_name}/{file_name}", file, proxy):

                    # Update resume data
                    uploaded_files.append(file)
                    if not script_args.no_write:
                        update_json_file(resume_file, resume_data)
                else:
                    logger.error("Error uploading: %s", file)
            else:
                logger.info("Skipping: %s", file)

        # Folder path is with / instead of /Root because the export folder function
        # uses megacmd instead of megatools.
        export_url = export_folder(user_name, password, f"/{folder_name}")
        export_urls.append(export_url)

        # Write export url to resume file
        resume_data[c_counter].update({"export url": export_url})
        if not script_args.no_write:
            update_json_file(resume_file, resume_data)

        c_counter += 1
    return export_urls


def find_files(search_path, wrong_extensions: list):
    """"Outputs a dict of all file paths and their sizes"""
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
    """"Input is {path: size in bytes dict}.
        divides files in lists of no more than 50GB"""
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
if not script_args.no_write:
    done_file = Path(script_dir, "done.txt")
    if not done_file.is_file():
        done_file.touch()
    else:
        with open(done_file) as f:
            done = [line.rstrip() for line in f]

# Counter for all the files being processed. Used for logging purposes.
total_files_count = multiprocessing.Value("i", 0)


def upload_folder(folder_path, proxy=False):
    """"Uploads a folder to mega.nz returns download urls"""
    logger.log(0, "Upload folder function called")

    if folder_path in done and not script_args.no_write:
        logger.info("Skipping: %s", folder_path)
        return []
    logger.info("Uploading %s", folder_path)

    paths = find_files(folder_path, [".json", ])
    logger.info("%s: Found %s files", folder_path, len(paths))
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

    logger.info("Uploading: %s chunks", len(chunks))
    export_urls = upload_chunks(chunks, folder_name, proxy)

    done.append(folder_path)
    if not script_args.no_write:
        with open(done_file, "a") as file:
            file.write(folder_path + linesep)

    return export_urls


proxies_store = multiprocessing.Queue()  # Available proxies

if script_args.proxy:
    # If --proxy is passed load proxies from proxy file
    proxy_file_path = Path(script_dir, "proxies.txt")
    if not proxy_file_path.is_file():
        proxy_file_path.touch()

    with open(proxy_file_path) as proxy_file:
        for proxy_line in proxy_file:
            prox = proxy_line.strip("\n")
            logger.debug("Loaded: %s", prox)
            proxies_store.put(prox)
    logger.info("%s proxies loaded", proxies_store.qsize())

# No proxies run on 1 thread
if proxies_store.qsize() == 0:
    THREADS = 1
else:
    # 1 thread for each proxy
    THREADS = proxies_store.qsize()

# Counter of all the active workers. Used for logging purposes.
worker_count = multiprocessing.Value("i", 0)


def worker(folder_path):
    """"This is actually just a wrapper around
        upload_folder to handle the proxies"""
    worker_count.value += 1  # Add to active worker counter. Used for logging purposes.
    logger.debug("Worker spawned. Total workers: %s", worker_count.value)

    proxy = False
    if script_args.proxy:
        # Get proxy
        proxy = proxies_store.get()
        logger.debug("Using proxy: %s", proxy)
        logger.debug("Proxies in store: %s", proxies_store.qsize())

    exported_urls = upload_folder(folder_path, proxy)
    logger.info("Done uploading: %s", folder_path)

    if script_args.proxy:
        # Return proxy
        proxies_store.put(proxy)
        logger.debug("Returning proxy: %s", proxy)
        logger.debug("Proxies in store: %s", proxies_store.qsize())

    worker_count.value -= 1  # Subtract to active worker counter. Used for logging purposes.
    logger.debug("Worker finished. Total workers: %s", worker_count.value)

    return {folder_path: exported_urls}


# Create output file
if not script_args.no_write:
    output_file = Path(script_dir, "out.txt")
    if not output_file.is_file():
        output_file.touch()


def urls_to_file(urls: list, folder_path):
    """"Write results to output file"""
    logger.log(0, "urls_to_file function called")

    logger.debug("Writing to file")

    with open(output_file, "a") as out_file:
        out_file.write(folder_path + linesep)
        for url in urls:
            logger.debug("Writing to results file: %s", url)
            out_file.write(url + linesep)
        out_file.write(linesep)


def upload_manager(queue):
    """"Starts upload process and processes results"""
    try:
        multiprocessing.freeze_support()  # todo: Does this do anything
        with multiprocessing.Pool(processes=THREADS) as pool:  # todo: Find fix for windows exe
            results = pool.map(worker, queue)  # Map pool to upload queue
    except RuntimeError as exc:
        tb = sys.exc_info()[2]
        logger.error(exc.with_traceback(tb))
        return

    all_export_urls = {}
    for res in results:
        all_export_urls.update(res)

    logger.info("Processed %s files", total_files_count.value)

    # Print results
    print()
    # Print folder path and export urls
    for e_file_path, res in all_export_urls.items():
        # Write to file
        if not script_args.no_write:
            urls_to_file(res, e_file_path)
        # Print folder path
        print(linesep + e_file_path)
        for e_url in res:
            # Print export url
            print(e_url)
    print()


upload_queue = []  # To be downloaded

# Upload sub dirs
if script_args.upload_subdirs:
    logger.debug("Uploading sub-directories")

    for folder in script_args.upload_subdirs:
        d_path = Path(folder)

        for sub_folder in listdir(d_path):  # Append target folders to upload list
            upload_queue.append(Path(d_path, sub_folder))

# Upload multiple dirs
elif script_args.upload_dirs:
    logger.debug("Uploading multiple directories")

    for folder in script_args.upload_dirs:  # Append target folders to upload list
        upload_queue.append(folder)

if script_args.upload_dirs or script_args.upload_subdirs:
    upload_manager(upload_queue)  # Start Upload process

# Keeps accounts active
if script_args.keep_alive and not script_args.no_write:  # Does not run if --no-write has been passed
    logger.debug("Keeping accounts alive")

    with open(account_file) as account_f:
        # Read accounts from file
        for file_line in account_f:
            line = file_line.strip("\n")
            usern, passwd = line.split(";")

            # Log in and log out using megacmd
            logger.info("Logging into: %s %s", usern, passwd)
            logout()
            login(usern, passwd)
            logout()

logger.info("Done")

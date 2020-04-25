#!/usr/bin/env python

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

# todo: Replace megacmd with mega python api

import argparse
import atexit
import json
import logging
import re
import subprocess
import time
from os import linesep, listdir, path, walk
from pathlib import Path
from random import choice
from sys import exit, platform

from bs4 import BeautifulSoup
from names import get_first_name

# sys_path.extend(['/home/myhome/devel/MEGA.nz/MEGAabuse', ])  # Uncomment for ipython ssh
import guerrillamail

script_dir = path.dirname(path.realpath(__file__))  # Comment for ipython
# script_dir = "V:\\MEGA.nz\\MEGAabuse"  # Uncomment for ipython
# script_dir = "/home/myhome/devel/MEGA.nz/MEGAabuse"  # Uncomment for ipython ssh

# Parse arguments
parser = argparse.ArgumentParser(description="MEGAabuse")

parser.add_argument(
    "-s", "--upload-subdirs",
    required=False,
    type=str,
    metavar="<dir>",
    help="Uploads all sub-folders of specified folder"
)
parser.add_argument(
    "-d", "--upload-dirs",
    required=False,
    type=str,
    nargs='+',
    metavar="<dir>",
    help="Uploads multiple folders"
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
    "-n", "--no-write",
    required=False,
    action="store_true",
    help="Dont write to any file except log file"
)

args = parser.parse_args()
# Exit if help argument has been passed.
# To prevent writing empty log files
try:
    if args.h:
        exit(0)
except AttributeError:
    # -h or --help has not been passed continue
    pass

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

# Create logger
logger = logging.getLogger('MEGAabuse')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(str(log_file))
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
if args.vv:
    # Enable debug mode
    ch.setLevel(logging.DEBUG)
elif args.v:
    # Enable console log output
    ch.setLevel(logging.INFO)
else:
    ch.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

# #################################### Begin account creator ###########################################################
c = 0  # Total accounts created


def random_text(length):
    return ''.join([choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for i in range(length)])


def random_mail():
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


def guerrilla_gen_bulk(accounts_number, fixed_pass, megareg_dir):
    """"Creates mega.nz accounts using guerrilla mail"""
    start = time.time()
    logger.info("Starting a new bulk")
    email_code_pairs = {}
    email_pass_pairs = {}
    confirm_commands = []
    name = get_first_name()
    n = accounts_number
    global c

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
        confirm_commands.append(
            megareg_dir + " " + current_command.replace("megareg.exe", ""))

    # Confirm accounts
    logger.info("Confirming accounts")
    for command in confirm_commands:
        subprocess.check_output(command, shell=True)

    c += accounts_number
    logger.info(
        f"Bulk done. Generated {accounts_number} accounts in {round(time.time() - start, 1)}s. Currently: {c}")
    return email_pass_pairs


# #################################### End account creator #############################################################
# #################################### MEGAabuse!!! ####################################################################

# Get the right megatools for your system
bin_path = Path(script_dir, "binaries")
if platform == "win32":
    megatools_path = Path(bin_path, "megatools_win", "megatools.exe")
    megacmd_path = Path(bin_path, "megacmd_windows")
    cmd_server_path = Path(megacmd_path, "MEGAcmdServer.exe")

elif platform == "darwin":
    megatools_path = Path(bin_path, "megatools_mac", "megatools")
    megacmd_path = Path(bin_path, "megacmd_mac")

elif platform == "linux":
    megatools_path = Path(bin_path, "megatools_linux", "megatools")
    megacmd_path = Path(bin_path, "megacmd_linux")
    cmd_server_path = Path(megacmd_path, "mega-cmd-server")
else:
    print("OS not supported")
    exit(1)

# Start MEGA cmd server
if platform == "linux" or platform == "win32":
    mcmd_p = subprocess.Popen(
        str(cmd_server_path),
        shell=True,
        stdout=subprocess.PIPE,
        cwd=megacmd_path
    )

    # Stop MEGA cmd server when program exits
    def exit_handler():
        if mcmd_p:
            mcmd_p.terminate()
    atexit.register(exit_handler)

# Create accounts.txt
account_file = Path(script_dir, "accounts.txt")
if not account_file.is_file():
    account_file.touch()


def get_account(amount):
    """""Wrapper for guerrilla_gen_bulk"""
    accounts = guerrilla_gen_bulk(amount, False, f"{megatools_path} reg")
    # Write credentials to file
    if not args.no_write:
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
    logger.debug("Logout function called")

    cmd_path = Path(megacmd_path, "mega-logout")
    cmd = str(cmd_path)
    logger.debug(cmd)

    subprocess.Popen(cmd, shell=True, cwd=megacmd_path).wait()


def login(username, password):
    """"Logs in to megacmd"""
    logger.debug("Login function called")

    cmd_path = Path(megacmd_path, "mega-login")
    cmd = f"{cmd_path} \"{username}\" \"{password}\""
    logger.debug(cmd)

    subprocess.Popen(cmd, shell=True, cwd=megacmd_path).wait()


url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


def export_folder(username, password, folder_name):
    """"Exports a folder"""
    logger.debug("Export function called")

    logout()
    login(username, password)

    cmd_path = Path(megacmd_path, "mega-export")
    cmd = f"{cmd_path} -a {folder_name}"
    logger.debug(cmd)

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
    logger.info(f"Exported: {url}")
    return url


def create_folder(user_name, password, folder_name):
    """"Create a folder om a mega account"""
    logger.debug("Create folder function called")

    cmd = f"{megatools_path} mkdir {folder_name} -u {user_name} -p {password}"
    logger.debug(cmd)

    subprocess.Popen(cmd, shell=True).wait()


def upload_file(username, password, remote_path, file_path):
    """"Uploads a file to mega"""
    logger.debug("Upload file function called")

    cmd = f"{megatools_path} put -u {username} -p {password} --path {remote_path} {file_path}"
    logger.debug(cmd)

    subprocess.Popen(cmd, shell=True).wait()


# Create resume dir
resume_dir = Path(script_dir, "resume")
if not resume_dir.is_dir():
    resume_dir.mkdir()


def upload_chunks(chunks, dir_name):
    """"Uploads the chunks to mega.nz"""
    logger.debug("Upload chunks function called")

    resume_file = Path(resume_dir, f"{dir_name}.json")
    if not resume_file.is_file():
        resume_file.touch()

    resume_data = []
    if not args.no_write:
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
                logger.debug(f"Found chunk in resume data {a}")
                break
            except IndexError:
                chunk_resume = {
                    "credentials": get_account(1),
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
        create_folder(user_name, password, f"/Root/{folder_name}")

        for file in chunk["files"]:
            if file not in uploaded_files:
                logger.info(f"Uploading: {file}")

                file_path = Path(file)
                extension = file.split(".")[-1]
                file_name = f"{file_path.stem}.{extension}"

                upload_file(user_name, password, f"/Root/{folder_name}/{file_name}", file)

                # Update resume data
                uploaded_files.append(file)
                if not args.no_write:
                    update_json_file(resume_file, resume_data)
            else:
                logger.info(f"Skipping: {file}")

        # Folder path is with / instead of /Root because the export folder function
        # uses megacmd instead of megatools.
        export_urls.append(export_folder(user_name, password, f"/{folder_name}"))

        c_counter += 1
    return export_urls


def find_files(search_path, wrong_extensions: list):
    """"Outputs a dict of all file paths and their sizes"""
    file_paths = {}
    for root, _, files in walk(search_path):
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
done_file = Path(script_dir, "done.txt")
if not done_file.is_file():
    done_file.touch()
else:
    with open(done_file) as f:
        done = [line.rstrip() for line in f]


def upload_folder(folder_path):
    """"Uploads a folder to mega.nz returns download urls"""
    logger.debug("Upload folder function called")

    if folder_path in done:
        logger.info(f"Skipping: {folder_path}")
        return
    else:
        logger.info(f"Uploading {folder_path}")

    paths = find_files(folder_path, [".json", ])
    file_lists = divide_files(paths, 15000000000)
    folder_name = Path(folder_path).parts[-1]

    chunks = []
    # A chunk is a set of files that fits in a mega account (50GB)
    for file_list in file_lists:
        chunks.append({
            "folder name": folder_name,
            "files": file_list
        })

    logger.info(f"Uploading: {len(chunks)} chunks")
    export_urls = upload_chunks(chunks, folder_name)

    done.append(folder_path)
    if not args.no_write:
        with open(done_file, "a") as file:
            file.write(folder_path + linesep)

    return export_urls


# Create output file
output_file = Path(script_dir, "out.txt")
if not output_file.is_file():
    output_file.touch()


def urls_to_file(urls: list, folder_path):
    """"Write results to output file"""
    logger.debug("urls_to_file function called")

    logger.debug("Writing to file")

    with open(output_file, "a") as out_file:
        out_file.write(folder_path + linesep)
        for url in urls:
            logger.debug(f"Writing to results file: {url}")
            out_file.write(url + linesep)
        out_file.write(linesep)


all_export_urls = {}


def run(folder_path):
    exported_urls = upload_folder(folder_path)
    logger.info(f"Done uploading: {folder_path}")

    if not args.no_write:
        urls_to_file(exported_urls, folder_path)
    all_export_urls.update({folder_path: exported_urls})


# Upload sub dirs
if args.upload_subdirs:
    logger.debug("Uploading sub-directories")

    d_path = Path(args.upload_subdirs)

    for sub_folder in listdir(d_path):
        run(Path(d_path, sub_folder))

# Upload multiple dirs
elif args.upload_dirs:
    logger.debug("Uploading multiple directories")

    for folder in args.upload_dirs:
        run(folder)

# Print results
if all_export_urls:
    print()
    # Print folder path and export urls
    for fp, r in all_export_urls.items():
        # Print folder path
        print(linesep + fp)
        for e in r:
            # Print export url
            print(e)
    print()

logger.info("Done")

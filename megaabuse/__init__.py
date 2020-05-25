"""" The megaabuse module

This file contains the main classes of the module.

"""

import atexit
import json
import logging
import multiprocessing
import re
import subprocess
import sys
from os import linesep, path, walk
from pathlib import Path

from .accountfactory import AccountFactory


def get_logger(name, *args, level=40, write=False):
    """" Creates a logger.

    If write is True a location must be passed as second argument.
    If ran with only the name argument returns a logger without a file handler
    and log level 40 (Warning).

    Parameters
    ----------
    name : str
        The name for the logger object.
    log_dir : str, optional
        The location of the logging folder. Will be created if does not exists.
    level : int, optional
        Sets logger level.
        0 : not set
        10 : debug
        20 : info
        40 : error
        anything else: critical
    write : bool, optional
        Write to file or not

    Returns
    -------
    logger object

    """

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    if write:  # Dont bother with log files if --no-write is passed
        # Create logs folder
        log_dir_path = Path(args[0])
        if not log_dir_path.is_dir():
            log_dir_path.mkdir()

        # Create log file
        log_file = Path(log_dir_path, "log.txt")
        # If log file exists rename old one before creating the file
        if log_file.is_file():
            count = 0
            while True:
                new_file_name = f"log.txt.{count}"
                new_file_path = Path(log_dir_path, new_file_name)
                if new_file_path.is_file():
                    count += 1
                else:
                    log_file.rename(new_file_path)
                    break
        log_file.touch()

        file_handler = logging.FileHandler(str(log_file))
        if level == "vvv":  # Enable super verbose output
            file_handler.setLevel(logging.NOTSET)
        else:
            file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    if level == 10:  # Enable debug mode
        stream_handler.setLevel(logging.DEBUG)
    elif level == 20:  # Enable console log output
        stream_handler.setLevel(logging.INFO)
    elif level == 0:  # Enable super verbose output
        stream_handler.setLevel(logging.NOTSET)
    elif level == 40:  # Enable error output
        stream_handler.setLevel(logging.ERROR)
    else:
        stream_handler.setLevel(logging.CRITICAL)

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


class CreateAccount(AccountFactory):
    """" A wrapper around AccountFactory

    Used for locking threads because AccountFactory is not threadsafe.
    used for writing accounts to file. (optional)

    Attributes
    ----------
    ACC_LOCK : multiprocessing.Lock()
        A lock used for locking the threadpool when generating accounts.

    Methods
    -------
    get(amount, proxy=False)
        Create mega.nz accounts using AccountFactory.guerrilla_gen_bulk

    """

    # Lock used for locking the pool when creating an account at the moment accounts can nut be created simultaneously
    ACC_LOCK = multiprocessing.Lock()

    def __init__(self, tools_path, *args, logger=None, write_files=False):
        """" Init function

        Parameters
        ----------
        tools_path : str or pathlib.Path
            Path to megatools
        accounts_file : str or pathlib.Path, optional
            Write generated accounts to this file
        logger : logger object, optional
            Use this logger
        write_files : bool, optional
            Write files or not

        """

        super().__init__(tools_path, logger)
        self.output = write_files

        # Create accounts.txt
        if self.output:
            self.account_file = Path(args[0])
            if not self.account_file.is_file():
                self.account_file.touch()

    # todo: Support multiprocessing. confirm_command or something when you do two at once
    def get(self, amount, proxy=False):
        """"" Wrapper for guerrilla_gen_bulk

        Parameters
        ----------
        amount : int
            Amount of accounts to generate
        proxy : str, optional
            Socks5 url

        """

        with self.ACC_LOCK:
            accounts = super().guerrilla_gen_bulk(amount, False, proxy)

        # Write credentials to file
        if self.output:
            with open(self.account_file, "a") as file:
                for user, password in accounts.items():
                    file.write(f"{user};{password}" + linesep)
        return accounts


class MegaCmd:
    """" A python wrapper around megacmd

    Attributes
    ----------
    URL_REGEX : re.Pattern
        Used for extracting mega export url from command output
    LOCK : multiprocessing.lock
        Used for locking the threadpool when exporting urls.
        Necessary since megacmd only allows one account to be logged in at a certain time.

    Methods
    ------
    logout()
        Log out of mega.nz
    login(username, password)
        Logs in to mega.nz
    export_folder(username, password, folder)
        Returns the export url of a folder

    """

    # Regex for extracting export url from export command output
    URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    LOCK = multiprocessing.Lock()  # Used for locking the pool while exporting.

    def __init__(self, m_cmd_path, *args, logger=None):
        """" Init function

        Parameters
        ----------
        m_cmd_path : str or pathlib.Path
            Path to mega cmd
        server_path : str or pathlib.Path, optional
            Path to mega cmd server
        logger : logger object, optional
            Use this logger

        """

        # Create logger or sub logger for class
        if logger is None:
            logger_name = "MegaExport"
        else:
            logger_name = f"{logger.name}.MegaExport"
        self.logger = logging.getLogger(logger_name)

        server_path = Path(args[0])
        self.cmd_path = Path(m_cmd_path)

        # Start MEGA cmd server
        if sys.platform == "linux" or sys.platform == "win32":
            if not server_path.is_file():
                raise FileNotFoundError("No megacmd found!")

            self.cmd_server_proc = subprocess.Popen(
                str(server_path),
                shell=True,
                stdout=subprocess.PIPE,
                cwd=self.cmd_path
            )

            atexit.register(self.exit_handler)

    def exit_handler(self):
        """"Stop MEGA cmd server when program exits"""
        logging.debug("Killing MEGA cmd server")
        if self.cmd_server_proc:
            self.cmd_server_proc.terminate()

    def logout(self):
        """" Logs out of megacmd """
        self.logger.log(0, "Logout function called")

        cmd_path = Path(self.cmd_path, "mega-logout")
        cmd = str(cmd_path)
        self.logger.log(0, cmd)

        proc = subprocess.Popen(cmd, shell=True, cwd=self.cmd_path)
        proc.wait()
        return proc.returncode

    def login(self, username, password):
        """" Logs in to megacmd """
        self.logger.log(0, "Login function called")

        cmd_path = Path(self.cmd_path, "mega-login")
        cmd = f"{cmd_path} \"{username}\" \"{password}\""
        self.logger.log(0, cmd)

        proc = subprocess.Popen(cmd, shell=True, cwd=self.cmd_path)
        proc.wait()
        return proc.returncode

    def export_folder(self, username, password, folder_name):
        """" Exports a folder

        Parameters
        ----------
        username : str
        password : str
        folder_name : str
            The root of megacmd is "/" don't confuse with megatools "/Root/"

        Returns
        -------
        str
            The export url of the exported folder

        """

        self.logger.log(0, "Export function called")

        with self.LOCK:
            self.logout()
            self.login(username, password)

            cmd_path = Path(self.cmd_path, "mega-export")
            cmd = f"{cmd_path} -a {folder_name}"
            self.logger.log(0, cmd)

            output = subprocess.Popen(
                cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                cwd=self.cmd_path
            ).communicate(b"yes")  # Set to 'no' if you are a pirate

        std_out_text = output[0].decode("utf-8")

        # Return url
        url = self.URL_REGEX.findall(std_out_text)[0]
        self.logger.info("Exported: %s", url)
        return url

    def keep_alive(self, username, password):
        """""Logs in to an account to keep it active"""
        with self.LOCK:
            self.logout()
            self.login(username, password)
            self.logout()


class MegaAbuse(CreateAccount, MegaCmd):
    """" The main class of MEGAabuse

    Attributes
    ----------
    total_files_count : multiprocessing.sharedctypes.Synchronized
        Counter for all the files being processed. Used for logging purposes.

    Methods
    -------
    update_json_file(file, data)
        Dumps json to file
    create_folder(user_name, password, folder_name, proxy=False)
        Creates a folder on a mega.nz drive
    upload_file(username, password, remote_path, file_path, proxy=False)
        Uploads a single file to mega.nz
    upload_chunks(chunks, dir_name, proxy)
        Uploads all files in the chunks prepared by upload_folder
    find_files(search_path, wrong_extensions)
        Finds all files in search path
    divide_files(paths, max_size)
        Divides files into groups of specified size
    upload_folder(folder_path, proxy=False)
        Main method. Uploads all files from a local folder to mega.nz

    """

    total_files_count = multiprocessing.Value("i", 0)

    def __init__(self, tools_path, cmd_path, *args, logger=None, write_files=False):
        """" Init function

        Starts the mega cmd server on Windows and Linux. Mac os does not use the mega cmd server.
        So it is unnecessary to pass the server path parameter on mac os.

        Parameters
        ----------
        tools_path : str or pathlib.Path
            Path to mega tools
        cmd_path : str or pathlib.Path, optional
            Path to mega cmd
        resume_dir : str or pathlib.Path, optional
            Path to resume dir
        accounts_file : str or pathlib.Path, optional
            Path to accounts file
        done_file : str or pathlib.Path, optional
            Path to done file
        cmd_server_path : str or pathlib.Path, optional
            Path to mega cmd server binary
        logger : logger object, optional
            Use this logger
        write_files : bool, optional
            To write files or not

        """

        self.tools_path = Path(tools_path)
        self.write_files = write_files

        self.done = []

        # Create resume dir
        if self.write_files:

            # Init CreateAccount with an accounts file
            CreateAccount.__init__(
                self,
                tools_path,
                args[1],
                logger=logger,
                write_files=write_files
            )

            # Resume file
            self.resume_dir = Path(args[0])
            if not self.resume_dir.is_dir():
                self.resume_dir.mkdir()

            # Read done file
            self.done_file = Path(args[2])
            if not self.done_file.is_file():
                self.done_file.touch()
            else:
                with open(self.done_file) as f_done:
                    self.done = [line.rstrip() for line in f_done]
        else:

            # Init CreateAccount without an accounts file
            CreateAccount.__init__(
                self,
                tools_path,
                logger=logger,
                write_files=write_files
            )

        # If running on mac os init MegaCmd without a server path
        if sys.platform == "darwin":
            MegaCmd.__init__(
                self,
                cmd_path,
                logger=logger
            )
        else:
            # Init MegaCmd with server path
            MegaCmd.__init__(
                self,
                cmd_path,
                Path(args[3]),
                logger=logger
            )

        # Create logger or sub logger for class
        if logger is None:
            self.logger = logging.getLogger("MegaAbuse")
        else:
            self.logger = logger

    @staticmethod
    def update_json_file(file, data):
        """" Updates a json file with new data """
        with open(file, "w") as json_file:
            json.dump(data, json_file, indent=4)

    def create_folder(self, user_name, password, folder_name, proxy=False):
        """" Create a folder om a mega account

        Parameters
        ----------
        user_name : str
        password : str
        folder_name : str
            Root is written as /Root/ instead of /
        proxy : str, optional
            Socks5 url

        """

        self.logger.log(0, "Create folder function called")

        cmd = f"{self.tools_path} mkdir {folder_name} -u {user_name} -p {password}"
        if proxy:
            cmd += f" --proxy={proxy}"
        self.logger.log(0, cmd)

        subprocess.Popen(cmd, shell=True).wait()

    def upload_file(self, username, password, remote_path, file_path, proxy=False):
        """" Uploads a file to mega

        Parameters
        ----------
        username : str
        password : str
        remote_path : str
            Target path on mega drive. Root is written as /Root/ instead of /
        file_path : str or Path
            path to local file to upload
        proxy : str, optional
            Socks5 url

        """

        self.logger.log(0, "Upload file function called")

        cmd = f"{self.tools_path} put -u {username} -p {password} --path \"{remote_path}\" \"{file_path}\""
        if proxy:
            cmd += f" --proxy={proxy}"
        self.logger.log(0, cmd)

        return bool(subprocess.Popen(cmd, shell=True).wait() == 0)

    def upload_chunks(self, chunks, dir_name, proxy):  # Proxy can be str or False
        """" Uploads the chunks to mega.nz """
        self.logger.log(0, "Upload chunks function called")

        resume_data = []
        if self.write_files:
            # Create resume file
            resume_file = Path(self.resume_dir, f"{dir_name}.json")
            if not resume_file.is_file() and self.write_files:
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
                    self.logger.debug("Found chunk in resume data %s", r_data)
                    break
                except IndexError:
                    chunk_resume = {
                        "credentials": super().get(1, proxy),
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
            self.create_folder(user_name, password, f"/Root/{folder_name}", proxy)

            for file in chunk["files"]:
                if file not in uploaded_files:
                    self.logger.info("Uploading: %s", file)

                    file_path = Path(file)
                    extension = file.split(".")[-1]
                    file_name = f"{file_path.stem}.{extension}"

                    # Returns True on a successful upload
                    if self.upload_file(user_name, password, f"/Root/{folder_name}/{file_name}", file, proxy):

                        # Update resume data
                        uploaded_files.append(file)
                        if self.write_files:
                            self.update_json_file(resume_file, resume_data)
                    else:
                        self.logger.error("Error uploading: %s", file)
                else:
                    self.logger.info("Skipping: %s", file)

            # Folder path is with / instead of /Root because the export folder function
            # uses megacmd instead of megatools.
            export_url = super().export_folder(user_name, password, f"/{folder_name}")
            export_urls.append(export_url)

            # Write export url to resume file
            resume_data[c_counter].update({"export url": export_url})
            if self.write_files:
                self.update_json_file(resume_file, resume_data)

            c_counter += 1
        return export_urls

    @staticmethod
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

    @staticmethod
    def divide_files(paths: dict, max_size):  # Max size is in bits
        """" Input is {path: size in bytes dict}.
             divides files in lists of no more than 15 GB """
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

    def upload_folder(self, folder_path, proxy=False):
        """" Uploads a folder to mega.nz returns download urls """
        self.logger.log(0, "Upload folder function called")

        if folder_path in self.done and self.write_files:
            self.logger.info("Skipping: %s", folder_path)
            return []
        self.logger.info("Uploading %s", folder_path)

        paths = self.find_files(folder_path, [".json", ])
        self.logger.info("%s: Found %s files", folder_path, len(paths))
        self.total_files_count.value += len(paths)
        file_lists = self.divide_files(paths, 15000000000)
        folder_name = Path(folder_path).parts[-1]

        chunks = []
        # A chunk is a set of files that fits in a mega account (50GB)
        for file_list in file_lists:
            chunks.append({
                "folder name": folder_name,
                "files": file_list
            })

        self.logger.info("Uploading: %s chunks", len(chunks))
        export_urls = self.upload_chunks(chunks, folder_name, proxy)

        self.done.append(folder_path)
        if self.write_files:
            with open(self.done_file, "a") as file:
                file.write(folder_path + linesep)

        return export_urls

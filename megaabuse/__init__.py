import atexit
import logging
import multiprocessing
import re
import subprocess
import sys
from os import linesep
from pathlib import Path

from .accountfactory import AccountFactory


class CreateAccount(AccountFactory):
    # Lock used for locking the pool when creating an account at the moment accounts can nut be created simultaneously
    ACC_LOCK = multiprocessing.Lock()

    def __init__(self, tools_path, file, logger=None, write_files=False):
        super().__init__(tools_path, logger)
        self.output = write_files

        # Create accounts.txt
        if self.output:
            self.account_file = Path(file)
            if not self.account_file.is_file():
                self.account_file.touch()

    # todo: Support multiprocessing. confirm_command or something when you do two at once
    def get(self, amount, proxy=False):
        """"" Wrapper for guerrilla_gen_bulk """

        with self.ACC_LOCK:
            accounts = super().guerrilla_gen_bulk(amount, False, proxy)

        # Write credentials to file
        if self.output:
            with open(self.account_file, "a") as file:
                for user, password in accounts.items():
                    file.write(f"{user};{password}" + linesep)
        return accounts


class MegaCmd:
    # Regex for extracting export url from export command output
    URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    LOCK = multiprocessing.Lock()  # Used for locking the pool while exporting.

    def __init__(self, m_cmd_path, *args, logger=None):
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

            cmd_server_proc = subprocess.Popen(
                str(server_path),
                shell=True,
                stdout=subprocess.PIPE,
                cwd=self.cmd_path
            )

            def exit_handler():
                """"Stop MEGA cmd server when program exits"""
                logging.debug("Killing MEGA cmd server")
                if cmd_server_proc:
                    cmd_server_proc.terminate()

            atexit.register(exit_handler)

    def logout(self):
        """" Logs out of megacmd """
        self.logger.log(0, "Logout function called")

        cmd_path = Path(self.cmd_path, "mega-logout")
        cmd = str(cmd_path)
        self.logger.log(0, cmd)

        subprocess.Popen(cmd, shell=True, cwd=self.cmd_path).wait()

    def login(self, username, password):
        """" Logs in to megacmd """
        self.logger.log(0, "Login function called")

        cmd_path = Path(self.cmd_path, "mega-login")
        cmd = f"{cmd_path} \"{username}\" \"{password}\""
        self.logger.log(0, cmd)

        subprocess.Popen(cmd, shell=True, cwd=self.cmd_path).wait()

    def export_folder(self, username, password, folder_name):
        """" Exports a folder """
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
        with self.LOCK:
            self.logout()
            self.login(username, password)
            self.logout()

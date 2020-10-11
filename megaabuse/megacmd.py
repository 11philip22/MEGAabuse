import atexit
import logging
import multiprocessing
import re
import subprocess
import sys
from pathlib import Path


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
    # URL_REGEX = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    LOCK = multiprocessing.Lock()  # Used for locking the pool while exporting.

    def __init__(self, **kwargs):
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
        if "logger" not in kwargs:
            logger_name = "MegaExport"
        else:
            logger_name = f"{kwargs['logger']}.MegaExport"
        self.logger = logging.getLogger(logger_name)

        self.cmd_path = Path(kwargs["mega_cmd_path"])

        # Start MEGA cmd server
        if sys.platform == "linux" or sys.platform == "win32":
            server_path = Path(kwargs["cmd_server_path"])

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
        # url = self.URL_REGEX.findall(std_out_text)[0]
        url = re.search(  # todo: find out what the fuck happened here
            "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            std_out_text
        ).group()
        self.logger.info("Exported: %s", url)
        return url

    def keep_alive(self, username, password):
        """""Logs in to an account to keep it active"""
        with self.LOCK:
            self.logout()
            self.login(username, password)
            self.logout()

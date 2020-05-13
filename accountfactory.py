import logging
from random import choice
import guerrillamail
import time
from bs4 import BeautifulSoup
from names import get_first_name
import subprocess

"""" Creates mega.nz accounts using guerrillamail """


class AccountFactory:
    """" Creates mega.nz accounts using guerrillamail """

    total_accounts_created = 0  # Total accounts created

    def __init__(self, tools_path, logger=None):
        self.megareg_dir = f"{tools_path} reg"

        # Create logger or sub logger for class
        if logger is None:
            logger_name = "AccountFactory"
        else:
            logger_name = f"{logger.name}.AccountFactory"
        self.logger = logging.getLogger(logger_name)

    @staticmethod
    def random_text(length):
        """" Returns a random string with specified length """
        return ''.join(
            [choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for i in range(length)])

    @staticmethod
    def random_mail():
        """" Returns a 30 character string """
        return ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789') for i in range(30)])

    def guerrilla_wait_for_mail(self):
        """" Wait for welcome mail """
        wait_time = 0
        while True:
            if wait_time > 120:
                self.logger.info("Waiting for mail time exceeded 2 minutes. Aborting")
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
        self.logger.info("Starting a new bulk")
        email_code_pairs = {}
        email_pass_pairs = {}
        confirm_commands = []
        name = get_first_name()
        needed = accounts_number

        # Register a bulk of size "needed"
        self.logger.info("Registering accounts")
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
            self.logger.log(0, cmd)
            confirm_text = subprocess.check_output(cmd, shell=True).decode('UTF-8')
            confirm_text = confirm_text[confirm_text.find("-"):]
            email_code_pairs[email] = confirm_text
            email_pass_pairs[email] = email_password
            needed -= 1
        self.logger.info("Done registering")

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
        self.logger.info("Confirming accounts")
        for command in confirm_commands:
            subprocess.check_output(command, shell=True)

        self.total_accounts_created += accounts_number
        self.logger.info(
            "Bulk done. Generated %s accounts in %ss. Currently: %s",
            accounts_number,
            round(time.time() - start, 1),
            self.total_accounts_created
        )
        return email_pass_pairs

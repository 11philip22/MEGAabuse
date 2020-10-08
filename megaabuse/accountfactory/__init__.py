"""" The accountfactory sub module

This file contains the classes that create mega.nz accounts.
The Currently supported methods are: Guerrillamail

"""

import logging
import subprocess
import time
from random import choice
import imaplib
from bs4 import BeautifulSoup
from names import get_first_name
import mariadb
from pathlib import Path
from datetime import datetime
import re
from . import guerrillamail
from .dov_ssha512 import DovecotSSHA512Hasher


class AccountFactory:
    """" baseclass

    To be inherited bt all account generating classes
    to avoid writing double functions

    Attributes
    ----------
    total_accounts_created : int
        The amount of accounts that is created during an instance

    """

    total_accounts_created = 0  # Total accounts created
    URL_REGEX = re.compile(
        "https://mega.nz/#confirm(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

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

    def extract_url(self, mail_str):
        """" Extracts url from mail """
        url = self.URL_REGEX.findall(mail_str)[0]
        if url:
            return url

        # soup = BeautifulSoup(mail_str, "html.parser")
        # for link in soup.findAll("a"):
        #     if link.get("href") is not None and "#confirm" in link.get("href"):
        #         return link.get("href").replace('3D"', "").replace('"', "")
        return None


class IGenMail(AccountFactory, DovecotSSHA512Hasher):
    """"Creates mega.nz accounts using iRedMail

    This is designed to work with mariadb.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super(DovecotSSHA512Hasher, self).__init__(prefix='{SSHA512}')

        self.conn = None

    def connect_to_db(self, host, user, password, port=3306, db="vmail"):
        """" Connects to DB """

        try:
            self.conn = mariadb.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=db
            )
            self.conn.autocommit = False
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def create_mail_user(self, email, password):
        """" Creates a new mail user

        Cleanup ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ DELETE ALL USERS EXCEPT POSTMASTER
        DELETE FROM mailbox WHERE NOT username = 'postmaster@domain.com';
        DELETE FROM forwardings WHERE NOT address =  'postmaster@domain.com';

        """

        if self.conn is None:
            self.logger.error("Can't create user! Not connected to db")
            return False

        storage_base_dir = "/var/vmail/vmail1"
        storage_base = str(Path(storage_base_dir).parent)
        storage_node = str(Path(storage_base_dir).name)
        crypt_password = self.encode(password)
        s_uname = email.split("@")
        user_name = s_uname[0]
        domain = s_uname[1]

        now = datetime.now()
        dt_str = now.strftime("%Y.%m.%d.%H.%M.%S")

        mail_dir = f"{domain}/{email[0]}/{email[1]}/{email[2]}/{email}-{dt_str}"

        try:
            cursor = self.conn.cursor()
            cursor.execute("""INSERT INTO mailbox (username, password, name, 
                                                   storagebasedirectory,storagenode, maildir, 
                                                   quota, domain, active, passwordlastchange, created) 
                                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW());""",
                           (email, crypt_password, user_name, storage_base, storage_node, mail_dir, "1024", domain, 1))
            cursor.execute("""INSERT INTO forwardings (address, forwarding, domain, dest_domain, is_forwarding)
                                               VALUES (?, ?, ?, ?, 1);""",
                           (email, email, domain, domain))
            self.conn.commit()
            return True
        except mariadb.Error as e:
            self.logger.error(e)
            return False

    def delete_mail_user(self, email):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM mailbox WHERE username=?;", (email,))
            cursor.execute("DELETE FROM forwardings WHERE address=?;", (email,))
            self.conn.commit()
            return True
        except mariadb.Error as e:
            self.logger.error(e)
            return False

    def create_mega_account(self, domain, imap_address, fixed_pass, proxy):
        self.logger.info("Registering accounts")

        email = f"{self.random_mail()}@{domain}"
        name = get_first_name()

        if fixed_pass:
            email_password = fixed_pass
        else:
            email_password = self.random_text(21)

        self.create_mail_user(email, email_password)

        cmd = f"{self.megareg_dir} -n {name} -e {email} -p {email_password} --register --scripted"
        if proxy:
            cmd += f" --proxy={proxy}"
        self.logger.log(0, cmd)

        confirm_text = subprocess.check_output(cmd, shell=True).decode('UTF-8')
        confirm_text = confirm_text[confirm_text.find("-"):]
        self.logger.info("Done registering")

        # Wait for mail
        while True:
            imap = imaplib.IMAP4_SSL(imap_address)
            if not imap.login(email, email_password)[0] == "OK":
                self.logger.error("Could not login to the mailserver")
                return False, False

            imap.select("inbox")

            welcome_mail = imap.search(None, "FROM", '"welcome@mega.nz"')[1]
            if welcome_mail == [b'']:
                imap.close()
                continue
            else:
                self.logger.info("Got mail")
                break

        data = imap.search(None, "FROM", '"welcome@mega.nz"')[1]
        typ, data = imap.fetch(data[0], '(RFC822)')
        raw_email = data[0][1]
        raw_email_string = raw_email.decode('utf-8')
        confirm_url = self.extract_url(raw_email_string)

        confirm_command = f"{self.megareg_dir} {confirm_text.replace('@LINK@', confirm_url)}"
        subprocess.check_output(confirm_command, shell=True)

        return email, email_password


class GuerrillaGen(AccountFactory):
    """" Creates mega.nz accounts using guerrillamail """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            while True:
                mail_id = self.guerrilla_wait_for_mail()[6:15]
                if not mail_id:
                    self.logger.info("Retrying")
                else:
                    break
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

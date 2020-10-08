import re
import sys
import unittest
from os import path, remove
from pathlib import Path
import subprocess

from megaabuse import CreateAccount, MegaCmd
from megaabuse.accountfactory import GuerrillaGen, IGenMail

SCRIPT_DIR = path.dirname(path.realpath(__file__))
BIN_PATH = Path(SCRIPT_DIR, "binaries")
if sys.platform == "win32":
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_win", "megatools.exe")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_windows")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "MEGAcmdServer.exe")
else:
    MEGATOOLS_PATH = Path(BIN_PATH, "megatools_linux", "megatools")
    MEGACMD_PATH = Path(BIN_PATH, "megacmd_linux")
    CMD_SERVER_PATH = Path(MEGACMD_PATH, "mega-cmd-server")

test_account = {}  # An mega.nz account used for testing


class TestIGenMail(unittest.TestCase):
    domain = "bok-bright.com"
    test_emails = []

    def setUp(self):
        self.acc_fac = IGenMail(MEGATOOLS_PATH)

    def tearDown(self):
        for mail in self.test_emails:
            cur = self.acc_fac.conn.cursor()
            # Remove email
            self.acc_fac.delete_mail_user(mail)
            # Check if removed from db
            cur.execute("SELECT username,name FROM mailbox WHERE username=?", (mail,))
            res = cur.fetchall()
            self.assertEqual(res, [])

    def test_db_connection(self):
        self.acc_fac.connect_to_db(
            host="mail.bok-bright.com",
            user="root",
            password="df29ySQLadm3737d4ba00c79cet"
        )

        self.assertEqual(self.acc_fac.conn.server_info, "10.3.22-MariaDB-1ubuntu1")

    def test_encode(self):
        string = "hoi"
        encoded_str = self.acc_fac.encode(string)
        print(encoded_str)

        self.assertEqual(len(encoded_str), 117)

    def test_create_mail_user(self):
        self.test_db_connection()

        mail = f"{self.acc_fac.random_mail()}@{self.domain}"
        self.test_emails.append(mail)
        print(f"Email: {mail}")
        pw = "hoi123456"

        # Create email
        self.acc_fac.create_mail_user(mail, pw)
        # Check if created in db
        cur = self.acc_fac.conn.cursor()
        cur.execute("SELECT username,name FROM mailbox WHERE username=?", (mail,))
        res = cur.fetchall()
        # Check against results from db
        self.assertEqual(res[0][0], mail)
        self.assertEqual(res[0][1], mail.split("@")[0])

    def test_create_mega_account(self):
        self.test_db_connection()

        mail, email_pw = self.acc_fac.create_mega_account(self.domain, f"mail.{self.domain}", False, False)
        self.test_emails.append(mail)
        print(f"Email: {mail}\nPassword: {email_pw}")

        cmd = MegaCmd(MEGACMD_PATH, CMD_SERVER_PATH)
        self.assertEqual(cmd.logout(), 0)
        self.assertEqual(cmd.login(mail, email_pw), 0)
        self.assertEqual(cmd.logout(), 0)


class TestGuerrillaGen(unittest.TestCase):
    def setUp(self):
        self.acc_fac = GuerrillaGen(MEGATOOLS_PATH)

    def test_account_creation(self):
        accounts = self.acc_fac.guerrilla_gen_bulk(1, False, False)
        test_account.update(accounts)
        print(test_account)

        self.assertTrue(bool(accounts))

    def test_account_creation_fixed_pass(self):
        fixed_password = "Test1234Jdjskdmelsk88fd"

        accounts = self.acc_fac.guerrilla_gen_bulk(1, fixed_password, False)
        test_account.update(accounts)
        print(test_account)

        for username, password in accounts.items():
            self.assertEqual(fixed_password, password)


class TestCreateAccount(unittest.TestCase):
    def setUp(self):
        self.account_file = Path(SCRIPT_DIR, "accounts.txt")
        # Make sure accounts file is not already there so we can have a meaningful test
        self.assertFalse(self.account_file.is_file())

    def tearDown(self):
        try:  # Cleanup
            remove(self.account_file)
        except FileNotFoundError:
            pass

    def test_account_creation_no_write(self):
        create_acc = CreateAccount(MEGATOOLS_PATH, write_files=False)
        accounts = create_acc.get(1, False)

        test_account.update(accounts)

        self.assertTrue(bool(accounts))
        self.assertFalse(self.account_file.is_file())

    def test_account_creation_write(self):
        create_acc = CreateAccount(MEGATOOLS_PATH, self.account_file, write_files=True)
        accounts = create_acc.get(1, False)

        test_account.update(accounts)  # Save account so later tests dont have to generate a new one

        self.assertTrue(bool(accounts))
        self.assertTrue(self.account_file.is_file())

    def test_total_accounts_counter(self):
        create_acc = CreateAccount(MEGATOOLS_PATH, write_files=False)

        accounts = create_acc.get(1, False)
        self.assertEqual(create_acc.total_accounts_created, 1)

        accounts.update(create_acc.get(2, False))
        self.assertEqual(create_acc.total_accounts_created, 3)


class TestMegaCmd(unittest.TestCase):
    def setUp(self):
        self.cmd = MegaCmd(MEGACMD_PATH, CMD_SERVER_PATH)

    def test_server_init(self):
        self.assertTrue(
            type(self.cmd.cmd_server_proc.pid) == int
        )

    def test_login(self):
        self.assertEqual(self.cmd.logout(), 0)
        for user, passwd in test_account.items():
            self.assertEqual(self.cmd.login(user, passwd), 0)

    def test_logout(self):
        for user, passwd in test_account.items():
            self.assertEqual(self.cmd.login(user, passwd), 0)
        self.assertEqual(self.cmd.logout(), 0)

    def test_export(self):
        url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[#]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

        test_file = Path(SCRIPT_DIR, "test.txt")
        test_file.touch()

        for username, password in test_account.items():
            cmd = f"{MEGATOOLS_PATH} mkdir /Root/testfolder -u {username} -p {password}"
            subprocess.Popen(cmd, shell=True).wait()

            cmd = f"{MEGATOOLS_PATH} put -u {username} -p {password} --path /Root/testfolder/test.txt {test_file}"
            subprocess.Popen(cmd, shell=True).wait()

            export_url = self.cmd.export_folder(username, password, "/testfolder")
            self.assertTrue(bool(url_regex.findall(export_url)))
            break
        remove(test_file)


class TestMegaAbuse(unittest.TestCase):
    def test_update_json_file(self):
        pass

    def test_create_folder(self):
        pass

    def test_upload_file(self):
        pass

    def test_upload_chunks(self):
        pass

    def test_find_files(self):
        pass

    def test_devide_files(self):
        pass

    def upload_folder(self):
        pass


if __name__ == '__main__':
    unittest.main()
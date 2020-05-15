import atexit
import sys
import unittest
from os import path, remove
from pathlib import Path

from megaabuse import CreateAccount, MegaCmd
from megaabuse.accountfactory import AccountFactory

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


class TestAccountFactory(unittest.TestCase):
    def test_account_creation(self):
        acc_fac = AccountFactory(MEGATOOLS_PATH)
        accounts = acc_fac.guerrilla_gen_bulk(1, False, False)

        self.assertTrue(bool(accounts))

    def test_account_creation_fixed_pass(self):
        fixed_password = "Test1234Jdjskdmelsk88fd"

        acc_fac = AccountFactory(MEGATOOLS_PATH)
        accounts = acc_fac.guerrilla_gen_bulk(1, fixed_password, False)
        for username, password in accounts.items():
            self.assertEqual(fixed_password, password)


test_account = {}  # An mega.nz account used for testing


class TestCreateAccount(unittest.TestCase):
    def test_account_creation_no_write(self):
        create_acc = CreateAccount(MEGATOOLS_PATH, write_files=False)
        accounts = create_acc.get(1, False)

        self.assertTrue(bool(accounts))

    def test_account_creation_write(self):
        account_file = Path(SCRIPT_DIR, "accounts.txt")

        # Make sure accounts file is not already there so we can have a meaningful test
        self.assertFalse(account_file.is_file())

        create_acc = CreateAccount(MEGATOOLS_PATH, account_file, write_files=True)
        accounts = create_acc.get(1, False)
        test_account.update(accounts)  # Save account so later tests dont have to generate a new one

        self.assertTrue(bool(accounts))
        self.assertTrue(account_file.is_file())

        # Cleanup
        remove(account_file)


class TestMegaCmd(unittest.TestCase):
    cmd = MegaCmd(MEGACMD_PATH, CMD_SERVER_PATH)

    def test_server_init(self):
        self.assertTrue(
            bool(type(self.cmd.cmd_server_proc.pid) == int)
        )

    def test_login(self):
        for user, passwd in test_account.items():
            self.assertEqual(self.cmd.login(user, passwd), 0)

    def test_logout(self):
        self.assertEqual(self.cmd.logout(), 0)

    def test_export(self):
        pass

    def test_server_stop(self):
        self.cmd.exit_handler()


if __name__ == '__main__':
    unittest.main()

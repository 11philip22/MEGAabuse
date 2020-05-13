import sys
import unittest
from os import path
from pathlib import Path

from megaabuse import CreateAccount
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


class TestCreateAccount(unittest.TestCase):
    def test_account_creation(self):
        create_acc = CreateAccount(MEGATOOLS_PATH, Path(SCRIPT_DIR, "accounts.txt"), logger=None, write_files=False)
        accounts = create_acc.get(1, False)

        self.assertTrue(bool(accounts))


if __name__ == '__main__':
    unittest.main()

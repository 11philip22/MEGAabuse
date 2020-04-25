from pathlib import Path
from mega import Mega
from os import path

script_dir = path.dirname(path.realpath(__file__))  # Comment for ipython

account_file = Path(script_dir, "accounts.txt")
with open(account_file) as account_f:
    # Read accounts from file
    for file_line in account_f:
        line = file_line.strip("\n")
        usern, passwd = line.split(";")

        # Log in and log out using megacmd
        # todo: Maybe it is not needed to redefine m every iteration
        ms = Mega()
        ms.login(usern, passwd)
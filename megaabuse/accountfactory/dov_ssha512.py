"""" Code taken from: https://github.com/ioparaskev """

from hmac import compare_digest as constant_time_compare
import base64
from hashlib import sha512
import os
import binascii


class SSHA512Hasher:
    def __init__(self, prefix=''):
        self.prefix = prefix

    def encode(self, word, salt=os.urandom(16)):
        sha = sha512()
        word = word.encode("utf-8")
        sha.update(word)
        sha.update(salt)
        ssha512 = base64.b64encode(sha.digest() + salt)

        return f"{self.prefix}{ssha512.decode('utf-8')}"

    def verify(self, word, encoded):
        stripped = encoded.replace(self.prefix, "")
        try:
            salt = self.extract_salt(stripped or encoded)
        except (RuntimeError, binascii.Error) as err:
            print(f"An error occured: {err}")
            return False

        encoded_2 = self.encode(word, salt)
        return constant_time_compare(encoded, encoded_2)

    @staticmethod
    def extract_salt(_hash):
        decoded = base64.b64decode(_hash)
        # we don't care how big salt is. everything after 64 is salt
        salt = decoded[64::]
        return salt


class DovecotSSHA512Hasher(SSHA512Hasher):
    def __init__(self):
        super(DovecotSSHA512Hasher, self).__init__(prefix='{SSHA512}')

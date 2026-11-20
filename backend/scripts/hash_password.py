"""Crea l'hash della password da mettere in APP_PASSWORD_HASH.
Uso: python scripts/hash_password.py"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.auth import hash_password  # noqa: E402

pw = getpass.getpass("Password: ")
if pw != getpass.getpass("Ripeti: "):
    sys.exit("Le password non coincidono.")
print(hash_password(pw))

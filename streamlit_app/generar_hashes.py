"""
Script one-time para generar hashes scrypt de passwords.

Uso:
    python streamlit_app/generar_hashes.py

Pega los valores generados en .streamlit/secrets.toml como password_hash.
Una vez migrados todos, elimina los campos password (plaintext).
"""

import getpass
import hashlib
import os


def hash_password(password: str) -> str:
    """Genera hash scrypt: salt_hex:hash_hex."""
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return salt.hex() + ":" + h.hex()


def main():
    print("=== Generador de hashes scrypt para secrets.toml ===\n")
    print("Introduce los passwords de cada usuario.")
    print("El hash generado va en el campo 'password_hash' de secrets.toml.\n")

    usuarios = ["jaime", "roberto", "elena", "benjamin"]

    for user in usuarios:
        pw = getpass.getpass(f"Password para {user}: ")
        if not pw:
            print(f"  (saltado)\n")
            continue
        h = hash_password(pw)
        print(f'  [users.{user}]')
        print(f'  password_hash = "{h}"')
        print()

    print("--- Copia las líneas anteriores a .streamlit/secrets.toml ---")
    print("--- Después elimina los campos 'password' (plaintext) ---")


if __name__ == "__main__":
    main()

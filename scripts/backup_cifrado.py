"""
backup_cifrado.py — Backup cifrado de archivos críticos del proyecto.

Cifra con AES-256 (via Fernet) los archivos que NO están en git y son
irreemplazables. Genera un archivo .zip.enc que se puede guardar en
Dropbox, USB o cualquier otro sitio seguro.

Uso:
    python scripts/backup_cifrado.py                  # backup con contraseña interactiva
    python scripts/backup_cifrado.py --output ruta    # especificar destino
    python scripts/backup_cifrado.py --restore archivo.zip.enc  # restaurar

Requiere: pip install cryptography
"""

import argparse
import base64
import getpass
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Archivos críticos irreemplazables (relativos a PROJECT_ROOT)
ARCHIVOS_CRITICOS = [
    "config/datos_sensibles.py",
    "gmail/credentials.json",
    "gmail/token.json",
    "gmail/token.json.backup",
    "gmail/config_local.py",
    "ventas_semana/.env",
    "api/.env",
    "streamlit_app/.streamlit/secrets.toml",
    "datos/emails_procesados.json",
    "datos/MAESTRO_PROVEEDORES.xlsx",
]

# Directorios con archivos N43 (extractos bancarios originales)
DIRS_CRITICOS = [
    "norma43/archivados",
    "cuadre/norma43/archivados",
]


def _derive_key(password: str, salt: bytes) -> bytes:
    """Deriva clave AES-256 de una contraseña usando PBKDF2."""
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=600_000, dklen=32)
    return base64.urlsafe_b64encode(key)


def _get_fernet(password: str, salt: bytes):
    """Crea instancia Fernet con clave derivada."""
    from cryptography.fernet import Fernet
    key = _derive_key(password, salt)
    return Fernet(key)


def _recopilar_archivos() -> list[tuple[str, str]]:
    """Recopila archivos críticos que existen. Devuelve [(ruta_relativa, ruta_absoluta)]."""
    archivos = []

    for rel in ARCHIVOS_CRITICOS:
        abs_path = os.path.join(PROJECT_ROOT, rel)
        if os.path.exists(abs_path):
            archivos.append((rel, abs_path))

    for dir_rel in DIRS_CRITICOS:
        dir_abs = os.path.join(PROJECT_ROOT, dir_rel)
        if os.path.isdir(dir_abs):
            for fname in os.listdir(dir_abs):
                fpath = os.path.join(dir_abs, fname)
                if os.path.isfile(fpath):
                    archivos.append((f"{dir_rel}/{fname}", fpath))

    return archivos


def backup(password: str, output_path: str | None = None) -> str:
    """Crea backup cifrado de archivos críticos.

    1. Recopila archivos
    2. Los comprime en un ZIP en memoria
    3. Cifra el ZIP con AES-256 (Fernet + PBKDF2)
    4. Guarda como .zip.enc
    """
    archivos = _recopilar_archivos()
    if not archivos:
        print("No se encontraron archivos críticos para respaldar.")
        return ""

    print(f"Archivos a respaldar: {len(archivos)}")
    for rel, _ in archivos:
        size = os.path.getsize(os.path.join(PROJECT_ROOT, rel))
        print(f"  {rel} ({size:,} bytes)")

    # Crear ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, abs_path in archivos:
            zf.write(abs_path, rel)

        # Añadir manifiesto
        manifiesto = {
            "fecha_backup": datetime.now().isoformat(),
            "proyecto": "gestion-facturas",
            "archivos": [rel for rel, _ in archivos],
            "total_archivos": len(archivos),
        }
        zf.writestr("_MANIFIESTO.json", json.dumps(manifiesto, indent=2, ensure_ascii=False))

    zip_data = zip_buffer.getvalue()
    print(f"\nZIP generado: {len(zip_data):,} bytes ({len(zip_data)//1024} KB)")

    # Cifrar
    salt = os.urandom(16)
    fernet = _get_fernet(password, salt)
    encrypted = fernet.encrypt(zip_data)

    # Guardar: salt (16 bytes) + datos cifrados
    if not output_path:
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(PROJECT_ROOT, "datos", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        output_path = os.path.join(backup_dir, f"backup_critico_{fecha}.zip.enc")

    with open(output_path, "wb") as f:
        f.write(salt + encrypted)

    print(f"\nBackup cifrado guardado: {output_path}")
    print(f"Tamaño: {os.path.getsize(output_path):,} bytes")
    print(f"Cifrado: AES-256 (Fernet + PBKDF2, 600k iteraciones)")
    print(f"\nATENCION:  GUARDA LA CONTRASEÑA en un sitio seguro.")
    print(f"ATENCION:  Sin ella, el backup es IRRECUPERABLE.")

    return output_path


def restore(encrypted_path: str, password: str, output_dir: str | None = None):
    """Restaura backup cifrado.

    1. Lee salt + datos cifrados
    2. Descifra con contraseña
    3. Extrae ZIP
    """
    if not os.path.exists(encrypted_path):
        print(f"Error: no se encuentra {encrypted_path}")
        return False

    with open(encrypted_path, "rb") as f:
        data = f.read()

    salt = data[:16]
    encrypted = data[16:]

    print(f"Archivo: {encrypted_path} ({len(data):,} bytes)")
    print("Descifrando...")

    try:
        fernet = _get_fernet(password, salt)
        zip_data = fernet.decrypt(encrypted)
    except Exception:
        print("ERROR: Contraseña incorrecta o archivo corrupto.")
        return False

    print(f"ZIP descifrado: {len(zip_data):,} bytes")

    if not output_dir:
        output_dir = os.path.join(PROJECT_ROOT, "datos", "backups", "restaurado")
    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf:
        # Mostrar contenido
        print(f"\nContenido ({len(zf.namelist())} archivos):")
        for name in zf.namelist():
            info = zf.getinfo(name)
            print(f"  {name} ({info.file_size:,} bytes)")

        # Extraer
        zf.extractall(output_dir)

    print(f"\nRestaurado en: {output_dir}")
    print("IMPORTANTE: Revisa los archivos antes de copiarlos al proyecto.")

    return True


def main():
    parser = argparse.ArgumentParser(description="Backup cifrado de archivos críticos")
    parser.add_argument("--output", "-o", help="Ruta del archivo de backup")
    parser.add_argument("--restore", "-r", help="Restaurar un backup cifrado")
    parser.add_argument("--password", "-p", help="Contraseña (si no se da, se pide interactivamente)")
    args = parser.parse_args()

    # Verificar cryptography
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("Instalando cryptography...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "cryptography"], check=True)
        from cryptography.fernet import Fernet

    if args.restore:
        pwd = args.password or getpass.getpass("Contraseña de descifrado: ")
        restore(args.restore, pwd)
    else:
        pwd = args.password
        if not pwd:
            pwd = getpass.getpass("Contraseña para cifrar el backup: ")
            pwd2 = getpass.getpass("Repetir contraseña: ")
            if pwd != pwd2:
                print("Error: las contraseñas no coinciden.")
                sys.exit(1)
        backup(pwd, args.output)


if __name__ == "__main__":
    main()

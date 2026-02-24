# src/facturas/tools/validate_patterns.py
from __future__ import annotations

import argparse
from pathlib import Path

from ruamel.yaml import YAML

# Importa el modelo Pattern donde lo tengas definido.
# En tu repo lo definiste en facturas/patterns.py junto a Anchor/Precedence.
# Si lo tienes en facturas/models.py, cambia la importación a:
#   from facturas.models import Pattern
from pydantic import ValidationError

try:
    from facturas.patterns import Pattern  # <- ajusta si tu Pattern vive en otro módulo
except Exception as e:
    Pattern = None
    _import_error = e
else:
    _import_error = None


def validate_file(path: Path, yaml: YAML, syntax_only: bool = False) -> tuple[bool, str]:
    """
    Devuelve (ok, mensaje).
    ok = True si todo bien; False si error.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"❌ No se pudo leer: {e}"

    # 1) Validación de sintaxis YAML
    try:
        data = yaml.load(text)
    except Exception as e:
        return False, f"❌ YAML inválido: {e}"

    if syntax_only:
        return True, "✅ Sintaxis correcta"

    # 2) Validación de esquema (Pydantic)
    if Pattern is None:
        return False, f"❌ No puedo importar Pattern: {_import_error}"

    # Avisos rápidos de claves típicas
    if not isinstance(data, dict):
        return False, "❌ El YAML raíz no es un mapeo (dict)."

    if "proveedor" not in data:
        # Busca posibles typos comunes
        candidates = [k for k in data.keys() if "provee" in k.lower()]
        if candidates:
            return False, f"❌ Falta 'proveedor' (quizá quisiste decir: {', '.join(candidates)})"
        return False, "❌ Falta 'proveedor' en el YAML."

    try:
        Pattern(**data)
    except ValidationError as ve:
        # Mensaje compacto
        lines = []
        for err in ve.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "")
            lines.append(f"- {loc}: {msg}")
        return False, "❌ Esquema inválido:\n" + "\n".join(lines)
    except Exception as e:
        return False, f"❌ Error validando contra Pattern: {e}"

    return True, "✅ OK (sintaxis + esquema)"


def main():
    parser = argparse.ArgumentParser(
        description="Valida patrones YAML: sintaxis y (opcional) esquema Pattern (Pydantic)."
    )
    parser.add_argument(
        "dir",
        type=Path,
        help="Carpeta con YAML (por ejemplo: patterns)",
    )
    parser.add_argument(
        "--syntax-only",
        action="store_true",
        help="Sólo verificar sintaxis YAML (no valida con Pattern)",
    )
    args = parser.parse_args()

    root: Path = args.dir
    if not root.exists() or not root.is_dir():
        print(f"❌ La carpeta no existe o no es un directorio: {root}")
        raise SystemExit(2)

    yaml = YAML(typ="safe")

    yml_files = sorted(root.rglob("*.yml"))
    if not yml_files:
        print("⚠️  No se encontraron .yml en la carpeta indicada.")
        raise SystemExit(0)

    print(f"🔎 Escaneando {len(yml_files)} archivos en: {root}\n")

    ok_count = 0
    bad_count = 0

    for path in yml_files:
        ok, msg = validate_file(path, yaml, syntax_only=args.syntax_only)
        status = "OK" if ok else "ERROR"
        print(f"[{status}] {path.relative_to(root.parent)} -> {msg}")
        if ok:
            ok_count += 1
        else:
            bad_count += 1

    print("\n──────── Resumen ────────")
    print(f"👍 Correctos: {ok_count}")
    print(f"❌ Con problemas: {bad_count}")

    raise SystemExit(0 if bad_count == 0 else 1)


if __name__ == "__main__":
    main()

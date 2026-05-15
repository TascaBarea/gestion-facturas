#!/bin/bash
# Mirror automático de datos críticos al Drive tras cada commit.
# Si el último commit tocó datos/DiccionarioProveedoresCategoria.xlsx,
# copia el fichero a Drive (Maestro/).
#
# Trade-off documentado: edición directa en Drive (web u otro PC)
# se sobreescribe con el próximo commit. Aceptable: un solo editor
# activo (Jaime desde su PC).
#
# Instalación: este hook NO está versionado (git no rastrea .git/hooks/).
# Ver docs/HOOKS.md para reinstalación tras un git clone fresh.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
DRIVE_MAESTRO="/g/Mi unidad/Barea - Datos Compartidos/Maestro"

# Archivos a sincronizar: ruta_relativa_repo -> nombre_en_Drive
declare -A MIRRORS=(
  ["datos/DiccionarioProveedoresCategoria.xlsx"]="DiccionarioProveedoresCategoria.xlsx"
  # MAESTRO_PROVEEDORES.xlsx NO se mirror-ea: esta gitignored (repo publico +
  # IBANs sensibles). git diff-tree no detecta ficheros gitignored, asi que el
  # hook nunca lo veria aunque se anadiera aqui. Sync de MAESTRO sigue manual.
)

CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)

for src_rel in "${!MIRRORS[@]}"; do
  if echo "$CHANGED_FILES" | grep -qFx "$src_rel"; then
    src_abs="$REPO_ROOT/$src_rel"
    tgt_abs="$DRIVE_MAESTRO/${MIRRORS[$src_rel]}"

    if [ ! -d "$DRIVE_MAESTRO" ]; then
      echo "[post-commit] Drive no montado: $DRIVE_MAESTRO - skip mirror de $src_rel" >&2
      continue
    fi

    cp -f "$src_abs" "$tgt_abs"
    echo "[post-commit] mirror OK: $src_rel -> Drive"
  fi
done

# src/facturas/export/excel.py
from __future__ import annotations

import os
from typing import Dict, Iterable
import pandas as pd

# Formato oficial (orden fijo)
COLUMNS_OFFICIAL = [
    "NumeroArchivo",    # XXXX
    "Fecha",            # DD-MM-AA
    "NºFactura",        # tal cual
    "Proveedor",        # normalizado
    "Descripcion",      # texto línea
    "Categoria",        # categoría cerrada
    "BaseImponible",    # '123,45' (coma decimal)
    "TipoIVA",          # 0|4|10|21 (entero o string)
    "Observaciones",    # flags ';' + notas
]


def _ensure_columns_and_order(df: pd.DataFrame) -> pd.DataFrame:
    """Garantiza columnas oficiales, orden y tipos básicos."""
    out = df.copy()

    # Renombrados tolerantes (por si llegan claves en mayúsculas / variantes)
    rename_map = {}
    for c in list(out.columns):
        c_norm = c.strip().lower().replace("_", "")
        if c_norm == "numeroarchivo":
            rename_map[c] = "NumeroArchivo"
        elif c_norm in ("fecha",):
            rename_map[c] = "Fecha"
        elif c_norm in ("nfactura", "nºfactura", "nº factura", "numfactura", "num_factura"):
            rename_map[c] = "NºFactura"
        elif c_norm in ("proveedor", "provider"):
            rename_map[c] = "Proveedor"
        elif c_norm in ("descripcion", "descripción", "articulo", "artículo"):
            rename_map[c] = "Descripcion"
        elif c_norm in ("categoria", "categoría"):
            rename_map[c] = "Categoria"
        elif c_norm in ("base", "baseimponible", "base_imponible"):
            rename_map[c] = "BaseImponible"
        elif c_norm in ("tipoiva", "iva", "tipo_iva"):
            rename_map[c] = "TipoIVA"
        elif c_norm in ("observaciones", "flags"):
            rename_map[c] = "Observaciones"
    if rename_map:
        out = out.rename(columns=rename_map)

    # Asegurar todas las columnas oficiales (si falta, crear vacía)
    for c in COLUMNS_OFFICIAL:
        if c not in out.columns:
            out[c] = ""

    # Forzar tipo string visible (evita NaN en Excel)
    for c in COLUMNS_OFFICIAL:
        out[c] = out[c].astype(str)

    # Ordenar columnas
    out = out[COLUMNS_OFFICIAL]

    return out


def _to_excel(df: pd.DataFrame, xlsx_path: str, metadata: Dict[str, str] | None = None) -> None:
    os.makedirs(os.path.dirname(xlsx_path) or ".", exist_ok=True)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Lineas", index=False)

        # Metadata en hoja separada
        meta_dict = metadata or {}
        meta_items = sorted(meta_dict.items())
        if meta_items:
            df_meta = pd.DataFrame(meta_items, columns=["Clave", "Valor"])
        else:
            df_meta = pd.DataFrame({"Clave": [], "Valor": []})
        df_meta.to_excel(writer, sheet_name="Metadata", index=False)


def exportar_a_excel(df_lineas: pd.DataFrame, xlsx_path: str, *, metadata: Dict[str, str] | None = None, include_es_portes: bool = False) -> None:
    """
    Exporta el DataFrame a Excel cumpliendo el esquema oficial.
    - Incluye SIEMPRE la columna 'Categoria' y el orden definido en COLUMNS_OFFICIAL.
    - 'Observaciones' debe venir ya como string (p.ej. 'AjusteRedondeo;CatAuto:SUBSTR').
    - Mantiene el separador decimal con coma si llega como string.
    """
    df = df_lineas.copy()

    # (Opcional) si no queremos mostrar portes, se espera que ya hayan sido filtrados aguas arriba.
    # Este parámetro se conserva por compatibilidad con la CLI.
    if not include_es_portes and "EsPortes" in df.columns:
        df = df[~(df["EsPortes"].astype(str).str.upper() == "TRUE")]

    df = _ensure_columns_and_order(df)

    # Validaciones mínimas: tipos/valores esperados
    # TipoIVA como entero o string numérico
    df["TipoIVA"] = df["TipoIVA"].str.replace("%", "").str.strip()

    _to_excel(df, xlsx_path, metadata=metadata)


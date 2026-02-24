# src/facturas/parse_lines.py
"""
Parser de líneas de producto con integración opcional de overlays YAML.

Función principal:
    parse_lines_text(texto: str, proveedor: str | None = None) -> list[dict]

Comportamiento:
- Si se pasa `proveedor` y existe un overlay en `patterns/` para él,
  se intenta parsear cada línea con `lines.regex_linea` del YAML.
- Si no hay overlay o la línea no hace match, se usa el parser genérico
  (heurístico) que busca un importe al final y toma el resto como descripción.
- Si el overlay define `portes.keywords`, marca `EsPortes=True` en las líneas
  cuya descripción contenga esas palabras clave.

Salida por línea (dict mínimo):
- Descripcion: str
- BaseImponible: str   (formato europeo, coma decimal)
- EsPortes: bool opcional

Nota: Este módulo NO aplica IVA ni prorratea portes. Eso ocurre en otras fases.
"""
from __future__ import annotations

from typing import List, Dict, Optional
import re

from .patterns_loader import (
    get_overlay_for,
    parse_line_with_overlay,
    mark_is_portes,
)

# ────────────────────────── utilidades numéricas ──────────────────────────
_EU_NUMBER_RX = re.compile(r"^(?P<int>\d{1,3}(?:\.\d{3})*|\d+)[,](?P<dec>\d{2})$")
_SIMPLE_DECIMAL_RX = re.compile(r"^(?P<int>\d+)[.](?P<dec>\d{2})$")
_TAIL_NUMBER_RX = re.compile(r"(?P<num>(\d{1,3}(?:\.\d{3})*,\d{2})|(\d+\.\d{2})|(\d+,\d{2}))\s*$")


def _to_eu_number(s: str) -> str:
    """Convierte '10.00'→'10,00'; deja '1.234,56' tal cual; '10,0'→'10,00'."""
    if not s:
        return ""
    s = s.strip()
    m = _EU_NUMBER_RX.match(s)
    if m:
        # Ya está en EU, asegurar 2 decimales
        return f"{m.group('int')},{m.group('dec')[:2].ljust(2,'0')}"
    m = _SIMPLE_DECIMAL_RX.match(s)
    if m:
        return f"{m.group('int')},{m.group('dec')[:2].ljust(2,'0')}"
    # Último recurso: reemplazar último punto por coma si no hay coma
    if "," not in s and s.count(".") == 1:
        s = s.replace(".", ",")
    # normalizar a 2 decimales si existe coma
    if "," in s:
        parts = s.split(",", 1)
        dec = (parts[1] + "00")[:2]
        s = parts[0] + "," + dec
    return s


# ────────────────────────── parser genérico ──────────────────────────

def _parse_line_generic(line: str) -> Optional[Dict[str, str]]:
    """Heurística: busca un importe al final de la línea y separa.
    Devuelve {'Descripcion','BaseImponible'} o None si no parece línea de producto.
    """
    if not line or not line.strip():
        return None
    line = line.rstrip()

    m = _TAIL_NUMBER_RX.search(line)
    if not m:
        # Aceptamos también líneas sin importe como descripciones sueltas
        desc = line.strip()
        if not desc:
            return None
        return {"Descripcion": desc, "BaseImponible": ""}

    num_raw = m.group("num")
    desc = line[: m.start()].strip()
    base = _to_eu_number(num_raw)

    if not desc and base:
        # Evita devolver líneas que son solo totales sin descripción
        return None

    return {"Descripcion": desc, "BaseImponible": base}


# ────────────────────────── API pública ──────────────────────────

def parse_lines_text(texto: str, proveedor: Optional[str] = None) -> List[Dict[str, str]]:
    """Parsea el bloque de líneas y devuelve una lista de dicts por línea.

    :param texto: bloque de texto donde están las líneas de producto
    :param proveedor: nombre del proveedor (opcional, para overlays)
    """
    rows: List[Dict[str, str]] = []
    if not texto:
        return rows

    ov = get_overlay_for(proveedor or "") if proveedor else None

    for raw in texto.splitlines():
        line = raw.strip()
        if not line:
            continue

        # 1) Intento con overlay
        parsed = parse_line_with_overlay(ov, line) if ov else None
        if parsed:
            row = {"Descripcion": parsed["Descripcion"], "BaseImponible": parsed["BaseImponible"]}
            if mark_is_portes(ov, row["Descripcion"]):
                row["EsPortes"] = True
            rows.append(row)
            continue

        # 2) Fallback genérico
        row = _parse_line_generic(line)
        if not row:
            continue

        if ov and mark_is_portes(ov, row.get("Descripcion", "")):
            row["EsPortes"] = True
        rows.append(row)

    return rows





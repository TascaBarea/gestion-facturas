"""
nucleo/utils.py — Utilidades compartidas entre módulos.
Formateo de moneda, conversión numérica, constantes de meses,
serialización JSON con soporte numpy.
"""

import json
import re
from datetime import date, datetime

import numpy as np
import pandas as pd


# ── Constantes de meses ──────────────────────────────────────────────────────

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

MESES_FULL = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# ── Conversión numérica ─────────────────────────────────────────────────────

def to_float(val) -> float:
    """Convierte a float, soportando formato español ('3,51') y NaN."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return 0.0
    return float(s.replace(",", "."))


def round_safe(n, d=2):
    """Round con fallback a 0."""
    try:
        return round(float(n), d)
    except (TypeError, ValueError):
        return 0.0


# ── Formateo de moneda ───────────────────────────────────────────────────────

def fmt_eur(n, decimals=2) -> str:
    """Formatea número como moneda española: x.xxx,xx €"""
    if decimals == 0:
        s = f"{abs(n):,.0f}"
    else:
        s = f"{abs(n):,.{decimals}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if n < 0 else ''}{s} €"


# ── HTML ─────────────────────────────────────────────────────────────────────

def clean_html(text) -> str:
    """Elimina tags HTML de un string."""
    if not text or pd.isna(text):
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


# ── JSON con soporte numpy ───────────────────────────────────────────────────

class NumpyEncoder(json.JSONEncoder):
    """Convierte tipos numpy a tipos nativos Python para JSON."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def json_dumps(obj) -> str:
    """json.dumps compacto con soporte numpy y unicode."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), cls=NumpyEncoder)


# ── Fechas y períodos ────────────────────────────────────────────────────────

def obtener_trimestre(fecha: date | None = None) -> str:
    """Devuelve '1T25', '2T25', etc. para la fecha dada (o hoy)."""
    if fecha is None:
        fecha = date.today()
    q = (fecha.month - 1) // 3 + 1
    return f"{q}T{fecha.year % 100}"


FORMATOS_FECHA = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%Y%m%d"]


def parse_flexible_date(texto: str) -> datetime | None:
    """Intenta parsear una fecha con múltiples formatos comunes."""
    texto = str(texto).strip()[:20]
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None

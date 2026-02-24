# src/facturas/patterns_loader.py
"""
Capa de overlays por proveedor (patterns/*.yml).
...
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

try:
    from ruamel.yaml import YAML
except Exception:
    YAML = None  # cargaremos solo si hace falta y si está instalado

# ──────────────────────────────── helpers ────────────────────────────────
PATTERNS_DIR = Path(__file__).resolve().parents[1] / "patterns"

def _norm(s: str) -> str:
    s = s or ""
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

@dataclass
class Overlay:
    path: Path
    data: Dict[str, Any]

    def get(self, key: str, default=None):
        return self.data.get(key, default)
def apply_overlay_lines(ov: Optional[Overlay], text: str) -> str:
    """Si el overlay define start_after/stop_before, devuelve solo el bloque de líneas.
    Si no, devuelve el texto original.
    """
    if not ov:
        return text

    lines_cfg = ov.get("lines") or {}
    start_after = lines_cfg.get("start_after")
    stop_before = lines_cfg.get("stop_before")

    if not start_after and not stop_before:
        return text

    t = text
    if start_after and isinstance(start_after, str):
        pos = t.find(start_after)
        if pos >= 0:
            t = t[pos + len(start_after):]
    if stop_before and isinstance(stop_before, str):
        pos = t.find(stop_before)
        if pos >= 0:
            t = t[:pos]
    return t
def parse_line_with_overlay(ov: Optional[Overlay], line: str) -> Optional[Dict[str, str]]:
    """Devuelve un dict {'Descripcion','BaseImponible'} si el overlay define regex_linea y hace match.
    Si no hay overlay o no hay match, devuelve None.
    """
    if not ov:
        return None
    lines_cfg = ov.get("lines") or {}
    rx = lines_cfg.get("regex_linea")
    if not isinstance(rx, str) or not rx.strip():
        return None

    m = re.match(rx, line)
    if not m:
        return None

    desc = (m.groupdict().get("descripcion") or "").strip()
    base = (m.groupdict().get("base") or "").strip()
def mark_is_portes(ov: Optional[Overlay], desc: str) -> bool:
    if not ov:
        return False
    portes = ov.get("portes") or {}
    kws = portes.get("keywords") or []
    d = _norm(desc)
    for kw in kws:
        if _norm(kw) in d:
            return True
    return False

    # Normalización de números según config (decimal/thousands)
    dec, tho = _numbers_cfg(ov)
    base = _normalize_number(base, dec, tho)

    return {"Descripcion": desc, "BaseImponible": base}
def _numbers_cfg(ov: Overlay) -> Tuple[str, str]:
    numbers = ov.get("numbers") or {}
    dec = numbers.get("decimal", ",")
    tho = numbers.get("thousands", ".")
    return dec, tho

def _normalize_number(s: str, decimal: str, thousands: str) -> str:
    """Normaliza el número a formato europeo con coma decimal."""
    if not s:
        return ""
    s = s.strip()
    if thousands:
        s = s.replace(thousands, "")
    if decimal and decimal != ",":
        s = s.replace(decimal, ",")
    if "." in s and "," not in s:
        s = s.replace(".", ",")
    if "," in s:
        intp, frac = s.split(",", 1)
        if len(frac) == 1:
            s = intp + "," + frac + "0"
        elif len(frac) > 2:
            s = intp + "," + frac[:2]
    return s

# ───────────────────────────── API pública ─────────────────────────────

def get_overlay_for(proveedor: str) -> Optional[Overlay]:
    """Primero busca un YAML exacto en patterns/ como BM.yml.
    Si no lo encuentra, intenta por provider o alias como antes.
    """
    prov_n = _norm(proveedor)
    if not prov_n:
        return None

    # Intento directo por nombre de archivo (más rápido y explícito)
    direct_path = PATTERNS_DIR / f"{prov_n}.yml"
    if direct_path.exists():
        try:
            data = _load_yaml(direct_path)
            return Overlay(path=direct_path, data=data)
        except Exception:
            pass  # continúa con la búsqueda por alias si el YAML falla

    # Búsqueda por aliases como fallback
    if not PATTERNS_DIR.exists():
        return None

    yml_files = sorted(PATTERNS_DIR.glob("*.yml"))
    for y in yml_files:
        try:
            ov = _load_yaml(y)
        except Exception:
            continue
        provider = _norm(ov.get("provider", ""))
        aliases = [_norm(a) for a in (ov.get("aliases") or []) if isinstance(a, str)]
        keys = [k for k in [provider, *aliases] if k]
        if any(k in prov_n or prov_n in k for k in keys):
            return Overlay(path=y, data=ov)
    return None

def apply_overlay_header(ov: Optional[Overlay], text: str) -> Tuple[Optional[str], Optional[str]]:
    ...
# El resto del archivo se mantiene igual.

# src/facturas/patterns_loader.py
"""
Capa de overlays por proveedor (patterns/*.yml).

Objetivo:
- Cargar el YAML del proveedor (ALCAMPO.yml, CERES.yml, BM.yml, ...)
- Extraer cabecera (fecha, ref) según regex del YAML
- Recortar bloque de líneas con tolerancia (start_after / stop_before)
- Parsear líneas con regex_linea o fallback genérico (último importe)
- Marcar PORTES por keywords
- Normalizar números según configuración (decimal / thousands)

Notas de robustez:
- PATTERNS_DIR resuelto a <repo>/patterns (parents[2]) con fallback a <repo>/src/patterns
- Búsqueda de overlay por nombre de archivo y por provider/aliases
- Recorte de líneas admite literales o lista de literales y normaliza texto (acentos, NBSP, mayúsculas, espacios)
- parse_line_with_overlay tolera columnas intermedias y usa fallback si no hay regex_linea
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import re
import unicodedata

try:
    from ruamel.yaml import YAML
except Exception:  # pragma: no cover
    YAML = None  # Se requiere ruamel.yaml en tiempo de ejecución

# ──────────────────────────────── helpers ────────────────────────────────
# Intentamos resolver <repo>/patterns primero
_THIS = Path(__file__).resolve()
_CANDIDATES = [
    _THIS.parents[2] / "patterns",  # <repo>/patterns
    _THIS.parents[1] / "patterns",  # <repo>/src/patterns (fallback)
]
for _p in _CANDIDATES:
    if _p.exists():
        PATTERNS_DIR = _p
        break
else:
    PATTERNS_DIR = _CANDIDATES[0]  # por defecto a la raíz


def _norm(s: str) -> str:
    s = s or ""
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_text_for_find(s: str, *, casefold=True, strip_nbsp=True, collapse_ws=True, remove_accents=True) -> str:
    if s is None:
        return ""
    # Unicode normalize
    s = unicodedata.normalize("NFKC", s)
    if strip_nbsp:
        s = s.replace("\u00A0", " ")
    if remove_accents:
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    if casefold:
        s = s.upper()
    if collapse_ws:
        s = re.sub(r"\s+", " ", s).strip()
    return s


def _find_any(text: str, needles):
    """Devuelve (pos, match_len) del primer literal encontrado en text; (-1,0) si no hay match."""
    if isinstance(needles, str):
        needles = [needles]
    for n in needles or []:
        if not n:
            continue
        pos = text.find(n)
        if pos >= 0:
            return pos, len(n)
    return -1, 0


@dataclass
class Overlay:
    path: Path
    data: Dict[str, Any]

    def get(self, key: str, default=None):
        return self.data.get(key, default)


# ───────────────────────────── API pública ─────────────────────────────

def get_overlay_for(proveedor: str) -> Optional[Overlay]:
    """Busca el overlay YAML en patterns/.

    Estrategia:
      1) Intento directo por nombre de archivo: <PROVEEDOR_NORMALIZADO>.yml
      2) Si no existe, abrir cada YAML y comparar `provider` y `aliases`.
    """
    prov_n = _norm(proveedor)
    if not prov_n:
        return None

    # 1) Coincidencia directa por nombre de archivo
    direct_path = PATTERNS_DIR / f"{prov_n}.yml"
    if direct_path.exists():
        data = _load_yaml(direct_path)
        return Overlay(path=direct_path, data=data)

    # 2) Búsqueda por metadatos
    if not PATTERNS_DIR.exists():
        return None

    for y in sorted(PATTERNS_DIR.glob("*.yml")):
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
    """Usa regex del overlay para extraer fecha y referencia si están definidas.
    Devuelve (fecha_DD-MM-YY, ref) o (None, None) si no aplica.
    """
    if not ov:
        return None, None
    date_cfg = ov.get("date") or {}
    ref_cfg = ov.get("ref") or {}

    fecha, ref = None, None

    # fecha
    rx = (date_cfg or {}).get("regex")
    if isinstance(rx, str) and rx.strip():
        m = re.search(rx, text)
        if m:
            # normalizamos a DD-MM-YY si es posible
            try:
                d, mth, y = m.group(1), m.group(2), m.group(3)
                y_i = int(y)
                if y_i > 1999:
                    y_i = y_i % 100
                fecha = f"{int(d):02d}-{int(mth):02d}-{y_i:02d}"
            except Exception:
                # si el grupo no coincide a 3 capturas, devolver crudo
                fecha = m.group(0)

    # referencia
    rxr = (ref_cfg or {}).get("regex")
    if isinstance(rxr, str) and rxr.strip():
        mr = re.search(rxr, text)
        if mr:
            ref = mr.group(1) if mr.groups() else mr.group(0)
            ref = ref.strip(" .,#;")

    return fecha, ref


def apply_overlay_lines(ov: Optional[Overlay], text: str) -> str:
    """Recorta bloque de líneas con tolerancia: admite lista de marcadores y normalización previa."""
    if not ov:
        return text

    lines_cfg = ov.get("lines") or {}
    start_after = lines_cfg.get("start_after")
    stop_before = lines_cfg.get("stop_before")

    norm_cfg = (lines_cfg.get("normalize") or {})
    flags = {
        "casefold": norm_cfg.get("casefold", True),
        "strip_nbsp": norm_cfg.get("strip_nbsp", True),
        "collapse_ws": norm_cfg.get("collapse_ws", True),
        "remove_accents": norm_cfg.get("remove_accents", True),
    }

    # Texto original para recortar al final; buscamos sobre versión normalizada
    t_raw = text or ""
    t_norm = _normalize_text_for_find(t_raw, **flags)

    def _norm_needles(v):
        if isinstance(v, str):
            return [_normalize_text_for_find(v, **flags)]
        return [_normalize_text_for_find(x, **flags) for x in (v or [])]

    start_needles = _norm_needles(start_after)
    stop_needles = _norm_needles(stop_before)

    # Recorte por start_after
    if start_needles:
        pos, mlen = _find_any(t_norm, start_needles)
        if pos >= 0:
            # Fallback: intenta recorte literal sobre texto sin normalizar
            cut_done = False
            for s in (start_after if isinstance(start_after, list) else [start_after]):
                if not s:
                    continue
                p2 = t_raw.find(s)
                if p2 >= 0:
                    t_raw = t_raw[p2 + len(s):]
                    cut_done = True
                    break
            if not cut_done:
                t_raw = t_raw[pos + mlen:]
            t_norm = _normalize_text_for_find(t_raw, **flags)

    # Recorte por stop_before
    if stop_needles:
        pos, _ = _find_any(t_norm, stop_needles)
        if pos >= 0:
            cut_done = False
            for s in (stop_before if isinstance(stop_before, list) else [stop_before]):
                if not s:
                    continue
                p2 = t_raw.find(s)
                if p2 >= 0:
                    t_raw = t_raw[:p2]
                    cut_done = True
                    break
            if not cut_done:
                t_raw = t_raw[:pos]

    return t_raw


def parse_line_with_overlay(ov: Optional[Overlay], line: str) -> Optional[Dict[str, str]]:
    """Devuelve {'Descripcion','BaseImponible'} si match; None si no hay match.
    Usa regex_linea si está definida; si no, fallback al último importe de la línea.
    """
    if not ov:
        return None
    lines_cfg = ov.get("lines") or {}
    rx = lines_cfg.get("regex_linea")
    if not isinstance(rx, str) or not rx.strip():
        # Fallback: último importe de la línea con coma decimal, tolerando columnas intermedias
        rx = r"^(?P<descripcion>.+?)\s+(?:\S+\s+){0,8}?(?P<base>\d{1,3}(?:\.\d{3})*,\d{2})$"

    # Ignorar cabeceras/subtotales por keywords
    ignore = (lines_cfg.get("ignore_if_contains") or [])
    if any(k for k in ignore if k and k.upper() in (line or "").upper()):
        return None

    m = re.match(rx, line)
    if not m:
        return None

    desc = (m.groupdict().get("descripcion") or "").strip()
    base = (m.groupdict().get("base") or "").strip()

    dec, tho = _numbers_cfg(ov)
    base = _normalize_number(base, dec, tho)
    return {"Descripcion": desc, "BaseImponible": base}


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


# ────────────────────────────── internos ───────────────────────────────

def _load_yaml(path: Path) -> Dict[str, Any]:
    if YAML is None:
        raise RuntimeError("ruamel.yaml no está instalado. Ejecuta: pip install ruamel.yaml")
    y = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as fh:
        return y.load(fh) or {}


def _numbers_cfg(ov: Overlay) -> Tuple[str, str]:
    numbers = ov.get("numbers") or {}
    dec = numbers.get("decimal", ",")
    tho = numbers.get("thousands", ".")
    return dec, tho


def _normalize_number(s: str, decimal: str, thousands: str) -> str:
    """Normaliza a formato europeo con coma decimal."""
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

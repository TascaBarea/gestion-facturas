# src/facturas/categorias.py (con soporte CUALQUIERA y JSON compilado)
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import unicodedata
import re
import os
import json
import pandas as pd
from difflib import SequenceMatcher
from pathlib import Path

DEFAULT_DICT_FILENAME = "DiccionarioProveedoresCategoria.xlsx"
DEFAULT_FIXED_PATH = r"C:\\_ARCHIVOS\\TRABAJO\\Facturas\\DiccionarioProveedoresCategoria.xlsx"
DEFAULT_COMPILED = Path(__file__).with_name("diccionario_compilado.json")

# ───────────────────────── utilidades de normalización ─────────────────────────
def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def _norm_basic(s: str) -> str:
    s = _strip_accents(s).upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

_NORMALIZE_UNITS = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:KG|KGS|G|GR|GRS|L|ML|CL)\b")
_NORMALIZE_PERC = re.compile(r"\b\d{1,3}\s?%")
_NORMALIZE_CODES = re.compile(r"\b\d{3,}\b")
_NON_ALNUM = re.compile(r"[^A-Z0-9 ]+")
_MULTI_SPACE = re.compile(r"\s+")

_CONECTORES_MAP = {"C/": "CON", "C\\": "CON", "C.": "CON"}


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = _strip_accents(str(s).upper())
    for k, v in _CONECTORES_MAP.items():
        s = s.replace(k, v)
    s = _NORMALIZE_UNITS.sub(" ", s)
    s = _NORMALIZE_PERC.sub(" ", s)
    s = _NORMALIZE_CODES.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s


def token_set_contains(haystack_norm: str, needle_norm: str) -> bool:
    if not haystack_norm or not needle_norm:
        return False
    H = set(haystack_norm.split())
    N = [t for t in needle_norm.split() if t]
    return all(t in H for t in N)

# ───────────────────────────── modelo de regla ─────────────────────────────
@dataclass
class ReglaCategoria:
    proveedor: str
    patron: str
    categoria: str
    tipo: str = "SUBSTR"

    def match(self, proveedor: str, descripcion: str) -> Tuple[bool, Optional[str]]:
        prov_ok = (self.proveedor == "*") or (self.proveedor in proveedor)
        if not prov_ok:
            return False, None
        if self.tipo == "REGEX":
            ok = re.search(self.patron, descripcion or "", flags=re.IGNORECASE) is not None
            return ok, ("REGEX" if ok else None)
        pat_norm = normalize_text(self.patron)
        desc_norm = normalize_text(descripcion or "")
        if self.tipo == "EXACT":
            ok = (pat_norm == desc_norm)
            return ok, ("EXACT_NORM" if ok else None)
        if pat_norm and pat_norm in desc_norm:
            return True, "SUBSTR_NORM"
        if token_set_contains(desc_norm, pat_norm):
            return True, "TOKSET"
        return False, None

# ────────────────────────── cargador / matcher principal ──────────────────────────
class CategoriaMatcher:
    def __init__(self, reglas: List[ReglaCategoria]):
        self.reglas = reglas

    @classmethod
    def from_default(cls) -> "CategoriaMatcher":
        env_path = os.getenv("FACTURAS_DICT")
        if env_path and env_path.lower().endswith(".json") and os.path.exists(env_path):
            return cls.from_compiled_json(env_path)
        if env_path and env_path.lower().endswith((".xls", ".xlsx")) and os.path.exists(env_path):
            return cls.from_excel(env_path)
        if DEFAULT_COMPILED.exists():
            return cls.from_compiled_json(str(DEFAULT_COMPILED))
        excel = Path.cwd() / DEFAULT_DICT_FILENAME
        if excel.exists():
            return cls.from_excel(str(excel))
        raise FileNotFoundError("No se encontró el diccionario (ni JSON compilado ni Excel).")

    @classmethod
    def from_excel(cls, path: str) -> "CategoriaMatcher":
        df = pd.read_excel(path, sheet_name=0)
        cols = {_strip_accents(str(c)).lower().strip(): c for c in df.columns}

        def pick(*candidates: str) -> Optional[str]:
            for cand in candidates:
                key = _strip_accents(cand).lower().strip()
                if key in cols:
                    return cols[key]
            return None

        proveedor_col = pick("proveedor", "provider")
        patron_col    = pick("articulo", "artículo", "patron", "patrón", "pattern", "regex", "palabra", "keyword")
        categoria_col = pick("categoria", "categoría", "category")
        tipo_col      = pick("tipo", "tipomatch", "match")

        if not (proveedor_col and patron_col and categoria_col):
            raise KeyError("Faltan columnas obligatorias en el Excel (PROVEEDOR/ARTICULO/CATEGORIA)")

        reglas: List[ReglaCategoria] = []
        for _, row in df.iterrows():
            prov_raw = row.get(proveedor_col, "") if proveedor_col else ""
            patron   = str(row.get(patron_col, "") or "").strip()
            cat      = str(row.get(categoria_col, "") or "").strip()
            if not patron or not cat:
                continue
            tipo_val = (str(row.get(tipo_col, "") or "SUBSTR").strip().upper() if tipo_col else "SUBSTR")
            tipo     = tipo_val if tipo_val in {"SUBSTR", "EXACT", "REGEX"} else "SUBSTR"

            prov_n   = _norm_basic(prov_raw) or "*"
            if prov_n == "CUALQUIERA":
                prov_n = "*"
            reglas.append(ReglaCategoria(proveedor=prov_n, patron=patron, categoria=cat, tipo=tipo))
        return cls(reglas)

    @classmethod
    def from_compiled_json(cls, path: str) -> "CategoriaMatcher":
        data = json.load(open(path, encoding="utf-8"))
        reglas = [ReglaCategoria(**r) for r in data["rules"]]
        return cls(reglas)

    def _rules_for(self, proveedor: str) -> List[ReglaCategoria]:
        prov_n = _norm_basic(proveedor)
        WILDCARDS = {"*", "CUALQUIERA"}
        return [r for r in self.reglas if r.proveedor in WILDCARDS or r.proveedor == prov_n]

    def match(self, proveedor: str, descripcion: str) -> Tuple[Optional[str], Optional[str]]:
        prov_n_basic = _norm_basic(proveedor)
        desc_raw = descripcion or ""
        for r in self._rules_for(proveedor):
            if r.tipo == "EXACT":
                ok, why = r.match(prov_n_basic, desc_raw)
                if ok:
                    return r.categoria, f"CatAuto:{why}"
        for r in self._rules_for(proveedor):
            if r.tipo == "SUBSTR":
                ok, why = r.match(prov_n_basic, desc_raw)
                if ok:
                    return r.categoria, f"CatAuto:{why}"
        for r in self._rules_for(proveedor):
            if r.tipo == "REGEX":
                ok, why = r.match(prov_n_basic, desc_raw)
                if ok:
                    return r.categoria, f"CatAuto:{why}"
        desc_norm = normalize_text(desc_raw)
        candidates = self._rules_for(proveedor)
        best_cat, best_score = None, 0.0
        for r in candidates:
            if r.tipo == "REGEX":
                continue
            score = SequenceMatcher(None, normalize_text(r.patron), desc_norm).ratio()
            if score > best_score:
                best_cat, best_score = r.categoria, score
        if best_cat and best_score >= 0.95:
            return best_cat, f"CatAuto:FUZZY({best_score:.2f})"
        return None, None

# ───────────────────────── búsqueda del Excel ─────────────────────────
def _resolve_default_dict_path() -> str | None:
    candidates: List[str] = []
    env_path = os.environ.get("FACTURAS_DICT")
    if env_path:
        candidates.append(env_path)
    candidates.append(DEFAULT_FIXED_PATH)
    candidates.append(os.path.join(os.getcwd(), DEFAULT_DICT_FILENAME))
    here = os.path.abspath(os.path.dirname(__file__))
    candidates.append(os.path.join(here, DEFAULT_DICT_FILENAME))
    candidates.append(os.path.join(os.path.dirname(here), DEFAULT_DICT_FILENAME))
    for p in candidates:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    return None

__all__ = ["CategoriaMatcher", "ReglaCategoria", "normalize_text", "token_set_contains"]




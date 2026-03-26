"""
Tests para nucleo/utils.py — funciones compartidas entre módulos.
"""

import json
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from nucleo.utils import (
    to_float, round_safe, fmt_eur, clean_html,
    NumpyEncoder, json_dumps, obtener_trimestre, parse_flexible_date,
    MESES, MESES_FULL,
)


# ── to_float ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestToFloat:

    def test_int(self):
        assert to_float(42) == 42.0

    def test_float(self):
        assert to_float(3.14) == 3.14

    def test_string_punto(self):
        assert to_float("12.50") == 12.5

    def test_string_coma_espanola(self):
        assert to_float("3,51") == 3.51

    def test_string_con_espacios(self):
        assert to_float("  7,25  ") == 7.25

    def test_string_vacio(self):
        assert to_float("") == 0.0

    def test_none(self):
        assert to_float(None) == 0.0

    def test_nan(self):
        assert to_float(float("nan")) == 0.0

    def test_pd_nat(self):
        assert to_float(pd.NaT) == 0.0

    def test_numpy_int(self):
        assert to_float(np.int64(100)) == 100.0

    def test_numpy_float(self):
        assert to_float(np.float64(9.99)) == 9.99


# ── round_safe ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRoundSafe:

    def test_normal(self):
        assert round_safe(3.14159, 2) == 3.14

    def test_none(self):
        assert round_safe(None) == 0.0

    def test_string_invalido(self):
        assert round_safe("abc") == 0.0

    def test_zero_decimals(self):
        assert round_safe(9.7, 0) == 10.0


# ── fmt_eur ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFmtEur:

    def test_formato_basico(self):
        assert fmt_eur(1234.56) == "1.234,56 €"

    def test_cero(self):
        assert fmt_eur(0) == "0,00 €"

    def test_sin_decimales(self):
        assert fmt_eur(1234.56, decimals=0) == "1.235 €"

    def test_grande(self):
        assert fmt_eur(1234567.89) == "1.234.567,89 €"

    def test_negativo(self):
        assert fmt_eur(-500.00) == "-500,00 €"

    def test_pequeno(self):
        assert fmt_eur(0.99) == "0,99 €"

    def test_miles_exactos(self):
        assert fmt_eur(1000, decimals=0) == "1.000 €"


# ── clean_html ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestCleanHtml:

    def test_sin_html(self):
        assert clean_html("texto plano") == "texto plano"

    def test_con_tags(self):
        assert clean_html("<b>negrita</b>") == "negrita"

    def test_none(self):
        assert clean_html(None) == ""

    def test_nan(self):
        assert clean_html(float("nan")) == ""

    def test_nested_tags(self):
        assert clean_html("<div><p>hola</p></div>") == "hola"


# ── NumpyEncoder ─────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestNumpyEncoder:

    def test_numpy_int(self):
        assert json.dumps({"n": np.int64(42)}, cls=NumpyEncoder) == '{"n": 42}'

    def test_numpy_float(self):
        result = json.loads(json.dumps({"n": np.float64(3.14)}, cls=NumpyEncoder))
        assert abs(result["n"] - 3.14) < 0.001

    def test_numpy_array(self):
        result = json.loads(json.dumps({"arr": np.array([1, 2, 3])}, cls=NumpyEncoder))
        assert result["arr"] == [1, 2, 3]


# ── json_dumps ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestJsonDumps:

    def test_compacto(self):
        result = json_dumps({"a": 1, "b": 2})
        assert " " not in result  # separadores compactos

    def test_unicode(self):
        result = json_dumps({"nombre": "café"})
        assert "café" in result  # no escapa unicode


# ── obtener_trimestre ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestObtenerTrimestre:

    def test_enero(self):
        assert obtener_trimestre(date(2026, 1, 15)) == "1T26"

    def test_abril(self):
        assert obtener_trimestre(date(2026, 4, 1)) == "2T26"

    def test_julio(self):
        assert obtener_trimestre(date(2026, 7, 31)) == "3T26"

    def test_diciembre(self):
        assert obtener_trimestre(date(2026, 12, 25)) == "4T26"

    def test_none_usa_hoy(self):
        result = obtener_trimestre()
        assert result  # No vacío


# ── parse_flexible_date ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestParseFlexibleDate:

    def test_dd_mm_yyyy_slash(self):
        dt = parse_flexible_date("15/03/2026")
        assert dt == datetime(2026, 3, 15)

    def test_dd_mm_yyyy_dash(self):
        dt = parse_flexible_date("15-03-2026")
        assert dt == datetime(2026, 3, 15)

    def test_yyyy_mm_dd(self):
        dt = parse_flexible_date("2026-03-15")
        assert dt == datetime(2026, 3, 15)

    def test_dd_mm_yy(self):
        dt = parse_flexible_date("15/03/26")
        assert dt == datetime(2026, 3, 15)

    def test_yyyymmdd(self):
        dt = parse_flexible_date("20260315")
        assert dt == datetime(2026, 3, 15)

    def test_invalido(self):
        assert parse_flexible_date("no es fecha") is None

    def test_vacio(self):
        assert parse_flexible_date("") is None

    def test_con_espacios(self):
        dt = parse_flexible_date("  15/03/2026  ")
        assert dt == datetime(2026, 3, 15)


# ── Constantes ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestConstantes:

    def test_meses_12(self):
        assert len(MESES) == 12

    def test_meses_full_12(self):
        assert len(MESES_FULL) == 12

    def test_enero(self):
        assert MESES[0] == "Ene"
        assert MESES_FULL[0] == "Enero"

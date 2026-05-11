"""
Tests sinteticos para scripts/auditoria_iva_mixto.py.

Casos cubiertos:
- Proveedor IVA uniforme sin keyword     -> SIN
- Proveedor IVA mixto intra-factura + descuadre -> ALTO
- Proveedor IVA mixto inter-factura + descuadre (caso PANRUJE 2T26) -> ALTO
- Proveedor IVA mixto sin descuadre sin keyword -> MEDIO
- Proveedor con keyword pero IVA uniforme -> BAJO
"""
from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pytest

from scripts.auditoria_iva_mixto import (
    KEYWORDS_DEFAULT,
    analizar_excel,
    calcular_nivel,
    construir_filas,
    es_id_dudosa,
    merge_resultados,
)


def _crear_excel(path: Path, rows: list[dict]) -> None:
    """Crea un Excel con hoja Lineas a partir de rows (lista de dicts)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lineas"
    headers = ["#", "FECHA", "REF", "PROVEEDOR", "ARTICULO", "CATEGORIA",
               "CANTIDAD", "PRECIO_UD", "TIPO IVA", "BASE", "CUOTA IVA",
               "TOTAL FAC", "CUADRE", "ARCHIVO", "EXTRACTOR"]
    ws.append(headers)
    for i, r in enumerate(rows, start=1):
        ws.append([
            i, "01/01/2026", "REF1", r["proveedor"], r.get("articulo", "PRODUCTO"),
            "CAT", 1, 10, r["iva"], 10, r["iva"] * 0.1, 11,
            r.get("cuadre", "OK"), r["archivo"], "extractor_test",
        ])
    wb.create_sheet("Facturas")
    wb.save(path)


@pytest.fixture()
def pattern():
    return re.compile("|".join(re.escape(k) for k in KEYWORDS_DEFAULT), re.IGNORECASE)


def test_iva_uniforme_sin_keyword_es_SIN(temp_dir, pattern):
    path = Path(temp_dir) / "a.xlsx"
    _crear_excel(path, [
        {"proveedor": "PROVA", "iva": 21, "archivo": "f1.pdf"},
        {"proveedor": "PROVA", "iva": 21, "archivo": "f2.pdf"},
    ])
    rec = analizar_excel(path, "TT", pattern)
    assert calcular_nivel(rec["PROVA"]) == "SIN"


def test_iva_mixto_intra_con_descuadre_es_ALTO(temp_dir, pattern):
    path = Path(temp_dir) / "b.xlsx"
    _crear_excel(path, [
        {"proveedor": "PROVB", "iva": 4, "archivo": "fa.pdf", "articulo": "ROSQUILLAS"},
        {"proveedor": "PROVB", "iva": 21, "archivo": "fa.pdf",
         "articulo": "PORTES", "cuadre": "DESCUADRE_1.5"},
    ])
    rec = analizar_excel(path, "TT", pattern)
    assert calcular_nivel(rec["PROVB"]) == "ALTO"


def test_iva_mixto_inter_con_descuadre_es_ALTO_caso_panruje(temp_dir, pattern):
    """Caso PANRUJE 2T26: cada factura tiene 1 sola linea pero los IVAs entre
    facturas distintas del mismo proveedor difieren, y ambas descuadran."""
    path = Path(temp_dir) / "c.xlsx"
    _crear_excel(path, [
        {"proveedor": "PANRUJE", "iva": 4, "archivo": "panruje_a.pdf",
         "articulo": "CAJAS DE ROSQUILLAS NORMALES + PORTES", "cuadre": "DESCUADRE_12.60"},
        {"proveedor": "PANRUJE", "iva": 21, "archivo": "panruje_b.pdf",
         "articulo": "CAJAS DE ROSQUILLAS NORMALES + PORTES", "cuadre": "DESCUADRE_68.64"},
    ])
    rec = analizar_excel(path, "TT", pattern)
    assert calcular_nivel(rec["PANRUJE"]) == "ALTO"
    filas = construir_filas({"PANRUJE": rec["PANRUJE"]})
    fila = filas[0]
    assert fila["HAS_IVAS_DISTINTOS_ENTRE_FACTURAS"] is True
    assert fila["HAS_FACTURA_IVA_MIXTO"] is False
    assert fila["N_FACTURAS_CON_DESCUADRE"] == 2


def test_iva_mixto_sin_descuadre_sin_keyword_es_MEDIO(temp_dir, pattern):
    path = Path(temp_dir) / "d.xlsx"
    _crear_excel(path, [
        {"proveedor": "PROVD", "iva": 4, "archivo": "fd.pdf", "articulo": "QUESO"},
        {"proveedor": "PROVD", "iva": 21, "archivo": "fd.pdf", "articulo": "OTRA COSA"},
    ])
    rec = analizar_excel(path, "TT", pattern)
    assert calcular_nivel(rec["PROVD"]) == "MEDIO"


def test_keyword_iva_uniforme_es_BAJO(temp_dir, pattern):
    path = Path(temp_dir) / "e.xlsx"
    _crear_excel(path, [
        {"proveedor": "PROVE", "iva": 21, "archivo": "fe.pdf",
         "articulo": "PRODUCTO X + PORTES"},
        {"proveedor": "PROVE", "iva": 21, "archivo": "fe2.pdf",
         "articulo": "PRODUCTO Y"},
    ])
    rec = analizar_excel(path, "TT", pattern)
    assert calcular_nivel(rec["PROVE"]) == "BAJO"


@pytest.mark.parametrize("nombre", [
    "1T25 0112 JIMELUZ",
    "ATRASADA 1T25 0328 CERES",
    "Garda TR PAGADA diferencia 217,15",
    "2T25 0501 BENJAMIN ORTEGA  OJO RET",
    "FACTURA 12345678",
    "T26 0408 PANRUJE",
])
def test_es_id_dudosa_marca_filenames(nombre):
    assert es_id_dudosa(nombre) is True


@pytest.mark.parametrize("nombre", [
    "PANRUJE SL",
    "CERES",
    "CERES CERVEZA SL",
    "BM SUPERMERCADOS",
    "DISTRIBUCIONES LAVAPIES S.COOP.MAD",
    "ORTEGA ALONSO BENJAMIN",
    "MERCADONA",
])
def test_es_id_dudosa_acepta_legitimos(nombre):
    assert es_id_dudosa(nombre) is False


def test_merge_resultados_combina_trimestres(temp_dir, pattern):
    """Verifica que merge_resultados acumula correctamente entre trimestres."""
    path1 = Path(temp_dir) / "q1.xlsx"
    path2 = Path(temp_dir) / "q2.xlsx"
    _crear_excel(path1, [
        {"proveedor": "PROVX", "iva": 4, "archivo": "x1.pdf"},
    ])
    _crear_excel(path2, [
        {"proveedor": "PROVX", "iva": 21, "archivo": "x2.pdf",
         "cuadre": "DESCUADRE_5"},
    ])
    r1 = analizar_excel(path1, "1T26", pattern)
    r2 = analizar_excel(path2, "2T26", pattern)
    merged = merge_resultados([("1T26", r1), ("2T26", r2)])
    # PROVX tiene 2 facturas, 2 IVAs distintos inter, 1 descuadre -> ALTO
    assert calcular_nivel(merged["PROVX"]) == "ALTO"
    assert merged["PROVX"].trimestres == {"1T26", "2T26"}

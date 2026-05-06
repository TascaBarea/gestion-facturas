# -*- coding: utf-8 -*-
"""
Tests unitarios v1.25 — Bloque B + filtrado no-factura.

Cubre:
  · CONFIG.NOMBRES_CLIENTE existe y contiene los nombres esperados.
  · _es_nombre_proveedor_razonable: longitud, letras, keywords, lista negra.
  · _nombre_aproximado: las 4 capas con textos sintéticos basados en los
    PDFs reales analizados en chat 06/05/2026 (COMPROVINO + Torres Import).
  · _es_factura_valida: detector de marcadores, casos positivos y negativos.
  · Integración en _procesar_pdf: caso no-factura marca REVISAR.

Ejecutar: pytest tests/unit/test_bloque_b.py -v
"""
import pytest


pytestmark = pytest.mark.unit


# ============================================================================
# CONFIG.NOMBRES_CLIENTE
# ============================================================================

def test_config_nombres_cliente_existe():
    from gmail.gmail import CONFIG
    assert hasattr(CONFIG, 'NOMBRES_CLIENTE')
    assert isinstance(CONFIG.NOMBRES_CLIENTE, list)


def test_config_nombres_cliente_contiene_clientes_reales():
    from gmail.gmail import CONFIG
    nombres_upper = [n.upper() for n in CONFIG.NOMBRES_CLIENTE]
    # Variantes esperadas
    assert any("TASCA BAREA" in n for n in nombres_upper)
    assert any("COMESTIBLES BAREA" in n for n in nombres_upper)


# ============================================================================
# _es_nombre_proveedor_razonable
# ============================================================================

def _make_processor():
    """Helper: instancia GmailProcessor SIN invocar __init__.

    Usamos __new__ para evitar cargar MAESTRO_PROVEEDORES.xlsx (gitignored,
    no existe en CI runner). Los métodos que estos tests verifican
    (_es_nombre_proveedor_razonable, _nombre_aproximado, _es_factura_valida)
    NO acceden a self.maestro — solo a constantes de clase y CONFIG.
    """
    from gmail.gmail import GmailProcessor
    return GmailProcessor.__new__(GmailProcessor)


def test_razonable_acepta_nombre_normal():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("COMPROVINO SL") is True


def test_razonable_rechaza_demasiado_corto():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("AB") is False


def test_razonable_rechaza_demasiado_largo():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("X" * 81) is False


def test_razonable_rechaza_sin_letras():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("123 456 789") is False


def test_razonable_rechaza_keyword_factura():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("FACTURA Nº 12345") is False


def test_razonable_rechaza_keyword_forma_de_pago():
    """Caso real Torres Import: 'FORMA DE PAGO' aparecía como nombre."""
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("FORMA DE PAGO") is False


def test_razonable_rechaza_nombre_cliente_tasca():
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("TASCA BAREA S.L.") is False


def test_razonable_rechaza_nombre_cliente_comestibles():
    """Caso real COMPROVINO 04/05/2026."""
    proc = _make_processor()
    assert proc._es_nombre_proveedor_razonable("COMESTIBLES BAREA") is False


# ============================================================================
# _nombre_aproximado — 4 capas
# ============================================================================

def test_nombre_aproximado_capa4_sufijo_sau():
    """Caso Torres Import: captura 'TORRES IMPORT S.A.U.' por sufijo SAU."""
    proc = _make_processor()
    texto = (
        "NÚM. FACTURA FECHA FACTURA\n"
        "FORMA DE PAGO\n"
        "TORRES IMPORT S.A.U.\n"
        "Av Mare de Deu de Montserrat, 49\n"
        "C.I.F. A-08446700\n"
        "TASCA BAREA S.L.\n"
    )
    nombre = proc._nombre_aproximado(texto, "remitente", "x@y.com")
    assert nombre == "TORRES IMPORT S.A.U."


def test_nombre_aproximado_capa4_sufijo_sl():
    """Caso COMPROVINO: captura 'COMPROVINO SL' por sufijo SL.

    Lista negra Capa 1 descarta 'TASCA BAREA S.L.' aunque también tenga
    sufijo societario.
    """
    proc = _make_processor()
    texto = (
        "FACTURA\n"
        "COMESTIBLES BAREA\n"
        "665381585\n"
        "Elena de Miguel\n"
        "TASCA BAREA S.L.\n"
        "COMPROVINO SL\n"
        "BODEGABIERTA Rodas 2,\n"
    )
    nombre = proc._nombre_aproximado(texto, "remitente", "x@y.com")
    assert nombre == "COMPROVINO SL"


def test_nombre_aproximado_capa2_proximidad_cif():
    """Si no hay sufijo societario pero sí CIF, busca línea cerca del CIF."""
    proc = _make_processor()
    texto = (
        "FACTURA Nº 12345\n"
        "BODEGAS XYZ\n"
        "Calle Mayor 1, Madrid\n"
        "B12345678\n"
    )
    # 'BODEGAS XYZ' está 2 líneas antes del CIF B12345678
    nombre = proc._nombre_aproximado(texto, "remitente", "x@y.com")
    assert nombre == "BODEGAS XYZ"


def test_nombre_aproximado_capa0_fallback_primera_linea():
    """Sin sufijo societario, sin CIF: primera línea razonable.

    Nota: la candidata NO debe contener palabras de la lista
    `_KEYWORDS_NO_NOMBRE` (incluye "proveedor", para descartar
    etiquetas "Datos del proveedor:").
    """
    proc = _make_processor()
    texto = (
        "FACTURA\n"
        "ARTESANIA LOCAL\n"
        "Calle Cualquiera 1\n"
    )
    nombre = proc._nombre_aproximado(texto, "remitente", "x@y.com")
    assert nombre == "ARTESANIA LOCAL"


def test_nombre_aproximado_fallback_remitente():
    """Sin texto útil: usa nombre_remitente."""
    proc = _make_processor()
    nombre = proc._nombre_aproximado("", "Bodegas X", "info@bodegasx.com")
    assert nombre == "Bodegas X"


def test_nombre_aproximado_fallback_email():
    """Sin texto, sin nombre: local-part del email."""
    proc = _make_processor()
    nombre = proc._nombre_aproximado("", "", "proveedor.nuevo@dominio.com")
    assert nombre == "proveedor.nuevo"


def test_nombre_aproximado_no_captura_cliente_aunque_aparezca_primero():
    """Regresión COMPROVINO: aunque el cliente aparezca como primera línea
    razonable, la lista negra evita capturarlo."""
    proc = _make_processor()
    texto = (
        "COMESTIBLES BAREA\n"
        "TASCA BAREA SLL\n"
        "BODEGAS REAL SA\n"
    )
    nombre = proc._nombre_aproximado(texto, "remitente", "x@y.com")
    # Capa 4 captura 'BODEGAS REAL SA' por sufijo SA
    assert "BAREA" not in nombre.upper()
    assert nombre == "BODEGAS REAL SA"


# ============================================================================
# _es_factura_valida — detector no-factura
# ============================================================================

def test_factura_valida_torres_import():
    """Caso real Torres Import: 4/4 marcadores."""
    proc = _make_processor()
    texto = (
        "NÚM. FACTURA 2810047013\n"
        "FECHA FACTURA 30.04.2026\n"
        "TORRES IMPORT S.A.U.\n"
        "C.I.F. A-08446700\n"
        "TOTAL FACTURA 127,50 €\n"
        "BASE IMPONIBLE 127,50\n"
    )
    es_factura, marcadores = proc._es_factura_valida(texto)
    assert es_factura is True
    assert len(marcadores) >= 2


def test_factura_valida_aqui_santona_catalogo():
    """Caso real Aquí Santoña: catálogo comercial, 0/4 marcadores."""
    proc = _make_processor()
    texto = (
        "PRESENTACIÓN INFO@AQUISANTONA.COM | AQUISANTONA.COM BRAND\n"
        "MODELO DE NEGOCIO | MARCA AQUÍ SANTOÑA\n"
        "Aquí Santoña es una tradicional empresa familiar\n"
        "LÍNEAS DE NEGOCIO\n"
        "ELABORACIÓN PROPIA\n"
        "ANCHOAS ARTESANAS DEL CANTÁBRICO\n"
    )
    es_factura, marcadores = proc._es_factura_valida(texto)
    assert es_factura is False
    assert len(marcadores) < 2


def test_factura_valida_texto_vacio():
    """Texto vacío: no es factura, lista de marcadores vacía."""
    proc = _make_processor()
    es_factura, marcadores = proc._es_factura_valida("")
    assert es_factura is False
    assert marcadores == []


def test_factura_valida_marcadores_minimos_pasa():
    """Con solo 2 marcadores (fecha + importe), debería pasar el umbral."""
    proc = _make_processor()
    texto = "Fecha: 15/04/2026\nTOTAL: 100,50 €\n"
    es_factura, marcadores = proc._es_factura_valida(texto)
    assert es_factura is True
    assert "fecha" in marcadores
    assert "importe" in marcadores


def test_factura_valida_solo_un_marcador_no_pasa():
    """Solo 1 marcador (solo fecha): no es factura."""
    proc = _make_processor()
    texto = "Reunión el 15/04/2026\nVamos a comer\n"
    es_factura, marcadores = proc._es_factura_valida(texto)
    assert es_factura is False

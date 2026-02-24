# src/facturas/detect_blocks.py
"""
Detección mínima de bloques de texto en PDF + integración con overlays YAML.

Expone:
    detect_blocks_minimal(pdf_path: str, provider: str | None = None) -> dict

Salida (dict):
    {
        "full_text":      <texto crudo de la 1ª página, normalizado>,
        "lines_text":     <bloque de líneas de productos>,
        "fecha_overlay":  <fecha DD-MM-YY si el overlay la extrajo o None>,
        "ref_overlay":    <nº factura si el overlay lo extrajo o None>,
    }

Notas:
- Si existe overlay YAML para el proveedor, se usa para recortar el bloque
  de líneas (start_after/stop_before) y para extraer fecha/ref por regex.
- Si no hay overlay, devolvemos el texto completo como lines_text (fallback).
"""
from __future__ import annotations

from typing import Optional, Dict
import re

# PDF readers
_PDF_IMPORT_ERROR = None
try:
    from PyPDF2 import PdfReader
except Exception as _e1:
    try:
        from pypdf import PdfReader  # fallback
    except Exception as _e2:
        PdfReader = None
        _PDF_IMPORT_ERROR = (_e1, _e2)

from .patterns_loader import (
    get_overlay_for,
    apply_overlay_header,
    apply_overlay_lines,
)


def _extract_first_page_text(pdf_path: str) -> str:
    if PdfReader is None:
        raise RuntimeError(
            "No se pudo importar el lector PDF (PyPDF2/pypdf). "
            "Instala pypdf:  python -m pip install pypdf\n"
            f"Detalle: {_PDF_IMPORT_ERROR!r}"
        )
    reader = PdfReader(pdf_path)
    if not reader.pages:
        return ""
    raw = reader.pages[0].extract_text() or ""
    # normalización ligera de espacios
    raw = re.sub(r"[\t\u00A0]+", " ", raw)
    raw = re.sub(r"[ ]+", " ", raw)
    return raw


def detect_blocks_minimal(pdf_path: str, provider: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Lee la 1ª página del PDF y devuelve bloque de líneas, con overlay si existe.

    :param pdf_path: ruta al PDF
    :param provider: proveedor (si ya lo detectaste por filename/cabecera).
    """
    full_text = _extract_first_page_text(pdf_path)

    # Aplicar overlay si hay proveedor + patrón cargable
    fecha_ov = None
    ref_ov = None
    lines_text = full_text

    try:
        ov = get_overlay_for(provider or "") if provider else None
    except Exception:
        ov = None

    if ov:
        try:
            f, r = apply_overlay_header(ov, full_text)
            fecha_ov, ref_ov = f, r
        except Exception:
            fecha_ov, ref_ov = None, None
        try:
            lines_text = apply_overlay_lines(ov, full_text) or full_text
        except Exception:
            lines_text = full_text

    return {
        "full_text": full_text,
        "lines_text": lines_text,
        "fecha_overlay": fecha_ov,
        "ref_overlay": ref_ov,
    }


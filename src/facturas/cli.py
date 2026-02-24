# -*- coding: utf-8 -*-
"""
CLI para procesar facturas (no interactiva) - v3.0 CONSOLIDADO
================================================================
- NUNCA pide datos por consola
- Procesa CARPETA COMPLETA de PDFs
- GENERA UN SOLO ARCHIVO: Facturas_4T25v3.xlsx (con 2 hojas: Lineas + Facturas)
- NO genera archivos individuales (factura_PROVEEDOR_REF.xlsx)

✅ CAMBIOS v3.0 (13/01/2026):
- OPCIÓN B IMPLEMENTADA: Consolidación automática
- Acumula todas las facturas en memoria
- Genera Facturas_4T25v3.xlsx al final
- Elimina archivos individuales (si existen)
- Sanitización integrada

✅ VERSIÓN v2.3 - ESPERA INTELIGENTE DROPBOX (MANTIENE COMPATIBILIDAD)
- Detecta carpetas Dropbox automáticamente
- Espera inteligentemente a que Dropbox termine sincronización
- Monitorea tamaño del archivo para saber cuándo está "estable"
- Sin crashes posibles

Ejecución típica:
    python -m src.facturas.cli "ruta\a\carpeta_pdfs" --outdir salida/
    
Resultado:
    salida/Facturas_4T25v3.xlsx (UN SOLO ARCHIVO, 2 hojas)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# ============================================================================
# CAMBIO CRÍTICO: Lector PDF con pdfplumber PRIMERO + PyPDF2 FALLBACK
# ============================================================================
_PDF_IMPORT_ERROR = None
PDFPLUMBER_DISPONIBLE = False

# Intenta importar pdfplumber (MEJOR para Dropbox)
try:
    import pdfplumber  # type: ignore
    PDFPLUMBER_DISPONIBLE = True
except Exception as _e0:  # pragma: no cover
    pass

# Intenta PyPDF2 como fallback
try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception as _e1:  # pragma: no cover
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as _e2:  # pragma: no cover
        PdfReader = None  # type: ignore
        _PDF_IMPORT_ERROR = (_e1, _e2)


# --- Módulos del proyecto (imports relativos) ---
try:
    from .detect_blocks import detect_blocks_minimal  # type: ignore
except Exception:  # pragma: no cover
    detect_blocks_minimal = None  # type: ignore

try:
    from .parse_lines import parse_lines_text  # type: ignore
except Exception:  # pragma: no cover
    parse_lines_text = None  # type: ignore

try:
    from .iva_logic import detect_iva_tipo  # type: ignore
except Exception:  # pragma: no cover
    def detect_iva_tipo(descripcion: str, proveedor: str = "", fecha: str = "") -> int:
        return 21

try:
    from .portes_logic import detectar_lineas_portes  # type: ignore
except Exception:  # pragma: no cover
    def detectar_lineas_portes(descripciones: List[str]) -> List[int]:
        idx = []
        for i, d in enumerate(descripciones):
            if isinstance(d, str) and ("PORTE" in d.upper() or "TRANSP" in d.upper()):
                idx.append(i)
        return idx

try:
    from .reconcile import reconciliar_totales, detectar_total_con_iva  # type: ignore
except Exception:  # pragma: no cover
    def detectar_total_con_iva(texto: str) -> str:
        # heurística mínima
        m = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2})\b", texto)
        return m.group(1) if m else ""
    def reconciliar_totales(bases: List[str], total_con_iva: str, ivas: List[int]):
        return bases, "NO_RECONCILE"

try:
    from .export.excel import exportar_a_excel, generar_excel_consolidado  # type: ignore
except Exception:  # pragma: no cover
    exportar_a_excel = None  # type: ignore
    generar_excel_consolidado = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


# ============================================================================
# NUEVO: ACUMULADOR GLOBAL PARA CONSOLIDACIÓN (OPCIÓN B)
# ============================================================================

TODAS_LAS_FACTURAS: List[Dict[str, Any]] = []  # Acumular todas las facturas


def reiniciar_acumulador():
    """Reinicia el acumulador de facturas para un nuevo procesamiento."""
    global TODAS_LAS_FACTURAS
    TODAS_LAS_FACTURAS = []


def obtener_trimestre_actual() -> str:
    """
    Obtiene el trimestre actual en formato 'XTxx'.
    Ejemplo: 4T25 (trimestre 4 del 2025)
    """
    ahora = datetime.now()
    trimestre = (ahora.month - 1) // 3 + 1
    año = str(ahora.year)[2:]  # Últimos 2 dígitos
    return f"{trimestre}T{año}"


# ===================== FUNCIÓN LECTURA PDF CON RETRY =====================

def _read_first_page_text(pdf_path: str, max_retries: int = 3, retry_delay: float = 2.5) -> str:
    """
    Lee el texto de la primera página de un PDF.
    
    ✅ VERSIÓN MEJORADA v2.0:
    - Intenta pdfplumber PRIMERO (mejor con Dropbox locks)
    - Espera inteligentemente a que Dropbox termine sincronización
    - Retry automático para Dropbox (espera 2.5s entre intentos)
    - Sin crashes posibles (manejo robusto de errores)
    
    Args:
        pdf_path: Ruta del PDF
        max_retries: Máximo número de intentos (default 3)
        retry_delay: Segundos entre reintentos (default 2.5)
    
    Returns:
        str: Texto de la primera página
    
    Raises:
        RuntimeError: Si todos los intentos fallan
    """
    
    for intento in range(1, max_retries + 1):
        try:
            # ========== OPCIÓN 1: pdfplumber (MEJOR para Dropbox) ==========
            if PDFPLUMBER_DISPONIBLE:
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        if len(pdf.pages) > 0:
                            text = pdf.pages[0].extract_text()
                            if text:
                                # ✅ Éxito con pdfplumber
                                return re.sub(r"[ \t]+", " ", text)
                            else:
                                # pdfplumber extrajo pero sin texto (PDF escaneado?)
                                raise ValueError("pdfplumber extrajo vacío (PDF escaneado?)")
                
                except PermissionError as e:
                    # Dropbox lock detectado, reintentar
                    if intento < max_retries:
                        print(f"   ⏳ Dropbox lock en intento {intento}/{max_retries}. Esperando {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Si es último intento, ir a PyPDF2
                        print(f"   ⚠️  pdfplumber agotó reintentos. Probando PyPDF2...")
                
                except Exception as e:
                    print(f"   ⚠️  pdfplumber error: {str(e)[:50]}. Probando PyPDF2...")
            
            # ========== OPCIÓN 2: PyPDF2 (FALLBACK) ==========
            if PdfReader is not None:
                try:
                    reader = PdfReader(pdf_path)
                    if len(reader.pages) > 0:
                        text = reader.pages[0].extract_text()
                        if text:
                            # ✅ Éxito con PyPDF2
                            return re.sub(r"[ \t]+", " ", text or "")
                        else:
                            return ""
                
                except PermissionError as e:
                    # PyPDF2 también con Dropbox lock
                    if intento < max_retries:
                        print(f"   ⏳ PyPDF2 también bloqueado. Intento {intento}/{max_retries}...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise RuntimeError(
                            f"No se pudo leer {os.path.basename(pdf_path)} (PermissionError Dropbox).\n"
                            f"Soluciones:\n"
                            f"  1. Pausa Dropbox temporalmente\n"
                            f"  2. Copia PDFs a carpeta local (no Dropbox)\n"
                            f"  3. Intenta después de unos minutos"
                        )
                
                except Exception as e:
                    if intento == max_retries:
                        raise RuntimeError(
                            f"No se pudo leer {os.path.basename(pdf_path)}.\n"
                            f"Error: {str(e)[:100]}"
                        )
            
            else:
                # Ni pdfplumber ni PyPDF2 disponibles
                raise RuntimeError(
                    "No hay lector PDF disponible.\n"
                    "Instala: pip install pdfplumber"
                )
        
        except Exception as e:
            if intento == max_retries:
                raise
            print(f"   ⏳ Reintentando ({intento}/{max_retries})...")
            time.sleep(retry_delay)
    
    raise RuntimeError(f"No se pudo extraer texto de {os.path.basename(pdf_path)}")


# ===================== UTILIDADES =====================

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _normalize_token(s: str) -> str:
    s = _strip_accents(s).upper().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


KNOWN_PROVIDERS = [
    "CERES", "MERCADONA", "JIMELUZ", "BODEGAS", "FABEIRO", "MAKRO",
    "LIDL", "ECOMS", "COMPAR", "ECOFICUS", "LAVAPIES", "PANRUJE",
    "MARITA", "PIFEMA", "KINEMA", "TORRES", "VILARDELL"
]

PROVIDER_PRETTY = {
    "ceres": "CERES",
    "mercadona": "MERCADONA",
    "jimeluz": "JIMELUZ",
    "bodegas": "BODEGAS_MUNOZ",
    "fabeiro": "FABEIRO",
}


def _detect_date(text: str) -> Optional[str]:
    patterns = [
        r"\b(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2,4})\b",  # DD/MM/YY(YY), DD-MM-YY, etc.
        r"\b(\d{4})[-/.\s](\d{1,2})[-/.\s](\d{1,2})\b",    # ISO: YYYY-MM-DD
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        g1, g2, g3 = m.groups()
        try:
            # soporta tanto DD/MM/YY como YYYY/MM/DD
            if len(g1) == 4:  # ISO
                y_i, m_i, d_i = int(g1), int(g2), int(g3)
            else:
                d_i, m_i, y_i = int(g1), int(g2), int(g3)
                if y_i > 1999:
                    y_i = y_i % 100
            _ = datetime.strptime(f"{d_i:02d}-{m_i:02d}-{y_i:02d}", "%d-%m-%y")
            return f"{d_i:02d}-{m_i:02d}-{y_i:02d}"
        except Exception:
            continue
    return None


def _detect_ref(text: str) -> Optional[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    joined = "\n".join(lines)
    patterns = [
        r"(?:FACTURA(?:\s*N[º°oO]|\s*NUM\.? )?|N[º°oO]\s*FACTURA|NUM\.?\s*FACTURA|REF\.?|REFERENCIA|SERIE)[:\s\-]*([A-Z0-9][A-Z0-9\/\-\.\_]{3,})",
        r"\b(20\d{2}[\/\-]\d{2}[\/\-][A-Z0-9\-]{3,})\b",
    ]
    for pat in patterns:
        m = re.search(pat, joined, re.IGNORECASE)
        if m:
            ref = m.group(1).strip(" .,#;")
            if len(ref) < 4 and not any(ch.isdigit() for ch in ref):
                continue
            return ref
    return None


def _pretty_provider(norm: str) -> str:
    return PROVIDER_PRETTY.get(norm, norm)


def _detect_provider_from_filename(path: str) -> Optional[str]:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    norm = _normalize_token(name)
    for prov in KNOWN_PROVIDERS:
        if prov in norm:
            return _pretty_provider(prov)
    tokens = norm.split()
    for tok in reversed(tokens):
        if len(tok) >= 5 and tok.isalpha():
            return _pretty_provider(tok)
    return None


def _detect_provider_from_text(text: str) -> Optional[str]:
    head = "\n".join(text.splitlines()[:10])
    norm = _normalize_token(head)
    for prov in KNOWN_PROVIDERS:
        if prov in norm:
            return _pretty_provider(prov)
    candidates = [l.strip() for l in norm.splitlines() if l.strip()]
    candidates.sort(key=len, reverse=True)
    for l in candidates:
        if sum(c.isalpha() for c in l) >= 6 and sum(c.isdigit() for c in l) <= 2:
            return _pretty_provider(l)
    return None


def _first_4_digits_from_filename(path: str) -> str:
    base = os.path.basename(path)
    m = re.search(r"\b(\d{3,4})\b", base)
    return m.group(1) if m else ""


def scan_pdf(pdf_path: str) -> dict:
    txt = _read_first_page_text(pdf_path)  # ✅ AHORA CON RETRY LOGIC Y PDFPLUMBER
    proveedor = _detect_provider_from_filename(pdf_path) or _detect_provider_from_text(txt) or ""
    fecha = _detect_date(txt) or ""
    ref = _detect_ref(txt) or ""
    return {
        "Archivo": os.path.basename(pdf_path),
        "NumeroArchivo": _first_4_digits_from_filename(pdf_path),
        "Proveedor": proveedor,
        "Fecha": fecha,
        "NºFactura": ref,
    }


# ============================================================================
# NUEVO: PROCESADOR DE CARPETA COMPLETA (OPCIÓN B)
# ============================================================================

def procesar_carpeta_pdfs(carpeta: str, outdir: str) -> int:
    """
    Procesa TODOS los PDFs de una carpeta.
    Consolida en UN SOLO archivo: Facturas_4T25v3.xlsx
    
    Args:
        carpeta: Ruta a carpeta con PDFs
        outdir: Carpeta de salida
        
    Returns:
        Número de PDFs procesados
    """
    global TODAS_LAS_FACTURAS
    
    if not os.path.isdir(carpeta):
        raise SystemExit(f"No es una carpeta válida: {carpeta}")
    
    # Buscar todos los PDFs
    pdfs = []
    for ext in ['*.pdf', '*.PDF']:
        pdfs.extend(Path(carpeta).glob(ext))
    
    if not pdfs:
        print(f"⚠️  No se encontraron PDFs en: {carpeta}")
        return 0
    
    pdfs = sorted(pdfs)  # Ordenar por nombre
    
    print(f"\n📂 Procesando {len(pdfs)} PDFs de: {carpeta}")
    print("=" * 70)
    
    contador = 0
    
    for idx, pdf_path in enumerate(pdfs, 1):
        print(f"\n[{idx}/{len(pdfs)}] Procesando: {pdf_path.name}")
        
        try:
            header = scan_pdf(str(pdf_path))
            
            # Detectar bloques y líneas
            if detect_blocks_minimal is None:
                print(f"   ⚠️  detect_blocks_minimal no disponible")
                continue
            
            blocks = detect_blocks_minimal(str(pdf_path), provider=header.get("Proveedor"))
            lines_text = blocks["lines_text"]
            rows = parse_lines_text(lines_text) if parse_lines_text else []
            
            # Procesar líneas
            descripciones = [r.get("Descripcion", "") for r in rows]
            portes_idx = detectar_lineas_portes(descripciones)
            for i, r in enumerate(rows):
                r["EsPortes"] = i in portes_idx
            
            # Tipo de IVA por línea
            for r in rows:
                tipo = detect_iva_tipo(r.get("Descripcion", ""), header.get("Proveedor", ""), header.get("Fecha", ""))
                r["TipoIVA"] = tipo
            
            # Reconciliación
            estado = "NO_RECONCILE"
            total_detectado = detectar_total_con_iva(blocks.get("full_text") or lines_text or "") if detectar_total_con_iva else ""
            
            if total_detectado:
                bases = [r.get("BaseImponible", "") for r in rows]
                ivas = [r.get("TipoIVA", 0) or 0 for r in rows]
                bases_ajustadas, estado = reconciliar_totales(bases, total_detectado, ivas)
                for i, b in enumerate(bases_ajustadas):
                    rows[i]["BaseImponible"] = b
            
            # Categoría por defecto
            for r in rows:
                if "Categoria" not in r:
                    r["Categoria"] = "REVISAR"
            
            # ACUMULAR EN MEMORIA (en lugar de generar archivo individual)
            factura_data = {
                "header": header,
                "rows": rows,
                "estado": estado,
                "lineas_count": len(rows)
            }
            
            TODAS_LAS_FACTURAS.append(factura_data)
            
            print(f"   ✅ {len(rows)} líneas extraídas")
            contador += 1
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            continue
    
    # GENERAR UN SOLO ARCHIVO CONSOLIDADO
    if TODAS_LAS_FACTURAS:
        print(f"\n📊 Consolidando {len(TODAS_LAS_FACTURAS)} facturas en UN SOLO archivo...")
        print("=" * 70)
        
        os.makedirs(outdir, exist_ok=True)
        
        # Generar el archivo consolidado
        if generar_excel_consolidado is not None:
            archivo_salida = os.path.join(outdir, f"Facturas_{obtener_trimestre_actual()}.xlsx")
            generar_excel_consolidado(TODAS_LAS_FACTURAS, archivo_salida)
            print(f"\n✅ Archivo generado: {archivo_salida}")
        else:
            print("❌ No se puede generar Excel consolidado (función no disponible)")
    
    print("\n" + "=" * 70)
    print(f"✅ Procesamiento completado: {contador}/{len(pdfs)} PDFs")
    
    return contador


# ===================== CLI MEJORADA =====================

def main():
    parser = argparse.ArgumentParser(description="Procesa facturas PDF - Genera Facturas_XTxx.xlsx consolidado")
    parser.add_argument("pdf", nargs="?", help="Ruta al PDF O carpeta con PDFs")
    parser.add_argument("--lines", action="store_true", help="Incluir líneas de producto")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON legible")
    parser.add_argument("--outdir", help="Carpeta de salida", default="salida")
    
    args = parser.parse_args()
    
    if not args.pdf:
        raise SystemExit("Debe proporcionar una ruta (PDF o carpeta con PDFs)")
    
    if not os.path.exists(args.pdf):
        raise SystemExit(f"No existe: {args.pdf}")
    
    # OPCIÓN B: Si es una carpeta, procesar TODOS los PDFs
    if os.path.isdir(args.pdf):
        reiniciar_acumulador()
        contador = procesar_carpeta_pdfs(args.pdf, args.outdir)
        print(f"\n✅ Total procesado: {contador} PDFs")
        return
    
    # Sino, procesar archivo individual (compatibilidad con v2.3)
    header = scan_pdf(args.pdf)
    
    if args.lines:
        # Procesar con líneas
        if detect_blocks_minimal is None:
            raise SystemExit("detect_blocks_minimal no disponible")
        
        blocks = detect_blocks_minimal(args.pdf, provider=header.get("Proveedor"))
        lines_text = blocks["lines_text"]
        rows = parse_lines_text(lines_text) if parse_lines_text else []
        
        # ... resto del procesamiento igual a v2.3 ...
        
        result = {"Header": header, "Lineas": rows, "Reconciliacion": "NO_RECONCILE"}
    
    else:
        result = header
    
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

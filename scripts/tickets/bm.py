"""
bm.py — Procesa tickets PDF de BM Supermercados descargados desde la app BM+.

Flujo semi-manual: App BM+ → WhatsApp Web → carpeta entrada → este script → gestion-facturas

Funcionalidades:
  1. Escanea carpeta de entrada por PDFs nuevos de BM
  2. Extrae fecha del ticket desde el PDF (pdfplumber)
  3. Renombra según convención gestion-facturas: TTYY_MMDD_BM_TJ.pdf
  4. Copia a la carpeta del trimestre correspondiente
  5. Registro anti-duplicación via comun.py
  6. Opcionalmente lanza parseo con main.py

Uso:
  python -m scripts.tickets.bm                          # procesar tickets nuevos
  python -m scripts.tickets.bm --dry-run                # solo muestra qué haría
  python -m scripts.tickets.bm --entrada "C:\\ruta"     # carpeta personalizada
  python -m scripts.tickets.bm --parsear                # procesar + parsear

Proveedor: DISTRIBUCION SUPERMERCADOS, SL (Grupo Uvesco)
CIF: B20099586
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from scripts.tickets.comun import (
    PROJECT_ROOT,
    configurar_logging,
    calcular_trimestre,
    obtener_carpeta_trimestre,
    generar_nombre_pdf,
    cargar_registro,
    guardar_registro,
    esta_procesado,
    registrar_ticket,
    extraer_texto_pdf,
    extraer_fecha_generica,
    imprimir_resumen,
)

# ── Constantes BM ────────────────────────────────────────────────────────────

PROVEEDOR = "BM"
CIF_BM = "B20099586"
KEYWORDS_BM = ["BM", "DISTRIBUCION SUPERMERCADOS", CIF_BM, "UVESCO", "Cuenta BM"]
CARPETA_ENTRADA_DEFAULT = Path.home() / "Downloads"
CARPETA_BACKUP = PROJECT_ROOT.parent / "bm-tickets" / "tickets_pdf"

logger = None  # Se inicializa en main()


# ── Funciones específicas de BM ──────────────────────────────────────────────

def es_pdf_bm(texto: str) -> bool:
    """Comprueba si el texto de un PDF parece ser un ticket de BM.

    Requiere al menos 2 coincidencias con las keywords de BM.
    """
    texto_upper = texto.upper()
    coincidencias = sum(1 for kw in KEYWORDS_BM if kw.upper() in texto_upper)
    return coincidencias >= 2


def extraer_numero_ticket(texto: str) -> str | None:
    """Extrae el número de ticket/factura simplificada de BM.

    Formato típico: 142312502C0001523
    """
    patron = re.search(r'(\d{10,}C?\d+)', texto)
    if patron:
        return patron.group(1)
    return None


def generar_huella(texto: str) -> str:
    """Genera una huella única del ticket BM para detectar duplicados.

    Combina fecha + total + número de ticket.
    """
    # Extraer total
    patron_total = re.search(
        r'TOTAL\s+COMPRA\s*\(?iva\s+incl\.?\)?\s*(\d+[.,]\d{2})',
        texto, re.IGNORECASE
    )
    total = patron_total.group(1) if patron_total else "?"

    # Extraer fecha
    fecha = extraer_fecha_generica(texto)
    fecha_str = fecha.strftime("%Y%m%d") if fecha else "?"

    # Extraer número ticket
    num = extraer_numero_ticket(texto) or "?"

    return f"BM_{fecha_str}_{total}_{num}"


# ── Procesamiento principal ──────────────────────────────────────────────────

def procesar_tickets(carpeta_entrada: Path, dry_run: bool = False,
                     forzar: bool = False, parsear: bool = False):
    """Procesa todos los PDFs de BM encontrados en la carpeta de entrada."""

    if not carpeta_entrada.exists():
        logger.error("Carpeta de entrada no existe: %s", carpeta_entrada)
        return

    # Cargar registro
    registro = cargar_registro(PROVEEDOR)

    # Buscar PDFs
    pdfs = list(carpeta_entrada.glob("*.pdf")) + list(carpeta_entrada.glob("*.PDF"))

    if not pdfs:
        logger.info("No hay PDFs en %s", carpeta_entrada)
        return

    logger.info("Encontrados %d PDFs en %s", len(pdfs), carpeta_entrada)

    tickets_nuevos = 0
    tickets_ignorados = 0
    tickets_no_bm = 0
    errores = 0

    for pdf_path in pdfs:
        logger.debug("Analizando: %s", pdf_path.name)

        # Extraer texto
        texto = extraer_texto_pdf(pdf_path)
        if not texto:
            logger.debug("  Sin texto extraíble, ignorando")
            continue

        # Verificar que es de BM
        if not es_pdf_bm(texto):
            logger.debug("  No es ticket de BM, ignorando")
            tickets_no_bm += 1
            continue

        # Anti-duplicación
        huella = generar_huella(texto)
        if esta_procesado(huella, registro) and not forzar:
            logger.info("  Ya procesado: %s (%s)", pdf_path.name, huella)
            tickets_ignorados += 1
            continue

        # Extraer fecha
        fecha = extraer_fecha_generica(texto)
        if not fecha:
            logger.warning("  No se pudo extraer fecha de %s, usando hoy", pdf_path.name)
            fecha = datetime.now()

        # Calcular destino
        carpeta_trim = obtener_carpeta_trimestre(fecha)
        nombre_nuevo = generar_nombre_pdf(fecha, PROVEEDOR, "TJ", carpeta_trim)
        num_ticket = extraer_numero_ticket(texto) or "?"

        logger.info("  %s", pdf_path.name)
        logger.info("    Fecha: %s | Ticket: %s", fecha.strftime("%d/%m/%Y"), num_ticket)
        logger.info("    -> %s (en %s/)", nombre_nuevo, calcular_trimestre(fecha))

        if dry_run:
            logger.info("    [DRY-RUN] No se copia nada")
            tickets_nuevos += 1
            continue

        # Copiar a gestion-facturas
        destino = carpeta_trim / nombre_nuevo
        try:
            shutil.copy2(pdf_path, destino)
            logger.info("    Copiado a: %s", destino)
        except Exception as e:
            logger.error("    Error copiando: %s", e)
            errores += 1
            continue

        # Backup local
        try:
            backup_trim = CARPETA_BACKUP / calcular_trimestre(fecha)
            backup_trim.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, backup_trim / nombre_nuevo)
        except Exception:
            pass  # Backup es opcional

        # Registrar
        registrar_ticket(huella, {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "ticket": num_ticket,
            "fichero": nombre_nuevo,
            "origen": pdf_path.name,
        }, registro)
        tickets_nuevos += 1

    # Guardar registro
    if not dry_run and tickets_nuevos > 0:
        guardar_registro(PROVEEDOR, registro)

    # Resumen
    imprimir_resumen(
        proveedor=PROVEEDOR,
        analizados=len(pdfs) - tickets_no_bm,
        nuevos=tickets_nuevos,
        duplicados=tickets_ignorados,
        errores=errores,
        dry_run=dry_run,
    )

    # Parsear si se solicita
    if parsear and not dry_run and tickets_nuevos > 0:
        _lanzar_parseo()


def _lanzar_parseo():
    """Lanza main.py de gestion-facturas para parsear los nuevos tickets."""
    main_py = PROJECT_ROOT / "main.py"
    if not main_py.exists():
        logger.warning("No se encontró main.py en %s", PROJECT_ROOT)
        return

    logger.info("Lanzando parseo con main.py...")
    try:
        resultado = subprocess.run(
            [sys.executable, str(main_py)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if resultado.returncode == 0:
            logger.info("Parseo completado correctamente")
            if resultado.stdout:
                print(resultado.stdout[-500:])
        else:
            logger.error("Error en parseo (código %d)", resultado.returncode)
            if resultado.stderr:
                print(resultado.stderr[-500:])
    except subprocess.TimeoutExpired:
        logger.error("Parseo abortado: timeout de 5 minutos")
    except Exception as e:
        logger.error("Error lanzando parseo: %s", e)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    global logger

    parser = argparse.ArgumentParser(
        description="Procesa tickets PDF de BM Supermercados para gestion-facturas"
    )
    parser.add_argument("--entrada", "-e", default=str(CARPETA_ENTRADA_DEFAULT),
                        help="Carpeta donde están los PDFs (default: ~/Downloads)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Solo muestra qué haría, sin copiar nada")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-procesa aunque ya esté en el registro")
    parser.add_argument("--parsear", "-p", action="store_true",
                        help="Lanzar main.py tras procesar")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Mostrar mensajes de debug")
    args = parser.parse_args()

    logger = configurar_logging("bm", args.verbose)

    print()
    print("+" + "=" * 48 + "+")
    print("|   BM TICKETS — Procesador de tickets PDF      |")
    print("+" + "=" * 48 + "+")
    print(f"  Entrada:  {args.entrada}")
    print(f"  Destino:  {PROJECT_ROOT}")
    print()

    procesar_tickets(
        carpeta_entrada=Path(args.entrada),
        dry_run=args.dry_run,
        forzar=args.force,
        parsear=args.parsear,
    )


if __name__ == "__main__":
    main()

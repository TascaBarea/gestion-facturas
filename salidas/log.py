"""
Módulo de generación de logs.

Genera logs detallados del procesamiento de facturas.
"""
from pathlib import Path
from typing import List, TYPE_CHECKING
from datetime import datetime
from config.settings import VERSION

if TYPE_CHECKING:
    from nucleo.factura import Factura


def generar_log(facturas: List['Factura'], ruta: Path) -> None:
    """
    Genera log detallado del procesamiento.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el log
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta, 'w', encoding='utf-8') as f:
        # Cabecera
        f.write(f"PARSEAR FACTURAS v{VERSION}\n")
        f.write(f"{'='*60}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Estadísticas generales
        total = len(facturas)
        con_cif = sum(1 for fa in facturas if fa.cif)
        con_iban = sum(1 for fa in facturas if fa.iban)
        con_lineas = sum(1 for fa in facturas if fa.lineas)
        total_lineas = sum(len(fa.lineas) for fa in facturas)
        
        f.write(f"RESUMEN:\n")
        f.write(f"  Facturas procesadas: {total}\n")
        
        if total > 0:
            f.write(f"  Con CIF extraído:    {con_cif} ({100*con_cif/total:.1f}%)\n")
            f.write(f"  Con IBAN extraído:   {con_iban} ({100*con_iban/total:.1f}%)\n")
            f.write(f"  Con líneas extraídas: {con_lineas} ({100*con_lineas/total:.1f}%)\n")
        else:
            f.write(f"  Con CIF extraído:    {con_cif}\n")
            f.write(f"  Con IBAN extraído:   {con_iban}\n")
            f.write(f"  Con líneas extraídas: {con_lineas}\n")
        
        f.write(f"  Total líneas:        {total_lineas}\n")
        
        # Estadísticas de cuadre
        cuadre_ok = sum(1 for fa in facturas if fa.cuadre == 'OK')
        cuadre_descuadre = sum(1 for fa in facturas if fa.cuadre and fa.cuadre.startswith('DESCUADRE'))
        cuadre_sin_total = sum(1 for fa in facturas if fa.cuadre == 'SIN_TOTAL')
        cuadre_sin_lineas = sum(1 for fa in facturas if fa.cuadre == 'SIN_LINEAS')
        
        f.write(f"\n  VALIDACIÓN CUADRE:\n")
        f.write(f"    OK:          {cuadre_ok}")
        if total > 0:
            f.write(f" ({100*cuadre_ok/total:.1f}%)")
        f.write("\n")
        f.write(f"    DESCUADRE:   {cuadre_descuadre}\n")
        f.write(f"    SIN_TOTAL:   {cuadre_sin_total}\n")
        f.write(f"    SIN_LINEAS:  {cuadre_sin_lineas}\n")
        
        # IBANs encontrados
        f.write(f"\n{'='*60}\n")
        f.write(f"IBANs ENCONTRADOS:\n")
        ibans_vistos = set()
        for fa in facturas:
            if fa.iban and fa.iban not in ibans_vistos:
                f.write(f"  {fa.proveedor}: {fa.iban}\n")
                ibans_vistos.add(fa.iban)
        
        # CIFs encontrados
        f.write(f"\n{'='*60}\n")
        f.write(f"CIFs ENCONTRADOS:\n")
        cifs_vistos = set()
        for fa in facturas:
            if fa.cif and fa.cif not in cifs_vistos:
                f.write(f"  {fa.proveedor}: {fa.cif}\n")
                cifs_vistos.add(fa.cif)
        
        # Facturas con errores
        f.write(f"\n{'='*60}\n")
        f.write(f"FACTURAS CON ERRORES:\n")
        for fa in facturas:
            if fa.errores:
                f.write(f"  {fa.archivo}: {', '.join(fa.errores)}\n")
        
        # Facturas con descuadre
        f.write(f"\n{'='*60}\n")
        f.write(f"FACTURAS CON DESCUADRE:\n")
        for fa in facturas:
            if fa.cuadre and fa.cuadre.startswith('DESCUADRE'):
                f.write(f"  {fa.archivo}: {fa.cuadre} (Total: {fa.total}, Calculado: {fa.total_calculado:.2f})\n")
        
        # Artículos pendientes de categorizar
        f.write(f"\n{'='*60}\n")
        f.write(f"ARTÍCULOS PENDIENTES DE CATEGORIZAR:\n")
        pendientes = set()
        for fa in facturas:
            for linea in fa.lineas:
                if not linea.categoria or linea.categoria == 'PENDIENTE':
                    pendientes.add((fa.proveedor, linea.articulo))
        for prov, art in sorted(pendientes):
            f.write(f"  [{prov}] {art}\n")
        
        # Estadísticas por proveedor
        f.write(f"\n{'='*60}\n")
        f.write(f"ESTADÍSTICAS POR PROVEEDOR:\n")
        proveedores = {}
        for fa in facturas:
            prov = fa.proveedor or 'DESCONOCIDO'
            if prov not in proveedores:
                proveedores[prov] = {'total': 0, 'ok': 0, 'lineas': 0, 'importe': 0.0}
            proveedores[prov]['total'] += 1
            proveedores[prov]['lineas'] += len(fa.lineas)
            proveedores[prov]['importe'] += fa.total or 0
            if fa.cuadre == 'OK':
                proveedores[prov]['ok'] += 1
        
        for prov, stats in sorted(proveedores.items()):
            pct = 100 * stats['ok'] / stats['total'] if stats['total'] > 0 else 0
            f.write(f"  {prov}: {stats['ok']}/{stats['total']} OK ({pct:.0f}%), "
                    f"{stats['lineas']} líneas, {stats['importe']:.2f}€\n")


def generar_log_errores(facturas: List['Factura'], ruta: Path) -> int:
    """
    Genera log solo con errores para revisión rápida.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el log
        
    Returns:
        Número de facturas con errores
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    errores = []
    for fa in facturas:
        if fa.tiene_errores or fa.cuadre != 'OK':
            errores.append(fa)
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(f"FACTURAS CON ERRORES - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"{'='*60}\n")
        f.write(f"Total: {len(errores)} de {len(facturas)} facturas\n\n")
        
        for fa in errores:
            f.write(f"\n{'-'*40}\n")
            f.write(f"Archivo: {fa.archivo}\n")
            f.write(f"Proveedor: {fa.proveedor}\n")
            f.write(f"Fecha: {fa.fecha}\n")
            f.write(f"Total: {fa.total}\n")
            f.write(f"Cuadre: {fa.cuadre}\n")
            if fa.errores:
                f.write(f"Errores: {', '.join(fa.errores)}\n")
            f.write(f"Líneas extraídas: {len(fa.lineas)}\n")
            if fa.ruta:
                f.write(f"Ruta: {fa.ruta}\n")
    
    return len(errores)


def imprimir_resumen(facturas: List['Factura']) -> None:
    """
    Imprime resumen en consola.
    
    Args:
        facturas: Lista de facturas procesadas
    """
    total = len(facturas)
    if total == 0:
        print("No se procesaron facturas.")
        return
    
    ok = sum(1 for f in facturas if f.cuadre == 'OK')
    con_lineas = sum(1 for f in facturas if f.lineas)
    total_lineas = sum(len(f.lineas) for f in facturas)
    importe_total = sum(f.total or 0 for f in facturas)
    
    print(f"\n{'='*50}")
    print(f"RESUMEN PROCESAMIENTO")
    print(f"{'='*50}")
    print(f"  Facturas:     {total}")
    print(f"  Cuadre OK:    {ok} ({100*ok/total:.1f}%)")
    print(f"  Con líneas:   {con_lineas} ({100*con_lineas/total:.1f}%)")
    print(f"  Total líneas: {total_lineas}")
    print(f"  Importe:      {importe_total:,.2f}€")
    print(f"{'='*50}\n")


def generar_log_detallado(facturas: List['Factura'], ruta: Path) -> None:
    """
    Genera log muy detallado con el contenido de cada factura.
    Útil para debugging.
    
    Args:
        facturas: Lista de facturas procesadas
        ruta: Ruta donde guardar el log
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(f"LOG DETALLADO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n\n")
        
        for i, fa in enumerate(facturas, 1):
            f.write(f"\n{'#'*80}\n")
            f.write(f"FACTURA {i}/{len(facturas)}: {fa.archivo}\n")
            f.write(f"{'#'*80}\n")
            f.write(f"  Número:    {fa.numero}\n")
            f.write(f"  Proveedor: {fa.proveedor}\n")
            f.write(f"  CIF:       {fa.cif}\n")
            f.write(f"  IBAN:      {fa.iban}\n")
            f.write(f"  Fecha:     {fa.fecha}\n")
            f.write(f"  Referencia: {fa.referencia}\n")
            f.write(f"  Total:     {fa.total}\n")
            f.write(f"  Cuadre:    {fa.cuadre}\n")
            f.write(f"  Método PDF: {fa.metodo_pdf}\n")
            f.write(f"  Errores:   {fa.errores}\n")
            
            f.write(f"\n  LÍNEAS ({len(fa.lineas)}):\n")
            for j, linea in enumerate(fa.lineas, 1):
                f.write(f"    {j}. {linea.articulo}\n")
                f.write(f"       Código: {linea.codigo}, IVA: {linea.iva}%, "
                        f"Base: {linea.base}€, Categoría: {linea.categoria}\n")
            
            if fa.texto_raw:
                f.write(f"\n  TEXTO RAW (primeros 500 chars):\n")
                f.write(f"    {fa.texto_raw[:500]}...\n")

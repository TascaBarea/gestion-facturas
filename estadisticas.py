# -*- coding: utf-8 -*-
"""
Generador de Estadísticas v1.0 - NUEVO MÓDULO (Sesión 12/01/2026)

✅ FUNCIONALIDAD:
- Clasifica facturas en 4 categorías de calidad
- Calcula tasas (%) para cada categoría
- Genera reportes en consola y JSON

✅ CATEGORÍAS:
1. OK: Factura con líneas y cuadre correcto
2. SIN_LINEAS: Factura sin líneas detectadas (JPG con mínimos)
3. SIN_CUADRAR: Factura con líneas pero cuadre no OK
4. OTROS_PROBLEMAS: Errores de procesamiento

✅ SALIDA:
  {
    'total_facturas': 161,
    'ok': 150,
    'sin_lineas': 8,
    'sin_cuadrar': 2,
    'otros_problemas': 1,
    'porcentaje_ok': 93.17,
    'porcentaje_sin_lineas': 4.97,
    'porcentaje_sin_cuadrar': 1.24,
    'porcentaje_otros': 0.62,
  }

Uso:
    from estadisticas import GeneradorEstadisticas
    
    generador = GeneradorEstadisticas(lista_facturas_procesadas)
    reporte = generador.generar_reporte()
    generador.mostrar_reporte_consola()
    generador.guardar_reporte_json("reporte.json")
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class GeneradorEstadisticas:
    """Generador de reportes de calidad de procesamiento."""
    
    CATEGORIA_OK = "OK"
    CATEGORIA_SIN_LINEAS = "SIN_LINEAS"
    CATEGORIA_SIN_CUADRAR = "SIN_CUADRAR"
    CATEGORIA_OTROS = "OTROS_PROBLEMAS"
    
    def __init__(self, facturas: Optional[List[Dict[str, Any]]] = None):
        """
        Inicializa generador de estadísticas.
        
        Args:
            facturas: Lista de dicts con información de facturas procesadas.
                     Cada dict debe tener:
                     - 'numero': str (número factura)
                     - 'proveedor': str (nombre proveedor)
                     - 'lineas': list (líneas detectadas)
                     - 'cuadre': str (estado cuadre)
                     - 'archivo': str (nombre archivo)
                     - Opcionalmente: 'errores', 'valido', etc.
        """
        self.facturas = facturas or []
        self.reporte: Dict[str, Any] = {}
    
    def _clasificar_factura(self, factura: Dict[str, Any]) -> str:
        """
        Clasifica una factura en categoría según su estado.
        
        Args:
            factura: Dict con información de factura
        
        Returns:
            str: Categoría (OK, SIN_LINEAS, SIN_CUADRAR, OTROS_PROBLEMAS)
        """
        
        # Verificar si hay errores o problemas
        if factura.get('errores'):
            return self.CATEGORIA_OTROS
        
        if not factura.get('valido'):
            return self.CATEGORIA_OTROS
        
        # Verificar si tiene líneas
        lineas = factura.get('lineas', [])
        if not lineas or len(lineas) == 0:
            return self.CATEGORIA_SIN_LINEAS
        
        # Verificar estado de cuadre
        cuadre = factura.get('cuadre', 'REVISAR')
        if cuadre == "OK":
            return self.CATEGORIA_OK
        elif cuadre == "SIN_LINEAS":
            return self.CATEGORIA_SIN_LINEAS
        else:
            return self.CATEGORIA_SIN_CUADRAR
    
    def generar_reporte(self) -> Dict[str, Any]:
        """
        Genera reporte de estadísticas.
        
        Returns:
            dict: Reporte con conteos y porcentajes
        """
        
        total = len(self.facturas)
        
        # Contar por categoría
        conteos = {
            self.CATEGORIA_OK: 0,
            self.CATEGORIA_SIN_LINEAS: 0,
            self.CATEGORIA_SIN_CUADRAR: 0,
            self.CATEGORIA_OTROS: 0,
        }
        
        detalle_por_categoria = {
            self.CATEGORIA_OK: [],
            self.CATEGORIA_SIN_LINEAS: [],
            self.CATEGORIA_SIN_CUADRAR: [],
            self.CATEGORIA_OTROS: [],
        }
        
        for factura in self.facturas:
            categoria = self._clasificar_factura(factura)
            conteos[categoria] += 1
            
            # Guardar detalle
            detalle_por_categoria[categoria].append({
                'numero': factura.get('numero', '?'),
                'archivo': factura.get('archivo', '?'),
                'proveedor': factura.get('proveedor', '?'),
            })
        
        # Calcular porcentajes
        def calcular_porcentaje(valor: int, total: int) -> float:
            return (valor / total * 100) if total > 0 else 0.0
        
        self.reporte = {
            'timestamp': datetime.now().isoformat(),
            'total_facturas': total,
            'ok': conteos[self.CATEGORIA_OK],
            'sin_lineas': conteos[self.CATEGORIA_SIN_LINEAS],
            'sin_cuadrar': conteos[self.CATEGORIA_SIN_CUADRAR],
            'otros_problemas': conteos[self.CATEGORIA_OTROS],
            'porcentaje_ok': round(
                calcular_porcentaje(conteos[self.CATEGORIA_OK], total), 2
            ),
            'porcentaje_sin_lineas': round(
                calcular_porcentaje(conteos[self.CATEGORIA_SIN_LINEAS], total), 2
            ),
            'porcentaje_sin_cuadrar': round(
                calcular_porcentaje(conteos[self.CATEGORIA_SIN_CUADRAR], total), 2
            ),
            'porcentaje_otros': round(
                calcular_porcentaje(conteos[self.CATEGORIA_OTROS], total), 2
            ),
            'detalle': detalle_por_categoria,
        }
        
        return self.reporte
    
    def mostrar_reporte_consola(self) -> None:
        """Muestra reporte formateado en consola."""
        
        if not self.reporte:
            self.generar_reporte()
        
        r = self.reporte
        
        print()
        print("=" * 70)
        print("📊 REPORTE DE ESTADÍSTICAS DE PROCESAMIENTO")
        print("=" * 70)
        print()
        print(f"⏱️  Generado: {r['timestamp']}")
        print()
        print(f"📋 TOTAL FACTURAS PROCESADAS: {r['total_facturas']}")
        print()
        print("─" * 70)
        print("CLASIFICACIÓN POR CATEGORÍA")
        print("─" * 70)
        print()
        
        # OK
        print(f"✅ OK (Completas con cuadre)")
        print(f"   Cantidad: {r['ok']}")
        print(f"   Porcentaje: {r['porcentaje_ok']}%")
        print(f"   Archivos: {len(r['detalle'].get('OK', []))} listados")
        print()
        
        # SIN_LINEAS
        print(f"🟡 SIN_LINEAS (JPG o archivos con mínimos)")
        print(f"   Cantidad: {r['sin_lineas']}")
        print(f"   Porcentaje: {r['porcentaje_sin_lineas']}%")
        print(f"   Archivos: {len(r['detalle'].get('SIN_LINEAS', []))} listados")
        if r['sin_lineas'] > 0 and r['detalle'].get('SIN_LINEAS'):
            for f in r['detalle']['SIN_LINEAS'][:3]:
                print(f"     - {f['archivo']} ({f['proveedor']})")
            if len(r['detalle']['SIN_LINEAS']) > 3:
                print(f"     ... y {len(r['detalle']['SIN_LINEAS']) - 3} más")
        print()
        
        # SIN_CUADRAR
        print(f"🔴 SIN_CUADRAR (Con líneas pero cuadre fallido)")
        print(f"   Cantidad: {r['sin_cuadrar']}")
        print(f"   Porcentaje: {r['porcentaje_sin_cuadrar']}%")
        print(f"   Archivos: {len(r['detalle'].get('SIN_CUADRAR', []))} listados")
        if r['sin_cuadrar'] > 0 and r['detalle'].get('SIN_CUADRAR'):
            for f in r['detalle']['SIN_CUADRAR'][:3]:
                print(f"     - {f['archivo']} ({f['proveedor']})")
            if len(r['detalle']['SIN_CUADRAR']) > 3:
                print(f"     ... y {len(r['detalle']['SIN_CUADRAR']) - 3} más")
        print()
        
        # OTROS_PROBLEMAS
        print(f"⚠️  OTROS_PROBLEMAS (Errores de procesamiento)")
        print(f"   Cantidad: {r['otros_problemas']}")
        print(f"   Porcentaje: {r['porcentaje_otros']}%")
        print(f"   Archivos: {len(r['detalle'].get('OTROS_PROBLEMAS', []))} listados")
        if r['otros_problemas'] > 0 and r['detalle'].get('OTROS_PROBLEMAS'):
            for f in r['detalle']['OTROS_PROBLEMAS'][:3]:
                print(f"     - {f['archivo']} ({f['proveedor']})")
            if len(r['detalle']['OTROS_PROBLEMAS']) > 3:
                print(f"     ... y {len(r['detalle']['OTROS_PROBLEMAS']) - 3} más")
        print()
        
        print("─" * 70)
        print("RESUMEN")
        print("─" * 70)
        print()
        print(f"  ✅ Aceptables (OK):        {r['ok']:>4} ({r['porcentaje_ok']:>6.2f}%)")
        print(f"  🟡 Revisar (SIN_LINEAS):   {r['sin_lineas']:>4} ({r['porcentaje_sin_lineas']:>6.2f}%)")
        print(f"  🔴 Revisar (SIN_CUADRAR):  {r['sin_cuadrar']:>4} ({r['porcentaje_sin_cuadrar']:>6.2f}%)")
        print(f"  ⚠️  Revisar (OTROS):        {r['otros_problemas']:>4} ({r['porcentaje_otros']:>6.2f}%)")
        print()
        print("=" * 70)
        print()
    
    def guardar_reporte_json(self, ruta_json: str) -> None:
        """
        Guarda reporte en formato JSON.
        
        Args:
            ruta_json: Ruta del archivo JSON a crear
        """
        
        if not self.reporte:
            self.generar_reporte()
        
        # Preparar datos para JSON (asegurar serializabilidad)
        reporte_serializable = {
            'timestamp': self.reporte['timestamp'],
            'total_facturas': self.reporte['total_facturas'],
            'ok': self.reporte['ok'],
            'sin_lineas': self.reporte['sin_lineas'],
            'sin_cuadrar': self.reporte['sin_cuadrar'],
            'otros_problemas': self.reporte['otros_problemas'],
            'porcentaje_ok': self.reporte['porcentaje_ok'],
            'porcentaje_sin_lineas': self.reporte['porcentaje_sin_lineas'],
            'porcentaje_sin_cuadrar': self.reporte['porcentaje_sin_cuadrar'],
            'porcentaje_otros': self.reporte['porcentaje_otros'],
            'detalle': self.reporte.get('detalle', {}),
        }
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_json) or ".", exist_ok=True)
        
        # Guardar
        with open(ruta_json, 'w', encoding='utf-8') as f:
            json.dump(reporte_serializable, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Reporte JSON guardado: {ruta_json}")
    
    def guardar_reporte_texto(self, ruta_txt: str) -> None:
        """
        Guarda reporte en formato texto plano.
        
        Args:
            ruta_txt: Ruta del archivo TXT a crear
        """
        
        if not self.reporte:
            self.generar_reporte()
        
        r = self.reporte
        
        lineas = [
            "=" * 70,
            "REPORTE DE ESTADÍSTICAS DE PROCESAMIENTO",
            "=" * 70,
            "",
            f"Timestamp: {r['timestamp']}",
            "",
            f"TOTAL FACTURAS: {r['total_facturas']}",
            "",
            "CLASIFICACIÓN:",
            f"  OK (completas):        {r['ok']:>4} ({r['porcentaje_ok']:>6.2f}%)",
            f"  SIN_LINEAS (JPG/min):   {r['sin_lineas']:>4} ({r['porcentaje_sin_lineas']:>6.2f}%)",
            f"  SIN_CUADRAR (fallidos): {r['sin_cuadrar']:>4} ({r['porcentaje_sin_cuadrar']:>6.2f}%)",
            f"  OTROS_PROBLEMAS:        {r['otros_problemas']:>4} ({r['porcentaje_otros']:>6.2f}%)",
            "",
            "=" * 70,
        ]
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_txt) or ".", exist_ok=True)
        
        # Guardar
        with open(ruta_txt, 'w', encoding='utf-8') as f:
            f.write("\n".join(lineas))
        
        print(f"✅ Reporte TXT guardado: {ruta_txt}")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("✅ estadisticas.py v1.0 - Generador de reportes de calidad")
    print()
    
    # Crear datos de ejemplo
    datos_ejemplo = [
        {
            'numero': '3001',
            'archivo': '3001_3T25_07_FABEIRO_SL_TF.pdf',
            'proveedor': 'FABEIRO_SL',
            'lineas': [1, 2, 3],
            'cuadre': 'OK',
            'valido': True,
        },
        {
            'numero': '3002',
            'archivo': '3002_3T25_07_COOPERATIVA_FS.jpg',
            'proveedor': 'COOPERATIVA_MONTBRIONE',
            'lineas': [],
            'cuadre': 'SIN_LINEAS',
            'valido': True,
        },
        {
            'numero': '3003',
            'archivo': '3003_3T25_07_LA_ROSQUILLERIA_FS.pdf',
            'proveedor': 'LA_ROSQUILLERIA',
            'lineas': [1, 2],
            'cuadre': 'DIFERENCIA_€0.15',
            'valido': True,
        },
        {
            'numero': '3004',
            'archivo': '3004_corrupted.pdf',
            'proveedor': 'DESCONOCIDO',
            'lineas': [],
            'cuadre': 'ERROR',
            'valido': False,
            'errores': ['Archivo corrupto'],
        },
    ]
    
    # Generar reporte
    generador = GeneradorEstadisticas(datos_ejemplo)
    reporte = generador.generar_reporte()
    
    # Mostrar en consola
    generador.mostrar_reporte_consola()
    
    # Guardar JSON (ejemplo)
    print("Ejemplo de guardado (sin ejecutar):")
    print("  generador.guardar_reporte_json('reporte.json')")
    print("  generador.guardar_reporte_texto('reporte.txt')")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLASIFICADOR DE MOVIMIENTOS BANCARIOS
Lee ficheros N43 de Sabadell y clasifica cada movimiento

Versión: 2.0
Autor: Tasca Barea + Claude
Propósito: Procesar movimientos bancarios y clasificarlos automáticamente
"""

import sys
import os
from pathlib import Path

# Añadir ruta del proyecto
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from banco.router import clasificar_movimiento


def seleccionar_archivo():
    """Seleccionar archivo de entrada interactivamente"""
    archivo_default = "PROVEEDOR 2025.xlsx"
    
    print("\n📁 SELECCIONAR ARCHIVO\n")
    print(f"Nombre por defecto: {archivo_default}")
    archivo = input("¿Cómo se llama tu archivo (o Enter para usar el default)?\n> ").strip()
    
    if not archivo:
        archivo = archivo_default
    
    if not os.path.exists(archivo):
        print(f"\n❌ No se encuentra el archivo '{archivo}'")
        return None
    
    print(f"✅ Archivo encontrado: {archivo}")
    return archivo


def seleccionar_hoja(excel_file):
    """Seleccionar qué hoja procesar"""
    hojas_disponibles = excel_file.sheet_names
    
    if "Tasca" not in hojas_disponibles or "Comestibles" not in hojas_disponibles:
        print("❌ No se encuentran las hojas 'Tasca' y 'Comestibles' en el archivo.")
        return None, None
    
    print("\n📋 SELECCIONAR HOJA\n")
    print("Hojas disponibles:")
    print("  1. Tasca")
    print("  2. Comestibles")
    
    opcion = input("¿Cuál deseas procesar? (1 o 2, default=1): ").strip()
    
    hoja = "Comestibles" if opcion == "2" else "Tasca"
    print(f"✅ Procesando hoja: {hoja}")
    
    return hoja, hojas_disponibles


def procesar_movimientos(archivo, hoja):
    """Procesar y clasificar todos los movimientos"""
    try:
        print(f"\n⏳ Cargando datos de {archivo} (hoja: {hoja})...")
        
        df_mov = pd.read_excel(archivo, sheet_name=hoja)
        df_fact = pd.read_excel(archivo, sheet_name="Facturas")
        df_fuzzy = pd.read_excel("DiccionarioEmisorTitulo.xlsx")
        
        print(f"✅ Datos cargados: {len(df_mov)} movimientos, {len(df_fact)} facturas")
        
        print("\n⏳ Clasificando movimientos...")
        
        resultados = []
        revisar_count = 0
        
        for idx, row in df_mov.iterrows():
            concepto = row["Concepto"]
            importe = row["Importe"]
            f_valor = pd.to_datetime(row["F. Valor"], errors="coerce")
            f_oper = pd.to_datetime(row.get("F. Operativa", f_valor), errors="coerce")
            
            try:
                cod, detalle, protocolo = clasificar_movimiento(
                    concepto, importe, f_valor, f_oper,
                    df_fact, df_fuzzy, None, df_mov, set()
                )
            except Exception as e:
                print(f"⚠️  Error clasificando movimiento #{idx}: {e}")
                cod, detalle, protocolo = "REVISAR", f"Error: {str(e)}", "ERROR"
            
            resultado = {
                "#": row["#"],
                "F. Valor": row["F. Valor"],
                "Concepto": concepto,
                "Importe": importe,
                "CLASIFICACION_TIPO": cod,
                "CLASIFICACION_DETALLE": detalle,
                "PROTOCOLO_APLICADO": protocolo
            }
            
            resultados.append(resultado)
            
            if cod == "REVISAR":
                revisar_count += 1
            
            # Mostrar progreso cada 50 movimientos
            if (idx + 1) % 50 == 0:
                print(f"  {idx + 1}/{len(df_mov)} movimientos procesados...")
        
        df_out = pd.DataFrame(resultados)
        
        print(f"\n✅ Clasificación completada")
        print(f"  • Total procesados: {len(resultados)}")
        print(f"  • Para revisar: {revisar_count}")
        print(f"  • Tasa clasificación: {((len(resultados)-revisar_count)/len(resultados)*100):.1f}%")
        
        return df_out
    
    except Exception as e:
        print(f"\n❌ Error cargando/procesando datos: {e}")
        return None


def guardar_resultado(df_out, archivo_salida="clasificados.xlsx"):
    """Guardar resultado a Excel"""
    if df_out is None:
        print("❌ No hay datos para guardar")
        return False
    
    try:
        if os.path.exists(archivo_salida):
            respuesta = input(f"\n⚠️  '{archivo_salida}' ya existe. ¿Sobrescribir? (s/N): ").strip().lower()
            if respuesta != "s":
                print("❌ Operación cancelada")
                return False
        
        df_out.to_excel(archivo_salida, index=False)
        print(f"\n✅ Archivo generado: {archivo_salida}")
        
        # Mostrar resumen
        print(f"\n📊 RESUMEN DEL ARCHIVO:")
        print(f"  • Filas: {len(df_out)}")
        print(f"  • Columnas: {len(df_out.columns)}")
        
        # Contar tipos
        tipos = df_out["CLASIFICACION_TIPO"].value_counts()
        print(f"\n  Tipos de clasificación:")
        for tipo, count in tipos.items():
            print(f"    • {tipo}: {count}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
        return False


def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("  🏦 CLASIFICADOR DE MOVIMIENTOS BANCARIOS")
    print("=" * 60)
    
    # Seleccionar archivo
    archivo = seleccionar_archivo()
    if not archivo:
        return False
    
    # Seleccionar hoja
    try:
        excel_file = pd.ExcelFile(archivo)
        hoja, hojas_disponibles = seleccionar_hoja(excel_file)
        if not hoja:
            return False
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return False
    
    # Procesar movimientos
    df_out = procesar_movimientos(archivo, hoja)
    if df_out is None:
        return False
    
    # Guardar resultado
    if not guardar_resultado(df_out):
        return False
    
    print("\n✅ Proceso completado correctamente")
    return True


if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

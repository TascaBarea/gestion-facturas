"""
Parser de ficheros Norma 43 (AEB)

Lee ficheros N43 del Banco Sabadell y los convierte a DataFrame.

ESTRUCTURA N43:
- Registro 11: Cabecera de cuenta
- Registro 22: Movimiento (fecha, importe, signo)
- Registro 23: Concepto (descripción del movimiento)
- Registro 33: Final de cuenta
- Registro 88: Final de fichero

CUENTAS CONFIGURADAS:
- 0001844495: TASCA
- 0001992404: COMESTIBLES

Uso:
    from banco.parser_n43 import leer_n43, leer_multiples_n43
    
    # Un solo fichero
    df = leer_n43("archivo.n43")
    
    # Varios ficheros
    df = leer_multiples_n43(["archivo1.n43", "archivo2.n43"])

Autor: Claude + Tasca
Fecha: 08/01/2026
Versión: 1.0
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

CUENTAS_CONOCIDAS = {
    "0001844495": "TASCA",
    "0001992404": "COMESTIBLES",
}

ENCODING_N43 = "latin-1"  # Codificación típica de ficheros bancarios españoles


# =============================================================================
# FUNCIONES DE PARSING
# =============================================================================

def parsear_fecha_n43(fecha_str: str) -> Optional[datetime]:
    """
    Convierte fecha N43 (AAMMDD) a datetime.
    
    Args:
        fecha_str: Fecha en formato AAMMDD (ej: "251006" = 2025-10-06)
    
    Returns:
        datetime o None si no se puede parsear
    """
    try:
        if len(fecha_str) != 6:
            return None
        año = 2000 + int(fecha_str[0:2])
        mes = int(fecha_str[2:4])
        dia = int(fecha_str[4:6])
        return datetime(año, mes, dia)
    except (ValueError, IndexError):
        return None


def parsear_importe_n43(importe_str: str, signo: str) -> float:
    """
    Convierte importe N43 a float.
    
    Args:
        importe_str: Importe en céntimos (14 dígitos)
        signo: "1" = cargo (negativo), "2" = abono (positivo)
    
    Returns:
        Importe como float con signo
    """
    try:
        importe = int(importe_str) / 100
        if signo == "1":  # Cargo = negativo
            importe = -importe
        return importe
    except ValueError:
        return 0.0


def parsear_registro_11(linea: str) -> Dict:
    """
    Parsea registro 11 (cabecera de cuenta).
    
    Estructura:
    - Pos 1-2: Código registro (11)
    - Pos 3-6: Código banco
    - Pos 7-10: Código oficina
    - Pos 11-20: Número cuenta
    - Pos 21-26: Fecha inicio (AAMMDD)
    - Pos 27-32: Fecha fin (AAMMDD)
    - Pos 33: Signo saldo inicial
    - Pos 34-47: Saldo inicial
    - Pos 48-51: Código divisa
    - Pos 52-...: Nombre cuenta
    """
    return {
        "codigo_banco": linea[2:6].strip(),
        "codigo_oficina": linea[6:10].strip(),
        "numero_cuenta": linea[10:20].strip(),
        "fecha_inicio": parsear_fecha_n43(linea[20:26]),
        "fecha_fin": parsear_fecha_n43(linea[26:32]),
        "saldo_inicial": int(linea[33:47]) / 100 if linea[32] == "2" else -int(linea[33:47]) / 100,
        "nombre_cuenta": linea[51:].strip(),
    }


def parsear_registro_22(linea: str) -> Dict:
    """
    Parsea registro 22 (movimiento).
    
    Estructura:
    - Pos 1-2: Código registro (22)
    - Pos 3-6: Libre
    - Pos 7-10: Oficina origen
    - Pos 11-16: Fecha operación (AAMMDD)
    - Pos 17-22: Fecha valor (AAMMDD)
    - Pos 23-24: Concepto común
    - Pos 25-27: Concepto propio
    - Pos 28: Signo (1=Cargo, 2=Abono)
    - Pos 29-42: Importe (14 dígitos, 2 decimales implícitos)
    - Pos 43-52: Nº documento
    - Pos 53-64: Referencia 1
    - Pos 65-80: Referencia 2
    """
    signo = linea[27:28]
    importe_str = linea[28:42]
    
    return {
        "oficina_origen": linea[6:10].strip(),
        "fecha_operativa": parsear_fecha_n43(linea[10:16]),
        "fecha_valor": parsear_fecha_n43(linea[16:22]),
        "concepto_comun": linea[22:24].strip(),
        "concepto_propio": linea[24:27].strip(),
        "signo": signo,
        "importe": parsear_importe_n43(importe_str, signo),
        "num_documento": linea[42:52].strip(),
        "referencia_1": linea[52:64].strip(),
        "referencia_2": linea[64:80].strip() if len(linea) >= 80 else "",
    }


def parsear_registro_23(linea: str) -> Tuple[str, str]:
    """
    Parsea registro 23 (concepto).
    
    Estructura:
    - Pos 1-2: Código registro (23)
    - Pos 3-4: Número de dato (01-05)
    - Pos 5-...: Concepto (texto libre)
    
    Returns:
        Tupla (numero_dato, concepto)
    """
    num_dato = linea[2:4]
    concepto = linea[4:].strip()
    return num_dato, concepto


def parsear_registro_33(linea: str) -> Dict:
    """
    Parsea registro 33 (final de cuenta).
    
    Estructura:
    - Pos 1-2: Código registro (33)
    - Pos 3-6: Código banco
    - Pos 7-10: Código oficina  
    - Pos 11-20: Número cuenta
    - Pos 21-25: Número de apuntes debe
    - Pos 26-39: Total debe
    - Pos 40-44: Número de apuntes haber
    - Pos 45-58: Total haber
    - Pos 59: Signo saldo final
    - Pos 60-73: Saldo final
    """
    return {
        "num_apuntes_debe": int(linea[20:25]),
        "total_debe": int(linea[25:39]) / 100,
        "num_apuntes_haber": int(linea[39:44]),
        "total_haber": int(linea[44:58]) / 100,
        "saldo_final": int(linea[59:73]) / 100 if linea[58] == "2" else -int(linea[59:73]) / 100,
    }


# =============================================================================
# FUNCIÓN PRINCIPAL DE LECTURA
# =============================================================================

def leer_n43(ruta_archivo: str, encoding: str = ENCODING_N43) -> pd.DataFrame:
    """
    Lee un fichero N43 y lo convierte a DataFrame.
    
    Args:
        ruta_archivo: Ruta al fichero .n43
        encoding: Codificación del fichero (por defecto latin-1)
    
    Returns:
        DataFrame con columnas:
        - #: Número secuencial
        - F. Operativa: Fecha de operación
        - F. Valor: Fecha valor
        - Concepto: Descripción del movimiento
        - Importe: Importe con signo
        - Saldo: (vacío, se calcularía después)
        - Referencia 1: Primera referencia
        - Referencia 2: Segunda referencia
        - Cuenta: Número de cuenta
        - Negocio: TASCA o COMESTIBLES
        - Archivo: Nombre del fichero origen
    """
    ruta = Path(ruta_archivo)
    
    if not ruta.exists():
        raise FileNotFoundError(f"No se encuentra el fichero: {ruta}")
    
    if not ruta.suffix.lower() == ".n43":
        print(f"⚠️  Advertencia: El fichero no tiene extensión .n43: {ruta.name}")
    
    # Leer fichero
    with open(ruta, "r", encoding=encoding) as f:
        lineas = f.readlines()
    
    # Variables de estado
    cabecera = None
    movimientos = []
    movimiento_actual = None
    conceptos_actuales = []
    numero_secuencial = 1
    
    for linea in lineas:
        linea = linea.rstrip("\r\n")
        
        if len(linea) < 2:
            continue
        
        tipo_registro = linea[0:2]
        
        if tipo_registro == "11":
            # Cabecera de cuenta
            cabecera = parsear_registro_11(linea)
        
        elif tipo_registro == "22":
            # Nuevo movimiento - guardar el anterior si existe
            if movimiento_actual is not None:
                movimiento_actual["Concepto"] = " ".join(conceptos_actuales)
                movimientos.append(movimiento_actual)
            
            # Parsear nuevo movimiento
            datos = parsear_registro_22(linea)
            
            # Determinar negocio por cuenta
            cuenta = cabecera["numero_cuenta"] if cabecera else ""
            negocio = CUENTAS_CONOCIDAS.get(cuenta, "DESCONOCIDO")
            
            movimiento_actual = {
                "#": numero_secuencial,
                "F. Operativa": datos["fecha_operativa"],
                "F. Valor": datos["fecha_valor"],
                "Concepto": "",  # Se llenará con registros 23
                "Importe": datos["importe"],
                "Saldo": None,
                "Referencia 1": datos["referencia_1"],
                "Referencia 2": datos["referencia_2"],
                "Cuenta": cuenta,
                "Negocio": negocio,
                "Archivo": ruta.name,
            }
            conceptos_actuales = []
            numero_secuencial += 1
        
        elif tipo_registro == "23":
            # Concepto del movimiento
            num_dato, concepto = parsear_registro_23(linea)
            if concepto:
                conceptos_actuales.append(concepto)
        
        elif tipo_registro == "33":
            # Final de cuenta - guardar último movimiento
            if movimiento_actual is not None:
                movimiento_actual["Concepto"] = " ".join(conceptos_actuales)
                movimientos.append(movimiento_actual)
                movimiento_actual = None
                conceptos_actuales = []
        
        elif tipo_registro == "88":
            # Final de fichero
            pass
    
    # Por si no hay registro 33
    if movimiento_actual is not None:
        movimiento_actual["Concepto"] = " ".join(conceptos_actuales)
        movimientos.append(movimiento_actual)
    
    # Crear DataFrame
    df = pd.DataFrame(movimientos)
    
    # Formatear fechas
    if not df.empty:
        df["F. Operativa"] = pd.to_datetime(df["F. Operativa"])
        df["F. Valor"] = pd.to_datetime(df["F. Valor"])
    
    return df


def leer_multiples_n43(rutas: List[str], encoding: str = ENCODING_N43) -> pd.DataFrame:
    """
    Lee múltiples ficheros N43 y los combina en un solo DataFrame.
    
    Args:
        rutas: Lista de rutas a ficheros .n43
        encoding: Codificación de los ficheros
    
    Returns:
        DataFrame combinado con todos los movimientos
    """
    dfs = []
    
    for ruta in rutas:
        try:
            df = leer_n43(ruta, encoding)
            dfs.append(df)
            print(f"  ✓ {Path(ruta).name}: {len(df)} movimientos")
        except Exception as e:
            print(f"  ✗ {Path(ruta).name}: Error - {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    # Combinar y renumerar
    df_combinado = pd.concat(dfs, ignore_index=True)
    df_combinado["#"] = range(1, len(df_combinado) + 1)
    
    return df_combinado


def buscar_n43_en_carpeta(carpeta: str, patron: str = "*.n43") -> List[Path]:
    """
    Busca ficheros N43 en una carpeta.
    
    Args:
        carpeta: Ruta a la carpeta
        patron: Patrón de búsqueda (por defecto *.n43)
    
    Returns:
        Lista de rutas encontradas
    """
    carpeta_path = Path(carpeta)
    
    if not carpeta_path.exists():
        return []
    
    return sorted(carpeta_path.glob(patron))


def detectar_cuenta(ruta_archivo: str) -> Tuple[str, str]:
    """
    Detecta la cuenta y negocio de un fichero N43 sin parsearlo completo.
    
    Args:
        ruta_archivo: Ruta al fichero
    
    Returns:
        Tupla (numero_cuenta, negocio)
    """
    with open(ruta_archivo, "r", encoding=ENCODING_N43) as f:
        for linea in f:
            if linea.startswith("11"):
                cuenta = linea[10:20].strip()
                negocio = CUENTAS_CONOCIDAS.get(cuenta, "DESCONOCIDO")
                return cuenta, negocio
    
    return "", "DESCONOCIDO"


# =============================================================================
# FUNCIONES DE EXPORTACIÓN
# =============================================================================

def exportar_a_excel(df: pd.DataFrame, ruta_salida: str, nombre_hoja: str = "Movimientos"):
    """
    Exporta DataFrame de movimientos a Excel.
    
    Args:
        df: DataFrame con movimientos
        ruta_salida: Ruta del archivo Excel de salida
        nombre_hoja: Nombre de la hoja
    """
    # Formatear fechas para Excel
    df_export = df.copy()
    df_export["F. Operativa"] = df_export["F. Operativa"].dt.strftime("%d/%m/%Y")
    df_export["F. Valor"] = df_export["F. Valor"].dt.strftime("%d/%m/%Y")
    
    df_export.to_excel(ruta_salida, sheet_name=nombre_hoja, index=False)
    print(f"✓ Exportado: {ruta_salida} ({len(df)} movimientos)")


def separar_por_negocio(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Separa movimientos por negocio (TASCA, COMESTIBLES).
    
    Args:
        df: DataFrame con columna "Negocio"
    
    Returns:
        Diccionario {negocio: DataFrame}
    """
    resultado = {}
    
    for negocio in df["Negocio"].unique():
        df_negocio = df[df["Negocio"] == negocio].copy()
        df_negocio["#"] = range(1, len(df_negocio) + 1)
        resultado[negocio] = df_negocio
    
    return resultado


# =============================================================================
# MAIN - PRUEBAS
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("PARSER N43 - Prueba")
    print("=" * 60)
    
    # Buscar ficheros de prueba
    rutas_prueba = [
        "/mnt/user-data/uploads/0259_0001992404_01012026.n43",
        "/mnt/user-data/uploads/0259_0001844495_01122025.n43",
    ]
    
    for ruta in rutas_prueba:
        if Path(ruta).exists():
            print(f"\n📄 Procesando: {Path(ruta).name}")
            
            # Detectar cuenta
            cuenta, negocio = detectar_cuenta(ruta)
            print(f"   Cuenta: {cuenta} ({negocio})")
            
            # Leer fichero
            df = leer_n43(ruta)
            print(f"   Movimientos: {len(df)}")
            
            # Mostrar primeros movimientos
            if not df.empty:
                print(f"\n   Primeros 5 movimientos:")
                for _, row in df.head(5).iterrows():
                    fecha = row["F. Valor"].strftime("%d/%m/%Y")
                    concepto = row["Concepto"][:50] + "..." if len(row["Concepto"]) > 50 else row["Concepto"]
                    print(f"   {fecha} | {row['Importe']:>10.2f}€ | {concepto}")

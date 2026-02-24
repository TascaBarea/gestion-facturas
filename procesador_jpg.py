# -*- coding: utf-8 -*-
"""
Procesador JPG v1.0 - NUEVO MÓDULO (Sesión 12/01/2026)

✅ FUNCIONALIDAD:
- Procesa archivos JPG sin extractor dedicado
- Extrae MÍNIMOS (#, FECHA, PROVEEDOR) del nombre del archivo
- Valida estructura: #_TRIMESTRE_FECHA[_CÓDIGO]_PROVEEDOR_TIPO.EXT
- Soporta códigos de cuenta de 8 dígitos (gestoría)

✅ ESTRUCTURA NOMBRE ARCHIVO:
  #_TRIMESTRE_FECHA[_CÓDIGO]_PROVEEDOR_TIPO.EXT
  
  Ejemplos:
  - 3001_3T25_07_40000011_FABEIRO_SL_TF.pdf
  - 3002_3T25_0731_COOPERATIVA_MONTBRIONE_FS.jpg
  - 3003_3T25_07_LA_ROSQUILLERIA_FS.jpg (sin código)
  
  Partes:
  - #: 3001 (número factura)
  - TRIMESTRE: 3T25 (Q3 2025)
  - FECHA: 07 (mes) o 0731 (día/mes)
  - CÓDIGO: 40000011 (nº cuenta gestoría - OPCIONAL)
  - PROVEEDOR: FABEIRO_SL
  - TIPO: TF (Factura), FS (Factura Simplificada)
  - EXT: .pdf, .jpg

✅ SALIDA:
  {
    'numero': '3001',
    'fecha': '01/07/2025',  # Convertida a DD/MM/YYYY
    'proveedor': 'FABEIRO_SL',
    'codigo_cuenta': '40000011',  # opcional, '' si no existe
    'archivo': 'nombre_archivo.jpg',
    'tipo': 'MINIMOS',
    'lineas': [],  # Vacío (no hay extractor)
    'total': None,
    'cuadre': 'SIN_LINEAS',
    'referencia': '',
    'valido': True/False,
    'errores': [],
  }

Uso:
    from procesador_jpg import ProcesadorJPG
    
    procesador = ProcesadorJPG("3001_3T25_07_FABEIRO_SL_TF.jpg")
    datos = procesador.procesar_archivo_minimo()
    
    if datos['valido']:
        print(f"Factura #{datos['numero']} de {datos['proveedor']}")
    else:
        print(f"Errores: {datos['errores']}")
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class ProcesadorJPG:
    """Procesador de archivos JPG/PDF sin extractor dedicado."""
    
    # Patrón regex para validar estructura de nombre
    # #_TRIMESTRE_FECHA[_CÓDIGO]_PROVEEDOR_TIPO.EXT
    PATRON_NOMBRE = re.compile(
        r"^(\d+)"                           # Grupo 1: # (número factura, 1+ dígitos)
        r"_"
        r"([1-4]T\d{2})"                    # Grupo 2: TRIMESTRE (1-4T + 2 dígitos año)
        r"_"
        r"(\d{2}(?:\d{2})?)"                # Grupo 3: FECHA (MM o DDMM)
        r"(?:_(\d{8}))?"                    # Grupo 4: CÓDIGO (opcional, 8 dígitos)
        r"_"
        r"([A-Z0-9_]+?)"                    # Grupo 5: PROVEEDOR (mayúsculas, números, guiones)
        r"_"
        r"([A-Z]{1,3})"                     # Grupo 6: TIPO (TF, FS, etc., 1-3 letras)
        r"(?:\.jpg|\.pdf|\.JPG|\.PDF)?$",   # Extensión (opcional en patrón, se verifica por separado)
        re.IGNORECASE
    )
    
    def __init__(self, ruta_archivo: str):
        """
        Inicializa procesador con ruta de archivo.
        
        Args:
            ruta_archivo: Ruta completa del archivo (puede ser ruta absoluta)
        """
        self.ruta_archivo = str(ruta_archivo)
        self.nombre_archivo = os.path.basename(self.ruta_archivo)
        self.nombre_sin_ext, self.extension = os.path.splitext(self.nombre_archivo)
        self.errores: List[str] = []
    
    def validar_nombre(self) -> bool:
        """
        Valida que el nombre del archivo siga el patrón correcto.
        
        Returns:
            bool: True si válido, False si no
        """
        self.errores = []
        
        # Validar extensión
        if self.extension.lower() not in ['.jpg', '.pdf']:
            self.errores.append(f"Extensión inválida: {self.extension}")
            return False
        
        # Validar patrón
        if not self.PATRON_NOMBRE.match(self.nombre_sin_ext):
            self.errores.append(
                f"Nombre no sigue patrón: #_TRIMESTRE_FECHA[_CÓDIGO]_PROVEEDOR_TIPO"
            )
            return False
        
        return True
    
    def extraer_numero(self) -> str:
        """Extrae número de factura del nombre."""
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        return m.group(1) if m else ""
    
    def extraer_trimestre(self) -> str:
        """Extrae trimestre del nombre (ej: 3T25)."""
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        return m.group(2) if m else ""
    
    def extraer_fecha_del_nombre(self) -> str:
        """
        Extrae fecha del nombre y la convierte a DD/MM/YYYY.
        
        Soporta:
        - MM: 07 → 01/07/2025
        - DDMM: 0731 → 31/07/2025
        
        Returns:
            str: Fecha en formato DD/MM/YYYY, '' si no puede extraerse
        """
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        if not m:
            return ""
        
        fecha_str = m.group(3)  # "07" o "0731"
        trimestre = m.group(2)  # "3T25"
        
        try:
            # Extraer año del trimestre (ej: "3T25" → 2025)
            ano_2digitos = int(trimestre[2:])
            ano = 2000 + ano_2digitos if ano_2digitos < 50 else 1900 + ano_2digitos
            
            if len(fecha_str) == 2:
                # Formato MM: usar día 1
                mes = int(fecha_str)
                dia = 1
            elif len(fecha_str) == 4:
                # Formato DDMM
                dia = int(fecha_str[:2])
                mes = int(fecha_str[2:])
            else:
                return ""
            
            # Validar rango
            if not (1 <= mes <= 12) or not (1 <= dia <= 31):
                return ""
            
            # Crear fecha y devolver en formato DD/MM/YYYY
            fecha_obj = datetime(ano, mes, dia)
            return fecha_obj.strftime("%d/%m/%Y")
        
        except (ValueError, IndexError):
            return ""
    
    def extraer_codigo_cuenta(self) -> str:
        """
        Extrae código de cuenta (8 dígitos, opcional).
        
        Returns:
            str: Código de 8 dígitos, '' si no existe o no válido
        """
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        if not m:
            return ""
        
        codigo = m.group(4)  # Grupo 4 es opcional
        return codigo if codigo and len(codigo) == 8 else ""
    
    def extraer_proveedor(self) -> str:
        """Extrae nombre proveedor del nombre."""
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        return m.group(5) if m else ""
    
    def extraer_tipo(self) -> str:
        """Extrae tipo de documento (TF, FS, etc.)."""
        m = self.PATRON_NOMBRE.match(self.nombre_sin_ext)
        return m.group(6) if m else ""
    
    def procesar_archivo_minimo(self) -> Dict[str, Any]:
        """
        Procesa archivo y extrae mínimos.
        
        Returns:
            dict: Información extraída con estructura:
            {
                'numero': str,
                'fecha': str (DD/MM/YYYY),
                'proveedor': str,
                'codigo_cuenta': str (8 dígitos, '' si N/A),
                'archivo': str,
                'tipo': 'MINIMOS',
                'lineas': [],
                'total': None,
                'cuadre': 'SIN_LINEAS',
                'referencia': '',
                'valido': bool,
                'errores': list,
            }
        """
        
        # Validar nombre
        valido = self.validar_nombre()
        
        return {
            'numero': self.extraer_numero(),
            'fecha': self.extraer_fecha_del_nombre(),
            'proveedor': self.extraer_proveedor(),
            'codigo_cuenta': self.extraer_codigo_cuenta(),
            'archivo': self.nombre_archivo,
            'tipo': 'MINIMOS',
            'lineas': [],
            'total': None,
            'cuadre': 'SIN_LINEAS',
            'referencia': '',
            'trimestre': self.extraer_trimestre(),
            'tipo_doc': self.extraer_tipo(),
            'valido': valido,
            'errores': self.errores,
        }


# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def procesar_jpg_archivo(ruta_archivo: str) -> Dict[str, Any]:
    """
    Procesa un archivo JPG y retorna datos mínimos.
    
    Args:
        ruta_archivo: Ruta del archivo
    
    Returns:
        dict: Datos extraídos (ver ProcesadorJPG.procesar_archivo_minimo)
    """
    procesador = ProcesadorJPG(ruta_archivo)
    return procesador.procesar_archivo_minimo()


def procesar_carpeta_jpg(
    ruta_carpeta: str,
    extension: str = ".jpg"
) -> List[Dict[str, Any]]:
    """
    Procesa todos los archivos JPG de una carpeta.
    
    Args:
        ruta_carpeta: Ruta de la carpeta
        extension: Extensión a buscar (.jpg, .pdf, etc.)
    
    Returns:
        list: Lista de dicts con datos procesados
    """
    resultados = []
    carpeta = Path(ruta_carpeta)
    
    if not carpeta.exists():
        return []
    
    for archivo in carpeta.glob(f"*{extension}"):
        datos = procesar_jpg_archivo(str(archivo))
        resultados.append(datos)
    
    return resultados


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("✅ procesador_jpg.py v1.0 - Procesador de archivos sin extractor")
    print()
    print("ESTRUCTURA NOMBRE ESPERADO:")
    print("  #_TRIMESTRE_FECHA[_CÓDIGO]_PROVEEDOR_TIPO.EXT")
    print()
    print("EJEMPLOS VÁLIDOS:")
    ejemplos = [
        "3001_3T25_07_40000011_FABEIRO_SL_TF.pdf",
        "3002_3T25_0731_COOPERATIVA_MONTBRIONE_FS.jpg",
        "3003_3T25_07_LA_ROSQUILLERIA_FS.jpg",
    ]
    
    for ejemplo in ejemplos:
        proc = ProcesadorJPG(ejemplo)
        datos = proc.procesar_archivo_minimo()
        
        print(f"\n  {ejemplo}")
        print(f"    Válido: {datos['valido']}")
        print(f"    Número: {datos['numero']}")
        print(f"    Fecha: {datos['fecha']}")
        print(f"    Proveedor: {datos['proveedor']}")
        print(f"    Código cuenta: {datos['codigo_cuenta']}")
        print(f"    Trimestre: {datos['trimestre']}")
        print(f"    Tipo: {datos['tipo_doc']}")
        
        if datos['errores']:
            print(f"    Errores: {', '.join(datos['errores'])}")
    
    print()
    print("EJEMPLOS INVÁLIDOS:")
    invalidos = [
        "factura_sin_patron.jpg",
        "3001_julio_2025_FABEIRO.jpg",
        "3001_3T25_FABEIRO.jpg",  # Falta FECHA
    ]
    
    for ejemplo in invalidos:
        proc = ProcesadorJPG(ejemplo)
        datos = proc.procesar_archivo_minimo()
        
        print(f"\n  {ejemplo}")
        print(f"    Válido: {datos['valido']}")
        if datos['errores']:
            print(f"    Errores: {datos['errores'][0]}")

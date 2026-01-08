#!/usr/bin/env python3
"""
PARSEAR FACTURAS
================
Sistema modular para extraccion y procesamiento de facturas.

CAMBIOS v5.16 (07/01/2026):
- NUEVO: Asignación automática TEMP001, TEMP002... para archivos sin número de gestoría
- Los archivos tipo "4T25 1020 PROVEEDOR TF.pdf" reciben TEMP001_4T25, etc.
- Contador TEMP reinicia por trimestre dentro de cada ejecución
- FIX: Extractores BERZAL, MADRUEÑO, ECOMS, EMBUTIDOS FERRIOL corregidos

CAMBIOS v5.12 (04/01/2026):
- NUEVO: Sistema inteligente de normalización de proveedores
- NUEVO: 150+ alias auto-generados para unificar proveedores fragmentados
- NUEVO: Módulo identificador_proveedor.py con fuzzy matching
- NUEVO: Detección por CIF del PDF como prioridad
- FIX: Proveedores como "2T25 0512 CERES" ahora se normalizan a "CERES"
- FIX: Typos como "VIRGEN DE LA SIERA" se corrigen automáticamente

CAMBIOS v5.11 (04/01/2026):
- SOPORTE OCR: Extractores con metodo_pdf='ocr' procesan imágenes
- SOPORTE JPG: Ahora busca archivos .pdf, .jpg, .jpeg, .png
- Nuevos extractores OCR: tirso.py, la_cuchara.py
- Fix bug doble IVA en bernal.py

CAMBIOS v5.10 (04/01/2026):
- Mensaje SIN_PROVEEDOR reemplazado por mensajes más específicos:
  - SIN_EXTRACTOR: No hay extractor para este proveedor
  - SIN_CATEGORIA: Hay extractor pero artículo no está en diccionario
- Nuevo extractor: EL CARRASCAL (Jose Luis Sánchez)

CAMBIOS v5.9 (02/01/2026):
- FIX: categoria_fija del extractor se usa como fallback automático
- Extractores con categoria_fija ya no requieren incluirla en cada línea
- Resuelve SIN_PROVEEDOR en YOIGO, MOLLETES, CELONIS, etc.

CAMBIOS v5.8 (02/01/2026):
- FIX: Categorías hardcodeadas en extractores ahora se respetan
- Condición corregida: solo requiere categoria (no id_categoria)
- Proveedores con categoría definida ya no muestran SIN_PROVEEDOR

CAMBIOS v5.7 (01/01/2026):
- Alias añadidos: TIRSO PAPEL Y BOLSAS (6 variantes)
- Alias añadidos: LA BARRA DULCE S.L.
- Extractores nuevos: tirso_papel_bolsas.py (OCR), la_barra_dulce.py

CAMBIOS v5.7 (01/01/2026):
- ALIAS_DICCIONARIO ampliado (DEBORA, HERNÁNDEZ, SERRRIN, etc.)
- Soporte para retenciones IRPF (JAIME FERNANDEZ 19%, DEBORA 1%, etc.)
- Mejor detección de proveedor en archivos mal nombrados
- normalizar_proveedor() mejorada (quita ATRASADA, prefijos de trimestre)
- buscar_proveedor_en_nombre() nueva función

CAMBIOS v5.5 (01/01/2026):
- Limpieza automática de __pycache__ para cargar extractores actualizados
- Soporte BM SUPERMERCADOS (IVA incluido → base)
- Soporte LAVAPIES mejorado (IVA deducido de factura)

CAMBIOS v5.2 (30/12/2025):
- Prorrateo de portes mejorado para IVAs mixtos
- Maneja productos IVA 4%/10% con portes IVA 21%
- Recalcula base inversa para que total cuadre siempre

Uso:
    python main.py -i "carpeta_facturas" [-o archivo.xlsx] [-d diccionario.xlsx]
"""

import sys
import shutil
from pathlib import Path

# ============================================================================
# LIMPIEZA DE CACHÉ - EJECUTAR ANTES DE IMPORTAR EXTRACTORES
# ============================================================================

def limpiar_pycache():
    """
    Elimina __pycache__ de extractores para forzar recarga de módulos.
    Esto asegura que siempre se usen los extractores más recientes.
    """
    script_dir = Path(__file__).parent
    pycache_dirs = [
        script_dir / 'extractores' / '__pycache__',
        script_dir / 'nucleo' / '__pycache__',
        script_dir / 'salidas' / '__pycache__',
        script_dir / 'config' / '__pycache__',
    ]
    
    for pycache in pycache_dirs:
        if pycache.exists():
            try:
                shutil.rmtree(pycache)
            except Exception:
                pass  # Ignorar errores de permisos

# Limpiar caché ANTES de cualquier import
limpiar_pycache()

sys.dont_write_bytecode = True  # Evita generar nuevos __pycache__

import argparse
from datetime import datetime
import re
from difflib import SequenceMatcher

# Anadir el directorio del script al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar modulos del proyecto (DESPUÉS de limpiar caché)
from config.settings import VERSION, CIF_PROPIO, DICCIONARIO_DEFAULT
from nucleo.factura import Factura, LineaFactura
from nucleo.pdf import extraer_texto_pdf
from nucleo.parser import (
    parsear_nombre_archivo,
    extraer_fecha,
    extraer_cif,
    extraer_iban,
    extraer_total,
    extraer_referencia,
    resetear_contadores_temp  # v5.16: Reset contadores TEMP por trimestre
)
from nucleo.validacion import validar_cuadre, validar_factura
from extractores import obtener_extractor, listar_extractores, EXTRACTORES
from extractores.generico import ExtractorGenerico
from salidas import generar_excel, generar_log, imprimir_resumen


# ============================================================================
# CONSTANTES PARA PRORRATEO
# ============================================================================

KEYWORDS_PRORRATEO = [
    'SERVICIO URGENTE',
    'PORTE',
    'PORTES',
    'TRANSPORTE',
    'ENVIO',
    'ENVÍO',
    'GASTOS ENVIO',
    'GASTOS ENVÍO',
    'GASTOS DE ENVIO',
    'GASTOS DE ENVÍO',
]

KEYWORDS_EXCLUIR_PRORRATEO = [
    'ENVASE',
    'CAJA RETORNABLE',
    'FIANZA',
    'DEPOSITO',
    'DEPÓSITO',
]


# ============================================================================
# MAPEO DE ALIAS PARA NORMALIZACIÓN (v5.7 - AMPLIADO)
# ============================================================================

ALIAS_DICCIONARIO = {
    # SABORES DE PATERNA
    'SABORES DE PATERNA': 'SABORES PATERNA',
    'PATERNA': 'SABORES PATERNA',
    # FELISA
    'FELISA GOURMET': 'FELISA',
    'FELISA GOURMET DON FELIX': 'FELISA',
    'PESCADOS DON FELIX': 'FELISA',
    # ZUCCA
    'QUESERIA ZUCCA': 'ZUCCA',
    'FORMAGGIARTE': 'ZUCCA',
    'FORMAGGIARTE ZUCCA': 'ZUCCA',
    'QUESOS ZUCCA': 'ZUCCA',
    # SERRIN - incluyendo errores ortográficos
    'SERRIN NOCHAO': 'SERRIN NO CHAO',
    'SERRIN NO CHAN': 'SERRIN NO CHAO',
    'SERRIN': 'SERRIN NO CHAO',
    'SERRRIN': 'SERRIN NO CHAO',  # error ortográfico con 3 R
    'SERRRIN NO CHAO': 'SERRIN NO CHAO',
    'SERRRIN TF': 'SERRIN NO CHAO',
    # DE LUIS
    'DE LUIS': 'DE LUIS SABORES UNICOS',
    # BERZAL
    'BERZAL': 'BERZAL HERMANOS',
    'BERZAL HNOS': 'BERZAL HERMANOS',
    'BERZAL HNOS.': 'BERZAL HERMANOS',
    # CONSERVAS TITO
    'PORVAZ': 'CONSERVAS TITO',
    'PORVAZ VILLAGARCIA': 'CONSERVAS TITO',
    'PORVAZ TITO': 'CONSERVAS TITO',
    # EMBUTIDOS BERNAL
    'JAMONES BERNAL': 'EMBUTIDOS BERNAL',
    'JAMONES Y EMBUTIDOS BERNAL': 'EMBUTIDOS BERNAL',
    'BERNAL': 'EMBUTIDOS BERNAL',
    # SILVA CORDERO
    'QUESOS SILVA CORDERO': 'SILVA CORDERO',
    'QUESOS DE ACEHUCHE': 'SILVA CORDERO',
    # QUESERIA NAVAS
    'CARLOS NAVAS': 'QUESERIA NAVAS',
    'QUESOS NAVAS': 'QUESERIA NAVAS',
    'QUESERIA CARLOS NAVAS': 'QUESERIA NAVAS',
    # LA ALACENA
    'CONSERVAS LA ALACENA': 'LA ALACENA',
    # GADITAUN
    'MARILINA GADITAUN': 'GADITAUN',
    'GARDITAUN MARIA LINAREJOS': 'GADITAUN',
    'GADITAUN MARIA LINAREJOS': 'GADITAUN',
    'GADITAUN MARILINA': 'GADITAUN',
    'MARILINA': 'GADITAUN',
    # BORBOTON
    'BODEGAS BORBOTON': 'BORBOTON',
    # ARTESANOS DEL MOLLETE
    'ARTESANOS DEL MOLLETE': 'MOLLETES ARTESANOS',
    'MOLLETES ARTESANOS DE ANTEQUERA': 'MOLLETES ARTESANOS',
    'ARTESANOS DEL MOLINO': 'MOLLETES ARTESANOS',
    # ZUBELZU
    'ZUBELZU PIPARRAK': 'ZUBELZU',
    'IBARRAKO': 'ZUBELZU',
    'IBARRAKO PIPARRAK': 'ZUBELZU',
    # LA MOLIENDA VERDE
    'MOLIENDA VERDE': 'LA MOLIENDA VERDE',
    # DISTRIBUCIONES LAVAPIES
    'LAVAPIES': 'DISTRIBUCIONES LAVAPIES',
    # GRUPO DISBER
    'DISBER': 'GRUPO DISBER',
    # MRM
    'INDUSTRIAS CARNICAS MRM': 'MRM',
    # PILAR RODRIGUEZ
    'EL MAJADAL': 'PILAR RODRIGUEZ',
    'EL MAJADAL PILAR RODRIGUEZ': 'PILAR RODRIGUEZ',
    # TERRITORIO CAMPERO
    'GRUPO TERRITORIO CAMPERO': 'TERRITORIO CAMPERO',
    'GRUPO CAMPERO': 'TERRITORIO CAMPERO',
    # MARITA
    'MARITA COSTA': 'MARITA',
    # LA BARRA DULCE
    'BARRA DULCE': 'LA BARRA DULCE',
    'LA BARRA DULCE S.L.': 'LA BARRA DULCE',
    # TIRSO PAPEL Y BOLSAS (NUEVO 01/01/2026)
    'TIRSO': 'TIRSO PAPEL Y BOLSAS',
    'TIRSO PAPEL': 'TIRSO PAPEL Y BOLSAS',
    'BOLSAS TIRSO': 'TIRSO PAPEL Y BOLSAS',
    'TIRSO PAPEL Y BOLSAS SL': 'TIRSO PAPEL Y BOLSAS',
    'TIRSO PAPAEL Y BOLSAS': 'TIRSO PAPEL Y BOLSAS',  # typo en archivos
    'TIRSO PAPAEL Y BOLSAS SL': 'TIRSO PAPEL Y BOLSAS',
    # LA CUCHARA GOURMET (NUEVO 04/01/2026)
    'LA CUCHARA': 'LA CUCHARA GOURMET',
    'LA CUCHARA LAVAPIES': 'LA CUCHARA GOURMET',
    'CUCHARA LAVAPIES': 'LA CUCHARA GOURMET',
    'LA CUCHARA GOURMET SL': 'LA CUCHARA GOURMET',
    # LA CONSERVERA DEL PREPIRINEO (NUEVO 01/01/2026)
    'CONSERVERA PREPIRINEO': 'LA CONSERVERA DEL PREPIRINEO',
    'CONSERVERA DEL PREPIRINEO': 'LA CONSERVERA DEL PREPIRINEO',
    'LA CONSERVERA PREPIRINEO': 'LA CONSERVERA DEL PREPIRINEO',
    # MIGUEZ CAL
    'FORPLAN': 'MIGUEZ CAL',
    # MARTIN ABENZA
    'CONSERVAS EL MODESTO': 'MARTIN ABENZA',
    'MARTIN ARBENZA': 'MARTIN ABENZA',
    'MARTIN ARBENZA EL MODESTO': 'MARTIN ABENZA',
    # WELLDONE
    'RODOLFO DEL RIO': 'WELLDONE',
    'WELLDONE LACTICOS': 'WELLDONE',
    # MANIPULADOS ABELLAN
    'EL LABRADOR': 'MANIPULADOS ABELLAN',
    'ABELLAN': 'MANIPULADOS ABELLAN',
    # LA ROSQUILLERIA  
    'EL TORRO': 'LA ROSQUILLERIA',
    # PANRUJE
    'ROSQUILLAS LA ERMITA': 'PANRUJE',
    # LICORES MADRUEÑO
    'MADRUEÑO': 'LICORES MADRUEÑO',
    # VINOS DE ARGANZA
    'ARGANZA': 'VINOS DE ARGANZA',
    # CVNE
    'BODEGAS CVNE': 'CVNE',
    # LA PURISIMA
    'BODEGAS LA PURISIMA': 'LA PURISIMA',
    'BODEGAS VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    # FRANCISCO GUERRA
    'GUERRA': 'FRANCISCO GUERRA',
    # FISHGOURMET
    'FISH GOURMET': 'FISHGOURMET',
    # ECOFICUS
    'ECO FICUS': 'ECOFICUS',
    # LOS GREDALES
    'GREDALES': 'LOS GREDALES',
    'LOS GREDALES DEL TOBOSO': 'LOS GREDALES',
    
    # ========== NUEVOS ALIAS v5.7 (01/01/2026) ==========
    
    # DEBORA GARCIA TOLEDANO - múltiples variantes
    'DEBORA': 'DEBORA GARCIA TOLEDANO',
    'DEBORAH': 'DEBORA GARCIA TOLEDANO',
    'BEDORAH': 'DEBORA GARCIA TOLEDANO',
    'DEBORA GARCIA': 'DEBORA GARCIA TOLEDANO',
    'DEBORAH GARCIA': 'DEBORA GARCIA TOLEDANO',
    'BEDORAH GARCIA': 'DEBORA GARCIA TOLEDANO',
    'DEBORAH GARCIA TOLEDANO': 'DEBORA GARCIA TOLEDANO',
    'BEDORAH GARCIA TOLEDANO': 'DEBORA GARCIA TOLEDANO',
    
    # HERNANDEZ SUMINISTROS
    'HERNANDEZ': 'HERNANDEZ SUMINISTROS',
    'HERNÁNDEZ': 'HERNANDEZ SUMINISTROS',
    'HERNANDEZ SUMINISTROS HOSTELEROS': 'HERNANDEZ SUMINISTROS',
    'HERNÁNDEZ SUMINISTROS HOSTELEROS': 'HERNANDEZ SUMINISTROS',
    'HERNANDEZ SUM HOSTELEROS': 'HERNANDEZ SUMINISTROS',
    
    # ISAAC RODRIGUEZ / TRUCCO COPIAS
    'TRUCCO COPIAS': 'ISAAC RODRIGUEZ',
    'TRUCCO COPIAS ISAAC RODRIGUEZ': 'ISAAC RODRIGUEZ',
    'TRUCCO ISSAC RODRIGUEZ': 'ISAAC RODRIGUEZ',
    'TRUCCO COPIAS ISAAC HERNANDEZ': 'ISAAC RODRIGUEZ',
    'ISAAC RODRIGUEZ TRUCCO COPIAS': 'ISAAC RODRIGUEZ',
    
    # LA DOLOROSA / PABLO RUIZ
    'LA DOLOROSA': 'PABLO RUIZ',
    'PABLO RUIZ LA DOLOROSA': 'PABLO RUIZ',
    
    # LUCERA / ENERGIA COLECTIVA
    'ENERGIA COLECTIVA': 'LUCERA',
    'ENERGIA COLECTIVA LUCERA': 'LUCERA',
    
    # JULIO GARCIA VIVAS
    'GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    'GARCIA VIVAS JULIO': 'JULIO GARCIA VIVAS',
    
    # ========== ALIAS AUTO-GENERADOS v5.12 (04/01/2026) ==========
    
    # ABBATI
    '2T25 0430 ABBATI CAFFE': 'ABBATI',
    'ABBATI CAFE': 'ABBATI',
    'CAFFE ABBATI': 'ABBATI',
    
    # ALFARERIA ANGEL Y LOLI
    'ALFARERIA ANGEL Y LOLI': 'ANGEL Y LOLI',
    'ANGEL Y LOLI ALFARERIA': 'ANGEL Y LOLI',
    
    # ANTHROPIC
    '4T 1108 ANTHROPIC': 'ANTHROPIC',
    '4T25 1120 ANTHROPIC': 'ANTHROPIC',
    '4T25 1224 ANTHROPIC': 'ANTHROPIC',
    
    # ARTESANOS DEL MOLLETE
    'ARTESANOS DEL MOLLETE': 'MOLLETES ARTESANOS',
    'MOLLETES ARTESANOS DE ANTEQUERA': 'MOLLETES ARTESANOS',
    'MOLLETES': 'MOLLETES ARTESANOS',
    
    # BENJAMIN ORTEGA (con fechas)
    '2T25 0401 BENJAMIN ORTEGA OJO RETENCION': 'BENJAMIN ORTEGA',
    '2T25 0501 BENJAMIN ORTEGA OJO RETENCION': 'BENJAMIN ORTEGA',
    '2T25 0601 BENJAMIN ORTEGA OJO RETENCION': 'BENJAMIN ORTEGA',
    '3T25 0701 BENJAMIN ORTEGA RETENCION': 'BENJAMIN ORTEGA',
    '3T25 0801 BENJAMIN ORTEGA RETENCION': 'BENJAMIN ORTEGA',
    '3T25 0901 BENJAMIN ORTEGA RETENCION': 'BENJAMIN ORTEGA',
    'BENJAMIN ORTEGA ALONSO': 'BENJAMIN ORTEGA',
    
    # BERZAL
    '10011 BERZAL HERMANOS': 'BERZAL',
    
    # BM SUPERMERCADOS (unificación)
    '1T25 0213 BM SUPERMERCADOS': 'BM SUPERMERCADOS',
    '1T25 0213 BM SUPERMERCADOS 3': 'BM SUPERMERCADOS',
    'BM': 'BM SUPERMERCADOS',
    '2 BM': 'BM SUPERMERCADOS',
    'BM SUPERMERCADOS 2': 'BM SUPERMERCADOS',
    'BM SUPERMERCADOS 3': 'BM SUPERMERCADOS',
    'SUPERMERCADOS BM': 'BM SUPERMERCADOS',
    'SUPERMERCADOS BM 2': 'BM SUPERMERCADOS',
    
    # BODEGAS BORBOTON
    '1T25 0109 BODEGAS BORBOTON': 'BODEGAS BORBOTON',
    'BORBOTON': 'BODEGAS BORBOTON',
    
    # CARLOS NAVAS / QUESERIA NAVAS
    'QUESERIA CARLOS NAVAS': 'CARLOS NAVAS',
    'QUESERIA NAVAS': 'CARLOS NAVAS',
    'QUESOS NAVAS': 'CARLOS NAVAS',
    
    # CARRASCAL
    'JOSE LUIS SANCHEZ EL CARRASCAL': 'CARRASCAL',
    
    # CASA DEL DUQUE
    'CASA DEL DUQUE SL': 'CASA DEL DUQUE',
    'T25 1206 CASA DEL DUQUE': 'CASA DEL DUQUE',
    
    # CELONIS
    '3T25 0815 CELONIS': 'CELONIS',
    '4T25 1015 CELONIS .': 'CELONIS',
    '4T25 1015 CELONIS TJ.': 'CELONIS',
    
    # CERES (eliminar prefijos de fecha)
    '1T25 0211 CERES OJO SIN APUNTE': 'CERES',
    '1T25 0328 CERES': 'CERES',
    '2T25 0401 CERES': 'CERES',
    '2T25 0422 CERES': 'CERES',
    '2T25 0425 CERES': 'CERES',
    '2T25 0520 CERES': 'CERES',
    '2T25 0523 CERES': 'CERES',
    '2T25 0527 CERES': 'CERES',
    '2T25 0610 CERES': 'CERES',
    '2T25 0620 CERES': 'CERES',
    'ATRASADA 1T25 0328 CERES': 'CERES',
    'CERES 2': 'CERES',
    
    # CONSERVERA PREPIRINEO
    'LA CONSERVERA DEL PREPIRINEO': 'CONSERVERA PREPIRINEO',
    
    # DE LUIS SABORES UNICOS
    'DE LUIS': 'DE LUIS SABORES UNICOS',
    
    # DEBORA GARCIA TOLEDANO
    'BEDORAH GARCIA TOLEDANO': 'DEBORA GARCIA TOLEDANO',
    'DEBORAH GARCIA': 'DEBORA GARCIA TOLEDANO',
    
    # DIA
    'DIA': 'DIA',
    '2DIA': 'DIA',
    'GRUPO DIA': 'DIA',
    
    # DISTRIBUCIONES LAVAPIES
    '1T25 0225 ASOCIACION COMERCIANTES LAVAPIES': 'DISTRIBUCIONES LAVAPIES',
    '2T25 0414 ASOCIACION COMERCIANTES LAVAPIES': 'DISTRIBUCIONES LAVAPIES',
    '4T25 1031 PANIFIESTO LAVAPIES': 'DISTRIBUCIONES LAVAPIES',
    'ASOCIACION COMERCIANTES LAVAPIES': 'DISTRIBUCIONES LAVAPIES',
    
    # ECOFICUS
    '3T25 0908 ECOFICUS': 'ECOFICUS',
    
    # ECOMS
    'ECOMS S': 'ECOMS',
    'ECOMS SUPERMARKET': 'ECOMS',
    'ECOMS SUPERMARKET SL': 'ECOMS',
    
    # EMBUTIDOS BERNAL / JAMONES BERNAL
    '4T25 1116 JAMONES Y EMBUTIDOS BERNAL': 'JAMONES BERNAL',
    'EMBUTIDOS BERNAL': 'JAMONES BERNAL',
    
    # EMBUTIDOS FERRIOL
    'EMBUTIDOS FERIOL': 'EMBUTIDOS FERRIOL',
    
    # FABEIRO
    '02218 FABEIRO': 'FABEIRO',
    '0731 FABEIRO': 'FABEIRO',
    
    # FELISA GOURMET
    'FELISA': 'FELISA GOURMET',
    
    # FISHGOURMET
    'FISH GOURMET': 'FISHGOURMET',
    
    # GADITAUN
    'GADITAUN MARILILNA': 'GADITAUN',
    'GARDITAUN MARIA LINAREJOS': 'GADITAUN',
    
    # GRUPO DISBER
    'GRUPO DISBER 2': 'GRUPO DISBER',
    
    # GRUPO TERRITORIO CAMPERO
    'TERRITORIO CAMPERO': 'GRUPO TERRITORIO CAMPERO',
    
    # HERNANDEZ SUMINISTROS
    'HERNANDEZ SUMINISTROS HOSTELEROS': 'HERNANDEZ SUMINISTROS',
    'Hernández Suministros': 'HERNANDEZ SUMINISTROS',
    
    # IBARRAKO PIPARRAK
    'IBARRAKO PIPPARRAK': 'IBARRAKO PIPARRAK',
    
    # ISTA
    'ISTA 2': 'ISTA',
    
    # JAIME FERNANDEZ (con fechas)
    '2T25 0401 JAIME FERNANDEZ OJO RETENCION': 'JAIME FERNANDEZ',
    '2T25 0501 JAIME FERNANDEZ OJO RETENCION': 'JAIME FERNANDEZ',
    '2T25 0601 JAIME FERNANDEZ OJO RETENCION': 'JAIME FERNANDEZ',
    '3T25 0701 JAIME FERNANDEZ RETENCION': 'JAIME FERNANDEZ',
    '3T25 0801 JAIME FERNANDEZ RETENCION': 'JAIME FERNANDEZ',
    '3T25 0901 JAIME FERNANDEZ RETENCION': 'JAIME FERNANDEZ',
    
    # JIMELUZ
    '1T25 0112 JIMELUZ': 'JIMELUZ',
    '2T25 0525 JIMELUZ EF (1)': 'JIMELUZ',
    'JIMELUZ SL': 'JIMELUZ',
    
    # JULIO GARCIA VIVAS (con fechas)
    '1T25 0131 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '1T25 0331 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '2T25 0430 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '2T25 0531 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '2T25 0630 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '3T25 0831 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '3T25 0930 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    '4T25 1031 GARCIA VIVAS JULIO': 'JULIO GARCIA VIVAS',
    '4T25 1130 JULIO GARCIA VIVAS': 'JULIO GARCIA VIVAS',
    
    # KINEMA
    'COOPERATIVA KINEMA': 'KINEMA',
    
    # LA ALACENA
    'CONSERVAS LA ALACENA': 'LA ALACENA',
    
    # LA BARRA DULCE
    'LA BARRA DULCE S.L': 'LA BARRA DULCE',
    
    # LA CUCHARA GOURMET
    '0731LA CUCHARA': 'LA CUCHARA GOURMET',
    '0731LA CUCHARA 2': 'LA CUCHARA GOURMET',
    
    # LA LLEIDIRIA / LA LLILDIRIA (unificar variantes)
    'LA LLEIDIRIA': 'LA LLILDIRIA',
    
    # LA MOLIENDA VERDE
    '4T24 0114 LA MOLIENDA VERDE': 'LA MOLIENDA VERDE',
    'LA MOLIENDA VERDE.': 'LA MOLIENDA VERDE',
    
    # LA PURISIMA
    '01134 LA PURISIMA': 'LA PURISIMA',
    'BODEGAS LA PURISIMA': 'LA PURISIMA',
    
    # LA ROSQUILLERIA
    'LA ROSQUILLERIA S.L.U.': 'LA ROSQUILLERIA',
    
    # LICORES MADRUEÑO
    'LICORES MADRUEÑO 2': 'LICORES MADRUEÑO',
    
    # LIDL
    '1T25 0328 LIDL': 'LIDL',
    
    # LOS GREDALES
    'BODEGA LOS GREDALES': 'LOS GREDALES',
    
    # MAKRO (NUEVO)
    'MAKRO': 'MAKRO',
    'MAKRO DISTRIBUCION': 'MAKRO',
    'MAKRO DISTRIBUCION MAYORISTA': 'MAKRO',
    
    # MANIPULADOS ABELLAN
    'EL LABRADOR': 'MANIPULADOS ABELLAN',
    
    # MARITA COSTA
    'MARITA': 'MARITA COSTA',
    
    # MARTIN ABENZA
    'MARTIN ARBENZA': 'MARTIN ABENZA',
    'MARTIN ARBENZA EL MODESTO': 'MARTIN ABENZA',
    
    # MIGUEZ CAL
    'FORPLAN MIGUEZ CAL': 'MIGUEZ CAL',
    
    # MONTBRIONE
    'COOPERATIVA MONTBRIO': 'MONTBRIONE',
    'COOPERATIVA MONTBRIONE': 'MONTBRIONE',
    
    # MRM
    '1T25 0213 MRM': 'MRM',
    '1T25 0213 MRM 2': 'MRM',
    'MRM 2': 'MRM',
    'O225 MRM': 'MRM',
    
    # OPENAI
    'OPEN AI': 'OPENAI',
    
    # PABLO RUIZ
    'PABLO RUIZ LA DOLOROSA': 'PABLO RUIZ',
    
    # PANIFIESTO (con fechas)
    '1T25 0131 PANIFIESTO': 'PANIFIESTO',
    '1T25 0228 PANIFIESTO': 'PANIFIESTO',
    '1T25 0331 PANIFIESTO': 'PANIFIESTO',
    '2T25 0430 PANIFIESTO': 'PANIFIESTO',
    '2T25 0531 PANIFIESTO': 'PANIFIESTO',
    '2T25 0630 PANIFIESTO': 'PANIFIESTO',
    '3T25 0732 PANIFIESTO': 'PANIFIESTO',
    '3T25 0831 PANIFIESTO': 'PANIFIESTO',
    '3T25 0930 PANIFIESTO': 'PANIFIESTO',
    'PANIFIESTO LAVAPIES': 'PANIFIESTO',
    
    # PILAR RODRIGUEZ
    'EL MAJADAL PILAR RODRIGUEZ': 'PILAR RODRIGUEZ',
    'PILAR RODRIGUEZ EL MAJADAL': 'PILAR RODRIGUEZ',
    'PILAR RODRIGUEZ MAJADAL': 'PILAR RODRIGUEZ',
    
    # PORVAZ / CONSERVAS TITO
    'PORVAZ CONSERVAS TITO': 'PORVAZ',
    
    # QUESERIA ZUCCA
    'FORMAGGIARTE ZUCCA': 'QUESERIA ZUCCA',
    'ZUCCA FORMAGGIARTE': 'QUESERIA ZUCCA',
    
    # QUESOS DEL CATI
    'QUESOS DEL CATÍ': 'QUESOS DEL CATI',
    
    # QUESOS SILVA CORDERO
    'QUESOS SILVA CORDERO': 'SILVA CORDERO',
    
    # SABORES DE PATERNA
    'SABORES PATERNA': 'SABORES DE PATERNA',
    
    # SERRIN NO CHAN
    'SERRIN NO CHAO': 'SERRIN NO CHAN',
    'SERRIN NOCHAO': 'SERRIN NO CHAN',
    
    # SOM ENERGIA
    '2T25 0527 SOM ENERGIA': 'SOM ENERGIA',
    '2T25 0527 SOM ENERGIA 2': 'SOM ENERGIA',
    'SOM ENERGIA 2': 'SOM ENERGIA',
    'SOM ENERGIA COM.': 'SOM ENERGIA',
    'SOM ENERGIA COMESTIBLES': 'SOM ENERGIA',
    'SOM ENERGIA RODAS': 'SOM ENERGIA',
    'SOM ENERGIA TAS.': 'SOM ENERGIA',
    
    # TIRSO
    'BOLSAS TIRSO': 'TIRSO',
    'TIRSO PAPEL Y BOLSAS': 'TIRSO',
    'TIRSO PAPEL Y BOLSAS SL': 'TIRSO',
    
    # TRUCCO
    '2T25 0523 ISAAC RODRIGUEZ TRUCCO COPIAS': 'TRUCCO',
    'ISAAC RODRIGUEZ TRUCCO COPIAS': 'TRUCCO',
    'TRUCCO COPIAS': 'TRUCCO',
    'TRUCCO COPIAS ISAAC RODRIGUEZ': 'TRUCCO',
    'TRUCCO ISSAC RODRIGUEZ': 'TRUCCO',
    
    # VINOS DE ARGANZA
    '1T25 0312 VINOS DE ARGANZA': 'VINOS DE ARGANZA',
    'VINOS DE ARGANZA SL': 'VINOS DE ARGANZA',
    
    # VIRGEN DE LA SIERRA (todas las variantes)
    '1T25 0311 VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    '2T 0512 BODEGA VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    'BODEGA VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    'BODEGA VIRGEN DE LA SIERRA COOP': 'VIRGEN DE LA SIERRA',
    'BODEGAS VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    'COOPERATIVA VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
    'VIRGEN DE LA SIERA': 'VIRGEN DE LA SIERRA',  # typo corregido
    
    # WEBEMPRESA
    '1T25 0326 WEBEMPRESA': 'WEBEMPRESA',
    'WEBEMPRESA EUROPA': 'WEBEMPRESA',
    
    # WELLDONE
    'WELLDONE LACTICOS': 'WELLDONE',
    
    # YOIGO
    'XFERA YOIGO': 'YOIGO',
    'YOIGO XFERA': 'YOIGO',
    
    # ZUBELZU
    'ZUBELZU PIPARRAK': 'ZUBELZU',
}


# ============================================================================
# RETENCIONES POR PROVEEDOR (NUEVO v5.7)
# ============================================================================

# Proveedores con retención IRPF (el importe de la factura incluye retención)
# El descuadre esperado es = base * porcentaje_retencion
RETENCIONES_PROVEEDOR = {
    # Alquiler local - 19%
    'JAIME FERNANDEZ': 0.19,
    'BENJAMIN ORTEGA': 0.19,
    'BENJAMIN ORTEGA ALONSO': 0.19,
    # Otros servicios profesionales - 15%
    'REGISTRO MERCANTIL': 0.15,
    # Servicios - 1%
    'DEBORA GARCIA TOLEDANO': 0.01,
    'DEBORA': 0.01,
    'DEBORAH': 0.01,
    'BEDORAH': 0.01,
}

# Tolerancia para descuadre por retención (€)
TOLERANCIA_RETENCION = 0.50


# ============================================================================
# CATEGORÍAS FIJAS POR PROVEEDOR (NUEVO v5.12)
# ============================================================================

# Proveedores que SIEMPRE tienen la misma categoría, sin necesidad de extractor.
# El extractor genérico asignará esta categoría a todas las líneas.
CATEGORIAS_FIJAS_PROVEEDOR = {
    # Electricidad
    'LUCERA': 'ELECTRICIDAD LOCAL',
    'ENERGIA COLECTIVA': 'ELECTRICIDAD LOCAL',
    'ENERGIA COLECTIVA LUCERA': 'ELECTRICIDAD LOCAL',
    'SOM ENERGIA': 'ELECTRICIDAD LOCAL',
    # Telefonía
    'YOIGO': 'TELEFONO',
    'XFERA YOIGO': 'TELEFONO',
    # Web/Software
    'WEBEMPRESA': 'WEB Y SOFTWARE',
    'ANTHROPIC': 'WEB Y SOFTWARE',
    'OPENAI': 'WEB Y SOFTWARE',
    'CELONIS': 'WEB Y SOFTWARE',
}


# ============================================================================
# FUNCIÓN: Normalizar nombre de proveedor (MEJORADA v5.12)
# ============================================================================

def normalizar_proveedor(nombre: str) -> str:
    """
    Normaliza nombre de proveedor:
    1. PRIMERO busca alias exacto del nombre original (para casos con fecha)
    2. Quita prefijos de fecha/referencia (ej: "4T25 1031", "ATRASADA")
    3. Quita sufijos OJO, RETENCION, etc.
    4. Quita sufijos de tipo factura (TF, TR, TJ, EF, RC)
    5. Quita sufijos numéricos (ej: " 2")
    6. Aplica mapeo de alias conocidos
    
    v5.12: Busca alias ANTES de limpiar, para capturar variantes con fecha.
    """
    if not nombre:
        return ""
    
    nombre_original = nombre.strip().upper()
    
    # v5.12: PRIMERO buscar el nombre original completo en alias
    # Esto captura casos como "2T25 0422 CERES" -> "CERES"
    if nombre_original in ALIAS_DICCIONARIO:
        return ALIAS_DICCIONARIO[nombre_original]
    
    # Paso 1: Quitar prefijos tipo "4T25 1031 " o "1T25 0331 "
    nombre = re.sub(r'^\d[TQ]\d{2}\s+\d{3,4}\s+', '', nombre_original)
    
    # Paso 1b: Quitar prefijo "ATRASADA" o "ATRASADA 3T25" etc.
    nombre = re.sub(r'^ATRASADA\s*(\d[TQ]\d{2})?\s*\d*\s*', '', nombre, flags=re.IGNORECASE)
    
    # Paso 1c: Quitar prefijo solo trimestre "4T25 " sin número
    nombre = re.sub(r'^\d[TQ]\d{2}\s+', '', nombre)
    
    # Paso 1d: Quitar prefijo número solo "442 "
    nombre = re.sub(r'^\d{3,4}\s+', '', nombre)
    
    # Paso 1e: v5.12 - Quitar prefijo "2T " sin año
    nombre = re.sub(r'^\d[TQ]\s+', '', nombre)
    
    # Paso 2: Quitar extensión .pdf si quedó
    nombre = re.sub(r'\.pdf$', '', nombre, flags=re.IGNORECASE)
    
    # Paso 3: v5.12 - Quitar sufijos OJO y similares PRIMERO
    nombre = re.sub(r'\s+OJO.*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s+RETENCION.*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s+SIN\s+APUNTE.*$', '', nombre, flags=re.IGNORECASE)
    
    # Paso 4: Quitar sufijos tipo factura: TF, TR, TJ, EF, RC, REC
    nombre = re.sub(r'\s+(TF|TR|TJ|EF|RC|REC|EG)\.?$', '', nombre, flags=re.IGNORECASE)
    
    # Paso 5: Quitar sufijos numéricos tipo " 2" o " 3"
    nombre = re.sub(r'\s+\d+$', '', nombre)
    
    nombre = nombre.strip().upper()
    
    # Paso 6: Aplicar mapeo de alias
    if nombre in ALIAS_DICCIONARIO:
        return ALIAS_DICCIONARIO[nombre]
    
    # Paso 7: Buscar coincidencia parcial en alias (para nombres con errores)
    for alias, normalizado in ALIAS_DICCIONARIO.items():
        # Si el nombre contiene el alias completo
        if alias in nombre:
            return normalizado
        # Si el alias contiene el nombre (nombre es substring)
        if len(nombre) >= 5 and nombre in alias:
            return normalizado
    
    return nombre


# ============================================================================
# FUNCIÓN: Buscar proveedor en nombre de archivo (NUEVA v5.7)
# ============================================================================

def buscar_proveedor_en_nombre(nombre_archivo: str, extractores_disponibles: dict) -> str:
    """
    Busca el nombre del proveedor en cualquier parte del nombre del archivo.
    Útil para archivos que no siguen el formato estándar "XXXX XTxx FECHA PROVEEDOR".
    
    Args:
        nombre_archivo: Nombre del archivo PDF
        extractores_disponibles: Diccionario de extractores {nombre: clase}
    
    Returns:
        Nombre del proveedor encontrado o None
    """
    nombre_upper = nombre_archivo.upper()
    
    # Lista de proveedores conocidos (ordenados por longitud descendente para match más específico)
    proveedores_conocidos = sorted(
        list(extractores_disponibles.keys()) + list(ALIAS_DICCIONARIO.keys()),
        key=len,
        reverse=True
    )
    
    for proveedor in proveedores_conocidos:
        if proveedor.upper() in nombre_upper:
            # Normalizar el proveedor encontrado
            return normalizar_proveedor(proveedor)
    
    return None


# ============================================================================
# FUNCIÓN: Calcular descuadre con retención (NUEVA v5.7)
# ============================================================================

def calcular_descuadre_con_retencion(total_lineas: float, total_factura: float, proveedor: str) -> tuple:
    """
    Calcula el descuadre considerando posible retención IRPF.
    
    Returns:
        (descuadre_real, tiene_retencion, porcentaje_retencion)
    """
    proveedor_upper = proveedor.upper().strip()
    
    # Buscar por nombre exacto o normalizado
    porcentaje = None
    if proveedor_upper in RETENCIONES_PROVEEDOR:
        porcentaje = RETENCIONES_PROVEEDOR[proveedor_upper]
    else:
        # Buscar por nombre parcial
        for nombre_ret, porc in RETENCIONES_PROVEEDOR.items():
            if nombre_ret in proveedor_upper or proveedor_upper in nombre_ret:
                porcentaje = porc
                break
    
    if porcentaje is not None:
        # La factura tiene retención: total_pagado = total_bruto - retencion
        # total_lineas es el bruto, total_factura es lo que se paga
        # descuadre = total_lineas - total_factura debería ser ≈ retención
        retencion_esperada = total_lineas * porcentaje
        descuadre = abs(total_lineas - total_factura)
        
        # Si el descuadre es aproximadamente igual a la retención esperada, es OK
        if abs(descuadre - retencion_esperada) < TOLERANCIA_RETENCION:
            return (0, True, porcentaje)
    
    # Sin retención: descuadre normal
    return (abs(total_lineas - total_factura), False, 0)


def buscar_en_diccionario(proveedor: str, indice: dict) -> str:
    """
    Busca el nombre del proveedor en el diccionario.
    Prueba múltiples variantes: exacto, alias, parcial.
    
    Returns:
        Nombre como está en el diccionario, o el original si no se encuentra
    """
    prov_upper = proveedor.upper().strip()
    
    # 1. Búsqueda exacta
    if prov_upper in indice:
        return prov_upper
    
    # 2. Buscar via alias
    if prov_upper in ALIAS_DICCIONARIO:
        alias = ALIAS_DICCIONARIO[prov_upper]
        if alias in indice:
            return alias
    
    # 3. Búsqueda parcial (substring)
    for nombre_dic in indice.keys():
        if nombre_dic in prov_upper or prov_upper in nombre_dic:
            return nombre_dic
    
    # 4. Búsqueda parcial en alias
    for alias_from, alias_to in ALIAS_DICCIONARIO.items():
        if alias_from in prov_upper or prov_upper in alias_from:
            if alias_to in indice:
                return alias_to
    
    return prov_upper


# ============================================================================
# FUNCIÓN: Prorratear portes/transporte entre productos
# ============================================================================

def es_linea_porte(articulo: str) -> bool:
    """Detecta si una línea es un porte/transporte."""
    articulo_upper = articulo.upper()
    
    for excluir in KEYWORDS_EXCLUIR_PRORRATEO:
        if excluir in articulo_upper:
            return False
    
    for keyword in KEYWORDS_PRORRATEO:
        if keyword in articulo_upper:
            return True
    
    return False


def prorratear_portes(lineas: list) -> list:
    """
    Distribuye portes proporcionalmente entre productos.
    
    Soporta IVAs mixtos: el porte se distribuye en proporción
    al importe de cada producto, manteniendo el IVA del porte.
    """
    if not lineas:
        return lineas
    
    lineas_producto = []
    lineas_porte = []
    
    for linea in lineas:
        if es_linea_porte(linea.articulo):
            lineas_porte.append(linea)
        else:
            lineas_producto.append(linea)
    
    if not lineas_porte or not lineas_producto:
        return lineas
    
    total_porte_base = sum(l.base for l in lineas_porte)
    total_productos_base = sum(l.base for l in lineas_producto)
    
    if total_productos_base <= 0:
        return lineas
    
    # Distribuir cada porte proporcionalmente
    for porte in lineas_porte:
        porte_base = porte.base
        porte_iva = porte.iva
        
        for i, prod in enumerate(lineas_producto):
            proporcion = prod.base / total_productos_base
            incremento_base = round(porte_base * proporcion, 2)
            
            # Si el IVA del producto es diferente al del porte,
            # recalculamos la base para que el total cuadre
            if prod.iva != porte_iva:
                # El incremento viene con IVA del porte
                # Lo convertimos a base equivalente con IVA del producto
                total_porte_linea = incremento_base * (1 + porte_iva / 100)
                incremento_base = round(total_porte_linea / (1 + prod.iva / 100), 2)
            
            prod.base = round(prod.base + incremento_base, 2)
    
    return lineas_producto


# ============================================================================
# FUNCIÓN: cargar_diccionario
# ============================================================================

def cargar_diccionario(ruta_excel: Path):
    """
    Carga el diccionario de proveedores y categorías.
    Hoja: 'Articulos' con columnas: PROVEEDOR, ARTICULO, CATEGORIA, TIPO_IVA, COD LOYVERSE
    """
    import pandas as pd
    
    # Intentar primero 'Articulos', luego 'COMPRAS' por compatibilidad
    try:
        df = pd.read_excel(ruta_excel, sheet_name='Articulos')
    except ValueError:
        df = pd.read_excel(ruta_excel, sheet_name='COMPRAS')
    
    articulos = {}
    proveedores = {}
    indice = {}
    
    for _, row in df.iterrows():
        proveedor = str(row.get('PROVEEDOR', '')).strip().upper()
        articulo = str(row.get('ARTICULO', '')).strip().upper()
        categoria = str(row.get('CATEGORIA', '')).strip()
        # Soporta ambos nombres de columna
        id_cat = str(row.get('COD LOYVERSE', row.get('ID_CATEGORIA', ''))).strip()
        iva = row.get('TIPO_IVA', 21)
        
        if not proveedor or not articulo:
            continue
        
        if proveedor not in indice:
            indice[proveedor] = {}
        
        indice[proveedor][articulo] = {
            'categoria': categoria,
            'id_categoria': id_cat,
            'iva': int(iva) if pd.notna(iva) else 21
        }
        
        articulos[articulo] = {
            'proveedor': proveedor,
            'categoria': categoria,
            'id_categoria': id_cat,
            'iva': int(iva) if pd.notna(iva) else 21
        }
        
        if proveedor not in proveedores:
            proveedores[proveedor] = []
        proveedores[proveedor].append(articulo)
    
    return articulos, proveedores, indice


# ============================================================================
# FUNCIÓN: categorizar_linea
# ============================================================================

def categorizar_linea(linea, proveedor: str, indice: dict, tiene_extractor: bool = True):
    """
    Categoriza una línea buscando en el diccionario.
    
    Args:
        linea: LineaFactura a categorizar
        proveedor: Nombre del proveedor
        indice: Diccionario de categorías
        tiene_extractor: True si hay extractor específico, False si usa genérico
    
    v5.12: Añadido soporte para CATEGORIAS_FIJAS_PROVEEDOR
    """
    import pandas as pd
    
    # Respetar categoría ya asignada por el extractor (hardcodeada)
    if linea.categoria and linea.categoria not in ('', 'PENDIENTE', None):
        linea.match_info = 'EXTRACTOR'
        return
    
    prov_normalizado = normalizar_proveedor(proveedor)
    
    # v5.12: Verificar si el proveedor tiene categoría fija
    if prov_normalizado in CATEGORIAS_FIJAS_PROVEEDOR:
        linea.categoria = CATEGORIAS_FIJAS_PROVEEDOR[prov_normalizado]
        linea.match_info = 'CATEGORIA_FIJA'
        return
    
    # También buscar por nombre original (por si no se normalizó)
    prov_upper = proveedor.upper().strip()
    if prov_upper in CATEGORIAS_FIJAS_PROVEEDOR:
        linea.categoria = CATEGORIAS_FIJAS_PROVEEDOR[prov_upper]
        linea.match_info = 'CATEGORIA_FIJA'
        return
    
    prov_diccionario = buscar_en_diccionario(prov_normalizado, indice)
    
    if prov_diccionario not in indice:
        # v5.10: Distinguir entre SIN_EXTRACTOR y SIN_CATEGORIA
        if tiene_extractor:
            linea.categoria = 'SIN_CATEGORIA'
            linea.match_info = 'ARTICULO_NO_EN_DICCIONARIO'
        else:
            linea.categoria = 'SIN_EXTRACTOR'
            linea.match_info = 'PROVEEDOR_SIN_EXTRACTOR'
        return
    
    articulos_prov = indice[prov_diccionario]
    articulo_upper = linea.articulo.upper().strip()
    
    # 1. Match exacto
    if articulo_upper in articulos_prov:
        data = articulos_prov[articulo_upper]
        linea.categoria = data['categoria']
        linea.id_categoria = data['id_categoria']
        linea.match_info = 'EXACTO'
        return
    
    # 2. Match parcial (substring)
    for art_dic, data in articulos_prov.items():
        if art_dic in articulo_upper or articulo_upper in art_dic:
            linea.categoria = data['categoria']
            linea.id_categoria = data['id_categoria']
            linea.match_info = 'PARCIAL'
            return
    
    # 3. Fuzzy matching (80% similitud)
    mejor_ratio = 0
    mejor_match = None
    mejor_tipo = 'FUZZY'
    
    for art_dic, data in articulos_prov.items():
        ratio = SequenceMatcher(None, articulo_upper, art_dic).ratio()
        if ratio > mejor_ratio and ratio >= 0.8:
            mejor_ratio = ratio
            mejor_match = data
            mejor_tipo = f'FUZZY_{int(ratio*100)}%'
    
    if mejor_match:
        linea.categoria = mejor_match['categoria']
        linea.id_categoria = mejor_match['id_categoria']
        linea.match_info = mejor_tipo
        return
    
    if not linea.categoria:
        linea.categoria = 'PENDIENTE'
        linea.match_info = 'SIN_MATCH'


# ============================================================================
# FUNCIÓN: procesar_factura (MEJORADA v5.12 - NORMALIZACIÓN)
# ============================================================================

def procesar_factura(ruta_archivo: Path, indice: dict, es_carpeta_atrasadas: bool = False) -> Factura:
    """
    Procesa una factura PDF o imagen (JPG/PNG).
    
    v5.16: Soporte para parámetro es_carpeta_atrasadas.
    v5.12: Normalización de proveedores mejorada.
    v5.11: Soporte para extractores OCR que procesan imágenes directamente.
    """
    info = parsear_nombre_archivo(ruta_archivo.name, es_carpeta_atrasadas=es_carpeta_atrasadas)
    
    # v5.12: NORMALIZAR proveedor desde el inicio
    proveedor_raw = info.get('proveedor', 'DESCONOCIDO')
    proveedor_normalizado = normalizar_proveedor(proveedor_raw)
    
    factura = Factura(
        archivo=ruta_archivo.name,
        numero=info.get('numero', ''),
        ruta=ruta_archivo,
        proveedor=proveedor_normalizado
    )
    
    extractor = obtener_extractor(factura.proveedor)
    
    # v5.7: Si no encontró extractor, buscar proveedor en el nombre del archivo
    if extractor is None:
        proveedor_alternativo = buscar_proveedor_en_nombre(ruta_archivo.name, EXTRACTORES)
        if proveedor_alternativo:
            factura.proveedor = proveedor_alternativo
            extractor = obtener_extractor(proveedor_alternativo)
    
    # v5.10: Guardar si hay extractor específico (no genérico)
    tiene_extractor_especifico = extractor is not None
    
    # v5.14: Guardar nombre del extractor para el Excel
    if tiene_extractor_especifico and extractor:
        factura.extractor_nombre = extractor.__class__.__name__
    else:
        factura.extractor_nombre = ''
    
    # v5.11: Detectar si el extractor usa OCR
    usa_ocr = extractor and hasattr(extractor, 'metodo_pdf') and extractor.metodo_pdf == 'ocr'
    
    # v5.11: Si el extractor es OCR y tiene método procesar(), usarlo directamente
    if usa_ocr and hasattr(extractor, 'procesar'):
        try:
            resultado_ocr = extractor.procesar(str(ruta_archivo))
            
            # Transferir datos del resultado OCR a la factura
            factura.fecha = resultado_ocr.get('fecha')
            factura.total = resultado_ocr.get('total')
            factura.cif = resultado_ocr.get('cif') or (extractor.cif if extractor else None)
            factura.metodo_pdf = 'ocr'
            factura.texto_raw = getattr(extractor, '_texto_ocr', '[OCR]')
            
            lineas_raw = resultado_ocr.get('lineas', [])
            
        except Exception as e:
            factura.agregar_error(f'OCR_ERROR: {str(e)[:50]}')
            factura.cuadre = 'ERROR_OCR'
            return factura
    else:
        # Flujo normal: extraer texto del PDF
        if extractor is None:
            extractor = ExtractorGenerico()
        
        metodo = extractor.metodo_pdf if extractor else 'pypdf'
        texto = extraer_texto_pdf(ruta_archivo, metodo=metodo, fallback=True)
        factura.texto_raw = texto
        factura.metodo_pdf = metodo
        
        if not texto:
            factura.agregar_error('PDF_VACIO')
            factura.cuadre = 'SIN_TEXTO'
            return factura
        
        if extractor and hasattr(extractor, 'extraer_fecha'):
            factura.fecha = extractor.extraer_fecha(texto)
        if not factura.fecha:
            factura.fecha = extraer_fecha(texto)
        
        factura.cif = extractor.cif if extractor and extractor.cif else extraer_cif(texto)
        factura.iban = extractor.iban if extractor and extractor.iban else extraer_iban(texto)
        
        if extractor and hasattr(extractor, 'extraer_referencia'):
            factura.referencia = extractor.extraer_referencia(texto)
        if not factura.referencia:
            factura.referencia = extraer_referencia(texto)
        
        if extractor and hasattr(extractor, 'extraer_total'):
            factura.total = extractor.extraer_total(texto)
        if factura.total is None:
            factura.total = extraer_total(texto, factura.proveedor)
        
        try:
            lineas_raw = extractor.extraer_lineas(texto) if extractor else []
        except Exception as e:
            factura.agregar_error(f'EXTRACTOR_ERROR: {str(e)[:50]}')
            lineas_raw = []
    
    lineas_convertidas = []
    for linea_raw in lineas_raw:
        if isinstance(linea_raw, LineaFactura):
            linea = linea_raw
        elif isinstance(linea_raw, dict):
            # v5.12: Detectar si la línea tiene importe_iva_inc (BM y similares)
            # En ese caso, necesitamos buscar IVA en diccionario ANTES de calcular base
            tiene_importe_iva_inc = 'importe_iva_inc' in linea_raw and 'base' not in linea_raw
            
            if tiene_importe_iva_inc:
                # Buscar IVA y categoría en el diccionario
                articulo_upper = linea_raw.get('articulo', '').upper().strip()
                prov_normalizado = normalizar_proveedor(factura.proveedor)
                prov_diccionario = buscar_en_diccionario(prov_normalizado, indice)
                
                iva_encontrado = None
                categoria_encontrada = None
                
                if prov_diccionario in indice:
                    articulos_prov = indice[prov_diccionario]
                    
                    # 1. Match exacto
                    if articulo_upper in articulos_prov:
                        data = articulos_prov[articulo_upper]
                        iva_encontrado = data.get('iva', data.get('tipo_iva'))
                        categoria_encontrada = data.get('categoria')
                    else:
                        # 2. Match parcial
                        for art_dic, data in articulos_prov.items():
                            if art_dic in articulo_upper or articulo_upper in art_dic:
                                iva_encontrado = data.get('iva', data.get('tipo_iva'))
                                categoria_encontrada = data.get('categoria')
                                break
                        
                        # 3. Fuzzy match si no hubo parcial
                        if iva_encontrado is None:
                            mejor_ratio = 0
                            for art_dic, data in articulos_prov.items():
                                ratio = SequenceMatcher(None, articulo_upper, art_dic).ratio()
                                if ratio > mejor_ratio and ratio >= 0.7:
                                    mejor_ratio = ratio
                                    iva_encontrado = data.get('iva', data.get('tipo_iva'))
                                    categoria_encontrada = data.get('categoria')
                
                # Si no encontró en diccionario: IVA=0, categoria=PENDIENTE
                if iva_encontrado is None:
                    iva_valor = 0
                    categoria_final = 'PENDIENTE'
                    base_calculada = linea_raw.get('importe_iva_inc', 0)  # Sin conversión
                else:
                    iva_valor = int(iva_encontrado)
                    categoria_final = categoria_encontrada or 'PENDIENTE'
                    # Calcular base desde importe con IVA
                    importe_con_iva = linea_raw.get('importe_iva_inc', 0)
                    factor = 1 + iva_valor / 100
                    base_calculada = round(importe_con_iva / factor, 2)
                
                linea = LineaFactura(
                    articulo=linea_raw.get('articulo', ''),
                    base=base_calculada,
                    iva=iva_valor,
                    codigo=str(linea_raw.get('codigo', '') or ''),
                    cantidad=linea_raw.get('cantidad'),
                    precio_ud=linea_raw.get('precio_ud'),
                    categoria=categoria_final,
                    id_categoria=''
                )
            else:
                # Flujo normal para extractores que devuelven 'base'
                iva_raw = linea_raw.get('iva')
                if iva_raw is None:
                    iva_valor = 21
                else:
                    iva_valor = int(iva_raw)
                
                # Categoría: usar la de la línea, o categoria_fija del extractor como fallback
                cat_linea = linea_raw.get('categoria', '')
                cat_extractor = getattr(extractor, 'categoria_fija', '') if extractor else ''
                categoria_final = cat_linea or cat_extractor
                
                linea = LineaFactura(
                    articulo=linea_raw.get('articulo', ''),
                    base=float(linea_raw.get('base', 0.0) or 0),
                    iva=iva_valor,
                    codigo=str(linea_raw.get('codigo', '') or ''),
                    cantidad=linea_raw.get('cantidad'),
                    precio_ud=linea_raw.get('precio_ud'),
                    categoria=categoria_final,
                    id_categoria=str(linea_raw.get('id_categoria', '') or '')
                )
        else:
            continue
        
        lineas_convertidas.append(linea)
    
    # Prorratear portes
    lineas_prorrateadas = prorratear_portes(lineas_convertidas)
    
    # Categorizar cada línea
    for linea in lineas_prorrateadas:
        categorizar_linea(linea, factura.proveedor, indice, tiene_extractor_especifico)
        factura.agregar_linea(linea)
    
    # v5.7: Validar cuadre considerando retenciones
    factura.cuadre = validar_cuadre_con_retencion(factura.lineas, factura.total, factura.proveedor)
    
    errores = validar_factura(factura)
    for error in errores:
        factura.agregar_error(error)
    
    return factura


# ============================================================================
# FUNCIÓN: validar_cuadre_con_retencion (NUEVA v5.7)
# ============================================================================

def validar_cuadre_con_retencion(lineas, total, proveedor=''):
    """
    Valida el cuadre de la factura considerando posibles retenciones IRPF.
    """
    if total is None:
        return 'SIN_TOTAL'
    if not lineas:
        return 'SIN_LINEAS'
    
    total_lineas = sum(l.base * (1 + l.iva/100) for l in lineas)
    
    # Considerar retención si aplica
    descuadre, tiene_retencion, porcentaje = calcular_descuadre_con_retencion(
        total_lineas, total, proveedor
    )
    
    if tiene_retencion:
        return f'OK_RETENCION_{int(porcentaje*100)}%'
    
    if descuadre < 0.02:
        return 'OK'
    else:
        return f'DESCUADRE_{descuadre:.2f}'


# ============================================================================
# CONFIGURACIÓN RUTAS (v5.16)
# ============================================================================

RUTA_BASE_CONTABILIDAD = Path(r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD")


# ============================================================================
# FUNCIÓN: detectar_trimestre
# ============================================================================

def detectar_trimestre(carpeta_nombre: str) -> str:
    """
    Detecta el trimestre del nombre de la carpeta.
    """
    match = re.search(r'(\d)\s*TRI', carpeta_nombre)
    if match:
        num_tri = match.group(1)
        if num_tri in '1234':
            return f'{num_tri}T25'
    
    match = re.search(r'TRI\w*\s*(\d)', carpeta_nombre)
    if match:
        num_tri = match.group(1)
        if num_tri in '1234':
            return f'{num_tri}T25'
    
    return datetime.now().strftime('%Y%m%d')


# ============================================================================
# FUNCIÓN: buscar_carpetas_trimestre (NUEVA v5.16)
# ============================================================================

def buscar_carpetas_trimestre(ruta_base: Path) -> list:
    """
    Busca carpetas de trimestres en la ruta base.
    
    Detecta patrones como:
    - "1 TRI 2025", "2 TRI 2025", etc.
    - "1T25", "2T25", etc.
    - "TRI 1 2025", etc.
    
    Returns:
        Lista de tuplas (carpeta_path, nombre, tiene_atrasadas)
    """
    carpetas = []
    
    if not ruta_base.exists():
        return carpetas
    
    # Patrones para detectar carpetas de trimestre
    patrones = [
        r'^\d\s*TRI.*\d{4}',      # "1 TRI 2025", "1TRI2025"
        r'^TRI.*\d\s*\d{4}',      # "TRI 1 2025"
        r'^\d[TQ]\d{2}',          # "1T25", "4Q25"
        r'.*TRIMESTRE.*\d',       # "TRIMESTRE 1 2025"
    ]
    
    for item in sorted(ruta_base.iterdir()):
        if item.is_dir():
            nombre = item.name
            # Verificar si coincide con algún patrón de trimestre
            for patron in patrones:
                if re.search(patron, nombre, re.IGNORECASE):
                    # Verificar si tiene subcarpeta ATRASADAS
                    tiene_atrasadas = (item / 'ATRASADAS').exists()
                    carpetas.append((item, nombre, tiene_atrasadas))
                    break
    
    return carpetas


# ============================================================================
# FUNCIÓN: mostrar_menu_interactivo (NUEVA v5.16)
# ============================================================================

def seleccionar_carpeta_grafico() -> Path:
    """
    Abre un diálogo gráfico para seleccionar carpeta con el ratón.
    
    Returns:
        Path de la carpeta seleccionada o None si cancela
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Crear ventana oculta
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal
        root.attributes('-topmost', True)  # Poner encima de otras ventanas
        
        # Directorio inicial
        directorio_inicial = RUTA_BASE_CONTABILIDAD
        if not directorio_inicial.exists():
            directorio_inicial = Path.home()
        
        # Mostrar diálogo
        carpeta = filedialog.askdirectory(
            title="Selecciona la carpeta de facturas",
            initialdir=str(directorio_inicial)
        )
        
        root.destroy()
        
        if carpeta:
            return Path(carpeta)
        return None
        
    except Exception as e:
        print(f"⚠️  Error al abrir selector gráfico: {e}")
        return None


def mostrar_menu_interactivo() -> tuple:
    """
    Muestra menú interactivo para seleccionar carpeta a procesar.
    
    Returns:
        Tupla (carpeta_principal, solo_atrasadas)
        - carpeta_principal: Path de la carpeta seleccionada
        - solo_atrasadas: True si solo procesar ATRASADAS
    """
    print("\n" + "="*60)
    print("PARSEAR FACTURAS - SELECCIÓN DE CARPETA")
    print("="*60)
    
    # Verificar ruta base
    ruta_base = RUTA_BASE_CONTABILIDAD
    
    if not ruta_base.exists():
        print(f"\n⚠️  Ruta por defecto no encontrada:")
        print(f"   {ruta_base}")
    
    # Buscar carpetas de trimestres
    carpetas = []
    if ruta_base.exists():
        carpetas = buscar_carpetas_trimestre(ruta_base)
    
    # Mostrar opciones
    print(f"\nOpciones:\n")
    
    opciones = []
    num = 1
    
    if carpetas:
        print(f"  Carpetas en: {ruta_base}\n")
        for carpeta_path, nombre, tiene_atrasadas in carpetas:
            # Opción: carpeta principal + ATRASADAS (si existe)
            if tiene_atrasadas:
                print(f"  {num}. {nombre} (+ ATRASADAS)")
            else:
                print(f"  {num}. {nombre}")
            opciones.append((carpeta_path, False))  # (path, solo_atrasadas=False)
            num += 1
            
            # Opción adicional: solo ATRASADAS
            if tiene_atrasadas:
                print(f"  {num}. {nombre} → solo ATRASADAS")
                opciones.append((carpeta_path, True))  # (path, solo_atrasadas=True)
                num += 1
        print()
    
    print(f"  E. 📁 Explorar con ratón (abrir selector de carpetas)")
    print(f"  M. Introducir ruta manualmente")
    print(f"  Q. Salir")
    
    # Pedir selección
    print("\nSelecciona una opción:")
    seleccion = input("> ").strip().lower()
    
    if seleccion == 'q':
        print("Saliendo...")
        sys.exit(0)
    
    if seleccion == 'e':
        print("\nAbriendo selector de carpetas...")
        carpeta = seleccionar_carpeta_grafico()
        if carpeta:
            print(f"   Seleccionada: {carpeta}")
            # Preguntar si solo ATRASADAS
            if (carpeta / 'ATRASADAS').exists():
                print(f"\n   Se detectó subcarpeta ATRASADAS.")
                print(f"   ¿Procesar solo ATRASADAS? (s/N):")
                resp = input("   > ").strip().lower()
                if resp == 's':
                    return (carpeta, True)
            return (carpeta, False)
        else:
            print("   Cancelado.")
            sys.exit(0)
    
    if seleccion == 'm':
        print("\nIntroduce la ruta completa de la carpeta:")
        ruta_manual = input("> ").strip()
        if not ruta_manual:
            print("ERROR: No se especificó ruta")
            sys.exit(1)
        carpeta = Path(ruta_manual)
        if not carpeta.exists():
            print(f"ERROR: No existe la ruta: {carpeta}")
            sys.exit(1)
        # Preguntar si solo ATRASADAS
        if (carpeta / 'ATRASADAS').exists():
            print(f"\n   Se detectó subcarpeta ATRASADAS.")
            print(f"   ¿Procesar solo ATRASADAS? (s/N):")
            resp = input("   > ").strip().lower()
            if resp == 's':
                return (carpeta, True)
        return (carpeta, False)
    
    try:
        idx = int(seleccion) - 1
        if 0 <= idx < len(opciones):
            return opciones[idx]
        else:
            print("ERROR: Opción no válida")
            sys.exit(1)
    except ValueError:
        print("ERROR: Introduce un número válido o E/M/Q")
        sys.exit(1)


# ============================================================================
# FUNCIÓN: procesar_carpeta_con_atrasadas (NUEVA v5.16)
# ============================================================================

def procesar_carpeta_con_atrasadas(carpeta: Path, solo_atrasadas: bool = False) -> list:
    """
    Obtiene lista de archivos a procesar, incluyendo subcarpeta ATRASADAS.
    
    Args:
        carpeta: Carpeta principal del trimestre
        solo_atrasadas: Si True, solo procesa la subcarpeta ATRASADAS
        
    Returns:
        Lista de tuplas (archivo_path, es_carpeta_atrasadas)
    """
    archivos = []
    extensiones = ['*.pdf', '*.jpg', '*.jpeg', '*.png']
    
    carpeta_atrasadas = carpeta / 'ATRASADAS'
    
    if solo_atrasadas:
        # Solo procesar ATRASADAS
        if carpeta_atrasadas.exists():
            for ext in extensiones:
                for archivo in carpeta_atrasadas.glob(ext):
                    archivos.append((archivo, True))
        else:
            print(f"⚠️  No existe subcarpeta ATRASADAS en: {carpeta}")
    else:
        # Procesar carpeta principal
        for ext in extensiones:
            for archivo in carpeta.glob(ext):
                archivos.append((archivo, False))
        
        # Procesar ATRASADAS si existe
        if carpeta_atrasadas.exists():
            for ext in extensiones:
                for archivo in carpeta_atrasadas.glob(ext):
                    archivos.append((archivo, True))
    
    return archivos


# ============================================================================
# FUNCIÓN: main
# ============================================================================

def main():
    """Funcion principal."""
    parser = argparse.ArgumentParser(
        description=f'ParsearFacturas v{VERSION} (con soporte OCR)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                              # Modo interactivo
  python main.py -i "C:\\Facturas\\4 TRI 2025"  # Modo directo
  python main.py -i facturas/ -o resultado.xlsx
  python main.py --listar-extractores

v5.16: Modo interactivo, soporte ATRASADAS, TEMP por trimestre
        """
    )
    
    parser.add_argument('--input', '-i', help='Carpeta de facturas (PDF/JPG/PNG)')
    parser.add_argument('--output', '-o', default=None, 
                        help='Archivo Excel de salida')
    parser.add_argument('--diccionario', '-d', default=DICCIONARIO_DEFAULT,
                        help='DiccionarioProveedoresCategoria.xlsx')
    parser.add_argument('--listar-extractores', action='store_true',
                        help='Listar extractores disponibles y salir')
    parser.add_argument('--version', '-v', action='version', version=f'v{VERSION}')
    
    args = parser.parse_args()
    
    if args.listar_extractores:
        extractores = listar_extractores()
        print(f"\nEXTRACTORES DISPONIBLES ({len(extractores)}):\n")
        for nombre, clase in sorted(extractores.items()):
            print(f"  - {nombre}")
        print()
        return
    
    # v5.16: Resetear contadores TEMP al inicio de cada ejecución
    resetear_contadores_temp()
    
    # v5.16: Modo interactivo si no se especifica -i
    solo_atrasadas = False
    if not args.input:
        carpeta, solo_atrasadas = mostrar_menu_interactivo()
    else:
        carpeta = Path(args.input)
    
    if not carpeta.exists():
        print(f"ERROR: No existe la carpeta: {carpeta}")
        sys.exit(1)
    
    diccionario_path = Path(args.diccionario)
    if not diccionario_path.exists():
        print(f"Aviso: Diccionario no encontrado: {diccionario_path}")
        print("   Continuando sin categorizacion...")
        indice = {}
    else:
        print(f"\nCargando diccionario...")
        _, _, indice = cargar_diccionario(diccionario_path)
        print(f"   {len(indice)} proveedores indexados")
    
    print("\n" + "="*60)
    print(f"PARSEAR FACTURAS v{VERSION}")
    print("="*60)
    
    script_dir = Path(__file__).parent
    outputs_dir = script_dir / 'outputs'
    outputs_dir.mkdir(exist_ok=True)
    
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute() and output_path.parent == Path('.'):
            ruta_excel = outputs_dir / output_path.name
        else:
            ruta_excel = output_path
    else:
        carpeta_nombre = carpeta.name.upper()
        trimestre = detectar_trimestre(carpeta_nombre)
        sufijo = '_ATRASADAS' if solo_atrasadas else ''
        ruta_excel = outputs_dir / f'Facturas_{trimestre}{sufijo}.xlsx'
    
    # v5.16: Buscar archivos incluyendo subcarpeta ATRASADAS
    archivos_con_tipo = procesar_carpeta_con_atrasadas(carpeta, solo_atrasadas)
    
    # Contar por tipo
    archivos_principal = [a for a, es_atr in archivos_con_tipo if not es_atr]
    archivos_atrasadas = [a for a, es_atr in archivos_con_tipo if es_atr]
    
    print(f"\nCarpeta: {carpeta}")
    if not solo_atrasadas:
        print(f"   Archivos principales: {len(archivos_principal)}")
    if archivos_atrasadas or solo_atrasadas:
        print(f"   Archivos ATRASADAS: {len(archivos_atrasadas)}")
    print(f"   Total: {len(archivos_con_tipo)}")
    
    if not archivos_con_tipo:
        print("ERROR: No se encontraron archivos PDF/JPG/PNG")
        sys.exit(1)
    
    facturas = []
    for i, (archivo, es_atrasadas) in enumerate(sorted(archivos_con_tipo, key=lambda x: x[0].name), 1):
        nombre_corto = archivo.name[:45] + '...' if len(archivo.name) > 48 else archivo.name
        marca = "[ATR]" if es_atrasadas else ""
        print(f"   [{i:3d}/{len(archivos_con_tipo)}] {marca} {nombre_corto}", end=" ")
        
        try:
            factura = procesar_factura(archivo, indice, es_carpeta_atrasadas=es_atrasadas)
            facturas.append(factura)
            
            if factura.errores:
                print(f"AVISO: {factura.errores[0][:30]}")
            elif factura.lineas:
                print(f"OK: {len(factura.lineas)} lineas, {factura.cuadre}")
            else:
                print("AVISO: SIN_LINEAS")
                
        except Exception as e:
            print(f"ERROR: {str(e)[:40]}")
            factura = Factura(archivo=archivo.name, numero='', ruta=archivo, proveedor='ERROR')
            factura.agregar_error(f'EXCEPCION: {str(e)[:50]}')
            facturas.append(factura)
    
    print(f"\nGenerando Excel...")
    total_filas = generar_excel(facturas, ruta_excel)
    print(f"   {ruta_excel}: {total_filas} filas")
    
    ruta_log = outputs_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    generar_log(facturas, ruta_log)
    print(f"   {ruta_log}")
    
    imprimir_resumen(facturas)
    
    print("Proceso completado\n")


if __name__ == '__main__':
    main()

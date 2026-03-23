---
name: debug-extractor
description: Diagnostica y corrige errores en un extractor de facturas PDF. Identifica el problema y propone fix.
disable-model-invocation: true
argument-hint: "<nombre_proveedor>  ej: BM, JIMELUZ, ANGEL_BORJA"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Diagnóstico y Fix de Extractor

Diagnostica errores en el extractor del proveedor indicado y propone corrección.

## Requisito previo

El usuario debe indicar el proveedor a depurar.
Si no se indica, pedir antes de continuar.

## Paso 1: Identificar el extractor

```bash
ls "C:/_ARCHIVOS/TRABAJO/Facturas/Parseo/extractores/" | grep -i "$1"
```

Leer el archivo del extractor:
```bash
cat "C:/_ARCHIVOS/TRABAJO/Facturas/Parseo/extractores/<archivo>.py"
```

## Paso 2: Ver errores recientes en logs

```bash
# Buscar errores de este proveedor en el log más reciente
ls -t "C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/outputs/"*.log 2>/dev/null | head -1
```

```bash
grep -i "$1" "$(ls -t C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/outputs/*.log 2>/dev/null | head -1)" | tail -30
```

Identificar el tipo de error:
- `DESCUADRE`: total factura ≠ suma líneas (> 0.05€)
- `SIN_LINEAS`: `extraer_lineas()` devuelve lista vacía
- `SIN_TOTAL`: `extraer_total()` devuelve None
- `SIN_FECHA`: `extraer_fecha()` devuelve None
- `SIN_PROVEEDOR`: el proveedor no se identifica (problema de alias)
- `AttributeError`: método eliminado o renombrado

## Paso 3: Obtener PDF fallido para test

Pedir al usuario una ruta a un PDF que falla, o buscar en la carpeta de facturas:
```bash
ls "C:/_ARCHIVOS/TRABAJO/Facturas/"*"$1"* 2>/dev/null | head -5
```

## Paso 4: Extraer texto crudo del PDF

```bash
python -c "
import pdfplumber
with pdfplumber.open(r'RUTA_PDF') as pdf:
    for i, p in enumerate(pdf.pages):
        print(f'--- PAG {i+1} ---')
        print(p.extract_text())
"
```

Si el texto está vacío, probar OCR:
```bash
python -c "
from pdf2image import convert_from_path
import pytesseract
imgs = convert_from_path(r'RUTA_PDF', dpi=300)
for img in imgs:
    print(pytesseract.image_to_string(img, lang='spa'))
"
```

## Paso 5: Diagnosticar el fallo

Con el texto crudo visible, ejecutar el extractor en modo debug:
```bash
python -c "
import sys; sys.path.insert(0, r'C:/_ARCHIVOS/TRABAJO/Facturas/Parseo')
from extractores import obtener_extractor
ext = obtener_extractor('NOMBRE_PROVEEDOR')
import pdfplumber
with pdfplumber.open(r'RUTA_PDF') as pdf:
    texto = chr(10).join(p.extract_text() or '' for p in pdf.pages)
print('=== TEXTO ===')
print(texto[:2000])
print('=== TOTAL ===')
print(ext.extraer_total(texto))
print('=== FECHA ===')
print(ext.extraer_fecha(texto))
print('=== REF ===')
print(ext.extraer_referencia(texto))
print('=== LINEAS ===')
lineas = ext.extraer_lineas(texto)
for l in lineas:
    print(l)
if lineas:
    total = ext.extraer_total(texto) or 0
    suma = sum(l['base'] * (1 + l['iva']/100) for l in lineas)
    print(f'Cuadre: {abs(total - suma):.2f}€ diff')
"
```

## Paso 6: Identificar y corregir el regex/lógica

Basándose en el texto crudo y el resultado del debug:
1. Localizar la línea del extractor que falla
2. Proponer regex corregido
3. Aplicar el fix con Edit
4. **Limpiar caché** (OBLIGATORIO tras cualquier cambio):

```cmd
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\__pycache__"
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\nucleo\__pycache__"
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\__pycache__"
```

## Paso 7: Verificar el fix

Repetir el comando de debug del Paso 5 y confirmar:
- `extraer_total()` devuelve valor correcto
- `extraer_lineas()` devuelve líneas con artículo, base, IVA
- Cuadre ≤ 0.05€
- Fecha y referencia correctas

Si algo sigue fallando, ajustar y volver al Paso 6.

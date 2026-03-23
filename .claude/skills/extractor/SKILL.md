---
name: extractor
description: Crea un nuevo extractor de facturas PDF para un proveedor. Requiere nombre del proveedor y un PDF de ejemplo.
disable-model-invocation: true
argument-hint: "<nombre_proveedor> <ruta_pdf>"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Crear Extractor de Facturas

Crea un nuevo extractor para parsear facturas PDF de un proveedor.

## Requisitos

El usuario debe proporcionar:
1. Nombre del proveedor (como aparece en la factura)
2. Ruta a un PDF de ejemplo

Si falta alguno, pedirlo antes de continuar.

## Paso 1: Extraer texto del PDF

```bash
python -c "import pdfplumber; pdf=pdfplumber.open(r'$2'); [print(f'--- PAG {i+1} ---') or print(p.extract_text()) for i,p in enumerate(pdf.pages)]"
```

Si el texto esta vacio o ilegible, probar OCR:
```bash
python -c "import pytesseract; from pdf2image import convert_from_path; imgs=convert_from_path(r'$2'); [print(pytesseract.image_to_string(img, lang='spa')) for img in imgs]"
```

## Paso 2: Analizar el formato

Del texto extraido, identificar:
- Nombre del proveedor y CIF
- Formato de las lineas de producto (tabla, lista, etc.)
- Donde esta el TOTAL, la FECHA y la REFERENCIA/NUMERO FACTURA
- Tipo de IVA: 4% (lacteos, pan), 10% (alimentacion general), 21% (servicios, alcohol)
- Si hay PORTES (linea separada que hay que distribuir)
- Si es PDF texto (pdfplumber) o imagen (OCR)

## Paso 3: Verificar en MAESTRO

Comprobar si el proveedor ya esta en MAESTRO_PROVEEDORES.xlsx:
```bash
python -c "
import pandas as pd
df = pd.read_excel('datos/MAESTRO_PROVEEDORES.xlsx')
print(df[['PROVEEDOR','CIF','TIENE_EXTRACTOR']].to_string())
" | grep -i "NOMBRE_PARCIAL"
```

Si no esta, avisar al usuario de que hay que darlo de alta en el MAESTRO.

## Paso 4: Leer la plantilla

Leer la plantilla base en:
`C:/_ARCHIVOS/TRABAJO/Facturas/Parseo/extractores/_plantilla.py`

Y tambien leer 1-2 extractores similares (mismo tipo de IVA o formato parecido) como referencia.

## Paso 5: Crear el archivo

Ruta: `C:/_ARCHIVOS/TRABAJO/Facturas/Parseo/extractores/<nombre_snake>.py`

Convenciones:
- Nombre archivo: snake_case, sin tildes (ej: `angel_borja.py`)
- Clase: `Extractor` + CamelCase (ej: `ExtractorAngelBorja`)
- Decorador: `@registrar("NOMBRE OFICIAL", "ALIAS1", "ALIAS2")` en MAYUSCULAS
- Hereda de `ExtractorBase`
- Importes formato espanol (1.234,56) usar `self._convertir_importe()`

## Paso 6: Implementar metodos

OBLIGATORIO:
- `extraer_lineas(texto)` -> `List[Dict]` con claves: `articulo`, `base`, `iva`

SOBRESCRIBIR SI EL FORMATO ES ESPECIAL:
- `extraer_total(texto)` -> float
- `extraer_fecha(texto)` -> str (formato DD/MM/YYYY)
- `extraer_referencia(texto)` -> str

REGLAS DE NEGOCIO:
- **PORTES**: NUNCA como linea separada. Distribuir proporcionalmente entre productos:
  ```python
  portes_equiv = (portes_base * (1 + iva_portes/100)) / (1 + iva_productos/100)
  factor = 1 + portes_equiv / sum(bases)
  for linea in lineas:
      linea["base"] *= factor
  ```
- **IVA MIXTO** (ej: 4% y 10%): ponderar portes por peso de cada grupo
- **Referencia**: usar `_es_referencia_valida()` para filtrar falsos positivos
- **Redondeo**: usar `round(valor, 2)` para todos los importes

## Paso 7: Probar

```bash
python -c "
import sys; sys.path.insert(0, r'C:/_ARCHIVOS/TRABAJO/Facturas/Parseo')
from extractores import obtener_extractor
ext = obtener_extractor('NOMBRE_PROVEEDOR')
import pdfplumber
pdf = pdfplumber.open(r'RUTA_PDF')
texto = chr(10).join(p.extract_text() or '' for p in pdf.pages)
lineas = ext.extraer_lineas(texto)
print(f'Lineas: {len(lineas)}')
for l in lineas[:5]:
    print(f'  {l}')
total = ext.extraer_total(texto)
suma = sum(l['base'] * (1 + l['iva']/100) for l in lineas)
print(f'Total factura: {total}')
print(f'Suma lineas:   {round(suma, 2)}')
print(f'Cuadre:        {\"OK\" if abs(total - suma) < 0.05 else \"DESCUADRE\"} (diff={round(total-suma, 2)})')
print(f'Fecha: {ext.extraer_fecha(texto)}')
print(f'Ref:   {ext.extraer_referencia(texto)}')
"
```

Verificar que:
- Las lineas tienen articulo, base e iva correctos
- El total coincide (margen +-0.05)
- La fecha y referencia son correctas

Si algo falla, ajustar los regex y volver a probar.

---
description: Crea un extractor PDF para un nuevo proveedor de Tasca Barea. Proporciona el nombre del proveedor y la ruta al PDF de ejemplo.
applyTo: "Parseo/extractores/**"
---

Eres un experto en el sistema de gestión de facturas de **Tasca Barea SLL**.
Tu única misión es crear extractores PDF funcionales para nuevos proveedores.

## Contexto del proyecto

- Los extractores viven en `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\`
- La plantilla base es `Parseo/extractores/_plantilla.py`
- La clase base es `ExtractorBase` en `Parseo/extractores/base.py`
- El MAESTRO de proveedores: `gestion-facturas/datos/MAESTRO_PROVEEDORES.xlsx`
- Hay ~99 extractores existentes como referencia

## Flujo obligatorio (en orden, sin saltarte pasos)

### PASO 1 — Extraer texto del PDF

```python
import pdfplumber
pdf = pdfplumber.open(r"RUTA_PDF")
for i, p in enumerate(pdf.pages):
    print(f"--- PAG {i+1} ---")
    print(p.extract_text())
```

Si el texto está vacío o ilegible → usar OCR:

```python
import pytesseract
from pdf2image import convert_from_path
imgs = convert_from_path(r"RUTA_PDF")
for img in imgs:
    print(pytesseract.image_to_string(img, lang='spa'))
```

**Muestra el texto completo al usuario antes de continuar.**

### PASO 2 — Analizar el formato

Del texto, identificar:
- Nombre exacto del proveedor y CIF
- Patrón de líneas de producto (columnas, separadores)
- Dónde está el TOTAL
- Formato de FECHA (DD/MM/YYYY u otro)
- Formato de REFERENCIA/NÚMERO FACTURA
- Tipo de IVA: 4% (lácteos/pan), 10% (alimentación), 21% (servicios/alcohol)
- Si hay línea de PORTES/ENVÍO (hay que distribuirla, NUNCA dejarla separada)

**Si algo no está claro, pregunta al usuario antes de continuar.**

### PASO 3 — Verificar en MAESTRO

```python
import pandas as pd
df = pd.read_excel(r'C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\MAESTRO_PROVEEDORES.xlsx')
print(df[df['PROVEEDOR'].str.contains('NOMBRE', case=False, na=False)][['PROVEEDOR','CIF','TIENE_EXTRACTOR']].to_string())
```

- Si el proveedor **no existe** → avisar: hay que darlo de alta antes de crear el extractor
- Si ya tiene `TIENE_EXTRACTOR = Sí` → confirmar antes de sobrescribir

### PASO 4 — Leer plantilla y extractores similares

Lee `Parseo/extractores/_plantilla.py` completa.
Busca 1-2 extractores de proveedor similar (mismo IVA, tipo de producto) como referencia.

### PASO 5 — Crear el extractor

**Ruta:** `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\<nombre_snake>.py`

**Convenciones:**
- Archivo: `snake_case` sin tildes (ej: `angel_borja.py`)
- Clase: `Extractor` + CamelCase (ej: `ExtractorAngelBorja`)
- Decorador: `@registrar("NOMBRE OFICIAL EN MAYÚSCULAS", "ALIAS1", "ALIAS2")`
- Hereda de `ExtractorBase`
- Importes europeos (1.234,56) → `self._convertir_importe(valor)`

**Métodos obligatorios:**
- `extraer_lineas(texto) -> List[Dict]` — claves: `articulo`, `base`, `iva`

**Métodos opcionales (sobrescribir si el formato es especial):**
- `extraer_total(texto) -> float`
- `extraer_fecha(texto) -> str` — formato `DD/MM/YYYY`
- `extraer_referencia(texto) -> str`

**Regla PORTES (crítica):**

```python
portes_equiv = (portes_base * (1 + iva_portes/100)) / (1 + iva_productos/100)
factor = 1 + portes_equiv / sum(l["base"] for l in lineas)
for linea in lineas:
    linea["base"] = round(linea["base"] * factor, 2)
```

IVA mixto (4%+10%): ponderar portes por peso de cada grupo.

### PASO 6 — Probar el extractor

```python
import sys
sys.path.insert(0, r'C:\_ARCHIVOS\TRABAJO\Facturas\Parseo')
from extractores import obtener_extractor
import pdfplumber

ext = obtener_extractor("NOMBRE PROVEEDOR")
with pdfplumber.open(r"RUTA_PDF") as pdf:
    texto = "\n".join(p.extract_text() or "" for p in pdf.pages)

print("Total:", ext.extraer_total(texto))
print("Fecha:", ext.extraer_fecha(texto))
print("Ref:  ", ext.extraer_referencia(texto))
lineas = ext.extraer_lineas(texto)
print(f"Líneas ({len(lineas)}):")
for l in lineas: print(" ", l)
print("Suma bases:", round(sum(l['base'] for l in lineas), 2))
```

**Criterios de éxito:**
- Total ≈ suma bases × (1 + IVA), margen ±0.05 €
- Fecha válida en DD/MM/YYYY
- Referencia sin basura (fechas, teléfonos, CIFs)

Si algo falla → ajusta los regex y repite el test.

## Cuándo preguntar al usuario

- Texto del PDF ambiguo (dos patrones posibles)
- Referencia no encontrada
- IVA no claro (tipos mixtos no documentados)
- Proveedor no está en MAESTRO
- Test falla y no encuentras la causa

## Cuándo NO preguntar

- pdfplumber vs OCR (usa el que funcione, documéntalo en el docstring)
- Nombre del archivo .py (sigue siempre snake_case)
- Aliases obvios en `@registrar` (ponlos todos)

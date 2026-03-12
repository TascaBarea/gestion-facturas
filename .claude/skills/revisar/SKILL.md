---
name: revisar
description: Analiza los movimientos REVISAR del cuadre bancario, agrupa por patron, diagnostica causas y genera plan de accion priorizado.
disable-model-invocation: true
argument-hint: "[ruta_archivo.xlsx]"
allowed-tools: Bash, Read, Grep, Glob
---

# Analizar REVISAR del Cuadre

Analiza un Excel de cuadre para agrupar, diagnosticar y priorizar los movimientos marcados como REVISAR.

## 1. Encontrar el archivo de cuadre

Si $ARGUMENTS contiene una ruta, usar ese archivo.
Si no, buscar el mas reciente en outputs/:
```bash
ls -t "C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/outputs/Cuadre_*.xlsx" | head -1
```

Verificar que el archivo existe antes de continuar.

## 2. Cargar datos con Python

Ejecutar un script Python que:

```python
import pandas as pd
from pathlib import Path
from collections import Counter
import re

archivo = "RUTA_DEL_ARCHIVO"
# Leer todas las hojas de movimientos (no Facturas)
xlsx = pd.ExcelFile(archivo)
hojas_mov = [h for h in xlsx.sheet_names if h.lower() != 'facturas']

# Cargar facturas para diagnostico
df_fact = pd.read_excel(archivo, sheet_name='Facturas')

# Cargar MAESTRO para verificar aliases
maestro_path = Path(r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\MAESTRO_PROVEEDORES.xlsx")
```

## 3. Agrupar REVISAR por patron

Para cada hoja de movimientos:
- Filtrar filas donde `Categoria_Tipo == "REVISAR"`
- Extraer el nombre del comercio/emisor del concepto:
  - `COMPRA TARJ. 5540XXXXXXXX1019 PANIFIESTO LAVAPIES-MADRID` -> `PANIFIESTO LAVAPIES`
  - `TRANSFERENCIA A VINOS DE ARGANZA` -> `VINOS DE ARGANZA`
  - `ADEUDO RECIBO CERES CERVEZA S L` -> `CERES CERVEZA S L`
  - `TELEFONOS YOIGO YC250014247872` -> `YOIGO`
  - `ELECTRICIDAD ENERGIA COLECTIVA, S.L.` -> `ENERGIA COLECTIVA`
  - Otros: tomar el concepto completo

Logica de extraccion:
```python
def extraer_nombre(concepto):
    c = str(concepto).upper().strip()
    if c.startswith("COMPRA TARJ") or c.startswith("ANUL COMPRA TARJ"):
        # Posicion 30+ hasta el guion
        try:
            nombre = c[30:].split("-")[0].strip()
            if len(nombre) > 2:
                return nombre
        except:
            pass
    elif c.startswith("TRANSFERENCIA A "):
        return c.replace("TRANSFERENCIA A ", "").strip()
    elif c.startswith("ADEUDO RECIBO "):
        return c.replace("ADEUDO RECIBO ", "").strip()
    elif "YOIGO" in c:
        return "YOIGO"
    elif c.startswith("ELECTRICIDAD "):
        return c.replace("ELECTRICIDAD ", "").split(",")[0].strip()
    return c[:50]
```

Agrupar y contar por nombre extraido.

## 4. Diagnosticar cada grupo

Para cada grupo de REVISAR (ordenado por frecuencia descendente):

**a) Verificar si el proveedor existe en MAESTRO:**
- Buscar el nombre en columnas NOMBRE_EN_CONCEPTO y TITULO_FACTURA del MAESTRO
- Si NO existe: causa = "Falta alias en MAESTRO", solucion = añadir alias
- Si SI existe: investigar por que fallo:

**b) Si existe en MAESTRO, verificar facturas:**
- Buscar en df_fact por titulo del proveedor
- Si no hay facturas: causa = "Sin facturas en el Excel"
- Si hay facturas pero estan usadas: causa = "Facturas agotadas (ya vinculadas)"
- Si hay facturas disponibles: causa = "Fallo en matching (fecha >60 dias o importe no coincide)"

**c) Categorizar irresolubles:**
- Conceptos con "REINTEGRO", "COMISION", "TRIBUTO", "SEGUROS SOCIALES" -> categoria "Operaciones bancarias"
- Conceptos con "SUBVENCION", "DEVOLUCION" -> categoria "Ingresos especiales"
- El Categoria_Detalle contiene notas humanas (INVESTIGAR, COMPROBAR, PRUEBA, ESTAFA, etc.) -> categoria "Notas manuales previas"

## 5. Generar plan de accion

Ordenar las acciones por impacto (numero de REVISAR que resolverian):

```
ACCION 1: [tipo] [detalle] -> -XX REVISAR
ACCION 2: [tipo] [detalle] -> -XX REVISAR
...
```

Tipos de accion:
- "Añadir alias al MAESTRO" - el mas comun y facil
- "Ajustar clasificador en cuadre.py" - requiere codigo
- "Faltan facturas en Excel" - el usuario debe añadirlas
- "Revisar manualmente" - no automatizable

## 6. Presentar informe

Formato de salida (pantalla):

```
ANALISIS REVISAR - [nombre_archivo]
======================================
Fecha: [hoy]
Total movimientos: XXXX | Clasificados: XXXX | REVISAR: XXX

POR HOJA:
  Tasca:        XXX REVISAR de XXXX movimientos
  Comestibles:  XXX REVISAR de XXXX movimientos

TOP 15 PATRONES REVISAR (por frecuencia):
  1. NOMBRE_COMERCIO          XX mov  [causa resumida]
  2. NOMBRE_COMERCIO          XX mov  [causa resumida]
  ...

DIAGNOSTICO DETALLADO:
  NOMBRE_COMERCIO (XX mov):
    Causa: [explicacion]
    Solucion: [accion concreta]
    Impacto: -XX REVISAR

PLAN DE ACCION (mayor impacto primero):
  1. [accion] -> -XX REVISAR
  2. [accion] -> -XX REVISAR
  ...
  Total potencial: -XXX REVISAR (XXX -> XXX)

IRRESOLUBLES (XXX mov):
  Operaciones bancarias:    XX mov
  Notas manuales previas:   XX mov
  Ingresos especiales:      XX mov
  Sin factura conocida:     XX mov
```

## 7. Guardar log

Guardar el mismo contenido en:
```
outputs/revisar_YYYYMMDD.txt
```

Al final, informar al usuario:
```
Informe guardado en outputs/revisar_YYYYMMDD.txt
¿Quieres que ejecute alguna accion? (ej: "haz la accion 2")
```

## Notas

- Idioma: espanol. Sin emojis.
- El MAESTRO esta en `datos/MAESTRO_PROVEEDORES.xlsx` (gitignored, solo local)
- No modificar ningun archivo automaticamente. Solo analizar y recomendar.
- Si el usuario pide ejecutar una accion, entonces si modificar (MAESTRO, cuadre.py, etc.)
- Las rutas de archivos Excel pueden tener espacios. Siempre usar comillas.

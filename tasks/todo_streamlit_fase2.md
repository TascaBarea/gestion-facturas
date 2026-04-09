# TODO: Fase 2 — Página Parseo real con extractores de Parseo/
<!-- Para ejecutar con: claude --dangerously-skip-permissions -->
<!-- Referencia: docs/PLAN_STREAMLIT_REORGANIZACION_v1.md -->

## CONTEXTO

Hay dos proyectos relevantes:
- **gestion-facturas**: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\`
- **Parseo**: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\`

Parseo contiene el motor de extracción de facturas:
- `main.py` (v5.10+) con función `procesar_factura(ruta_pdf, indice) -> Factura`
- `extractores/` con 104 extractores específicos por proveedor
- `nucleo/` con clases Factura, LineaFactura, funciones de PDF y parser
- `config/settings.py` con constantes
- `salidas/` con generación de Excel y logs

La página `streamlit_app/pages/parseo.py` ahora es un placeholder.
Hay que reemplazarla con una página funcional que use el motor Parseo real.

## RUTA DROPBOX FACTURAS

Las facturas están en Dropbox. Patrón de rutas:

```
C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\
├── FACTURAS 2025\FACTURAS RECIBIDAS\
│   ├── 1 TRIMESTRE 2025\
│   │   ├── *.pdf          (facturas del trimestre)
│   │   └── ATRASADAS\     (facturas atrasadas)
│   ├── 2 TRIMESTRE 2025\
│   ├── 3 TRIMESTRE 2025\
│   └── 4 TRIMESTRE 2025\
├── FACTURAS 2026\FACTURAS RECIBIDAS\
│   ├── 1 TRIMESTRE 2026\
│   ├── 2 TRIMESTRE 2026\
│   └── ...
```

La carpeta base es:
```python
DROPBOX_BASE = Path(r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD")
```

Los años disponibles se detectan buscando carpetas `FACTURAS YYYY`.
Los trimestres se detectan buscando carpetas `N TRIMESTRE YYYY` dentro de `FACTURAS RECIBIDAS`.
Cada trimestre puede tener una subcarpeta `ATRASADAS`.

## DICCIONARIO

El diccionario de categorías está en:
```python
DICCIONARIO_PATH = Path(r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\DiccionarioProveedoresCategoria.xlsx")
```

Se carga con la función `cargar_diccionario()` de main.py.

## OBJETIVO

Reemplazar el placeholder `streamlit_app/pages/parseo.py` con una página funcional que:

1. Detecte automáticamente las carpetas de Dropbox (años + trimestres)
2. Permita seleccionar trimestre via dropdown
3. Pregunte si incluir ATRASADAS (checkbox)
4. Permita elegir: todas las facturas, solo nuevas, o una concreta (selectbox)
5. Ejecute el parseo usando el motor real de Parseo/
6. Muestre resultados: tabla resumen + detalle expandible por factura
7. Exporte a Excel

---

## TAREAS

### Tarea 1: Verificar que Parseo es importable

Primero verifica que se puede importar desde Parseo:

```python
import sys
sys.path.insert(0, r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo")

# Estos imports deben funcionar:
from main import procesar_factura, cargar_diccionario, normalizar_proveedor, ALIAS_DICCIONARIO
from nucleo.factura import Factura, LineaFactura
from extractores import obtener_extractor, listar_extractores, EXTRACTORES
```

Si hay errores de import, diagnostica y resuelve. Posibles problemas:
- `config.settings` puede tener rutas relativas → ajustar
- `limpiar_pycache()` se ejecuta al importar main.py → no debería dar error
- `sys.dont_write_bytecode = True` → OK, no afecta

Si `config.settings` da problemas por rutas, crea un wrapper que ajuste las rutas antes de importar.

### Tarea 2: Crear función de detección de carpetas

Crear lógica para detectar carpetas de Dropbox automáticamente.

```python
from pathlib import Path

DROPBOX_BASE = Path(r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD")

def detectar_trimestres() -> list[dict]:
    """
    Escanea Dropbox y devuelve lista de trimestres disponibles.
    Cada elemento: {
        'label': '1T26',           # Para mostrar en dropdown
        'display': '1 TRIMESTRE 2026',  # Nombre completo
        'path': Path(...),         # Ruta a la carpeta
        'tiene_atrasadas': bool,   # Si existe subcarpeta ATRASADAS
        'path_atrasadas': Path(...) | None,
        'num_pdfs': int,           # Número de PDFs en carpeta principal
        'num_atrasadas': int,      # Número de PDFs en ATRASADAS
    }
    Ordenados de más reciente a más antiguo.
    """
    trimestres = []
    
    # Buscar carpetas FACTURAS YYYY
    for year_dir in sorted(DROPBOX_BASE.glob("FACTURAS *"), reverse=True):
        year_match = re.search(r'FACTURAS\s+(\d{4})', year_dir.name)
        if not year_match:
            continue
        year = year_match.group(1)
        
        recibidas = year_dir / "FACTURAS RECIBIDAS"
        if not recibidas.exists():
            continue
        
        # Buscar N TRIMESTRE YYYY
        for tri_dir in sorted(recibidas.glob("* TRIMESTRE *"), reverse=True):
            tri_match = re.search(r'(\d)\s*TRIM', tri_dir.name)
            if not tri_match:
                continue
            num = tri_match.group(1)
            label = f"{num}T{year[2:]}"  # "1T26"
            
            atrasadas = tri_dir / "ATRASADAS"
            pdfs = list(tri_dir.glob("*.pdf"))
            pdfs_atrasadas = list(atrasadas.glob("*.pdf")) if atrasadas.exists() else []
            
            trimestres.append({
                'label': label,
                'display': tri_dir.name,
                'path': tri_dir,
                'tiene_atrasadas': atrasadas.exists() and len(pdfs_atrasadas) > 0,
                'path_atrasadas': atrasadas if atrasadas.exists() else None,
                'num_pdfs': len(pdfs),
                'num_atrasadas': len(pdfs_atrasadas),
            })
    
    return trimestres
```

### Tarea 3: Crear la página parseo.py completa

Reemplazar `streamlit_app/pages/parseo.py` con una página funcional.

**Estructura de la página:**

```
HEADER: "🔍 Parseo de Facturas"

SIDEBAR/CONTROLES (en la zona principal, no en sidebar):
├── Dropdown: Seleccionar trimestre (detectado automáticamente)
├── Checkbox: "Incluir ATRASADAS" (solo si tiene_atrasadas)
├── Radio: "Todas las facturas" / "Solo nuevas" / "Factura concreta"
│   └── Si "concreta": selectbox con lista de PDFs
├── Botón: "Ejecutar Parseo"

RESULTADOS (tras ejecutar):
├── Métricas: Total | OK | Descuadre | Sin extractor | Líneas
├── Tabla resumen: archivo, proveedor, líneas, cuadre (con colores)
├── Expander por factura: detalle líneas + desglose IVA + texto raw
└── Botón: "Descargar Excel"
```

**Imports necesarios:**

```python
import streamlit as st
import sys
import re
import io
import pandas as pd
from pathlib import Path
from datetime import datetime

from utils.auth import require_role

# Intentar importar Parseo (modo local)
PARSEO_DISPONIBLE = False
try:
    sys.path.insert(0, r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo")
    from main import procesar_factura, cargar_diccionario
    from extractores import listar_extractores
    PARSEO_DISPONIBLE = True
except ImportError as e:
    pass  # Modo cloud: parseo no disponible
```

**Auth:**
```python
require_role(["admin"])
```

**Detección "solo nuevas":**
Para saber qué facturas ya se parsearon, buscar si existe un Excel previo de output.
Alternativa más simple: comparar con un registro en session_state o un archivo de control.
La opción más pragmática: listar los PDFs y mostrar cuántos hay, el usuario decide.
Simplificación para v1: "Solo nuevas" compara contra el Excel COMPRAS existente — si el archivo ya aparece en la columna ARCHIVO del Excel, se considera procesada.

**Ruta del Excel COMPRAS existente:**
Buscar en `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\outputs\Facturas_XTYY.xlsx`
o en `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs\`

**Formato de resultados en pantalla:**
- Usar formato moneda español: `1.234,56 €`
- Colores: ✅ verde para OK, ⚠️ ámbar para descuadre < 1€, ❌ rojo para descuadre > 1€
- Tabla con st.dataframe, columnas formateadas

**Export Excel:**
Usar la función `generar_excel` de salidas/ si importable.
Si no, generar con pandas + openpyxl directamente (dos hojas: Lineas + Facturas).

**Manejo de la ruta del Diccionario:**
```python
DICCIONARIO_PATH = Path(r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\DiccionarioProveedoresCategoria.xlsx")

@st.cache_data(ttl=300)
def cargar_indice():
    if DICCIONARIO_PATH.exists():
        _, _, indice = cargar_diccionario(DICCIONARIO_PATH)
        return indice
    return {}
```

**Caching:**
- Cachear `detectar_trimestres()` con `@st.cache_data(ttl=60)`
- Cachear `cargar_indice()` con `@st.cache_data(ttl=300)`
- NO cachear el parseo (debe ejecutarse cada vez)

**Progress bar durante parseo:**
```python
barra = st.progress(0, text="Parseando facturas...")
for i, pdf in enumerate(archivos):
    factura = procesar_factura(pdf, indice)
    resultados.append(factura)
    barra.progress((i+1)/len(archivos), text=f"[{i+1}/{len(archivos)}] {pdf.name[:40]}")
barra.empty()
```

### Tarea 4: Manejar el caso cloud (Parseo no disponible)

Si `PARSEO_DISPONIBLE` es False (ejecutando en Streamlit Cloud):
```python
if not PARSEO_DISPONIBLE:
    st.warning("⚠️ Parseo local no disponible — el motor de extractores requiere acceso al PC.")
    st.info("Alternativa: sube PDFs manualmente para parseo básico con extractores embebidos.")
    # Mostrar file_uploader como fallback
    # Usar extractores embebidos básicos (los 4 que ya tenemos)
```

Para el fallback con file_uploader, reutilizar la lógica del parseo.py que ya generamos
en la sesión anterior (BM, GUERRA, MARITA, MIGUEZ CAL). Copiar las clases de extractores
embebidos como fallback.

### Tarea 5: Generar Excel de salida

El Excel debe tener dos hojas:

**Hoja "Lineas":**
Columnas: #, ARCHIVO, PROVEEDOR, CÓDIGO, ARTÍCULO, CATEGORÍA, CANTIDAD, PRECIO_UD, TIPO_IVA, BASE, CUOTA_IVA, TOTAL, MATCH

**Hoja "Facturas":**
Columnas: #, ARCHIVO, PROVEEDOR, FECHA, REF, CIF, TOTAL_FACTURA, TOTAL_CALCULADO, CUADRE, EXTRACTOR, LÍNEAS, ERRORES

Nombre del archivo: `Facturas_{trimestre}_{fecha}.xlsx` donde fecha = YYYYMMDD

```python
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_lineas.to_excel(writer, sheet_name='Lineas', index=False)
    df_facturas.to_excel(writer, sheet_name='Facturas', index=False)

st.download_button(
    "📥 Descargar Excel",
    data=buffer.getvalue(),
    file_name=f"Facturas_{trimestre}_{datetime.now().strftime('%Y%m%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

### Tarea 6: Test

1. Verificar sintaxis: `python -c "import ast; ast.parse(open('streamlit_app/pages/parseo.py').read())"`
2. Verificar imports de Parseo:
```python
import sys
sys.path.insert(0, r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo")
from main import procesar_factura, cargar_diccionario
from extractores import listar_extractores
print(f"Extractores disponibles: {len(listar_extractores())}")
```
3. Verificar detección de carpetas Dropbox:
```python
# Ejecutar la función detectar_trimestres() y mostrar resultados
```
4. Si hay facturas PDF en alguna carpeta, hacer una prueba con 1-2 facturas.
5. Verificar que la app arranca: `cd streamlit_app && streamlit run app.py`

---

## RESULTADO ESPERADO

Al terminar:
1. La página Parseo muestra dropdown con trimestres detectados de Dropbox
2. Checkbox "Incluir ATRASADAS" aparece si la carpeta tiene subcarpeta ATRASADAS
3. Al hacer click en "Ejecutar Parseo", procesa los PDFs con los 104 extractores reales
4. Muestra resultados con métricas, tabla resumen y detalle expandible
5. Botón "Descargar Excel" genera archivo descargable
6. Si no hay acceso a Parseo (cloud), muestra fallback con file uploader

## NOTAS PARA CLAUDE CODE

- La ruta de Parseo es `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo` — verificar que existe
- NO modificar ningún archivo de Parseo/ — solo leer/importar
- NO modificar app.py ni auth.py (ya actualizados en Fase 1)
- Preservar el formato moneda español en toda la UI: `1.234,56 €`
- Si `config.settings` de Parseo da error al importar, crear un wrapper que gestione los paths
- El diccionario está en `gestion-facturas/datos/DiccionarioProveedoresCategoria.xlsx`
- Los resultados del parseo NO se guardan automáticamente — solo se muestran y se pueden descargar
- Usar `@st.cache_data` para cosas lentas (diccionario, detección carpetas), NO para el parseo en sí

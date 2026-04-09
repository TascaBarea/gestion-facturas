# TODO: Fase 1 — Reestructurar Streamlit App
<!-- Para ejecutar con: claude --autoaccept -->
<!-- Sesión nocturna — 05/04/2026 -->
<!-- Referencia: docs/PLAN_STREAMLIT_REORGANIZACION_v1.md -->

## CONTEXTO

La app Streamlit está en `streamlit_app/` dentro de `gestion-facturas/`.
Ruta completa: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\streamlit_app\`

Estructura actual:
```
streamlit_app/
├── .streamlit/
│   ├── config.toml
│   ├── secrets.toml
│   └── secrets.toml.example
├── pages/
│   ├── alta_evento.py
│   ├── calendario_eventos.py
│   ├── cuadre.py
│   ├── documentos.py
│   ├── ejecutar.py
│   ├── log_gmail.py
│   ├── maestro.py
│   ├── monitor.py
│   └── ventas.py
├── utils/
│   ├── __init__.py
│   ├── auth.py
│   ├── data_client.py
│   └── wc_client.py
├── app.py
├── generar_hashes.py
└── requirements.txt
```

## OBJETIVO

Reorganizar la app en 4 secciones con sidebar agrupado + página de inicio Hub.
NO romper nada existente. Todas las páginas actuales deben seguir funcionando.

## IDENTIDAD VISUAL

- Sidebar: gradiente `#1A1A1A → #2A1A1A`
- Acento primario: granate `#8B0000` / bermellón `#CA3026`
- Tipografía headings: Syne
- Tipografía body: DM Sans
- Formato cifras: español `1.234,56 €`

---

## TAREAS (ejecutar en orden)

### Tarea 1: Leer y entender app.py actual

Lee `streamlit_app/app.py` completo. Identifica:
- Cómo está definido ALL_PAGES (diccionario con st.Page)
- Cómo se aplican los roles (page_ids_for_role)
- El CSS inline (preservar tal cual)
- La lógica de login y sesión (no tocar)

### Tarea 2: Actualizar ROLE_PAGES en auth.py

En `streamlit_app/utils/auth.py`, actualizar el diccionario ROLE_PAGES:

```python
ROLE_PAGES = {
    "admin":   ["inicio", "parseo", "facturas", "maestro", "diccionario", "log_gmail",
                "ventas", "articulos",
                "alta_evento", "calendario_eventos",
                "cuadre", "ejecutar", "monitor", "documentos"],
    "socio":   ["inicio", "ventas", "calendario_eventos", "alta_evento", "documentos"],
    "comes":   ["inicio", "ventas", "documentos"],
    "eventos": ["inicio", "alta_evento", "calendario_eventos"],
}
```

### Tarea 3: Crear página de inicio (inicio.py)

Crear `streamlit_app/pages/inicio.py`.

Esta página muestra 4 tarjetas grandes en grid 2x2, una por sección:
- COMPRAS (📦) — con dato de facturas recientes si disponible
- VENTAS (📊) — con dato de ventas semana si disponible
- EVENTOS (🎪) — con próximo evento si disponible
- OPERACIONES (⚙️) — con estado backend

Cada tarjeta es clickeable y navega a la primera página de su sección.

Patrón de la tarjeta (usar st.columns + st.container o HTML con st.markdown):
- Icono grande
- Nombre de sección (font Syne, tamaño grande)
- Descripción corta
- Un dato clave (si hay backend disponible, sino mostrar "—")

Usar los colores de marca:
- COMPRAS: fondo bermellón suave `#CA302610`, texto `#CA3026`
- VENTAS: fondo sage suave `#ACC8A215`, texto `#1A2517`
- EVENTOS: fondo dorado suave `#F6AA0012`, texto `#8B6D00`
- OPERACIONES: fondo neutro gris

Para datos en vivo, intentar llamar a las funciones de data_client:
```python
from utils.data_client import backend_disponible, get_meta, get_gmail, get_ventas_comes, fetch_backend_json
```
Si el backend no está disponible, mostrar "—" en lugar de datos.

Para la navegación al hacer click en una tarjeta, usar st.page_link() o st.switch_page():
```python
# Ejemplo
if st.button("Ver Compras", key="btn_compras"):
    st.switch_page("pages/parseo.py")
```

Importar auth:
```python
from utils.auth import require_role
require_role(["admin", "socio", "comes", "eventos"])
```

### Tarea 4: Modificar app.py — Reorganizar ALL_PAGES con secciones

En `streamlit_app/app.py`, cambiar el diccionario ALL_PAGES para usar secciones de st.navigation.

El formato de st.navigation con secciones es:
```python
pages = st.navigation({
    "": [inicio_page],  # Sin cabecera de sección
    "Compras": [parseo_page, facturas_page, maestro_page, diccionario_page, log_gmail_page],
    "Ventas": [ventas_page, articulos_page],
    "Eventos": [calendario_page, alta_evento_page],
    "Operaciones": [cuadre_page, ejecutar_page, monitor_page, documentos_page],
})
```

Donde cada page se define como:
```python
inicio_page = st.Page("pages/inicio.py", title="Inicio", icon="🏠", default=True)
parseo_page = st.Page("pages/parseo.py", title="Parseo", icon="🔍")
# ... etc
```

IMPORTANTE:
- `default=True` solo en inicio
- Los nombres de archivo deben coincidir con los que existen en pages/
- Las páginas nuevas que aún no existen (parseo.py, facturas.py, diccionario.py, articulos.py) deben crearse como placeholder
- Mantener el filtrado por rol: solo mostrar las páginas que el rol permite

La lógica de filtrado por rol ya existe en app.py. Adaptarla para que funcione con el nuevo formato dict de secciones:
```python
allowed = page_ids_for_role(role)
filtered_pages = {}
for section, section_pages in all_pages.items():
    visible = [p for p in section_pages if p.url_path.replace("/", "") in allowed or p.url_path == ""]
    if visible:
        filtered_pages[section] = visible
```

Nota: el url_path de st.Page se deriva del nombre del archivo. Verificar que coincida con los IDs en ROLE_PAGES.

### Tarea 5: Crear páginas placeholder

Crear las siguientes páginas que aún no existen, como placeholders simples:

**`streamlit_app/pages/parseo.py`:**
```python
import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("🔍 Parseo de Facturas")
st.info("Página en construcción. Próximamente: selección de carpeta Dropbox, ejecución de parseo, visualización de resultados.")
```

**`streamlit_app/pages/facturas.py`:**
```python
import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📋 Listado de Facturas")
st.info("Página en construcción. Próximamente: listado filtrable de facturas procesadas.")
```

**`streamlit_app/pages/diccionario.py`:**
```python
import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📖 Diccionario de Artículos")
st.info("Página en construcción. Próximamente: visualización del DiccionarioProveedoresCategoria.")
```

**`streamlit_app/pages/articulos.py`:**
```python
import streamlit as st
from utils.auth import require_role

require_role(["admin"])

st.header("📦 Artículos")
st.info("Página en construcción. Próximamente: catálogo de artículos Loyverse.")
```

### Tarea 6: Verificar que no se rompe nada

1. Revisar que todas las páginas existentes siguen importando correctamente
2. Verificar que los imports de utils.auth y utils.data_client funcionan
3. Comprobar que el CSS inline de app.py no se ha modificado
4. Verificar que la lógica de login no se ha tocado
5. Verificar que la lógica de rate limiting no se ha tocado

### Tarea 7: Actualizar requirements.txt si necesario

El requirements.txt actual es:
```
streamlit>=1.32.0
WooCommerce>=3.0.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
```

Verificar que st.navigation con secciones (dict) requiere streamlit >= 1.36.0.
Si es así, actualizar:
```
streamlit>=1.36.0
```

### Tarea 8: Test de sintaxis

Ejecutar en PowerShell:
```
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\streamlit_app
python -c "import app" 2>&1
```

Si hay errores de importación, corregirlos.

Para cada página nueva:
```
python -c "import ast; ast.parse(open('pages/inicio.py').read())"
python -c "import ast; ast.parse(open('pages/parseo.py').read())"
python -c "import ast; ast.parse(open('pages/facturas.py').read())"
python -c "import ast; ast.parse(open('pages/diccionario.py').read())"
python -c "import ast; ast.parse(open('pages/articulos.py').read())"
```

---

## RESULTADO ESPERADO

Al terminar, la app debe:
1. Arrancar sin errores con `streamlit run app.py`
2. Mostrar login → tras login mostrar página Inicio con 4 tarjetas
3. Sidebar con 4 secciones (Compras, Ventas, Eventos, Operaciones)
4. Todas las páginas existentes accesibles y funcionando
5. 4 páginas placeholder nuevas (parseo, facturas, diccionario, artículos)
6. Filtrado por rol funcionando correctamente

## NOTAS PARA CLAUDE CODE

- NO modificar el CSS inline de app.py (es la identidad visual)
- NO modificar la lógica de login (_show_login)
- NO modificar utils/data_client.py ni utils/wc_client.py
- NO tocar .streamlit/secrets.toml
- Preservar los iconos y títulos que ya tenían las páginas existentes
- Si st.navigation con dict de secciones da problemas, consultar: https://docs.streamlit.io/develop/api-reference/navigation/st.navigation
- Si switch_page no funciona para navegación desde tarjetas, usar st.page_link como alternativa

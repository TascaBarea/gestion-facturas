# PASO 1 — Informe de arquitectura actual de /documentos

**Fecha:** 24/04/2026
**Fichero analizado:** [streamlit_app/pages/documentos.py](../streamlit_app/pages/documentos.py)

## Framework

**No es FastAPI.** Es una página **Streamlit** multipágina. El "endpoint" lo resuelve el propio Streamlit por convención `streamlit_app/pages/<nombre>.py` → ruta `/documentos` tras el login. No hay template HTML separado — Streamlit genera la UI directamente desde llamadas Python (`st.markdown`, `st.container`, `st.columns`, etc.).

El dominio `gestion.tascabarea.com` es un CNAME sobre Streamlit Cloud; la app se sirve desde allí, no desde el VPS.

## Estructura del código

- **Único fichero**: `streamlit_app/pages/documentos.py` (142 líneas).
- **Autorización**: `require_role(["admin", "socio", "comes"])` vía `utils.auth`.
- **Imports dinámicos**: añade raíz del proyecto al `sys.path` y hace `from nucleo.sync_drive import listar_carpeta, CARPETA_RAIZ`.
- **Helper `listar_carpeta(carpeta)`** (de `nucleo/sync_drive.py`): acepta `None | str | list[str]`, lista archivos de la carpeta anidada en Drive, devuelve `list[dict]` con `id/name/mimeType/modifiedTime/size/webViewLink`.

## Secciones que pinta hoy

Hardcoded en la parte final del fichero:

1. `_mostrar_carpeta("Ventas", "📈", "Dashboards y datos de ventas semanales")`
2. `_mostrar_carpeta("Facturas", "🧾", "Facturas procesadas y pagos registrados")`
3. Bloque adicional *"Otros archivos"* — lista archivos sueltos de la raíz filtrando carpetas.

Problemas actuales:

- **"Facturas" no existe** como carpeta en Drive tras R.5 — se llama `Compras/`. La sección probablemente muestra "Sin archivos" hoy.
- `listar_carpeta("Ventas")` devuelve **subcarpetas**, no archivos — porque `Ventas/` contiene `Año en curso/` y `Histórico/`. La UI las pinta como si fueran archivos.
- **Faltan 4 carpetas de la nueva estructura**: Movimientos Banco, Articulos, Maestro, Cuadres.

## Funciones auxiliares

- `_fmt_size(size_str)`: convierte bytes a `KB/MB` legible.
- `_fmt_date(iso_str)`: ISO → `DD/MM/YYYY HH:MM`.
- `_mostrar_carpeta(nombre, icono, descripcion)`:
  - Título `### {icono} {nombre}` + caption descripcion.
  - Llama `listar_carpeta(nombre)`.
  - Si vacío → `st.info("Sin archivos en esta carpeta.")`.
  - Por archivo: card con `📊 / 📄 / 📕 / 📎` según MIME, nombre-link, tamaño, fecha actualización.

## Rutas Drive relevantes (tras R.5)

```
Barea - Datos Compartidos/                (raíz, CARPETA_RAIZ)
├── Articulos/                            plana
├── Compras/
│   ├── Año en curso/
│   └── Histórico/
├── Cuadres/                              plana
├── Maestro/                              plana (MAESTRO + Diccionario)
├── Movimientos Banco/
│   ├── Año en curso/
│   └── Histórico/
└── Ventas/
    ├── Año en curso/
    └── Histórico/
```

## Tests existentes

Búsqueda `tests/*documentos*` y `tests/*streamlit*`: **no hay tests** para este módulo. Se podrán añadir a criterio del usuario.

## Dependencias que se tocan si se amplía

- `streamlit_app/pages/documentos.py` (único fichero productivo).
- `nucleo/sync_drive.py` — NO se toca; ya soporta `listar_carpeta(list[str])` para rutas anidadas.

## Integración con sync_drive

```python
from nucleo.sync_drive import listar_carpeta
# Firma: listar_carpeta(carpeta: None | str | list[str]) -> list[dict]
# None  → lista raíz
# "A"   → lista A/
# ["A", "B"] → lista A/B/
```

Path segmentado para `Compras/Año en curso/`: `listar_carpeta(["Compras", "Año en curso"])`.

## Conclusión

Arquitectura sencilla, localizada en 1 único fichero. La implementación propuesta requiere:
1. Una estructura `CARPETAS_DOCUMENTOS` (lista cerrada de 6 entradas).
2. Iterar sobre ella y llamar `_mostrar_carpeta(...)` o variante con `st.tabs(["Año en curso", "Histórico"])` según si tiene `subcarpetas`.
3. Renombrar "Facturas" → "Compras" en el código y ajustar `ruta_drive` a `["Compras"]`.

Riesgo de regresión nulo fuera de esta página.

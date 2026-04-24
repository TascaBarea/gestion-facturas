# Cierre sesión 24/04/2026 — `/documentos` v2 + config/loader cascade

Autopsia condensada del despliegue de `/documentos` v2 en Streamlit Cloud tras
una cascada de **5 bugs latentes** destapados por el feat inicial.

## Stack de commits (orden cronológico)

| Commit | Tipo | Qué | Por qué |
|--------|------|-----|---------|
| `572f155` | feat | Ampliar `/documentos` a 6 secciones Drive (v2) | Alinear con estructura Drive post-R.5. |
| `d803bf0` | fix | Añadir Google API libs a `streamlit_app/requirements.txt` | Cloud no tenía `google-api-python-client` etc. |
| `c820b65` | fix | Deps transitivas (`pdfplumber`, `rapidfuzz`) + `sys.path` en `app.py` + logging visible | `nucleo/__init__.py` arrastra `.maestro` que importa top-level. |
| `410858f` | fix | `config/loader.py` cascada `secrets → env → legacy` | `config/settings.py:17` importaba `datos_sensibles` sin try/except → `ModuleNotFoundError` en Cloud. |
| `5530c10` | fix | Loader captura `ImportError` (no solo `ModuleNotFoundError`) | `from config import datos_sensibles` lanza `ImportError` no subclase de `ModuleNotFoundError`. |

Verificado visualmente en producción (`tascabarea.streamlit.app/documentos`):
las 6 secciones cargan con pestañas / lista plana correctamente.

## Lecciones clave

### 1. `ModuleNotFoundError` vs `ImportError` — Python los distingue según sintaxis

```python
import config.datos_sensibles          # ModuleNotFoundError si no existe
from config import datos_sensibles     # ImportError: cannot import name ...
```

`ModuleNotFoundError` hereda de `ImportError`, **NO al revés**. Un `except ModuleNotFoundError` deja escapar el segundo caso. Para cubrir ambos: `except ImportError`.

Regla: en código que tiene que ser robusto ante módulos opcionales, SIEMPRE capturar `ImportError`, nunca `ModuleNotFoundError` aislado.

### 2. Logging visible en UI es una jugada estratégica

El commit `c820b65` añadió:

```python
try:
    from nucleo.sync_drive import listar_carpeta, CARPETA_RAIZ
    _DRIVE_OK = True
except ImportError as _e:
    _DRIVE_OK = False
    _DRIVE_IMPORT_ERR = f"{type(_e).__name__}: {_e}"
    _DRIVE_IMPORT_TB = traceback.format_exc()

# Render:
if not _DRIVE_OK:
    st.error(f"No se pudo importar `nucleo.sync_drive` — **{_DRIVE_IMPORT_ERR}**")
    with st.expander("Traceback completo (diagnóstico)"):
        st.code(_DRIVE_IMPORT_TB, language="text")
    st.stop()
```

Antes: a ciegas, hipótesis tras hipótesis. Después: el usuario pega el traceback literal y el fix es quirúrgico.

Regla: al menos en páginas nuevas de Streamlit, envolver imports críticos con este patrón. Coste: ~10 líneas. Beneficio: elimina 3-4 iteraciones de debug a ciegas.

### 3. Streamlit Cloud cachea bytecode `.pyc` agresivamente

A veces un redeploy "normal" no limpia cachés antiguos. Triggereable forzando clone completo con commit vacío o reboot manual tras fallo. No confiar en que el primer redeploy post-fix sea definitivo — esperar y validar visualmente.

### 4. "More than one requirements file detected" NO es inofensivo

Cuando ese warning aparece en logs de Cloud, Cloud está eligiendo **uno** distinto al que piensas. Para Streamlit Cloud el canónico es el que está junto al main file (`streamlit_app/requirements.txt` en este proyecto), NO el de la raíz. Cualquier lib añadida al de raíz sin reflejarlo en el de Streamlit **no llega a Cloud**.

Regla: al añadir libs que Streamlit necesite, editar ambos requirements o documentar explícitamente cuál es el canónico (ver SPEC §13.10).

## Deuda abierta

- `/documentos` muestra la estructura pero no lista archivos en Cloud (`gmail/token.json` está gitignored). Decisión próxima sesión: Opción A (botones "Abrir en Drive") vs Opción B (token como secret).
- Requirements duplicados — 3 opciones en SPEC §13.10.
- Favicon Comestibles Barea (asset óvalo La Rumán necesita recorte a ~512×512).

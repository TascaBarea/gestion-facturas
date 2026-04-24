# Requirements del repo — mapa y responsabilidades

**Fecha:** 24/04/2026
**Motivo:** debugging del bug /documentos en Streamlit Cloud
(commit `572f155`), que reveló que el `requirements.txt` usado en
producción era incompleto.

## Inventario

| Fichero | Tamaño | Target | Quién lo consume |
|---|---|---|---|
| `streamlit_app/requirements.txt` | 82 B (ahora ~320 B tras fix) | Streamlit Cloud | app.py + pages/*.py en `tascabarea.streamlit.app` |
| `requirements.txt` (raíz) | 727 B | dev local + VPS | `pip install -r requirements.txt` en PC y `/opt/gestion-facturas/.venv` |
| `pyproject.toml` | 583 B | pytest + tooling | `pytest`, marcadores, optional deps `[dev]` |

## Cuál lee Streamlit Cloud (y por qué)

Según [docs Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), el orden de preferencia es:

1. `requirements.txt` **en el mismo directorio que el main file** (aquí `streamlit_app/app.py`).
2. `requirements.txt` en la raíz del repo.
3. `environment.yml`, `Pipfile`, `pyproject.toml`.

Con 2 `requirements.txt` (raíz + subdirectorio), Streamlit Cloud usa el del subdirectorio y emite el warning *"More than one requirements file detected"* en el log de deploy. En este repo eso significa que **`streamlit_app/requirements.txt` es el canónico para producción Cloud**.

## Bug que provocó este documento

`streamlit_app/requirements.txt` tenía solo 5 libs (streamlit, WooCommerce, pandas, openpyxl, plotly). No incluía las dependencias Google API que usa `nucleo/sync_drive.py` (llamado por `streamlit_app/pages/documentos.py`):

- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

Resultado: en Streamlit Cloud, `from nucleo.sync_drive import listar_carpeta` lanzaba `ImportError`, el `try/except` de [documentos.py](../streamlit_app/pages/documentos.py) ponía `_DRIVE_OK=False` y mostraba el mensaje amigable "No se pudo importar `nucleo.sync_drive`".

En desarrollo local y en VPS el bug estaba oculto porque esos entornos usan `requirements.txt` de la raíz (que sí tiene todas las libs).

## Fix aplicado

Añadidas las 4 libs Google a `streamlit_app/requirements.txt` con pins `>=` alineados con las versiones del raíz. No se elimina el `requirements.txt` de la raíz (sigue siendo el fuente de verdad para PC y VPS).

## Deuda técnica

La duplicación de requirements tiene 3 problemas:

1. **Riesgo de divergencia**: al añadir una lib nueva al raíz, es fácil olvidar sincronizar `streamlit_app/requirements.txt`. Este bug es un ejemplo.
2. **Reproducibilidad asimétrica**: raíz usa pins exactos (`==`), Streamlit usa mínimos (`>=`). Entornos distintos pueden acabar con versiones distintas ante problemas sutiles.
3. **Dependencias transitivas**: Streamlit Cloud resuelve `>=` permisivamente, dev local con `==`. Un día algo puede funcionar en Cloud pero no en local.

### Opciones de limpieza futura (no se aplican ahora)

- **A**: mover `streamlit_app/requirements.txt` → `requirements.txt` raíz único, configurar Streamlit Cloud para usar main file `streamlit_app/app.py` (ya lo hace). Un solo fichero, un solo truth.
- **B**: convertir `streamlit_app/requirements.txt` en un `-r ../requirements.txt` para referenciarlo. Simple pero requiere que Streamlit Cloud tenga acceso al fichero padre (sí lo tiene, clona repo entero).
- **C**: dejar la duplicación pero añadir un test CI que verifique que todas las libs importadas por `streamlit_app/` están en `streamlit_app/requirements.txt`.

Por ahora fix puntual con sincronización manual.

## Pendientes

- [ ] Cuando añadamos una lib nueva usada por Streamlit Cloud, recordar sincronizar ambos `requirements.txt`.
- [ ] Revisar próximo trimestre si alguna de las opciones A/B/C es implementable sin riesgo.

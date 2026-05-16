# streamlit_app — Dashboard local de gestion-facturas

Dashboard Streamlit para visualización y operación sobre los datos del sistema
gestion-facturas (COMPRAS, VENTAS, MAESTRO, etc.).

## Entornos

- **Producción:** `tascabarea.streamlit.app` (auto-deploy desde rama `main`).
- **Dev/testing:** `dashboard.tascabarea.com` (Cloudflare Tunnel al VPS Contabo).
- **Local:** este script `.bat`, para iteración rápida desde PC.

## Arranque local (Windows)

Doble click sobre `Arrancar Dashboard.bat`. El script:

1. Cambia al directorio del repo (`C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas`).
2. Activa el venv `.venv`.
3. Entra a `streamlit_app/` y lanza `streamlit run app.py`.

Streamlit abre el navegador en `http://localhost:8501`.

## Requisitos previos

- Python 3.x con venv en `.venv/` en la raíz del repo.
- Dependencias instaladas (`pip install -r requirements.txt`).
- Drive Desktop montando `G:\Mi unidad\Barea - Datos Compartidos\` (las páginas de datos esperan esa ruta).

## Notas

- La ruta del repo en el `.bat` está hardcoded. Si se mueve el repo, editar la línea `cd /d ...`.
- Para arranque en VPS, ver `systemd` service en `/opt/gestion-facturas/`.

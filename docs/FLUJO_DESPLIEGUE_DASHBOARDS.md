# Flujo de despliegue de dashboards

## Arquitectura

- **Producción:** Streamlit Cloud → `https://tascabarea.streamlit.app`
  - Redespliega automáticamente al detectar push en rama principal de GitHub
  - Siempre disponible (no depende del PC de Jaime)
  - URL que usa el equipo (Elena, socios)

- **Desarrollo/pruebas:** Localhost → `http://localhost:8502`
  - Cloudflare Tunnel disponible opcionalmente en `https://dashboard.tascabarea.com`
  - Solo cuando el PC de Jaime está encendido con tunnel activo
  - Usar para probar cambios antes de subir a producción

## Flujo de trabajo para cambiar un dashboard

```
1. Modificar template en ventas_semana/dashboards/dashboard_*_template.html
2. Ejecutar generar_dashboard.py (inyecta datos en template → genera HTML final)
3. Probar en local: streamlit run streamlit_app/app.py → http://localhost:8502
4. Si OK → git add + commit + push
5. Streamlit Cloud redespliega automáticamente (1-2 minutos)
6. Verificar en https://tascabarea.streamlit.app
```

## Flujo de trabajo para actualizar datos semanales

```
1. Se ejecutan los scripts de ventas (script_barea.py, etc.)
2. Se ejecuta generar_dashboard.py con datos actualizados
3. git add + commit + push
4. Streamlit Cloud muestra datos nuevos automáticamente
```

## Tunnel Cloudflare (solo desarrollo)

Para activar el tunnel de desarrollo:
```powershell
# Terminal 1: Streamlit
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
.venv\Scripts\activate
streamlit run streamlit_app/app.py

# Terminal 2: Tunnel
cloudflared tunnel run barea-api
```

Config del tunnel en `$env:USERPROFILE\.cloudflared\config.yml`:
- `dashboard.tascabarea.com` → `localhost:8502`
- `api.tascabarea.com` → `localhost:8000`
- Tunnel ID: `54062b38-f8c9-45b3-8281-35030bf71130`

**No usar Cloudflare Tunnel como producción.** Si el PC se apaga, el dashboard se cae.

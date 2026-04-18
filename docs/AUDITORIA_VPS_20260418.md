# AUDITORÍA VPS — 18/04/2026

> VPS: `root@194.34.232.6` (Contabo, Ubuntu 24.04.2 LTS)
> Auditoría de solo lectura. No se modifica nada en el VPS ni en el PC.
> Estado tras el fix aplicado el 18/04/2026 (token OAuth + copia extractores).

## Resumen ejecutivo

| Estado | Cuenta |
|:------:|:------:|
| ✅ OK | 18 |
| ⚠️ Revisar | 9 |
| ❌ Fallo | 5 |

---

## ❌ Hallazgos críticos

### ❌-1. Ruta Tesseract hardcoded a Windows en código del VPS
**Archivo:** [nucleo/pdf.py:25](../nucleo/pdf.py#L25)
```python
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
Consecuencia: OCR NO funciona en Linux — cualquier extractor que dependa de OCR falla. Evidencia en log `2026-04-18.log`:
```
DEBUG | Error OCR: C:\Program Files\Tesseract-OCR\tesseract.exe is not installed or it's not in your PATH
```
El binario `/usr/bin/tesseract` existe con idioma `spa` instalado. Solución: detectar plataforma como ya se hizo con `PARSEO_DIR` (gmail/gmail.py:110).

### ❌-2. gmail.py NO está programado en cron/systemd del VPS
`crontab -l` solo contiene el backup de `control-barea`. No hay entrada para `gmail.py --produccion` (esperada: viernes 03:00).
La ejecución del 2026-04-18 00:26 fue manual o disparada desde Streamlit. **La automatización del SPEC v4.4 no está operativa en VPS.**

### ❌-3. `script_barea.py` (Ventas) sin ejecución programada
- En VPS: no hay cron/timer que lo ejecute.
- En Windows: `schtasks` no lo encuentra.
- `LOYVERSE_TOKEN`, `WOO_CONSUMER_KEY`, `WOO_CONSUMER_SECRET` **FALTAN** en `config/datos_sensibles.py` del VPS.
Consecuencia: aunque se programase, fallaría por credenciales. **Ventas semanales no se están generando automáticamente.**

### ❌-4. Código VPS muy desincronizado de `main`
| | VPS | PC |
|---|---|---|
| Versión gmail.py | 1.17 | 1.18.2 |
| Último commit | `6f3083f feat(streamlit)` | `16940e2 fix: UX MOV_BANCO` |
El VPS tiene ramas divergentes del `main` actual: le faltan validaciones de negocio v1.18, sync Drive para archivos de datos (commit `e3a1ddd`), GBP dual, etc. Además el repo VPS tiene cambios locales sin commitear en `config/datos_sensibles.py.example`, `core/config.py`, `gmail/gmail.py`, `gmail/gmail_config.py`, `streamlit_app/pages/ejecutar.py`. No está claro si un `git pull` sobrescribiría trabajo válido.

### ❌-5. Extractor `pago_alto_landon.py` con `IndentationError` (line 111)
Detectado al cargar los 117 extractores. Bug pre-existente en el repo local — no afecta a otros extractores pero ese proveedor nunca se procesa correctamente.

---

## ⚠️ Hallazgos importantes

### ⚠️-1. Import `gmail_config` falla fuera del cwd
```python
from gmail.dropbox_api import DropboxAPIClient  # → ImportError: No module named 'gmail_config'
```
`dropbox_api.py` importa `gmail_config` sin prefijo de paquete; solo funciona si cwd = `/opt/gestion-facturas/gmail/`. Riesgoso al ejecutar desde otra carpeta.

### ⚠️-2. Paquetes del venv faltantes
En `/opt/gestion-facturas/.venv/`:
- `reportlab` — usado por `generar_dashboard.py` (si se quiere ejecutar el dashboard en VPS)
- `matplotlib` — ídem
- `playwright` — requerido por `scripts/tickets/dia.py`
- `beautifulsoup4` — usado por scripts de scraping
- `fastapi`/`uvicorn` — esperable en venv aunque el API corre en Docker (`barea_api` container)

### ⚠️-3. Versiones del venv divergen de `requirements.txt`
- `pandas==2.3.0` (requirements) vs `3.0.2` (instalado)
- `pdfplumber==0.11.7` vs `0.11.9`
- `google-auth==2.41.1` vs `2.49.2`
- `streamlit==1.56.0` (requirements no lo pin — se añadió después)
Sugiere `pip install` suelto fuera de `requirements.txt`. Riesgo de reproducibilidad.

### ⚠️-4. REINICIO PENDIENTE en VPS
`/var/run/reboot-required` presente. 4 paquetes con actualización pendiente (apparmor, rsyslog, snapd, libapparmor1). No es urgente pero hay que planificar una ventana.

### ⚠️-5. `rclone` no instalado
El playbook esperaba `rclone` para backups a Dropbox/Drive. No está instalado. Los backups PostgreSQL de `control-barea` funcionan (4 archivos recientes) pero solo locales en `/root/backups/`.

### ⚠️-6. Cloudflared conecta con desconexiones transitorias
Log muestra desconexión puntual el 18/04 06:05 (`timeout: no recent network activity`), reconectó automáticamente. Servicio activo desde hace 1 semana. No crítico, pero vigilable.

### ⚠️-7. `sync_drive` sin función `get_drive_service`
Auditoría verificó import OK, pero no encontró función para obtener service. Puede ser una API diferente — no es fallo por sí mismo, solo que el test propuesto no aplicaba.

### ⚠️-8. MAESTRO más reciente en VPS que en PC
- VPS: `2026-04-11 21:40`
- PC: `2026-04-11 16:58`
Ambos con 195 proveedores / 194 con extractor, pero VPS 5 h más nuevo. Posiblemente modificaciones vía Streamlit de Benjamin. Hay que confirmar que el PC pulla datos del VPS y no al revés.

### ⚠️-9. Logs de ejecución gmail muestran 9/13 facturas en REVISAR
Log `2026-04-18.log`: 1 exitosa, 9 requieren revisión. Mezcla de dos causas (ahora mitigadas):
- Extractores no encontrados — resuelto al copiar `/opt/Parseo/extractores/`
- Error OCR por ruta Windows hardcoded — aún pendiente (❌-1)
La próxima ejecución debería mejorar pero no alcanzará 100% hasta corregir ❌-1.

---

## ✅ Todo OK

1. Estructura de carpetas conforme al SPEC v4.4 (gmail/, ventas_semana/, nucleo/, datos/, scripts/, api/, streamlit_app/).
2. Archivos de datos presentes: MAESTRO, DiccionarioProveedoresCategoria, DiccionarioEmisorTitulo, emails_procesados, EXTRACTORES_COMPLETO.
3. `config/datos_sensibles.py` existe con claves Dropbox + IBANs.
4. `streamlit_app/.streamlit/secrets.toml` presente.
5. `nucleo/` completo (maestro.py, utils.py, logging_config.py, parser.py, sync_drive.py, pdf.py, factura.py, validacion.py, categorias.py).
6. **Token OAuth Gmail con 3 scopes** (gmail.readonly, gmail.modify, drive) — corregido hoy.
7. Dropbox: APP_KEY, APP_SECRET, REFRESH_TOKEN configurados.
8. `sync_drive` importable.
9. Streamlit corriendo (PID 518297, puerto 8501, 127.0.0.1).
10. FastAPI en Docker (container `barea_api` healthy, 7 días uptime).
11. Caddy activo (80/443) + Docker Caddy interno (8080).
12. Cloudflare Tunnel activo (systemd, 1 semana uptime).
13. Docker Compose saludable (`barea_api`, `barea_caddy`, `barea_postgres` healthy).
14. **Extractores copiados** — 117 archivos `.py` en `/opt/Parseo/extractores`, 539 alias registrados (1 fallo: pago_alto_landon).
15. Tesseract binario `/usr/bin/tesseract 5.3.4` con `spa`+`eng`.
16. Python 3.12.3 venv con pdfplumber, pytesseract, pdf2image, pillow, openpyxl, pandas, plotly, dropbox, google-auth, google-api-python-client, streamlit.
17. Disco 4% usado de 145 GB, RAM 1.1/7.8 GB, load 0.27 — holgado.
18. Backups diarios `control-barea` PostgreSQL en `/root/backups/` (4 archivos consecutivos).

---

## Plan de acción priorizado

### Inmediato (crítico)
1. **[❌-1]** Parchar `nucleo/pdf.py:25` para detectar plataforma:
   ```python
   TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe' if platform.system() == 'Windows' else '/usr/bin/tesseract'
   ```
   Commit + push + `git pull` en VPS. Esfuerzo: 10 min.
2. **[❌-4]** Reconciliar código VPS con `main`:
   - Inspeccionar los 5 archivos modificados sin commitear en VPS.
   - Decidir: commitear lo valioso, descartar lo resto, luego `git pull`.
   - Esfuerzo: 30–60 min.
3. **[❌-2]** Programar `gmail.py` en cron VPS:
   ```
   0 3 * * 5 cd /opt/gestion-facturas && PARSEO_DIR=/opt/Parseo /opt/gestion-facturas/.venv/bin/python3 gmail/gmail.py --produccion >> /var/log/gmail_barea.log 2>&1
   ```
   Esfuerzo: 5 min.

### Corto plazo (esta semana)
4. **[❌-3]** Decidir dónde corre `script_barea.py` (Ventas):
   - Añadir `LOYVERSE_TOKEN`, `WOO_CONSUMER_KEY`, `WOO_CONSUMER_SECRET` a `/opt/gestion-facturas/config/datos_sensibles.py` vía scp seguro.
   - Programar cron VPS (lunes 03:00) o Task Scheduler Windows.
5. **[❌-5]** Arreglar `IndentationError` en `Parseo/extractores/pago_alto_landon.py:111`.
6. **[⚠️-1]** Arreglar import absoluto en `gmail/dropbox_api.py` (`from . import gmail_config` o `gmail.gmail_config`).

### Medio plazo (este mes)
7. **[⚠️-2]** Instalar en venv: `reportlab matplotlib playwright beautifulsoup4` (+ `fastapi uvicorn` si se pretende ejecutar `barea_api` fuera de Docker).
8. **[⚠️-3]** Regenerar `requirements.txt` con `pip freeze` actual y fijar versiones.
9. **[⚠️-4]** Planificar ventana de mantenimiento para `apt upgrade` + reboot.
10. **[⚠️-5]** Instalar y configurar `rclone` para offload de backups a cloud.
11. **[⚠️-8]** Definir dirección canónica del sync MAESTRO (PC→VPS o VPS→PC) y documentarla.

### Validación post-fix
- Ejecutar `gmail.py --produccion` en VPS tras aplicar 1 y 3 → verificar que bajan los REVISAR de 9/13.
- Abrir https://gestion.tascabarea.com/documentos → debe dejar de dar 403.

---

## Notas metodológicas
- Fecha ejecución: sábado 18/04/2026, 13:30–13:40 CEST.
- Todas las comprobaciones vía SSH sobre clave ed25519. No se alteró nada en el VPS.
- Token OAuth ya regenerado en sesión previa (ver `gmail/token.json.bak.20260418` en VPS).
- Extractores ya copiados (117 archivos → `/opt/Parseo/extractores/`).

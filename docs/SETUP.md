# SETUP.md — Recuperación del entorno gestion-facturas

**Última actualización:** 25/03/2026
**Objetivo:** Reconstruir el sistema completo en un PC nuevo en <2 horas.

---

## 1. Requisitos del sistema

| Componente | Versión | Notas |
|---|---|---|
| Python | 3.13 | PATH configurado |
| Tesseract OCR | 5.x | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| Git | 2.x | Con `gh` CLI (`C:\Program Files\GitHub CLI`) |
| Dropbox | Desktop app | Sincronización local activa |

---

## 2. Instalación paso a paso

### 2.1 Clonar y dependencias

```bash
git clone https://github.com/TascaBarea/gestion-facturas.git
cd gestion-facturas
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Archivos sensibles (NO están en el repo)

Crear manualmente estos ficheros:

**`config/datos_sensibles.py`** — Copiar de `config/datos_sensibles.py.example` y rellenar:
- IBANs empresa (TASCA, COMESTIBLES)
- CIFs propios (`CIFS_PROPIOS`)
- Emails socios (`EMAILS_RESUMEN_SEMANAL`)
- Token Netlify (`NETLIFY_TOKEN`, `NETLIFY_SITE_ID`)

**`ventas_semana/.env`** — Variables de API:
```
WC_URL=https://tascabarea.com
WC_KEY=ck_...
WC_SECRET=cs_...
LOY_TOKEN_TASCA=...
LOY_TOKEN_COMES=...
PATH_VENTAS=C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\Ventas Barea 2026.xlsx
PATH_ARTICULOS=C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\Articulos 26.xlsx
```

**`gmail/credentials.json`** — Descargar desde Google Cloud Console (proyecto Gmail API).

**`gmail/token.json`** — Generar ejecutando:
```bash
python gmail/renovar_token_business.py
```

**`gmail/config_local.py`** — App password de Gmail.

**`streamlit_app/.streamlit/secrets.toml`** — Copiar de `secrets.toml.example` y rellenar:
- WC_URL, WC_KEY, WC_SECRET
- Usuarios con passwords (jaime, roberto, elena, benjamin)

### 2.3 Excel de datos (gitignored)

Restaurar en `datos/` desde backup:
- `MAESTRO_PROVEEDORES.xlsx` — 193 proveedores, 14 columnas
- `Ventas Barea 2026.xlsx` — Ventas semanales
- `Articulos 26.xlsx` — Catálogo Loyverse
- `emails_procesados.json` — Control de duplicados Gmail

### 2.4 Dropbox

La carpeta de facturas procesadas se copia a:
```
C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\FACTURAS 2026\FACTURAS RECIBIDAS\
```
Verificar que Dropbox Desktop está instalado y sincronizando.

---

## 3. Tareas programadas (Task Scheduler)

### Gmail — Viernes 03:00
```bash
# Ejecutar como administrador:
gmail\gmail_auto_setup.bat
```
- **Nombre tarea:** `Gmail_Facturas_Semanal`
- **Horario:** Viernes 03:00 UTC
- **Wake timer:** Sí (despierta PC de suspensión)
- **Log:** `outputs/logs_gmail/auto_YYYY-MM-DD.log`

### Ventas — Lunes 03:00
```bash
# Ejecutar como administrador:
ventas_semana\barea_auto_setup.bat
```
- **Nombre tarea:** `Ventas_Barea_Semanal`
- **Horario:** Lunes 03:00 UTC
- **Wake timer:** Sí
- **Log:** `outputs/logs_barea/auto_YYYY-MM-DD.log`
- **Especial:** Si día <= 7 (1ª semana del mes) → genera dashboard mensual cerrado + envía email

### Verificar tras instalar
```bash
# Ejecutar manualmente para confirmar que funcionan:
gmail\gmail_auto.bat
ventas_semana\barea_auto.bat
```

---

## 4. APIs y servicios externos

| Servicio | Uso | Credenciales en |
|---|---|---|
| Gmail API | Leer facturas email | `gmail/credentials.json` + `token.json` |
| WooCommerce API | Pedidos, productos, eventos | `ventas_semana/.env` |
| Loyverse API (x2) | Ventas TPV (Tasca + Comes) | `ventas_semana/.env` |
| Netlify API | Deploy dashboards HTML | `config/datos_sensibles.py` |
| Streamlit Cloud | App web multi-usuario | `streamlit_app/.streamlit/secrets.toml` |

### URLs de servicio
- **Streamlit app:** https://tascabarea.streamlit.app (cuenta: tascabarea@gmail.com)
- **Netlify dashboards:** https://barea-dashboards.netlify.app
- **WooCommerce:** https://tascabarea.com
- **GitHub repo:** https://github.com/TascaBarea/gestion-facturas (PUBLIC)

---

## 5. Alertas de fallo

Si un script automático falla, `alerta_fallo.py` envía email a `tascabarea@gmail.com` con las últimas 30 líneas del log.

- **Scope:** `gmail.send`
- **Token:** Reutiliza `gmail/token.json`
- **Si el token expira:** ejecutar `gmail/renovar_token_business.py`

---

## 6. Estructura de directorios a crear

```
gestion-facturas/
├── datos/                  ← Restaurar Excel desde backup
│   └── backups/            ← Se crea automáticamente
├── outputs/
│   ├── logs_gmail/
│   ├── logs_barea/
│   └── backups/
└── ventas_semana/
    └── dashboards/         ← Se generan automáticamente
```

---

## 7. Symlink nucleo/ ↔ Parseo/

El directorio `nucleo/` es compartido con el repo Parseo:
```bash
# Si Parseo está en C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\
mklink /D nucleo C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\nucleo
```

---

## 8. Checklist de verificación

- [ ] `python -c "import pandas; print(pandas.__version__)"` → 2.3.0
- [ ] `tesseract --version` → 5.x
- [ ] `python gmail/gmail.py --test` → Sin errores de auth
- [ ] `python ventas_semana/script_barea.py --help` → Muestra opciones
- [ ] Abrir https://tascabarea.streamlit.app → Login funciona
- [ ] Task Scheduler muestra 2 tareas activas
- [ ] Dropbox sincroniza `CONTABILIDAD/`

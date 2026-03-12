# CLAUDE.md — gestion-facturas

## Proyecto
Sistema integrado de facturación para **Tasca Barea** y **Comestibles Barea** (2 tiendas).
4 módulos: Parseo (compras PDF), Gmail (pagos email), Ventas (Loyverse+WooCommerce), Cuadre (banco).
Documentación completa: `docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md` (versión actual: v4.8).

## Estructura clave
```
gestion-facturas/
├── ventas_semana/          # Ⓒ VENTAS — script_barea.py + generar_dashboard.py
│   ├── script_barea.py     # Proceso semanal: WooCommerce → Loyverse → Artículos → IVA → Dashboards → GBP → Email
│   ├── generar_dashboard.py # Dashboards HTML + PDF mensual
│   ├── barea_auto.bat      # Lanzador automático (lunes 03:00)
│   └── .env                # LOY_TOKEN_TASCA, LOY_TOKEN_COMES, WC_URL, WC_KEY, WC_SECRET
├── gmail/                  # Ⓑ GMAIL — gmail.py + auth + descarga + SEPA
│   ├── gmail.py            # Proceso semanal viernes
│   ├── gmail_auto.bat      # Lanzador automático (viernes 03:00)
│   ├── token.json          # OAuth2 (gmail.readonly + gmail.modify + business.manage)
│   └── credentials.json    # OAuth2 client secrets
├── datos/                  # Excel de datos (gitignored)
│   ├── Ventas Barea 2026.xlsx       # 6 pestañas: TascaRecibos/Items, ComesRecibos/Items, WOO, GoogleBusiness
│   ├── Ventas Barea Historico.xlsx  # 2023-2025: Tasca/Comes Items/Recibos + GoogleBusiness25
│   ├── Articulos 26.xlsx           # Catálogo: Comestibles (572) + Tasca (87) + Historial_Precios
│   └── DiccionarioProveedoresCategoria.xlsx  # 1282 artículos × proveedor
├── config/                 # datos_sensibles.py (gitignored), proveedores.py, settings.py
├── nucleo/                 # Ⓐ PARSEO — parser.py, factura.py, pdf.py
├── cuadre/                 # Ⓓ CUADRE — banco/, norma43/
├── outputs/                # Logs, dashboards, PDFs (gitignored)
├── alerta_fallo.py         # Email de alerta si falla ejecución automática
└── docs/                   # ESQUEMA_PROYECTO_DEFINITIVO
```

## Ejecución automática (Programador de Tareas Windows)
- **Lunes 03:00**: `barea_auto.bat` → `script_barea.py` (ventas semanales)
  - Si día ≤ 7 (1er lunes del mes): añade `--dashboard-mensual` → PDF + email socios + GBP
- **Viernes 03:00**: `gmail_auto.bat` → `gmail.py --produccion` (facturas email)
- Ambos .bat: anti-suspensión, verificación internet con reintentos, alertas por email si falla

## Reglas técnicas
- **Python 3.13** con pandas + openpyxl para Excel
- `save_to_excel(df, path, sheet, unique_col)`: SIEMPRE lee datos existentes antes de escribir. Dedup por unique_col. Aborta si lectura falla (protege datos). Hace backup automático antes de la primera escritura
- **Logging**: `script_barea.py` usa `logging` (no print). Logs en `outputs/logs_ventas/YYYY-MM-DD.log`
- **Backups Excel**: `datos/backups/` — copia automática antes de cada ejecución de script_barea
- **Formato decimal español** en datos 2024 (comas: "3,51"). Datos 2025+ usan punto
- APIs: Loyverse REST, WooCommerce REST, Gmail API (OAuth2)
- Gmail token compartido entre gmail/ y ventas_semana/ (mismo token.json en gmail/)
- Emails GBP llegan a benjaimes@gmail.com → reenviados a tascabarea@gmail.com (filtro Gmail)

## Reglas de trabajo
- Idioma: siempre español
- No crear commits sin que lo pida explícitamente
- No tocar archivos sensibles: .env, credentials.json, token.json, datos_sensibles.py
- Avisar siempre antes de escribir Excel (puede estar abierto y openpyxl falla)
- Actualizar ESQUEMA DEFINITIVO al cerrar sesión si hubo cambios significativos
- No crear archivos .md innecesarios
- Preferir editar archivos existentes a crear nuevos

## Errores conocidos
- Excel abierto → openpyxl falla silenciosamente o corrompe. Siempre avisar al usuario
- `ERRORLEVEL` en batch no se actualiza dentro de bloques `if ()` → usar `goto` + labels
- Token Gmail caduca → ejecutar `gmail/renovar_token_business.py`
- `text/html` en MIME (no `text\html`) — cuidado al parsear payloads de Gmail API

## Skills disponibles (/comandos)
- `/ventas` — Descargar ventas semanales y regenerar dashboards
- `/dashboard` — Generar dashboards (opciones: email, cerrados, test)
- `/estado` — Informe de estado del proyecto
- `/esquema` — Actualizar ESQUEMA DEFINITIVO con cambios de la sesión
- `/log-gmail` — Analizar logs de ejecución Gmail
- `/extractor` — Crear nuevo extractor PDF para un proveedor

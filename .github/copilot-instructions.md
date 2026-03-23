# GitHub Copilot Instructions — gestion-facturas
<!-- Versión: 1.1 — 24/03/2026 -->
<!-- Referencia completa: CLAUDE.md + docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md -->
<!-- Conocimiento específico por módulo: .github/instructions/*.instructions.md -->

## Proyecto
Sistema integrado de gestión de facturas para **Tasca Barea SLL** (bar + tienda gourmet + experiencias, Madrid).
Desarrollado y mantenido por Jaime Fernández. Stack: Python 3.13, pandas, openpyxl, pdfplumber, Gmail API, Loyverse API.
Contexto completo de empresa: `docs/TASCA_BAREA_CONTEXT.md`

## Instrucciones específicas por módulo
Cada módulo tiene su propio archivo de instrucciones con conocimiento técnico detallado:
- **Cuadre** → `.github/instructions/cuadre.instructions.md`
- **Ventas** → `.github/instructions/ventas.instructions.md`
- **Gmail** → `.github/instructions/gmail.instructions.md`
- **Núcleo/Parseo** → `.github/instructions/nucleo.instructions.md`

## Módulos (4 principales)
| Módulo | Versión | Archivo | Automatización |
|--------|---------|---------|----------------|
| Ⓑ GMAIL | v1.14 | `gmail/gmail.py` | Automático (viernes 03:00) |
| Ⓒ VENTAS | v4.7 | `ventas_semana/script_barea.py` | Automático (lunes 03:00) |
| Ⓓ CUADRE | v1.7 | `cuadre/banco/cuadre.py` | Manual |
| Ⓐ PARSEO | v5.18 | `Parseo/` (repo separado) | Manual |

## Estructura clave
```
gestion-facturas/
├── CLAUDE.md                        ← Instrucciones para Claude Code
├── .github/copilot-instructions.md  ← Este archivo (GitHub Copilot)
├── tasks/lessons.md                 ← Errores conocidos y reglas aprendidas
├── tasks/todo.md                    ← Plan de sesión activa
├── gmail/gmail.py                   ← Módulo Gmail principal (~2180 líneas)
├── ventas_semana/script_barea.py    ← Descarga ventas Loyverse + WooCommerce
├── ventas_semana/generar_dashboard.py ← Dashboards HTML + PDF + email
├── cuadre/banco/cuadre.py           ← Clasificador movimientos bancarios
├── datos/                           ← Excel maestros (gitignored)
├── config/datos_sensibles.py        ← IBANs, CIFs, credenciales (gitignored)
└── docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md ← Documentación técnica completa (v5.3)
```

## Archivos PROHIBIDOS — nunca modificar
- `gmail/token.json` y `gmail/credentials.json` — OAuth2 Gmail
- `config/datos_sensibles.py` — IBANs, CIFs, DNIs (nunca al repositorio)
- `ventas_semana/.env` — API keys Loyverse y WooCommerce

## Reglas críticas de negocio
- **Excel abierto**: avisar SIEMPRE antes de escribir. Leer antes de sobrescribir. Hacer backup.
- **Versiones**: actualizar en 2 sitios siempre — header del código + tabla en CLAUDE.md
- **ESTADO_PAGO y MOV#** en Excel COMPRAS: los rellena únicamente `cuadre.py`, nunca otros scripts
- **Portes/envío en extractores**: SIEMPRE distribuir proporcionalmente entre productos, NUNCA como línea separada
- **Batch scripts (.bat)**: usar `goto + labels` para manejo de errores, nunca `if ERRORLEVEL` anidado
- **Token Gmail caducado**: ejecutar `gmail/renovar_token_business.py`

## Prioridades de desarrollo activas
1. 🔴 CUADRE: conectar con COMPRAS para actualizar `ESTADO_PAGO` automáticamente
2. 🟡 Limpiar WooCommerce: reducir 69 → 10 columnas en pestaña WOOCOMMERCE
3. 🟡 Cruce Artículos↔Proveedores via `DiccionarioProveedoresCategoria.xlsx`

## Skills disponibles (/comandos para Claude Code)
`/ventas` · `/dashboard` · `/estado` · `/esquema` · `/log-gmail` · `/extractor`
`/revisar` · `/lecciones` · `/plan` · `/cuadre` · `/debug-extractor` · `/nuevo-proveedor`

## Errores conocidos frecuentes
| Error | Solución |
|-------|---------|
| Excel bloqueado al escribir | Cerrar el archivo en Excel primero |
| MIME type Gmail incorrecto | Usar `text/html` con barra normal, nunca invertida |
| Token Gmail expirado | Ejecutar `gmail/renovar_token_business.py` |
| Coma decimal en datos 2024 | Usar `_convertir_importe()` — 2025+ ya usa punto |

## Notas operativas
- Jaime es el único desarrollador. Estilo directo, prefiere que el agente tome iniciativa.
- "la tienda" = Comestibles Barea (Embajadores 38) · "la tasca/el bar" = Tasca Barea (Rodas 2)
- Los datos de ventas Loyverse son fiables. El stock NO lo es.
- La gestoría Kinema accede a documentos vía Dropbox compartido.

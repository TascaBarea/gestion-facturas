# CLAUDE.md — gestion-facturas
<!-- Versión: 4.1 — 20/03/2026 -->
<!-- IMPORTANTE: Leer tasks/lessons.md al iniciar cada sesión -->

## Proyecto
Tasca Barea SLL (bar + tienda gourmet + experiencias, Madrid). Ver `docs/TASCA_BAREA_CONTEXT.md` para contexto completo de empresa.
4 módulos: Gmail (pagos email), Ventas (Loyverse+WooCommerce), Cuadre (banco NORMA43), Artículos (catálogo Loyverse).
Parseo (extractores PDF): repo separado → `Parseo/` · ver `Parseo/CLAUDE.md`.
Documentación técnica completa: `docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md` (v5.3).

## Estructura
```
gestion-facturas/
├── CLAUDE.md               ← Este archivo (carga automática)
├── tasks/
│   ├── lessons.md          ← LEER al iniciar sesión
│   └── todo.md             ← Plan de sesión activa
├── ventas_semana/          # Ⓒ VENTAS v4.7 — lunes 03:00
│   ├── script_barea.py
│   ├── generar_dashboard.py
│   ├── barea_auto.bat
│   └── .env                # NO TOCAR
├── gmail/                  # Ⓑ GMAIL v1.14 — viernes 03:00
│   ├── gmail.py
│   ├── token.json          # NO TOCAR
│   └── credentials.json    # NO TOCAR
├── datos/                  # Excel (gitignored) — avisar antes de escribir
├── config/                 # datos_sensibles.py — NO TOCAR
├── nucleo/                 # Módulo core compartido con Parseo/ (symlink)
├── cuadre/                 # Ⓓ CUADRE v1.6
├── outputs/                # Logs gitignored
└── docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md
```

## Versiones actuales
<!-- Al modificar un módulo: actualizar aquí Y en ESQUEMA -->
| Módulo  | Versión | Archivo fuente                     |
|---------|---------|------------------------------------|
| Gmail   | v1.14   | gmail/gmail.py                     |
| Ventas  | v4.7    | ventas_semana/script_barea.py      |
| Cuadre  | v1.7    | cuadre/banco/cuadre.py             |
| ESQUEMA | v4.4    | docs/ESQUEMA_PROYECTO_DEFINITIVO   |

---

## COMPORTAMIENTO específico de este repo

### Verificación antes de completar
- Scripts Python: ejecutar y confirmar sin errores
- Extractores: test con PDF real del proveedor (ver Parseo/CLAUDE.md)

### Al cerrar sesión
- Actualizar ESQUEMA si hubo cambios significativos
- Actualizar versión en 2 sitios: header del código + tabla arriba

---

## Prioridades de desarrollo activas
<!-- Ver ESQUEMA §6.9 para lista completa -->
1. 🔴 CUADRE: conectar con COMPRAS para actualizar `ESTADO_PAGO` automáticamente
2. 🟡 Limpiar WooCommerce: reducir 69 → 10 columnas en pestaña WOOCOMMERCE
3. 🟡 Cruce Artículos↔Proveedores via `DiccionarioProveedoresCategoria.xlsx`

---

## Errores conocidos → ver tasks/lessons.md para lista completa

| Error | Regla rápida |
|-------|-------------|
| Excel abierto | Avisar SIEMPRE antes de escribir. Leer antes de sobrescribir. Hacer backup. |
| ERRORLEVEL en batch | Usar goto + labels, nunca if anidado |
| Token Gmail caducado | Ejecutar gmail/renovar_token_business.py |
| MIME type Gmail | text/html con barra normal, nunca invertida |

---

## Skills (/comandos)

| Comando               | Acción                                                          |
|-----------------------|-----------------------------------------------------------------|
| `/ventas`             | Descargar ventas semanales y regenerar dashboards               |
| `/dashboard`          | Generar dashboards HTML + PDF (opciones: email, cerrados, test) |
| `/estado`             | Informe de estado: versiones, pendientes, errores recientes     |
| `/esquema`            | Actualizar ESQUEMA DEFINITIVO con cambios de la sesión          |
| `/log-gmail`          | Analizar logs de la última ejecución Gmail                      |
| `/extractor`          | Crear nuevo extractor PDF para proveedor nuevo                  |
| `/revisar`            | Analizar movimientos REVISAR del cuadre: agrupar + diagnosticar |
| `/lecciones`          | Mostrar lessons.md y proponer nuevas reglas si procede          |
| `/plan`               | Crear o revisar tasks/todo.md para la sesión actual             |
| `/cuadre [mes]`       | Proceso completo de cuadre bancario mensual (NORMA43 vs fact.)  |
| `/debug-extractor`    | Diagnosticar y corregir errores en un extractor existente       |
| `/nuevo-proveedor`    | Alta completa de proveedor nuevo (MAESTRO + alias + extractor)  |
| `/validar-patrones`   | Testear regex del extractor genérico contra textos de prueba    |

---

## Asistentes IA configurados
- **Claude Code**: usa este archivo (carga automática)
- **GitHub Copilot (VS Code)**: ver `.github/copilot-instructions.md`

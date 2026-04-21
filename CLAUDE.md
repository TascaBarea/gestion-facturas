# CLAUDE.md — gestion-facturas
<!-- Versión: 4.4 — 09/04/2026 -->
<!-- IMPORTANTE: Leer tasks/lessons.md al iniciar cada sesión -->

## Proyecto
Tasca Barea SLL (bar + tienda gourmet + experiencias, Madrid). Ver `docs/TASCA_BAREA_CONTEXT.md` para contexto completo de empresa.
4 módulos: Gmail (pagos email), Ventas (Loyverse+WooCommerce), Cuadre (banco NORMA43), Artículos (catálogo Loyverse).
Parseo (extractores PDF): repo separado → `Parseo/` · ver `Parseo/CLAUDE.md`.
Documentación técnica completa: `docs/SPEC_GESTION_FACTURAS_v4.md` (documento maestro único).

## Arquitectura (en migración)
Objetivo: 3 capas. Migración progresiva en curso.
```
core/          → Capa 1: datos, modelos, config, utilidades (EN CONSTRUCCIÓN)
engines/       → Capa 2: lógica de negocio (EN CONSTRUCCIÓN)
cli/           → Capa 3: interfaces CLI (EN CONSTRUCCIÓN)
api/           → Capa 3: REST API (FastAPI, ya funcional)
streamlit_app/ → Capa 3: web UI (ya funcional)
```
Config centralizada en `core/config.py`. Env vars para cloud: GESTION_FACTURAS_DIR, DROPBOX_BASE, PARSEO_DIR.

## Estructura
```
gestion-facturas/
├── CLAUDE.md               ← Este archivo (carga automática)
├── core/                   # Capa 1 — config centralizada (nuevo)
├── engines/                # Capa 2 — motores de negocio (nuevo, vacío)
├── cli/                    # Capa 3 — interfaces CLI (nuevo, vacío)
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
├── cuadre/                 # Ⓓ CUADRE v1.7
├── outputs/                # Logs gitignored
└── docs/SPEC_GESTION_FACTURAS_v4.md  ← Documento maestro único
```

## Documentación y reglas
- **Reglas automáticas**: `.claude/rules/` — se cargan según directorio (api, extractores, Excel)
- **Doc maestro**: `docs/SPEC_GESTION_FACTURAS_v4.md` — arquitectura, módulos, scripts, infraestructura
- **API reference**: `docs/api.md` — endpoints, auth, runner, MAESTRO CRUD
- **Errores conocidos**: `tasks/lessons.md` — leer al iniciar sesión
- **Tests**: `pytest tests/unit/` — 4 suites (security, maestro, nucleo, runner)

## Versiones actuales
<!-- Al modificar un módulo: actualizar aquí Y en SPEC -->
| Módulo  | Versión | Archivo fuente                     |
|---------|---------|------------------------------------|:
| Gmail   | v1.18   | gmail/gmail.py                     |
| Ventas  | v4.7    | ventas_semana/script_barea.py      |
| Cuadre  | v1.7    | cuadre/banco/cuadre.py             |
| SPEC    | v4.5    | docs/SPEC_GESTION_FACTURAS_v4.md   |

---

## COMPORTAMIENTO específico de este repo

### Formato de cifras (OBLIGATORIO)
- Moneda: siempre EUR con formato español → `1.234,56 €`
- Separador de miles: punto (.)
- Separador decimal: coma (,)
- Aplica en: Streamlit UI, dashboards, logs, outputs

### Verificación antes de completar
- Scripts Python: ejecutar y confirmar sin errores
- Extractores: test con PDF real del proveedor (ver Parseo/CLAUDE.md)

### Al cerrar sesión
- Actualizar ESQUEMA si hubo cambios significativos
- Actualizar versión en 2 sitios: header del código + tabla arriba

---

## scripts/tickets/ — Módulo de adquisición de tickets de proveedores

Módulo unificado para descargar/procesar tickets de compra de proveedores.
Todos usan lógica compartida de `comun.py` (trimestre, nomenclatura, anti-duplicación).

| Proveedor | Script | Método | Estado |
|-----------|--------|--------|--------|
| BM Supermercados | `scripts/tickets/bm.py` | Semi-manual (app BM+ → PDF → PC) | Operativo |
| DIA | `scripts/tickets/dia.py` | Automático (API + Playwright login) | Operativo |
| Makro | `scripts/tickets/makro.py` | Pendiente | Placeholder |

Uso:
  python -m scripts.tickets.bm --dry-run        # BM: ver qué haría
  python -m scripts.tickets.bm                   # BM: procesar tickets nuevos
  python -m scripts.tickets.bm --parsear         # BM: procesar + parsear con main.py
  python -m scripts.tickets.dia                   # DIA: descargar tickets nuevos
  python -m scripts.tickets.dia --login           # DIA: renovar sesión

Registros anti-duplicación en: datos/tickets_registros/

---

## Prioridades de desarrollo activas
<!-- Ver ESQUEMA §6.9 para lista completa -->
1. 🔴 CUADRE: conectar con COMPRAS para actualizar `ESTADO_PAGO` automáticamente
2. 🟡 Limpiar WooCommerce: reducir 69 → 10 columnas en pestaña WOOCOMMERCE
3. 🟡 Cruce Artículos↔Proveedores via `DiccionarioProveedoresCategoria.xlsx`

---

## Errores conocidos → ver `tasks/lessons.md`

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
| `/frontend-design`    | Genera interfaces HTML/CSS/JS con personalidad, sin AI slop     |


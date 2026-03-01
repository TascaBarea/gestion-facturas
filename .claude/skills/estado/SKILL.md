---
name: estado
description: Muestra un resumen completo del estado del proyecto gestion-facturas. Usar cuando el usuario pregunte como va el proyecto, que queda pendiente, o quiera una vision general.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

# Estado del Proyecto

Genera un informe de estado del proyecto gestion-facturas. Sigue estos pasos EN ORDEN:

## 1. Leer porcentajes de modulos

Lee `docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md` (solo las primeras 60 lineas) para obtener los porcentajes de cada modulo (PARSEO, GMAIL, VENTAS, CUADRE).

## 2. Leer pendientes

Lee el archivo `C:/Users/jaime/.claude/projects/C---ARCHIVOS-TRABAJO-Facturas-gestion-facturas/memory/pendientes.md` para las tareas activas.

## 3. Ultimos commits

Ejecuta `git log --oneline -10` para ver actividad reciente.

## 4. Ultimos logs de Gmail

Busca el log mas reciente en `outputs/logs_gmail/` con `ls -lt outputs/logs_gmail/ | head -5`. Lee las ultimas 30 lineas del log mas reciente para detectar errores o warnings.

## 5. Estado de archivos de salida

Comprueba la fecha de modificacion de los archivos clave:
```bash
ls -la "outputs/PAGOS_Gmail_1T26.xlsx" "datos/Ventas Barea 2026.xlsx" "ventas_semana/dashboards/dashboard_comes.html" "ventas_semana/dashboards/dashboard_tasca.html" 2>/dev/null
```

## 6. Presentar el informe

Presenta un resumen estructurado con:

```
ESTADO DEL PROYECTO - gestion-facturas
=======================================

MODULOS:
| Modulo  | Estado | Version |
|---------|--------|---------|
| PARSEO  | XX%    | ...     |
| GMAIL   | XX%    | ...     |
| VENTAS  | XX%    | ...     |
| CUADRE  | XX%    | ...     |

ULTIMA ACTIVIDAD:
- Gmail: [fecha ultimo log] - [OK/errores]
- Ventas: [fecha modificacion Excel]
- Dashboards: [fecha modificacion HTML]

ULTIMOS COMMITS:
- [3 ultimos commits]

PENDIENTES (top 5):
- [tareas de pendientes.md]
```

Idioma: espanol. Sin emojis.

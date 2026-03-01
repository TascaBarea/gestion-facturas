---
name: esquema
description: Actualiza el documento ESQUEMA_PROYECTO con los cambios realizados en la sesion actual. Mantiene formato consistente y changelog.
disable-model-invocation: true
argument-hint: "<descripcion breve de los cambios>"
allowed-tools: Bash, Read, Write, Edit, Grep
---

# Actualizar ESQUEMA del Proyecto

Actualiza el documento de referencia del proyecto con los cambios realizados.

## Archivo

`docs/ESQUEMA_PROYECTO_DEFINITIVO_v2_6.md`

## Pasos

### 1. Leer el ESQUEMA actual completo

Lee el archivo entero para entender la estructura y la version actual.

### 2. Identificar que actualizar

Segun $ARGUMENTS o la conversacion, determina que secciones tocar:

- **Seccion 1 (Vision General)**: si cambian los porcentajes de completitud de algun modulo
- **Seccion 3 (Funciones)**: si hay cambios en GMAIL, VENTAS, CUADRE o PARSEO
  - Actualizar version, estado
  - Anadir bloque NOVEDADES vX.X con fecha y bullet points
- **Seccion 5 (Extractores)**: si se crean o corrigen extractores
  - Anadir a la tabla 5.2/5.3 correspondiente
  - Actualizar estadisticas en 5.7.5
- **Seccion 7 (Cuadre)**: si cambian clasificadores o resultados
- **Changelog**: SIEMPRE anadir entrada nueva al inicio del changelog

### 3. Reglas de formato

**Version**: incrementar el numero menor (ej: v2.6 -> v2.7). Cambios grandes: incrementar mayor.

**Fecha**: actualizar la linea `**Fecha:**` en la cabecera con la fecha actual.

**NOVEDADES** (dentro de seccion 3, debajo de cada modulo):
```
NOVEDADES vX.X (DD/MM/YYYY):
               P1 - TITULO DEL CAMBIO:
               - Descripcion corta
               - Otra descripcion
               P2 - OTRO CAMBIO:
               - Detalle
```

**Changelog** (seccion final del documento):
```
### vX.X (DD/MM/YYYY)
- ✅ **Titulo en negrita** -- Descripcion del cambio
  - Sub-detalle si es necesario
```

**Numeros**: si se anaden extractores, actualizar el conteo en TODAS las secciones donde aparezca (5.7.5, seccion 3 PARSEO, vision general, changelog anterior).

### 4. Actualizar MEMORY.md y pendientes.md

Si los cambios afectan a archivos clave o patrones tecnicos, actualizar:
- `C:/Users/jaime/.claude/projects/C---ARCHIVOS-TRABAJO-Facturas-gestion-facturas/memory/MEMORY.md`
- `C:/Users/jaime/.claude/projects/C---ARCHIVOS-TRABAJO-Facturas-gestion-facturas/memory/pendientes.md`

Mover tareas completadas a la seccion "Completado" con fecha.

### 5. Confirmar cambios

Muestra un resumen de los cambios realizados al usuario antes de terminar.

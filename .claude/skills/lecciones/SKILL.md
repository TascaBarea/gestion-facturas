---
name: lecciones
description: Muestra las lecciones aprendidas del proyecto y propone nuevas reglas si procede. Usar cuando el usuario quiera revisar errores conocidos, añadir una leccion, o tras recibir una correccion.
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Grep, Glob
---

# Lecciones Aprendidas

Gestiona el archivo `tasks/lessons.md` del proyecto. Sigue estos pasos:

## 1. Leer lessons.md actual

Lee `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\tasks\lessons.md` completo.

## 2. Mostrar resumen

Muestra al usuario:
- Numero total de REGLAS CRITICAS (por seccion)
- Ultimas 5 entradas del REGISTRO DE CORRECCIONES
- Si hay reglas que parecen obsoletas o redundantes, señalarlas

## 3. Proponer nuevas reglas (si procede)

Si en la sesion actual se ha corregido algun comportamiento:
- Formular la regla nueva con formato: fecha | modulo | error | regla
- Añadirla al REGISTRO DE CORRECCIONES
- Si es un patron recurrente, añadirla tambien a REGLAS CRITICAS

Si el usuario proporciona una leccion explicita, añadirla directamente.

## 4. Confirmar cambios

Mostrar que se ha actualizado y el estado final del archivo.

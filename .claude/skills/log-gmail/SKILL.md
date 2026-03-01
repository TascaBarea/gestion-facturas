---
name: log-gmail
description: Analiza los logs de ejecucion de Gmail para detectar errores, facturas rechazadas o proveedores no identificados.
disable-model-invocation: true
argument-hint: "[fecha YYYY-MM-DD] [errores]"
allowed-tools: Bash, Read, Grep, Glob
---

# Analizar Logs Gmail

Revisa y resume los logs de ejecucion del modulo Gmail.

## 1. Encontrar el log correcto

Los logs estan en `outputs/logs_gmail/`. Hay dos tipos por fecha:
- `YYYY-MM-DD.log` - ejecucion manual
- `auto_YYYY-MM-DD.log` - ejecucion automatica (viernes 03:00)

Si $ARGUMENTS contiene una fecha, buscar ese log. Si no, usar el mas reciente:
```bash
ls -t outputs/logs_gmail/*.log | head -3
```

## 2. Leer el log completo

Lee el archivo encontrado con Read.

## 3. Extraer metricas

Busca y cuenta:
- Total de emails procesados: lineas con "Procesando email" o "Procesando:"
- Exitosos: lineas con "Guardado en Excel" o "Copiado a Dropbox"
- Proveedores no identificados: lineas con "NO IDENTIFICADO" o "Proveedor no identificado"
- Errores de extraccion: lineas con "ALERTA ROJA" o "ERROR"
- Duplicados detectados: lineas con "DUPLICADO" o "Duplicado"
- Facturas atrasadas: lineas con "ATRASADA"
- Proformas: lineas con "PROFORMA"
- Warnings: lineas con "WARNING" o "AVISO"

## 4. Si el usuario pide "errores"

Filtra solo las secciones del log donde hay WARNING o ERROR. Para cada error, muestra:
- El email que se estaba procesando (la linea "Procesando:" mas cercana antes del error)
- El detalle del error
- Sugerencia de solucion si es posible

## 5. Presentar resumen

```
LOG GMAIL - [fecha] ([manual/auto])
=====================================

METRICAS:
| Concepto              | Total |
|-----------------------|-------|
| Emails procesados     | XX    |
| Exitosos              | XX    |
| No identificados      | XX    |
| Errores               | XX    |
| Duplicados            | XX    |
| Proformas             | XX    |

PROVEEDORES NO IDENTIFICADOS:
- [lista si los hay]

ERRORES:
- [lista con contexto si los hay]

RECOMENDACIONES:
- [si hay proveedores desconocidos: sugerir alta en MAESTRO_PROVEEDORES.xlsx]
- [si hay errores de extraccion: sugerir revisar extractores]
```

Idioma: espanol. Sin emojis.

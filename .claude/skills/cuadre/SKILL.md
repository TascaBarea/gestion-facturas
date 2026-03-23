---
name: cuadre
description: Ejecuta el proceso de cuadre bancario mensual (NORMA43 vs facturas). Requiere el mes a cuadrar.
disable-model-invocation: true
argument-hint: "[mes_año]  ej: enero, febrero-2026, 01-2026"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Proceso de Cuadre Bancario Mensual

Ejecuta el proceso completo de cuadre para el mes indicado.

## Requisito previo

El usuario debe indicar el mes a cuadrar (ej: "enero", "febrero 2026", "01-2026").
Si no se indica, pedir antes de continuar.

## Paso 1: Verificar Excel cerrado

Antes de cualquier escritura, confirmar con el usuario que el Excel de cuadre está cerrado.
**NUNCA escribir en el Excel si puede estar abierto en otro proceso.**

## Paso 2: Localizar archivos de entrada

```bash
# Ver archivos disponibles en datos/
ls "C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/datos/"
```

Identificar:
- Excel de movimientos bancarios (NORMA43 exportado) para el mes indicado
- Excel de facturas del período (`FACTURAS_*.xlsx` o similar)
- Excel maestro: `MAESTRO_PROVEEDORES.xlsx`

## Paso 3: Ejecutar cuadre

```bash
cd "C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas"
python cuadre/cuadre.py
```

Si el script requiere parámetros de mes, pasarlos según la interfaz del script.

## Paso 4: Revisar resultados

Métricas clave a reportar:
- Total movimientos procesados
- Clasificados (% sobre total)
- En estado REVISAR (% sobre total) — objetivo: <15%
- Movimientos sin clasificar por categoría

## Paso 5: Analizar movimientos REVISAR

Si hay movimientos en REVISAR, invocar `/revisar` para análisis detallado:
```
/revisar
```

## Paso 6: Verificar facturas no cuadradas

```bash
python -c "
import pandas as pd
df = pd.read_excel('datos/FACTURAS_PENDIENTES.xlsx')
print(df[df['ESTADO'] != 'CUADRADO'][['PROVEEDOR','IMPORTE','FECHA','REFERENCIA']].to_string())
" 2>/dev/null || echo "Verificar nombre exacto del archivo de facturas"
```

## Paso 7: Guardar y reportar

Confirmar que el Excel de salida se guardó correctamente.
Reportar al usuario:
- Resumen de métricas (clasificados, REVISAR, sin cuadrar)
- Facturas pendientes si las hay
- Recomendaciones para reducir REVISAR si >15%

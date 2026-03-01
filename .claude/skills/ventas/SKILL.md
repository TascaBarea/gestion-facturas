---
name: ventas
description: Descarga ventas semanales de Loyverse y WooCommerce, actualiza Excel y regenera dashboards.
disable-model-invocation: true
argument-hint: "[mensual]"
allowed-tools: Bash, Read
---

# Descargar Ventas Semanales

Ejecuta la descarga de ventas de Loyverse (Tasca + Comestibles) y WooCommerce.

## Verificaciones previas

1. Comprobar que existe el archivo .env:
```bash
ls ventas_semana/.env
```
Si no existe, avisar al usuario que necesita configurar las API keys de Loyverse y WooCommerce.

2. Avisar al usuario de que cierre `Ventas Barea 2026.xlsx` y `Articulos 26.xlsx` si los tiene abiertos (en Windows, si estan abiertos dara error de escritura).

## Construir el comando

Script: `python ventas_semana/script_barea.py`

Si $ARGUMENTS contiene `mensual`:
```bash
python ventas_semana/script_barea.py --dashboard-mensual
```

El flag `--dashboard-mensual` implica:
- Dashboards con solo meses cerrados (excluye mes en curso)
- Genera PDF resumen mensual
- Envia email a socios con PDF + dashboards adjuntos

## Ejecutar

Ejecutar desde `C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/`.

El script tarda 1-3 minutos (descarga de APIs).

## Interpretar resultado

El script imprime paso a paso:
- Semana procesada (lunes a domingo)
- Recibos e items descargados por tienda (Tasca y Comestibles)
- Pedidos WooCommerce descargados
- Articulos actualizados en Excel
- Estado de regeneracion de dashboards
- Si se envio email mensual (cuando `--dashboard-mensual`)

Resumir al usuario de forma clara:
- Periodo descargado
- Items/recibos por tienda
- Si los dashboards se regeneraron OK
- Si hubo errores

## Errores comunes

- `FileNotFoundError: .env`: falta configuracion, crear `ventas_semana/.env`
- `PermissionError` en Excel: archivo abierto, cerrar y reintentar
- `HTTP 401/403` en Loyverse: token expirado, regenerar en panel Loyverse (back.loyverse.com)
- `ConnectionError` / Timeout: problema de red, reintentar en unos minutos
- `HTTP 401` en WooCommerce: verificar WC_KEY y WC_SECRET en .env

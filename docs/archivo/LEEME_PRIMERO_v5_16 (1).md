# LEEME PRIMERO - ParsearFacturas

**Versión:** v5.16  
**Fecha:** 07/01/2026  
**Autor:** Tasca Barea + Claude  

---

## ⚠️ IMPORTANTE - ANTES DE EJECUTAR

### Pasos para actualizar a v5.16:

```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# 1. Copiar archivos actualizados
copy main.py .
copy parser.py nucleo\
copy excel.py salidas\

# 2. Ejecutar (modo interactivo)
python main.py

# 3. O modo directo
python main.py -i "C:\Facturas\4 TRI 2025"
```

---

## CAMBIOS v5.16 (07/01/2026)

### 🆕 Modo interactivo con selector gráfico

| Opción | Descripción |
|--------|-------------|
| `E` | Abre explorador de Windows para seleccionar carpeta con ratón |
| `M` | Introducir ruta manualmente |
| `Q` | Salir |
| `1,2,3...` | Seleccionar carpeta de la lista (si se detectan) |

### 🆕 Soporte ATRASADAS automático

- main.py busca subcarpeta `ATRASADAS` automáticamente
- Opción de procesar solo ATRASADAS por separado
- Archivos marcados con `[ATR]` en el log

### 🆕 Campo # mejorado

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Normal | `XXXX` | `4006` |
| Atrasada | `XXX ATRASADA` | `460 ATRASADA` |
| Sin numerar | `TEMPXXX_XTxx` | `TEMP001_4T25` |
| Error | `ERROR_3DIG_XXX` | 3 dígitos fuera de carpeta ATRASADAS |

### 🆕 Hoja Facturas mejorada

Nuevas columnas:
- `ARCHIVO` - Nombre del archivo (después de #)
- `TOTAL FACTURA` - Total extraído del PDF
- `Total` - Total calculado (suma líneas)

Orden: `#, ARCHIVO, CUENTA, TITULO, Fec.Fac., REF, TOTAL FACTURA, Total, OBSERVACIONES`

---

## ARCHIVOS MODIFICADOS v5.16

| Archivo | Destino | Cambios |
|---------|---------|---------|
| `main.py` | raíz | Modo interactivo, selector gráfico, búsqueda ATRASADAS |
| `parser.py` | nucleo/ | Detección 3 dígitos=ATRASADA, TEMP por trimestre |
| `excel.py` | salidas/ | Columnas ARCHIVO y TOTAL FACTURA |

---

## VERIFICACIÓN POST-ACTUALIZACIÓN

Después de ejecutar `python main.py`:

1. ✅ Se abre menú con opción `E` para explorar con ratón
2. ✅ Detecta subcarpeta ATRASADAS si existe
3. ✅ Archivos de 3 dígitos muestran `XXX ATRASADA` en columna #
4. ✅ Hoja Facturas tiene columnas ARCHIVO y TOTAL FACTURA

---

## ESTADO ACTUAL (07/01/2026)

| Métrica | Valor |
|---------|-------|
| Extractores activos | ~95 |
| Tasa cuadre | **81.2%** |
| Objetivo | 80% ✅ **ALCANZADO** |

---

## ⚠️ REGLAS CRÍTICAS PARA CLAUDE

| # | Regla |
|---|-------|
| 1 | **LEER** LEEME_PRIMERO, ESTADO_PROYECTO, ESQUEMA y SESION antes de trabajar |
| 2 | **VERIFICAR** si extractor existe antes de crear nuevo |
| 3 | **SIEMPRE** archivos .py COMPLETOS, nunca parches de líneas |
| 4 | **PROBAR** con PDFs reales antes de entregar |
| 5 | **PREGUNTAR** si hay duda, no asumir |
| 6 | **PORTES**: extractor los devuelve como línea, main.py los prorratea |
| 7 | **3 DÍGITOS = ATRASADA** (con palabra o en carpeta ATRASADAS) |

---

## PENDIENTE PRÓXIMA SESIÓN

### 🟡 Proveedores pendientes

| Proveedor | Errores | Tipo | Prioridad |
|-----------|---------|------|-----------|
| JAMONES BERNAL | 6 | DESCUADRE | Media |
| JIMELUZ | 18 | OCR | Baja (aparcado) |

### 🟢 Mejoras futuras

- [ ] Probar generador SEPA con Banco Sabadell
- [ ] Automatizar descarga de Gmail
- [ ] Dashboard de métricas

---

## ARCHIVOS DE LA SESIÓN 07/01/2026

| Archivo | Destino | Estado |
|---------|---------|--------|
| `main.py` | raíz | ✅ v5.16 - Modo interactivo |
| `parser.py` | nucleo/ | ✅ v5.16 - ATRASADAS y TEMP |
| `excel.py` | salidas/ | ✅ v5.16 - Nuevas columnas |
| `ESQUEMA_PROYECTO_v5_16.md` | docs/ | ✅ Documentación completa |

---

## HISTORIAL

| Fecha | Versión | Cambio principal |
|-------|---------|------------------|
| **07/01/2026** | **v5.16** | **Modo interactivo, ATRASADAS, TEMP, hoja Facturas mejorada** |
| 07/01/2026 | v5.14 | SILVA CORDERO, LA ALACENA corregidos |
| 06/01/2026 | v5.13 | MARITA COSTA, ANGEL Y LOLI, LA BARRA DULCE, ZUCCA |
| 05/01/2026 | v5.12 | Normalización, BM simplificado |
| 04/01/2026 | v5.11 | +5 extractores, OCR, cache auto |

---

*Última actualización: 07/01/2026*

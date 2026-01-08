# ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 06/01/2026  
**Versión actual:** v5.13  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas

---

## MÉTRICAS ACTUALES

### Resultados v5.11 (referencia)

| Métrica | Valor |
|---------|-------|
| **Tasa de éxito** | **72.5%** |
| **Extractores totales** | ~88 |
| **Facturas analizadas** | 965 (4 trimestres) |
| **Proveedores únicos** | 371 (fragmentados) |

### Resultados esperados v5.13

| Métrica | v5.11 | v5.12 | v5.13 (esperado) |
|---------|-------|-------|------------------|
| **Tasa de éxito** | 72.5% | ~76% | **78-80%** |
| **Proveedores únicos** | 371 | ~100-150 | ~100-150 |
| **Alias configurados** | ~170 | 290 | 290 |

**Objetivo:** 80% cuadre OK

---

## CAMBIOS v5.13 (06/01/2026)

### Extractores corregidos en sesión 06/01/2026

| Extractor | Problema | Solución | Validación |
|-----------|----------|----------|------------|
| **MARITA COSTA** | IVA incorrecto (2%/4%/10% histórico) | Combinatoria con desglose fiscal | 10/10 ✓ |
| **ANGEL Y LOLI** | Portes/Descuento mal detectados | Detección automática según fórmula | 4/4 ✓ |
| **LA BARRA DULCE** | Categoría incorrecta (PASTELERIA) | `categoria_fija = 'DULCES'` | 8/8 ✓ |
| **ZUCCA** | Sin categoría asignada (nan) | `categoria_fija = 'QUESO PAR'` + DESPENSA para yogur | 11/11 ✓ |

### Detalles técnicos

**MARITA COSTA v5.13:**
- Asignación IVA por combinatoria usando desglose fiscal de factura
- Soporta IVA 2% (2024), 4% (AOVE/LUCÍA PICOS), 10% (resto)
- Maneja cambios históricos automáticamente

**ANGEL Y LOLI v5.13:**
- Detecta PORTES vs DESCUENTO automáticamente:
  - Si IMPORTE + val2 ≈ BASE → val2 es PORTES
  - Si IMPORTE - val2 ≈ BASE → val2 es DESCUENTO
- Patrón flexible que permite números en descripción (ej: "CUENCO 10 CM")

**LA BARRA DULCE v5.13:**
- Categoría cambiada de `PASTELERIA` a `DULCES`

**ZUCCA v5.13:**
- Añadida `categoria_fija = 'QUESO PAR'`
- Yogures → categoría `DESPENSA` (IVA 10%)
- Quesos → categoría `QUESO PAR` (IVA 4%)

---

## EVOLUCIÓN HISTÓRICA

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.0 | 26/12/2025 | 54% | Normalización + prorrateo portes |
| v5.7 | 01/01/2026 | ~66% | LA ROSQUILLERIA corregido |
| v5.11 | 04/01/2026 | ~72.5% | +5 extractores, OCR, cache auto |
| v5.12 | 05/01/2026 | ~76% | Normalización proveedores, BM simplificado |
| **v5.13** | **06/01/2026** | **~78-80%** | **MARITA, ANGEL Y LOLI, LA BARRA DULCE, ZUCCA** |

---

## ⚠️ PENDIENTE PRÓXIMA SESIÓN (07/01/2026)

### 🔴 PRIORIDAD 1: Revisar ZUCCA otra vez
- Verificar que funciona correctamente tras integración
- Comprobar categorías QUESO PAR y DESPENSA

### 🔴 RECORDATORIO: Modificar Excel de salida
- Quitar columnas innecesarias
- Añadir columnas nuevas

### Tareas inmediatas
- [ ] Copiar extractores v5.13 a carpeta extractores/
- [ ] Ejecutar en 4 trimestres
- [ ] Verificar métricas de cuadre
- [ ] **Revisar ZUCCA** - confirmar funcionamiento

### Proveedores pendientes

| # | Proveedor | Errores | Tipo | Estado |
|---|-----------|---------|------|--------|
| 1 | ~~MARITA COSTA~~ | ~~10~~ | ~~DESCUADRE~~ | ✅ CORREGIDO |
| 2 | **QUESERIA ZUCCA** | 8 | DESCUADRE | ⚠️ REVISAR |
| 3 | JAMONES BERNAL | 6 | DESCUADRE | PENDIENTE |
| 4 | JIMELUZ | 18 | OCR | PENDIENTE |

---

## ARCHIVOS v5.13

### Extractores nuevos/modificados (sesión 06/01/2026)

| Archivo | Destino | Estado |
|---------|---------|--------|
| `marita_costa.py` | extractores/ | ✅ NUEVO |
| `angel_loli.py` | extractores/ | ✅ CORREGIDO |
| `la_barra_dulce.py` | extractores/ | ✅ CORREGIDO |
| `zucca.py` | extractores/ | ✅ CORREGIDO |

### Archivos v5.12 (sesión anterior)

| Archivo | Destino | Estado |
|---------|---------|--------|
| `main_v512.py` | Reemplaza main.py | ✅ |
| `bm.py` | extractores/ | ✅ |
| `pifema.py` | extractores/ | ✅ |
| `serrin_no_chan.py` | extractores/ | ✅ |

---

## PROYECCIÓN

| Escenario | Tasa | Facturas OK |
|-----------|------|-------------|
| **v5.11** | 72.5% | 700 |
| **v5.12** | ~76% | ~733 |
| **v5.13 (actual)** | ~78% | ~753 |
| + ZUCCA revisado + BERNAL | ~79% | ~762 |
| **OBJETIVO** | **80%** | **~772** |

---

*Actualizado: 06/01/2026*

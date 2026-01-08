# ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 05/01/2026  
**Versión actual:** v5.12  
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

### Resultados esperados v5.12

| Métrica | v5.11 | v5.12 (esperado) |
|---------|-------|------------------|
| **Tasa de éxito** | 72.5% | **75-78%** |
| **Proveedores únicos** | 371 | **~100-150** |
| **Alias configurados** | ~170 | **290** |

**Objetivo:** 80% cuadre OK

---

## CAMBIOS v5.12 (05/01/2026)

### 1. Normalización de proveedores CORREGIDA

| Proveedor | Variantes v5.11 | v5.12 |
|-----------|-----------------|-------|
| CERES | 12 variantes | 1 |
| BM SUPERMERCADOS | 6 variantes | 1 |
| VIRGEN DE LA SIERRA | 7 variantes | 1 |

### 2. Soporte `importe_iva_inc`

Para extractores donde los importes INCLUYEN IVA (como BM):
- Extractor devuelve `importe_iva_inc`
- main.py busca IVA en diccionario
- Calcula `base = importe_iva_inc / (1 + iva/100)`

### 3. Extractores modificados

| Extractor | Cambio |
|-----------|--------|
| **bm.py** | Simplificado - IVA/cat del diccionario |
| **pifema.py** | + `categoria_fija = 'VINOS'` |
| **serrin_no_chan.py** | - `categoria_fija` (consulta diccionario) |

### 4. CATEGORIAS_FIJAS_PROVEEDOR

```python
{
    'LUCERA': 'ELECTRICIDAD LOCAL',
    'SOM ENERGIA': 'ELECTRICIDAD LOCAL',
    'YOIGO': 'TELEFONO',
    'WEBEMPRESA': 'WEB Y SOFTWARE',
    ...
}
```

---

## EVOLUCIÓN HISTÓRICA

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.0 | 26/12/2025 | 54% | Normalización + prorrateo portes |
| v5.7 | 01/01/2026 | ~66% | LA ROSQUILLERIA corregido |
| v5.11 | 04/01/2026 | ~72.5% | +5 extractores, OCR, cache auto |
| **v5.12** | **05/01/2026** | **~75-78%** | **Normalización, BM simplificado** |

---

## ⚠️ PENDIENTE PRÓXIMA SESIÓN

### 🔴 RECORDATORIO: Modificar Excel de salida
- Quitar columnas innecesarias
- Añadir columnas nuevas

### Tareas inmediatas
- [ ] Ejecutar main_v512.py en 4 trimestres
- [ ] Verificar unificación de proveedores
- [ ] Eliminar extractores/lucera.py
- [ ] Copiar extractores modificados (bm, pifema, serrin_no_chan)

### Proveedores pendientes

| # | Proveedor | Errores | Tipo |
|---|-----------|---------|------|
| 1 | MARITA COSTA | 10 | DESCUADRE |
| 2 | QUESERIA ZUCCA | 8 | DESCUADRE |
| 3 | JAMONES BERNAL | 6 | DESCUADRE |
| 4 | JIMELUZ | 18 | OCR |

---

## ARCHIVOS v5.12

| Archivo | Destino | Estado |
|---------|---------|--------|
| `main_v512.py` | Reemplaza main.py | ✅ |
| `bm.py` | extractores/ | ✅ |
| `pifema.py` | extractores/ | ✅ |
| `serrin_no_chan.py` | extractores/ | ✅ |
| `identificador_proveedor.py` | nucleo/ (opcional) | ✅ |

---

## PROYECCIÓN

| Escenario | Tasa | Facturas OK |
|-----------|------|-------------|
| **v5.11** | 72.5% | 700 |
| **v5.12 (esperado)** | ~76% | ~733 |
| + MARITA/ZUCCA | ~78% | ~753 |
| **OBJETIVO** | **80%** | **~772** |

---

*Actualizado: 05/01/2026*

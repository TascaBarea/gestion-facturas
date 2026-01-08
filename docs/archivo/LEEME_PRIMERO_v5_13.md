# LEEME PRIMERO - ParsearFacturas

**Versión:** v5.13  
**Fecha:** 06/01/2026  
**Autor:** Tasca Barea + Claude  

---

## ⚠️ IMPORTANTE - ANTES DE EJECUTAR

### Pasos para actualizar a v5.13:

```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# 1. Si no lo has hecho, backup del main actual
mv main.py main_v511_backup.py

# 2. Usar main v5.12 (si no está)
cp main_v512.py main.py

# 3. IMPORTANTE: Eliminar extractor LUCERA (está roto)
del extractores\lucera.py

# 4. Copiar extractores v5.12 (si no están)
copy bm.py extractores\
copy pifema.py extractores\
copy serrin_no_chan.py extractores\

# 5. Copiar extractores NUEVOS v5.13
copy marita_costa.py extractores\
copy angel_loli.py extractores\
copy la_barra_dulce.py extractores\
copy zucca.py extractores\

# 6. Ejecutar
python main.py -i "C:\Facturas\1 TRI 2025"
```

---

## CAMBIOS v5.13 (06/01/2026)

### Extractores corregidos

| Extractor | Cambio | Validación |
|-----------|--------|------------|
| **marita_costa.py** | IVA por combinatoria con desglose fiscal | 10/10 ✓ |
| **angel_loli.py** | Detección auto PORTES vs DESCUENTO | 4/4 ✓ |
| **la_barra_dulce.py** | `categoria_fija = 'DULCES'` | 8/8 ✓ |
| **zucca.py** | `categoria_fija = 'QUESO PAR'` + DESPENSA | 11/11 ✓ |

### Cambios v5.12 (sesión anterior)

| Cambio | Descripción |
|--------|-------------|
| **Normalización proveedores** | 371 → ~100-150 proveedores únicos |
| **290 alias** | +120 nuevos vs v5.11 |
| **CATEGORIAS_FIJAS_PROVEEDOR** | LUCERA, SOM ENERGIA, YOIGO, etc. |
| **Soporte importe_iva_inc** | Para BM y similares |

---

## VERIFICACIÓN POST-ACTUALIZACIÓN

Después de ejecutar, verificar en el Excel que:

1. **MARITA COSTA** - IVA correcto (4% AOVE, 10% resto)
2. **ANGEL Y LOLI** - Portes/descuentos prorrateados correctamente
3. **LA BARRA DULCE** - Categoría = DULCES
4. **ZUCCA** - Categoría = QUESO PAR (yogures = DESPENSA)
5. **CERES** aparece como "CERES" (no fragmentado)
6. **BM** aparece como "BM SUPERMERCADOS"

---

## ⚠️ PENDIENTE PRÓXIMA SESIÓN (07/01/2026)

### 🔴 PRIORIDAD 1: Revisar ZUCCA otra vez
- Verificar funcionamiento tras integración
- Comprobar categorías correctas

### 🔴 Modificar Excel de salida
- Quitar columnas innecesarias
- Añadir columnas nuevas según necesidades

### Proveedores pendientes

| Proveedor | Errores | Tipo | Estado |
|-----------|---------|------|--------|
| ~~MARITA COSTA~~ | ~~10~~ | ~~DESCUADRE~~ | ✅ |
| **QUESERIA ZUCCA** | 8 | DESCUADRE | ⚠️ REVISAR |
| JAMONES BERNAL | 6 | DESCUADRE | PENDIENTE |
| JIMELUZ | 18 | OCR | PENDIENTE |

---

## ARCHIVOS DE LA SESIÓN 06/01/2026

| Archivo | Destino | Estado |
|---------|---------|--------|
| `marita_costa.py` | extractores/ | ✅ NUEVO |
| `angel_loli.py` | extractores/ | ✅ CORREGIDO |
| `la_barra_dulce.py` | extractores/ | ✅ CORREGIDO |
| `zucca.py` | extractores/ | ✅ CORREGIDO |

---

## HISTORIAL

| Fecha | Versión | Cambio principal |
|-------|---------|------------------|
| **06/01/2026** | **v5.13** | **MARITA COSTA, ANGEL Y LOLI, LA BARRA DULCE, ZUCCA** |
| 05/01/2026 | v5.12 | Normalización, BM simplificado, soporte importe_iva_inc |
| 04/01/2026 | v5.11 | +5 extractores, OCR, cache auto |
| 03/01/2026 | v5.9 | Fix categoria_fija |
| 01/01/2026 | v5.7 | LA ROSQUILLERIA |

---

*Última actualización: 06/01/2026*

# LEEME PRIMERO - ParsearFacturas

**Versión:** v5.12  
**Fecha:** 05/01/2026  
**Autor:** Tasca Barea + Claude  

---

## ⚠️ IMPORTANTE - ANTES DE EJECUTAR

### Pasos para actualizar a v5.12:

```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# 1. Backup del main actual
mv main.py main_v511_backup.py

# 2. Usar el nuevo main
cp main_v512.py main.py

# 3. IMPORTANTE: Eliminar extractor LUCERA (está roto)
del extractores\lucera.py

# 4. Copiar extractores modificados
copy bm.py extractores\
copy pifema.py extractores\
copy serrin_no_chan.py extractores\

# 5. (Opcional) Copiar módulo identificador
copy identificador_proveedor.py nucleo\

# 6. Ejecutar
python main.py -i "C:\Facturas\1 TRI 2025"
```

---

## CAMBIOS v5.12

| Cambio | Descripción |
|--------|-------------|
| **Normalización proveedores** | 371 → ~100-150 proveedores únicos |
| **290 alias** | +120 nuevos vs v5.11 |
| **CATEGORIAS_FIJAS_PROVEEDOR** | LUCERA, SOM ENERGIA, YOIGO, etc. |
| **Soporte importe_iva_inc** | Para BM y similares (IVA del diccionario) |
| **bm.py simplificado** | IVA y categoría vienen del diccionario |
| **pifema.py** | categoria_fija = 'VINOS' |
| **serrin_no_chan.py** | Consulta diccionario (sin categoria_fija) |

---

## VERIFICACIÓN POST-ACTUALIZACIÓN

Después de ejecutar, verificar en el Excel que:

1. **CERES** aparece como "CERES" (no "2T25 0422 CERES")
2. **BM** aparece como "BM SUPERMERCADOS"
3. **FABEIRO** aparece como "FABEIRO" (no "0731 FABEIRO")
4. **LUCERA** tiene categoría "ELECTRICIDAD LOCAL"
5. **PIFEMA** tiene categoría "VINOS"

---

## ⚠️ RECORDATORIO PRÓXIMA SESIÓN

### 🔴 Modificar Excel de salida
- Quitar columnas innecesarias
- Añadir columnas nuevas según necesidades

### Proveedores pendientes
| Proveedor | Errores | Tipo |
|-----------|---------|------|
| MARITA COSTA | 10 | DESCUADRE |
| QUESERIA ZUCCA | 8 | DESCUADRE |
| JAMONES BERNAL | 6 | DESCUADRE |
| JIMELUZ | 18 | OCR |

---

## ARCHIVOS DE LA SESIÓN

| Archivo | Destino | Estado |
|---------|---------|--------|
| `main_v512.py` | Reemplaza main.py | ✅ |
| `bm.py` | extractores/ | ✅ |
| `pifema.py` | extractores/ | ✅ |
| `serrin_no_chan.py` | extractores/ | ✅ |
| `identificador_proveedor.py` | nucleo/ (opcional) | ✅ |

---

## HISTORIAL

| Fecha | Versión | Cambio principal |
|-------|---------|------------------|
| **05/01/2026** | **v5.12** | **Normalización, BM simplificado, soporte importe_iva_inc** |
| 04/01/2026 | v5.11 | +5 extractores, OCR, cache auto |
| 03/01/2026 | v5.9 | Fix categoria_fija |
| 01/01/2026 | v5.7 | LA ROSQUILLERIA |

---

*Última actualización: 05/01/2026*

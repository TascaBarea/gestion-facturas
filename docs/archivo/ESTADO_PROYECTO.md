# 📊 ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 31/12/2025  
**Versión actual:** v5.4  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas

---

## 🎯 MÉTRICAS ACTUALES

### Resultados v5.4 (31/12/2025)

| Métrica | Valor |
|---------|-------|
| **Tasa de éxito** | ~60% |
| **Extractores totales** | ~140 |
| **Facturas analizadas** | ~910 (4 trimestres) |
| **Proveedores únicos** | ~148 |
| **Artículos en diccionario** | ~925 |

**Objetivo:** 80% cuadre OK

### Desglose por tipo de error (estimado)

| Error | Facturas | % | Estado |
|-------|----------|---|--------|
| ✅ OK | ~546 | 60% | Procesadas correctamente |
| ❌ DESCUADRE | ~180 | 20% | IVA/bases mal calculados |
| ❌ SIN_TOTAL | ~90 | 10% | Falta extraer_total() |
| ❌ SIN_LINEAS | ~50 | 5% | Extractor no existe |
| ❌ OTROS | ~44 | 5% | FECHA, CIF pendiente... |

### Evolución histórica

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.0 | 26/12/2025 | 54% | Normalización + prorrateo portes |
| v5.2 | 26/12/2025 | ~66% | +10 extractores corregidos |
| v5.3 | 28/12/2025 | ~57% | +6 extractores nuevos |
| **v5.4** | **31/12/2025** | **~60%** | **+LAVAPIES, mejoras MUÑOZ/GREDALES** |

**Objetivo:** 80% cuadre OK

---

## ✅ SESIONES RECIENTES

### 31/12/2025 - Sesión actual
| Extractor | CIF | Facturas | Estado |
|-----------|-----|----------|--------|
| **DISTRIBUCIONES LAVAPIES** | F88424072 | 13/13 ✅ | **NUEVO - PENDIENTE INTEGRAR** |
| BODEGAS MUÑOZ MARTIN | E83182683 | 4/4 ✅ | Mejorado (OCR) - Ya integrado |
| LOS GREDALES | B83594150 | 5/5 ✅ | Mejorado (líneas) - Ya integrado |

### 30/12/2025 - Sesión anterior
| Extractor | CIF | Facturas | Estado |
|-----------|-----|----------|--------|
| DE LUIS | B78380685 | OK | Ya integrado |
| ALFARERIA TALAVERANA | B45007374 | OK | Ya integrado |
| PORVAZ | E36131709 | OK | Ya integrado |
| INMAREPRO | B86310109 | OK | Ya integrado |

### 29/12/2025
| Extractor | Cambio |
|-----------|--------|
| DEBORA GARCIA | Bug IRPF corregido |
| FELISA | Alias añadido |
| HERNÁNDEZ BODEGA | Encoding Ñ |
| SILVA CORDERO | IVA mixto |

---

## ⚠️ PROVEEDORES PRIORITARIOS (PRÓXIMA SESIÓN)

### 🔴 TOP 10 por impacto

| # | Proveedor | Errores | Tipo | Dificultad |
|---|-----------|---------|------|------------|
| 1 | **BM SUPERMERCADOS** | 37 | DESCUADRE | 🟡 Media |
| 2 | **JIMELUZ** | 19 | OCR | 🔴 Alta |
| 3 | **FELISA GOURMET** | 12 | DESCUADRE | 🟢 Fácil |
| 4 | ~~DISTRIBUCIONES LAVAPIES~~ | ~~11~~ | ~~DESCUADRE~~ | ✅ HECHO |
| 5 | **LA ROSQUILLERIA** | 10 | OCR | 🔴 Alta |
| 6 | JAMONES BERNAL | 6 | DESCUADRE | 🟡 Media |
| 7 | SILVA CORDERO | 5 | DESCUADRE | 🟡 Media |
| 8 | EMJAMESA | 4 | DESCUADRE | 🟡 Media |
| 9 | ECOFICUS | 4 | DESCUADRE | 🟡 Media |
| 10 | ALCAMPO | 4 | DESCUADRE | 🟡 Media |

### Recomendación próxima sesión

**Opción A - Quick wins:**
- BM SUPERMERCADOS (37 errores)
- FELISA GOURMET (12 errores)
- Potencial: **+49 facturas** (~+5%)

**Opción B - OCR:**
- JIMELUZ (19)
- LA ROSQUILLERIA (10)
- Potencial: **+29 facturas** (~+3%)

---

## 📦 PENDIENTE INTEGRAR

```cmd
# Copiar extractor LAVAPIES
copy lavapies.py C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\extractores\

# Limpiar caché
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\extractores
rmdir /s /q __pycache__

# Commit
git add .
git commit -m "Sesión 31/12: +LAVAPIES (IVA deducido de factura, 13 facturas)"
git push
```

---

## 🔧 TÉCNICAS IMPLEMENTADAS

| Técnica | Proveedores | Descripción |
|---------|-------------|-------------|
| **IVA deducido de factura** | LAVAPIES | Subset-sum para detectar qué productos van a cada IVA |
| **OCR híbrido** | MUÑOZ, ECOMS, VIRGEN | pdfplumber + Tesseract fallback |
| **Avisos discrepancia** | LAVAPIES | Alerta cuando IVA factura ≠ esperado |
| **Validación BASE IMPONIBLE** | GREDALES | Fallback si líneas no cuadran |
| **Prorrateo portes** | Todos | Portes distribuidos proporcionalmente |

---

## 📈 PROYECCIÓN

| Escenario | Tasa | Facturas OK |
|-----------|------|-------------|
| **Actual (v5.4)** | **~60%** | **~546** |
| + BM + FELISA | ~65% | ~591 |
| + JIMELUZ + ROSQUILLERIA | ~68% | ~619 |
| **OBJETIVO** | **80%** | **~728** |

---

## 📋 TAREAS PENDIENTES

### Inmediato
- [x] ~~LAVAPIES~~ ✅ HECHO 31/12
- [ ] **INTEGRAR lavapies.py** en repositorio
- [ ] BM SUPERMERCADOS (37 errores)
- [ ] FELISA GOURMET (12 errores)

### Corto plazo
- [ ] Consolidar nombres duplicados (BM, ECOMS)
- [ ] Llegar a **70%** cuadre OK

### Medio plazo
- [ ] Llegar a **80%** cuadre OK
- [ ] Integrar extractor Gmail
- [ ] Completar IBANs (~25% actual)
- [ ] Generador SEPA con validación

---

## 🗂️ HISTORIAL DE SESIONES

| Fecha | Versión | Extractores | Mejora |
|-------|---------|-------------|--------|
| **31/12/2025** | **v5.4** | **+1 nuevo, +2 mejorados** | **LAVAPIES, MUÑOZ OCR, GREDALES líneas** |
| 30/12/2025 | v5.3+ | +4 corregidos | DE LUIS, ALFARERIA, PORVAZ, INMAREPRO |
| 29/12/2025 | v5.3 | +4 bugs | DEBORA, FELISA, HERNÁNDEZ, SILVA |
| 28/12/2025 | v5.3 | +6 nuevos | ECOMS, VIRGEN, MARITA, CASA DUQUE, CELONIS, PIFEMA |
| 26/12/2025 | v5.2 | +10 corregidos | Múltiples fixes |

---

*Actualizado: 31/12/2025*  
*¡Feliz Año Nuevo! 🎉*

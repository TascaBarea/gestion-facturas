# ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 2025-12-21
**Versión actual:** v4.5

---

## 📊 MÉTRICAS ACTUALES

### v4.5 - Resultados (21/12/2025)

| Trimestre | Facturas | Cuadre OK | % | Con Líneas | Importe |
|-----------|----------|-----------|---|------------|---------|
| 1T25 | 252 | ~175 | **~70%** | ~205 (81%) | 48,173€ |
| 2T25 | 307 | ~175 | **~57%** | ~240 (78%) | 46,720€ |
| 3T25 | 161 | ~95 | **~59%** | ~125 (78%) | 35,539€ |
| 4T25 | 183 | ~100 | **~55%** | ~130 | pendiente |
| **TOTAL** | **903** | **~545** | **~60%** | ~700 | ~130,000€ |

### Evolución histórica

| Versión | Fecha | Cuadre 1T25 | Cambio principal |
|---------|-------|-------------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores monolíticos |
| v3.6 | 10/12/2025 | 47% | +6 extractores servicios |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v4.2 | 19/12/2025 | 56% | +12 extractores, bug IVA 0 |
| v4.3 | 20/12/2025 | 60% | +6 extractores OCR |
| v4.4 | 21/12/2025 AM | 66% | +12 extractores sesión mañana |
| **v4.5** | **21/12/2025 PM** | **~70%** | **+8 extractores sesión tarde** |

**Mejora total:** 42% → ~70% = **+28 puntos** (+67% relativo)

---

## ✅ SESIÓN 2025-12-21 TARDE: 8 EXTRACTORES NUEVOS

### Extractores creados

| # | Proveedor | CIF/NIF | Facturas | Método | IBAN |
|---|-----------|---------|----------|--------|------|
| 1 | JAIME FERNÁNDEZ MORENO | REDACTED_DNI | 7/7 ✅ | pdfplumber | ⚠️ pendiente |
| 2 | BENJAMÍN ORTEGA ALONSO | REDACTED_DNI | 7/7 ✅ | pdfplumber | ⚠️ pendiente |
| 3 | IBARRAKO PIPARRAK | F20532297 | 3/3 ✅ | pdfplumber | ES69 2095... ✅ |
| 4 | ALFARERÍA ÁNGEL Y LOLI | REDACTED_DNI | 4/4 ✅ | pdfplumber | ⚠️ pendiente |
| 5 | ABBATI CAFFE | B82567876 | 3/3 ✅ | pdfplumber | N/A (domiciliación) |
| 6 | PANIFIESTO LAVAPIES | B87874327 | 10/10 ✅ | pdfplumber | N/A (tarjeta) |
| 7 | JULIO GARCIA VIVAS | REDACTED_DNI | 8/8 ✅ | **híbrido** | ⚠️ pendiente |
| 8 | PRODUCTOS ADELL | B12711636 | 3/3 ✅ | pdfplumber | ES62 3058... ✅ |
| **TOTAL** | | | **45/45** | | **100%** |

### Archivos generados

```
extractores/
├── jaime_fernandez.py      # Alquiler local (retención IRPF)
├── benjamin_ortega.py      # Alquiler local (retención IRPF)
├── ibarrako.py             # Piparras vascas
├── angel_loli.py           # Vajilla artesanal
├── abbati.py               # Café
├── panifiesto.py           # Pan artesanal (albaranes diarios)
├── julio_garcia.py         # Verduras mercado (híbrido pdfplumber+OCR)
├── productos_adell.py      # Conservas Croquellanas
├── productos.py            # LIMPIADO - solo ZUBELZU y ANA CABALLO
└── __init__.py             # Actualizado con imports
```

### Características especiales sesión tarde

| Proveedor | IVA | Peculiaridad |
|-----------|-----|--------------|
| JAIME FERNÁNDEZ | 21% | Alquiler con retención IRPF 19% |
| BENJAMÍN ORTEGA | 21% | Alquiler con retención IRPF 19% |
| IBARRAKO | 10% | Piparras - separado de productos.py |
| ÁNGEL Y LOLI | 21% | Vajilla artesanal Úbeda |
| ABBATI | 10% | Café - pago domiciliación |
| PANIFIESTO | 4% | Facturas mensuales con 20-30 albaranes diarios |
| JULIO GARCIA | 4%/10% | **Híbrido** - algunas facturas escaneadas requieren OCR |
| PRODUCTOS ADELL | 10% | Conservas - columna "Cajas" variable |

### Limpieza de código

Se eliminaron clases duplicadas de `productos.py`:
- ~~ExtractorMolletes~~ → `artesanos_mollete.py`
- ~~ExtractorIbarrako~~ → `ibarrako.py`
- ~~ExtractorProductosAdell~~ → `productos_adell.py`
- ~~ExtractorGrupoCampero~~ → `territorio_campero.py`
- ~~ExtractorEcoficus~~ → `ecoficus.py`

---

## ✅ SESIÓN 2025-12-21 MAÑANA: 12 EXTRACTORES

(Documentados en versión anterior v4.4)

| # | Proveedor | CIF | Facturas | Método |
|---|-----------|-----|----------|--------|
| 1 | QUESERIA ZUCCA | B42861948 | 7/7 ✅ | pdfplumber |
| 2 | PANRUJE | B13858014 | 6/6 ✅ | pdfplumber |
| 3 | GRUPO DISBER | B43489039 | 4/4 ✅ | pdfplumber |
| 4 | LIDL | A60195278 | 5/5 ✅ | pdfplumber |
| 5 | LA ROSQUILLERIA | B86556081 | 7/7 ✅ | OCR |
| 6 | GADITAUN | REDACTED_DNI | 5/5 ✅ | OCR |
| 7 | DE LUIS | B87893681 | 5/5 ✅ | híbrido |
| 8 | MANIPULADOS ABELLAN | B30243737 | 6/6 ✅ | OCR |
| 9 | ECOMS/DIA | B72738602 | 6/8 ✅ | híbrido |
| 10 | MARITA COSTA | REDACTED_DNI | 9/9 ✅ | pdfplumber |
| 11 | SERRÍN NO CHAN | B87214755 | 7/7 ✅ | pdfplumber |
| 12 | FISHGOURMET | B85975126 | 5/5 ✅ | OCR |

**Total día 21/12/2025: 117/119 facturas validadas (98%)**

---

## ⚠️ PROBLEMAS PENDIENTES

### Por tipo de error

| Error | Cantidad | Proveedores principales |
|-------|----------|------------------------|
| FECHA_PENDIENTE | ~35 | BM tickets, OPENAI, CELONIS |
| SIN_TOTAL | ~20 | LA PURISIMA, VIRGEN SIERRA |
| DESCUADRE | ~15 | PIFEMA, algunos tickets |
| CIF_PENDIENTE | ~10 | Proveedores nuevos |
| SIN_LINEAS | ~8 | GRUPO KUAI, LA LLEIDIRIA |

### Proveedores prioritarios para próxima sesión

| Proveedor | Facturas | Error | Impacto |
|-----------|----------|-------|---------|
| **JIMELUZ** | 14 | SIN_TOTAL/DESCUADRE | ALTO |
| **BM tickets** | 10 | FECHA_PENDIENTE | MEDIO |
| **PIFEMA** | 4 | DESCUADRE ~100€ | MEDIO |

### IBANs pendientes de recopilar

| Proveedor | NIF | Método pago |
|-----------|-----|-------------|
| JAIME FERNÁNDEZ MORENO | REDACTED_DNI | Transferencia |
| BENJAMÍN ORTEGA ALONSO | REDACTED_DNI | Transferencia |
| ALFARERÍA ÁNGEL Y LOLI | REDACTED_DNI | Transferencia |
| JULIO GARCIA VIVAS | REDACTED_DNI | Transferencia |
| WELLDONE LACTICOS | 27292516A | Transferencia |

---

## 📋 SESIONES ANTERIORES

### v4.3 - Sesión 20/12/2025
- +6 extractores: MANIPULADOS ABELLAN, LA ROSQUILLERIA, FABEIRO, KINEMA, SILVA CORDERO, ARTESANOS MOLLETE
- 38 facturas validadas

### v4.2 - Sesión 19/12/2025 tarde
- +6 extractores: ISTA, CVNE, QUESOS FELIX, MIGUEZ CAL, LAVAPIES, MARTIN ABENZA
- Bug IVA 0 corregido

### v4.1 - Sesión 19/12/2025 mañana
- BM refactorizado completo
- +4: ECOFICUS, SABORES PATERNA, LA BARRA DULCE

### v4.0 - Sesión 18/12/2025
- Arquitectura modular implementada
- Sistema @registrar funcionando

---

## 🔧 DECISIONES TÉCNICAS VIGENTES

1. **pdfplumber SIEMPRE** - Preferido sobre pypdf/PyPDF2
2. **OCR solo para escaneados** - Tesseract con pdf2image
3. **Híbrido cuando necesario** - Intenta pdfplumber, fallback OCR
4. **IVA 0 válido** - Para portes y conceptos exentos
5. **Formato europeo:** `_convertir_europeo()` para números con coma
6. **Tolerancia cuadre:** 0.10€
7. **1 artículo = 1 línea** - SIEMPRE líneas individuales
8. **Portes:** Distribuir proporcionalmente, nunca línea separada
9. **Registro automático:** Decorador `@registrar()` en cada extractor
10. **Archivos separados:** Cada proveedor complejo tiene su propio .py

---

## 📝 CHANGELOG

| Versión | Fecha | Cambios |
|---------|-------|---------|
| **v4.5** | **2025-12-21 PM** | **+8 extractores: JAIME FERNANDEZ, BENJAMIN ORTEGA, IBARRAKO, ANGEL LOLI, ABBATI, PANIFIESTO, JULIO GARCIA (híbrido), PRODUCTOS ADELL. Limpieza productos.py. 45 facturas validadas.** |
| v4.4 | 2025-12-21 AM | +12 extractores: ZUCCA, PANRUJE, DISBER, LIDL, ROSQUILLERIA, GADITAUN, DE LUIS, ABELLAN, ECOMS, MARITA COSTA, SERRIN, FISHGOURMET. 72 facturas validadas. |
| v4.3 | 2025-12-20 | +6 extractores OCR. 38 facturas. 60% cuadre. |
| v4.2 | 2025-12-19 tarde | +6 extractores. Bug IVA 0. 56% cuadre. |
| v4.1 | 2025-12-19 mañana | BM refactorizado. +4 extractores. |
| v4.0 | 2025-12-18 | Arquitectura modular. Sistema @registrar. |
| v3.5 | 2025-12-09 | Baseline: 42% cuadre. |

---

*Última actualización: 21/12/2025 PM - Sesión tarde 8 extractores*

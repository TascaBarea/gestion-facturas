# PROVEEDORES - Estado de Extractores

**Actualizado:** 01/01/2026 (noche) | **Versión:** v5.7

---

## 📊 RESUMEN

| Estado | Cantidad | % |
|--------|----------|---|
| ✅ Con extractor funcionando | **~145** | ~96% |
| ⚠️ Parcial/OCR | ~3 | 2% |
| ❌ Sin extractor | ~2 | 2% |
| **Total proveedores activos** | **~150** | 100% |

---

## ✅ SESIÓN 01/01/2026 NOCHE (1 corregido + 4 verificados)

| # | Proveedor | CIF | IBAN | Facturas | Método |
|---|-----------|-----|------|----------|--------|
| 1 | **LA ROSQUILLERIA** | B73814949 | - | ✅ | OCR |
| 2 | LA BARRA DULCE | B19981141 | REDACTED_IBAN | 9/9 ✅ | pdfplumber |
| 3 | CONSERVERA PREPIRINEO | F50765338 | ES78 2085 0871 6703 3009 9948 | 2/2 ✅ | pdfplumber |
| 4 | QUESOS CATI | F12499455 | REDACTED_IBAN | 3/3 ✅ | pdfplumber |
| 5 | TIRSO PAPEL Y BOLSAS | B86005006 | - | ⚠️ OCR | OCR (malo) |

### Características especiales

| Proveedor | IVA | Peculiaridad |
|-----------|-----|--------------|
| **LA ROSQUILLERIA** | **10%/0%** | ⚠️ **CORREGIDO:** IVA era 4%, ahora 10%. Portes IVA 0% en línea separada. OCR con preprocesamiento. |
| LA BARRA DULCE | 10% | Pastelería artesanal (bizcochos, galletas) |
| CONSERVERA PREPIRINEO | 10% | Conservas vegetales aragonesas |
| QUESOS CATI | 4% | Quesos de cabra de Castellón. Cuadro fiscal. |
| TIRSO PAPEL Y BOLSAS | 21% | OCR muy malo. Requiere revisión manual. |

### Corrección LA ROSQUILLERIA

**Problema anterior:**
- IVA asumido: 4% (incorrecto)
- Portes prorrateados (causaba descuadre)
- Método: TOTAL / 1.04

**Solución v5.7:**
- IVA productos: **10%** (rosquillas = alimentación elaborada)
- Portes: **0%** (línea separada)
- Método: OCR + cuadro fiscal + líneas individuales

---

## ✅ SESIÓN 01/01/2026 MAÑANA (1 nuevo + 1 verificado)

| # | Proveedor | CIF | IBAN | Facturas | Método |
|---|-----------|-----|------|----------|--------|
| 1 | **BM SUPERMERCADOS** | B20099586 | N/A (tarjeta) | 6/6 ✅ | pdfplumber |
| 2 | FELISA GOURMET | B72113897 | REDACTED_IBAN | 13/13 ✅ | pdfplumber |

### Características especiales

| Proveedor | IVA | Peculiaridad |
|-----------|-----|--------------|
| **BM SUPERMERCADOS** | 4%/10%/21% | ⚠️ **Tickets con IVA incluido** - Conversión a base. IVA deducido por reglas: producto > sección > diccionario. |
| FELISA GOURMET | 10%/21% | Conservas premium Barbate. 10% productos, 21% transporte (8,30€ fijo). |

---

## ✅ SESIÓN 31/12/2025 (1 nuevo + 2 mejorados)

| # | Proveedor | CIF | IBAN | Facturas | Método |
|---|-----------|-----|------|----------|--------|
| 1 | **DISTRIBUCIONES LAVAPIES** | F88424072 | ES39 3035 0376 14 3760011213 | 13/13 ✅ | pdfplumber |
| 2 | BODEGAS MUÑOZ MARTIN | E83182683 | REDACTED_IBAN | 4/4 ✅ | **híbrido** |
| 3 | LOS GREDALES | B83594150 | REDACTED_IBAN | 5/5 ✅ | pdfplumber |

### Características especiales

| Proveedor | IVA | Peculiaridad |
|-----------|-----|--------------|
| **LAVAPIES** | 10%/21% | ⚠️ **IVA deducido de factura** - Algoritmo subset-sum para determinar IVA. |
| BODEGAS MUÑOZ | 21% | **Híbrido pdfplumber+OCR** - Algunas facturas escaneadas |
| LOS GREDALES | 21% | Líneas individuales con categorías (SAUVIGNON, SYRAH...) |

---

## 🔴 PENDIENTES PRIORITARIOS

| # | Proveedor | Errores | Tipo | Impacto |
|---|-----------|---------|------|---------|
| 1 | ~~BM SUPERMERCADOS~~ | ~~37~~ | ~~DESCUADRE~~ | ✅ HECHO |
| 2 | **JIMELUZ** | 19 | OCR | ALTO |
| 3 | ~~LA ROSQUILLERIA~~ | ~~10~~ | ~~OCR~~ | ✅ HECHO |
| 4 | **DIA** | 6+ | SIN_LINEAS | MEDIO |
| 5 | **JAMONES BERNAL** | 6 | DESCUADRE | BAJO |
| 6 | **QUESOS ROYCA** | 3 | SIN_LINEAS | BAJO |

---

## 📋 EXTRACTORES POR ARCHIVO (Sesiones recientes)

### Sesión 01/01/2026 noche
| Archivo | Proveedor | CIF | Estado |
|---------|-----------|-----|--------|
| `la_rosquilleria.py` | LA ROSQUILLERIA | B73814949 | **CORREGIDO** |
| `main.py` | (aliases TIRSO, CONSERVERA, BARRA DULCE) | - | v5.7 |
| `__init__.py` | (imports actualizados) | - | v5.7 |
| `settings.py` | (VERSION) | - | v5.7 |

### Sesión 01/01/2026 mañana
| Archivo | Proveedor | CIF |
|---------|-----------|-----|
| `bm.py` | BM SUPERMERCADOS | B20099586 |
| `felisa.py` | FELISA GOURMET (actualizado) | B72113897 |

### Sesión 31/12/2025
| Archivo | Proveedor | CIF |
|---------|-----------|-----|
| `lavapies.py` | DISTRIBUCIONES LAVAPIES | F88424072 |
| `bodegas_munoz.py` | BODEGAS MUÑOZ MARTIN | E83182683 |
| `gredales.py` | LOS GREDALES DE EL TOBOSO | B83594150 |

---

## 🔧 VARIANTES DE NOMBRES REGISTRADAS (nuevos)

| Extractor | Variantes en @registrar() |
|-----------|--------------------------|
| LA ROSQUILLERIA | LA ROSQUILLERIA, ROSQUILLERIA, EL TORRO, ROSQUILLAS EL TORRO |
| LA BARRA DULCE | LA BARRA DULCE, BARRA DULCE, LA BARRA DULCE S.L. |
| CONSERVERA PREPIRINEO | LA CONSERVERA DEL PREPIRINEO, CONSERVERA PREPIRINEO, CONSERVERA DEL PREPIRINEO |
| QUESOS CATI | QUESOS DEL CATI, QUESOS DE CATI, QUESOS CATI, CATI |
| TIRSO | TIRSO PAPEL Y BOLSAS, TIRSO, TIRSO PAPEL, BOLSAS TIRSO |
| BM SUPERMERCADOS | BM SUPERMERCADOS, BM, DISTRIBUCION SUPERMERCADOS |

---

## 📝 CHANGELOG PROVEEDORES

| Fecha | Cambio |
|-------|--------|
| **01/01/2026 noche** | **LA ROSQUILLERIA corregido (IVA 10%), +4 verificados (BARRA DULCE, CONSERVERA, CATI, TIRSO)** |
| 01/01/2026 mañana | +BM SUPERMERCADOS (IVA incluido→base), FELISA verificado |
| 31/12/2025 | +LAVAPIES (IVA deducido de factura), MUÑOZ OCR, GREDALES líneas |
| 30/12/2025 | DE LUIS, ALFARERIA, PORVAZ corregidos. +INMAREPRO |
| 29/12/2025 | Bugs: DEBORA, FELISA, HERNÁNDEZ, SILVA. Fix base.py |
| 28/12/2025 | +6: ECOMS, VIRGEN, MARITA, CASA DUQUE, CELONIS, PIFEMA |
| 26/12/2025 | +16: YOIGO, SOM, OPENAI, ANTHROPIC, BIELLEBI... |

---

*Última actualización: 01/01/2026 (noche)*

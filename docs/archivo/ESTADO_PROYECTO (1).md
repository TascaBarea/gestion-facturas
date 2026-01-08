# 📊 ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 03/01/2026 (noche)  
**Versión actual:** v5.9  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas

---

## 🎯 MÉTRICAS ACTUALES

### Resultados v5.9 (03/01/2026)

| Métrica | Valor |
|---------|-------|
| **Tasa de éxito** | **~60%** |
| **Extractores totales** | ~83 |
| **Facturas analizadas** | 937 (4 trimestres) |
| **Proveedores únicos** | 93 |
| **Artículos en diccionario** | ~925 |

**Objetivo:** 80% cuadre OK

### Desglose por trimestre (último conocido)

| Trimestre | Facturas | OK | % |
|-----------|----------|-----|---|
| 1T25 | 252 | 188 | **74.6%** ⭐ |
| 2T25 | 307 | 183 | 59.6% |
| 3T25 | 161 | 99 | 61.5% |
| 4T25 | 217 | 156 | **71.9%** |
| **TOTAL** | **937** | **626** | **~67%** |

### Evolución histórica

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.0 | 26/12/2025 | 54% | Normalización + prorrateo portes |
| v5.5 | 01/01/2026 | ~62% | +BM SUPERMERCADOS, FELISA verificado |
| v5.7 | 01/01/2026 | ~66% | +LA ROSQUILLERIA corregido (IVA 10%) |
| v5.8 | 02/01/2026 | ~66% | Nueva hoja Facturas (cabeceras) |
| **v5.9** | **03/01/2026** | **~67%** | **Fix categoria_fija, +PRAIZAL, +FISHGOURMET** |

---

## ✅ SESIONES RECIENTES

### 03/01/2026 (noche) - Sesión actual v5.9

| Módulo | Cambio | Estado |
|--------|--------|--------|
| **main.py** | Fix categoria_fija como fallback | ✅ LISTO |
| **praizal.py** | Nuevo extractor (Quesos) | ✅ LISTO |
| **fishgourmet.py** | Categoría corregida a SALAZONES | ✅ LISTO |
| **7 extractores** | Añadido categoria_fija | ✅ LISTO |
| **EXTRACTORES_COMPLETO.xlsx** | Análisis 93 proveedores | ✅ LISTO |

**Problema pendiente:** SIN_PROVEEDOR sigue apareciendo (posible caché)

### 02/01/2026 (noche) - v5.8
| Módulo | Cambio | Estado |
|--------|--------|--------|
| **salidas/excel.py** | Nueva hoja "Facturas" (cabeceras) | ✅ LISTO |
| **salidas/excel.py** | Integración DiccionarioEmisorTitulo.xlsx | ✅ LISTO |

### 01/01/2026 (noche) - v5.7
| Extractor | CIF | Facturas | Estado |
|-----------|-----|----------|--------|
| **LA ROSQUILLERIA** | B73814949 | 10+ | **CORREGIDO - IVA 10%** |
| LA BARRA DULCE | B19981141 | 9/9 ✅ | Verificado |

---

## ⚠️ PROVEEDORES PRIORITARIOS (PRÓXIMA SESIÓN)

### 🔴 TOP 10 por impacto

| # | Proveedor | Errores | Tipo | Dificultad |
|---|-----------|---------|------|------------|
| 1 | ~~BM SUPERMERCADOS~~ | ~~37~~ | ~~DESCUADRE~~ | ✅ HECHO |
| 2 | **JIMELUZ** | 21 | OCR | 🔴 Alta |
| 3 | ~~LA ROSQUILLERIA~~ | ~~10~~ | ~~OCR~~ | ✅ HECHO |
| 4 | **DIA/ECOMS** | 17 | SIN_LINEAS | 🟡 Media |
| 5 | **MARITA COSTA** | 8 | DESCUADRE | 🟡 Media |
| 6 | **JAMONES BERNAL** | 6 | DESCUADRE | 🟡 Media |
| 7 | **LA ROSQUILLERIA** | 7 | SIN_LINEAS | 🟡 Media |
| 8 | EMJAMESA | 4 | DESCUADRE | 🟡 Media |
| 9 | QUESOS ROYCA | 3 | SIN_LINEAS | 🟡 Media |
| 10 | ZUCCA | 3 | DESCUADRE | 🟡 Media |

### 🔴 CRÍTICO - Resolver mañana
**Problema SIN_PROVEEDOR**: categoria_fija no se aplica correctamente
- Verificar caché en TODAS las carpetas
- Verificar main.py tiene el fix (líneas 745-758)

---

## 📦 EXTRACTORES CON CATEGORIA_FIJA

Total: **38 extractores HARDCODED**

| Extractor | Categoría |
|-----------|-----------|
| abbati.py | CAFE |
| angel_loli.py | CACHARRERIA |
| anthropic.py | GASTOS VARIOS |
| artesanos_mollete.py | PAN Y BOLLERIA |
| benjamin_ortega.py | ALQUILER LOCAL |
| celonis_make.py | GASTOS VARIOS |
| conservera_prepirineo.py | CONSERVAS VEGETALES |
| de_luis.py | QUESOS |
| debora_garcia.py | Co2 GAS PARA LA CERVEZA |
| fishgourmet.py | SALAZONES |
| gredales.py | VINOS |
| hernandez.py | MENAJE |
| ibarrako.py | PIPARRAS |
| inmarepro.py | GASTOS VARIOS |
| ista.py | CONSUMO AGUA FRIA |
| jaime_fernandez.py | ALQUILER LOCAL |
| julio_garcia.py | GENERICO PARA VERDURAS |
| kinema.py | GESTORIA |
| la_barra_dulce.py | PASTELERIA |
| la_rosquilleria.py | ROSQUILLAS MARINERAS |
| manipulados_abellan.py | CONSERVAS VEGETALES |
| marita_costa.py | GOURMET |
| martin_abenza.py | CONSERVAS |
| openai.py | GASTOS VARIOS |
| pablo_ruiz_la_dolorosa.py | FERMENTOS |
| panifiesto.py | PAN |
| panruje.py | ROSQUILLAS MARINERAS |
| pilar_rodriguez.py | HUEVOS |
| praizal.py | QUESOS |
| segurma.py | ALARMA |
| serrin_no_chan.py | ULTRAMARINOS GALLEGOS |
| som_energia.py | ELECTRICIDAD |
| territorio_campero.py | PATATAS FRITAS APERITIVO |
| tirso_papel_bolsas.py | PAPELERIA Y EMBALAJE |
| trucco.py | OTROS GASTOS |
| webempresa.py | GASTOS VARIOS |
| welldone.py | QUESOS |
| yoigo.py | TELEFONO Y COMUNICACIONES |

---

## 🔧 TÉCNICAS IMPLEMENTADAS

| Técnica | Proveedores | Descripción |
|---------|-------------|-------------|
| **IVA incluido → Base** | BM | Conversión: base = importe / (1 + tipo/100) |
| **IVA deducido de factura** | LAVAPIES | Subset-sum para detectar qué productos van a cada IVA |
| **Reglas IVA por sección** | BM | FRUTERÍA→4%, CARNICERÍA→10%, DROGUERÍA→21% |
| **OCR híbrido** | MUÑOZ, ECOMS, VIRGEN | pdfplumber + Tesseract fallback |
| **Líneas separadas por IVA** | LA ROSQUILLERIA | Productos 10% + Portes 0% |
| **Prorrateo portes** | Todos | Portes distribuidos proporcionalmente |
| **categoria_fija fallback** | 38 extractores | main.py usa categoria_fija si línea no tiene categoría |
| **Hoja cabeceras** | v5.8 | Una fila por factura con CUENTA/TITULO |

---

## 📈 PROYECCIÓN

| Escenario | Tasa | Facturas OK |
|-----------|------|-------------|
| **Actual (v5.9)** | **~67%** | **~626** |
| + Resolver SIN_PROVEEDOR | ~68% | ~637 |
| + DIA/ECOMS + JIMELUZ | ~72% | ~675 |
| **OBJETIVO** | **80%** | **~750** |

---

## 📋 TAREAS PENDIENTES

### Inmediato (mañana)
- [ ] **CRÍTICO: Resolver SIN_PROVEEDOR** (limpiar todos los cachés)
- [ ] Verificar fix categoria_fija funciona
- [ ] Actualizar DiccionarioEmisorTitulo.xlsx (40 proveedores pendientes)

### Corto plazo
- [ ] DIA/ECOMS (17 errores)
- [ ] JIMELUZ (OCR - 21 errores)
- [ ] MARITA COSTA (8 errores)
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
| **03/01/2026 noche** | **v5.9** | **+1 nuevo, +7 actualizados** | **Fix categoria_fija, PRAIZAL, FISHGOURMET** |
| 02/01/2026 noche | v5.8 | excel.py actualizado | Nueva hoja Facturas, integración cuentas |
| 01/01/2026 noche | v5.7 | +1 corregido, +4 verificados | LA ROSQUILLERIA (IVA 10%), aliases |
| 01/01/2026 mañana | v5.5 | +1 nuevo, +1 verificado | BM (IVA deducido), FELISA |
| 31/12/2025 | v5.4 | +1 nuevo, +2 mejorados | LAVAPIES, MUÑOZ OCR, GREDALES |
| 30/12/2025 | v5.3+ | +4 corregidos | DE LUIS, ALFARERIA, PORVAZ, INMAREPRO |

---

*Actualizado: 03/01/2026 (noche)*

# ESTADO DEL PROYECTO - ParsearFacturas

**Última actualización:** 04/01/2026 (noche)  
**Versión actual:** v5.11  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas

---

## MÉTRICAS ACTUALES

### Resultados v5.11 (04/01/2026)

| Métrica | Valor |
|---------|-------|
| **Tasa de éxito** | **~69%** |
| **Extractores totales** | ~88 |
| **Facturas analizadas** | 949 (4 trimestres) |
| **Proveedores únicos** | 91 |
| **Cobertura IBANs** | **100%** (para transferencias) |

**Objetivo:** 80% cuadre OK

### Desglose por trimestre

| Trimestre | Facturas | OK | % |
|-----------|----------|-----|---|
| 1T25 | 252 | 191 | **75.8%** |
| 2T25 | 307 | 186 | 60.6% |
| 3T25 | 161 | 106 | 65.8% |
| 4T25 | 229 | 173 | **75.5%** |
| **TOTAL** | **949** | **656** | **~69%** |

### Cobertura IBANs

| Forma de pago | Proveedores | Con IBAN | % |
|---------------|-------------|----------|---|
| TRANSFERENCIA | 89 | 89 | **100%** |
| TARJETA | 1 | N/A | No necesita |
| RECIBO | 1 | N/A | No necesita |

---

## SESIÓN 04/01/2026

### Extractores nuevos creados

| Extractor | CIF | Categoría | Estado |
|-----------|-----|-----------|--------|
| **ALCAMPO** | A28581882 | Diccionario | OK 4/4 |
| **ANA CABALLO** | B87925970 | LICORES Y VERMUS | OK 3/3 |
| **CONTROLPLAGA** | REDACTED_DNI | DESINSECTACION | OK 2/2 |
| **EMBUTIDOS FERRIOL** | B57955098 | CHACINAS | OK 1T25 |
| **LA LLEIDIRIA** | B42953455 | QUESOS | Pendiente verificar |

### Mejoras en main.py v5.11

| Característica | Descripción |
|----------------|-------------|
| **Limpieza auto __pycache__** | Ya no hay que hacerlo manual |
| **Soporte OCR** | metodo_pdf='ocr' para escaneados |
| **Soporte JPG/PNG** | Busca imágenes además de PDF |
| **Fix doble IVA** | Corregido en bernal.py |

### Bug crítico corregido

**Problema:** Filtro `'CANT' in 'PICANTE'` = True - filtraba productos válidos

```python
# ANTES (buggy):
if any(x in descripcion.upper() for x in ['CANT', ...]):

# DESPUÉS (corregido):
palabras = descripcion.upper().split()
if any(x in palabras for x in ['CANT', ...]):
```

### Herramientas creadas

| Script | Función |
|--------|---------|
| `arreglar_codificacion.py` | Corrige UTF-8 corrupto en extractores |
| `verificar_codificacion.py` | Detecta archivos con problemas |
| `revisar_filtros.py` | Detecta filtros problemáticos |

---

## EVOLUCIÓN HISTÓRICA

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.0 | 26/12/2025 | 54% | Normalización + prorrateo portes |
| v5.7 | 01/01/2026 | ~66% | LA ROSQUILLERIA corregido |
| v5.9 | 03/01/2026 | ~67% | Fix categoria_fija, +PRAIZAL |
| v5.10 | 04/01/2026 | ~68% | SIN_EXTRACTOR vs SIN_CATEGORIA |
| **v5.11** | **04/01/2026** | **~69%** | **+5 extractores, OCR, limpieza cache auto** |

---

## PROVEEDORES PRIORITARIOS

### TOP por impacto (pendientes)

| # | Proveedor | Errores | Tipo | Estado |
|---|-----------|---------|------|--------|
| 1 | **MARITA COSTA** | 10 | DESCUADRE | Pendiente |
| 2 | **QUESERIA ZUCCA** | 8 | DESCUADRE | Pendiente |
| 3 | **JAMONES BERNAL** | 6 | DESCUADRE | Pendiente |
| 4 | **JIMELUZ** | 21 | OCR | Pendiente |
| 5 | **LA LLEIDIRIA** | 2 | OCR | Verificar |

---

## TAREAS PENDIENTES

### Próxima sesión
- [ ] Ejecutar `arreglar_codificacion.py` (si hay extractores nuevos)
- [ ] Verificar LA LLEIDIRIA funciona con OCR
- [ ] Ejecutar main.py completo en 4 trimestres

### Corto plazo
- [ ] MARITA COSTA (10 descuadres - portes)
- [ ] QUESERIA ZUCCA (8 descuadres - redondeo)
- [ ] JAMONES BERNAL (6 descuadres)
- [ ] Llegar a **72%** cuadre OK

### Medio plazo
- [ ] JIMELUZ (21 errores OCR)
- [ ] DIA/ECOMS (17 SIN_LINEAS)
- [ ] Llegar a **80%** cuadre OK

---

## TÉCNICAS IMPLEMENTADAS

| Técnica | Descripción |
|---------|-------------|
| **Limpieza auto cache** | main.py limpia __pycache__ al inicio |
| **OCR híbrido** | pdfplumber + Tesseract fallback |
| **Soporte imágenes** | JPG, PNG además de PDF |
| **Filtro palabras completas** | .split() antes de buscar |
| **categoria_fija fallback** | main.py usa categoria_fija |
| **Corrección codificación** | arreglar_codificacion.py |

---

## PROYECCIÓN

| Escenario | Tasa | Facturas OK |
|-----------|------|-------------|
| **Actual (v5.11)** | **~69%** | **~656** |
| + MARITA COSTA | ~70% | ~665 |
| + ZUCCA + BERNAL | ~72% | ~684 |
| **OBJETIVO** | **80%** | **~760** |

---

*Actualizado: 04/01/2026 (noche)*

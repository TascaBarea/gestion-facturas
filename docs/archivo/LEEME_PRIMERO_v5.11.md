# LEEME PRIMERO - ParsearFacturas

**Versión:** v5.11  
**Fecha:** 04/01/2026  
**Autor:** Tasca Barea + Claude  

---

## IMPORTANTE - LEER ANTES DE CONTINUAR

### Estado actual (04/01/2026 noche)

**Versión v5.11 incluye:**
```
- Limpieza automática de __pycache__ (ya no hay que hacerlo manual)
- Soporte OCR para facturas escaneadas
- Soporte JPG/PNG además de PDF
- 5 extractores nuevos: ALCAMPO, ANA CABALLO, CONTROLPLAGA, FERRIOL, LLEIDIRIA
- Bug CANT corregido (filtro palabras completas)
- 100% cobertura IBANs para transferencias
```

### AL INICIO DE SESIÓN

**Ya NO necesitas limpiar caché manualmente** - main.py lo hace automáticamente.

Solo ejecuta:
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# Si hay extractores nuevos descargados de Claude:
python arreglar_codificacion.py

# Ejecutar
python main.py
```

---

## ESTADO ACTUAL (04/01/2026)

| Trimestre | Facturas | Cuadre OK | % |
|-----------|----------|-----------|---|
| 1T25 | 252 | 191 | **75.8%** |
| 2T25 | 307 | 186 | 60.6% |
| 3T25 | 161 | 106 | 65.8% |
| 4T25 | 229 | 173 | **75.5%** |
| **TOTAL** | **949** | **656** | **~69%** |

**Objetivo:** 80% cuadre OK

### Cobertura IBANs

| Tipo | Proveedores | Con IBAN |
|------|-------------|----------|
| TRANSFERENCIA | 89 | **100%** |
| TARJETA/RECIBO | 2 | No necesitan |

---

## CARACTERÍSTICAS v5.11

| Característica | Descripción |
|----------------|-------------|
| **Limpieza auto cache** | Ya no hay que hacer rmdir manual |
| **Soporte OCR** | Para facturas escaneadas (metodo_pdf='ocr') |
| **Soporte imágenes** | Procesa JPG, PNG además de PDF |
| **categoria_fija** | Fallback automático si línea no tiene categoría |

---

## HERRAMIENTAS DISPONIBLES

| Script | Función | Cuándo usar |
|--------|---------|-------------|
| `arreglar_codificacion.py` | Corrige UTF-8 corrupto | Después de añadir extractores de Claude |
| `verificar_codificacion.py` | Detecta problemas | Diagnóstico |
| `revisar_filtros.py` | Detecta filtros buggy | Prevención |

---

## PROBLEMA CONOCIDO: Codificación UTF-8

Al descargar archivos de Claude, los caracteres especiales se corrompen.

**Solución:** Ejecutar `python arreglar_codificacion.py`

---

## PRÓXIMA SESIÓN - PRIORIDADES

### ALTA PRIORIDAD
| Proveedor | Descuadres | Causa probable |
|-----------|------------|----------------|
| MARITA COSTA | 10 | Portes no incluidos |
| QUESERIA ZUCCA | 8 | Redondeo IVA |
| JAMONES BERNAL | 6 | Portes/redondeo |

### MEDIA PRIORIDAD
- JIMELUZ (21 errores OCR)
- DIA/ECOMS (17 SIN_LINEAS)

---

## REGLA CRÍTICA: Filtros con palabras completas

```python
# MAL - subcadenas
if 'CANT' in descripcion.upper():  # Filtra 'PICANTE'!

# BIEN - palabras completas
palabras = descripcion.upper().split()
if 'CANT' in palabras:
```

---

## HISTORIAL

| Fecha | Versión | Cambios |
|-------|---------|---------|
| **04/01/2026** | **v5.11** | **+5 extractores, OCR, cache auto, 100% IBANs** |
| 03/01/2026 | v5.9 | Fix categoria_fija, +PRAIZAL |
| 02/01/2026 | v5.8 | Nueva hoja Facturas |
| 01/01/2026 | v5.7 | LA ROSQUILLERIA (IVA 10%) |

---

*Última actualización: 04/01/2026 (noche)*

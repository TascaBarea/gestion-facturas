# 📖 LEEME PRIMERO - ParsearFacturas

**Versión:** v5.10  
**Fecha:** 04/01/2026  
**Autor:** Tasca Barea + Claude  

---

## ⚠️ IMPORTANTE - LEER ANTES DE CONTINUAR

### Estado actual (04/01/2026 noche)

**Última sesión - 5 extractores nuevos + bug crítico corregido:**
```
alcampo.py                       # NUEVO - Supermercado (diccionario IVA)
ana_caballo.py                   # NUEVO - Licores y vermus
controlplaga.py                  # NUEVO - Desinsectación
embutidos_ferriol.py             # NUEVO + CORREGIDO (bug CANT)
la_lleidiria.py                  # NUEVO - Quesería (OCR)
hernandez.py                     # CORREGIDO (bug CANT)
arreglar_codificacion.py         # HERRAMIENTA - Corrige UTF-8
```

### ⚠️ ACCIÓN REQUERIDA AL INICIO

**Ejecutar SIEMPRE antes de trabajar:**
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# 1. Limpiar caché
rmdir /s /q extractores\__pycache__
rmdir /s /q __pycache__

# 2. Corregir codificación (si hay extractores nuevos)
python arreglar_codificacion.py

# 3. Verificar extractores
python -c "from extractores import listar_extractores; print(len(listar_extractores()), 'extractores')"
```

Debe mostrar: **~88 extractores**

---

## 📊 ESTADO ACTUAL (04/01/2026)

| Trimestre | Facturas | Cuadre OK | % |
|-----------|----------|-----------|---|
| 1T25 | 252 | 191 | **75.8%** ⭐ |
| 2T25 | 307 | 186 | 60.6% |
| 3T25 | 161 | 106 | 65.8% |
| 4T25 | 229 | 173 | **75.5%** |
| **TOTAL** | **949** | **656** | **~69%** |

**Objetivo:** 80% cuadre OK

---

## 🔧 HERRAMIENTAS NUEVAS (04/01/2026)

| Script | Función | Cuándo usar |
|--------|---------|-------------|
| `arreglar_codificacion.py` | Corrige caracteres UTF-8 corruptos | **Después de añadir extractores** |
| `verificar_codificacion.py` | Detecta archivos con problemas | Diagnóstico |
| `revisar_filtros.py` | Detecta filtros problemáticos | Prevención bugs |

---

## ⚠️ PROBLEMA CONOCIDO: Codificación UTF-8

Al descargar archivos de Claude, los caracteres especiales se corrompen (`€` → `â‚¬`)

**Solución:** Ejecutar `python arreglar_codificacion.py`

---

## 📋 PRÓXIMA SESIÓN - PRIORIDADES

### 🔴 INMEDIATO
1. Ejecutar `arreglar_codificacion.py`
2. Verificar LA LLEIDIRIA funciona (2/2 OK)
3. Ejecutar main.py completo

### 🔴 ALTA PRIORIDAD
| Proveedor | Descuadres | Causa probable |
|-----------|------------|----------------|
| MARITA COSTA | 10 | Portes no incluidos |
| QUESERIA ZUCCA | 8 | Redondeo IVA |
| JAMONES BERNAL | 6 | Portes/redondeo |

### 🟡 MEDIA PRIORIDAD
- JIMELUZ (21 errores OCR)
- DIA/ECOMS (17 SIN_LINEAS)

---

## 📚 REGLAS CRÍTICAS

### Filtros con palabras completas (bug corregido hoy)

```python
# ❌ MAL - subcadenas
if 'CANT' in descripcion.upper():  # Filtra 'PICANTE'!

# ✅ BIEN - palabras completas
palabras = descripcion.upper().split()
if 'CANT' in palabras:
```

---

## 🗂️ HISTORIAL

| Fecha | Versión | Cambios |
|-------|---------|---------|
| **04/01/2026** | **v5.10** | **+5 extractores, bug CANT, herramientas UTF-8** |
| 03/01/2026 | v5.9 | Fix categoria_fija, +PRAIZAL |
| 02/01/2026 | v5.8 | Nueva hoja Facturas |
| 01/01/2026 | v5.7 | LA ROSQUILLERIA (IVA 10%) |

---

*Última actualización: 04/01/2026 (noche)*

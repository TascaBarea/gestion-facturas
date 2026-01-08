# 🔍 ANÁLISIS TÉCNICO DEFINITIVO
## ParsearFacturas - Estado Enero 2026
### Por: Claude (Analista Senior IT)

**Fecha:** 02/01/2026  
**Versión analizada:** v5.7 (main.py) / v5.8 (excel.py pendiente integrar)  
**Dedicación del desarrollador:** ~20 horas/semana

---

## 📊 RESUMEN EJECUTIVO

| Métrica | Valor | Objetivo |
|---------|-------|----------|
| **Tasa de éxito** | 66% | 80% |
| **Extractores únicos** | 87 archivos | - |
| **Facturas procesadas** | 937 (4 trimestres) | - |
| **Gap para objetivo** | +14 puntos | ~131 facturas más |

### Veredicto: 🟡 PROYECTO FUNCIONAL CON DEUDA TÉCNICA ACUMULADA

El sistema funciona y procesa facturas, pero ha crecido de forma orgánica acumulando inconsistencias que frenan el progreso. **El 80% es alcanzable**, pero requiere un cambio de enfoque: menos extractores nuevos, más consolidación.

---

## 🔴 PUNTOS DÉBILES CRÍTICOS

### 1. IMPORTS DUPLICADOS EN `__init__.py`

**Problema:** 4 extractores están importados 2 veces:
- `zucca` (líneas ~103 y ~229)
- `gaditaun` (líneas ~110 y ~360)
- `ecoms` (líneas ~111 y ~345)
- `fabeiro` (líneas ~112 y ~211)

**Impacto:** 
- El segundo import sobrescribe al primero
- Si las versiones difieren, comportamiento impredecible
- Dificulta saber qué versión está activa

**Solución:** Eliminar imports duplicados. Dejar solo la versión más reciente.

**Esfuerzo:** 15 minutos

---

### 2. ARQUITECTURA HÍBRIDA CONFUSA

**Problema:** Coexisten dos patrones de organización:

| Patrón | Ejemplo | Problema |
|--------|---------|----------|
| **Archivos agrupadores** | `vinos.py`, `quesos.py`, `servicios.py` | Difícil encontrar un extractor específico |
| **Archivos individuales** | `zucca.py`, `lidl.py`, `bm.py` | Inconsistente con lo anterior |

**Impacto:**
- No sabes dónde buscar un extractor
- Riesgo de crear duplicados sin darte cuenta
- El `__init__.py` tiene 400+ líneas de imports

**Solución:** Migrar TODO a archivos individuales (1 proveedor = 1 archivo). Eliminar agrupadores.

**Esfuerzo:** 4-6 horas (una sola vez)

---

### 3. VERSIONES DESINCRONIZADAS

**Problema:**
- `main.py` dice v5.7
- `excel.py` nuevo es v5.8
- `settings.py` tiene VERSION = ?
- Documentación dice v5.8

**Impacto:**
- Confusión sobre qué está desplegado
- Difícil reproducir errores
- No hay forma de saber si un fix está activo

**Solución:** 
1. Centralizar VERSION en `config/settings.py`
2. Que `main.py` lo importe y lo muestre
3. Incrementar versión en cada sesión de trabajo

**Esfuerzo:** 30 minutos

---

### 4. EXCEL.PY v5.8 NO INTEGRADO

**Problema:** La nueva hoja "Facturas" con cabeceras está desarrollada pero no desplegada.

**Impacto:**
- El trabajo de la sesión 02/01 no está en producción
- No se puede verificar si funciona con datos reales
- Bloquea el progreso hacia la integración con gestoría

**Solución:** Integrar HOY. Pasos:
```cmd
copy excel.py C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\salidas\
rmdir /s /q C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\salidas\__pycache__
```

**Esfuerzo:** 5 minutos + prueba

---

### 5. DiccionarioEmisorTitulo.xlsx INCOMPLETO

**Problema:** 40 proveedores (~18%) sin CUENTA asignada.

**Impacto:**
- La nueva hoja "Facturas" mostrará "PENDIENTE" en esos casos
- No se puede cuadrar con contabilidad automáticamente

**Solución:** Completar el mapeo de los 40 proveedores faltantes.

**Esfuerzo:** 1-2 horas (trabajo manual)

---

### 6. PROVEEDORES PROBLEMÁTICOS ENQUISTADOS

**Problema:** Los mismos proveedores llevan semanas/meses en la lista de pendientes:

| Proveedor | Errores | Desde cuándo | Por qué no avanza |
|-----------|---------|--------------|-------------------|
| JIMELUZ | 21 | Diciembre | OCR muy malo, no prioritario |
| DIA/ECOMS | 17 | Diciembre | Requiere extractor nuevo |
| RETENCIONES | 16 | Diciembre | Ya corregido pero no integrado |
| MARITA COSTA | 8 | Diciembre | Descuadres complejos |

**Impacto:**
- Sensación de estancamiento
- El 80% parece inalcanzable
- Recursos desperdiciados revisando lo mismo

**Solución:** Tomar decisiones definitivas:
- JIMELUZ → **Aparcar** (no prioritario según tú)
- DIA/ECOMS → **Crear extractor simple** (quick win)
- RETENCIONES → **Integrar el fix existente**
- MARITA COSTA → **Analizar 1 factura a fondo**

**Esfuerzo:** 2-3 horas para cerrar estos 4

---

## 🟡 PUNTOS DÉBILES MODERADOS

### 7. Sin tests automatizados

**Problema:** No hay forma de verificar que un cambio no rompe extractores existentes.

**Impacto:** Miedo a refactorizar. Bugs que reaparecen.

**Solución:** Crear carpeta `tests/facturas_ejemplo/` con 1 PDF por proveedor crítico y un script que verifique que el cuadre sigue siendo OK.

**Esfuerzo:** 4-6 horas (pero ahorra tiempo futuro)

---

### 8. Logging insuficiente

**Problema:** Cuando algo falla, el log dice "DESCUADRE_0.15" pero no dice POR QUÉ.

**Impacto:** Debug manual mirando PDFs uno a uno.

**Solución:** Añadir modo `--debug` que muestre:
- Texto extraído del PDF
- Líneas detectadas con importes
- Cálculo del cuadre paso a paso

**Esfuerzo:** 2-3 horas

---

### 9. Flujo Gmail → SEPA no conectado

**Problema:** Cada componente funciona aislado:
- Gmail extractor: Implementado pero no usado
- ParsearFacturas: Funcionando
- Generador SEPA: Prototipo listo
- Pero **no hay orquestador** que los una

**Impacto:** Todo sigue siendo manual.

**Solución:** Crear `flujo_semanal.py` que:
1. Descargue facturas de Gmail
2. Las procese con ParsearFacturas
3. Genere borrador de pagos
4. (Opcional) Genere SEPA

**Esfuerzo:** 8-12 horas

---

## ✅ PUNTOS FUERTES

| Fortaleza | Descripción |
|-----------|-------------|
| **Limpieza de caché** | El problema de `__pycache__` está resuelto en main.py |
| **Sistema de registro** | `@registrar()` funciona bien |
| **Prorrateo de portes** | Implementado correctamente |
| **Soporte retenciones** | IRPF 19% manejado |
| **Alias extensos** | 50+ mapeos para normalizar nombres |
| **Dedicación** | 20h/semana es suficiente para avanzar bien |

---

## 🎯 ESTRATEGIA RECOMENDADA

### Opción A: "CONSOLIDAR PRIMERO" (Recomendada ⭐)

**Filosofía:** Antes de añadir más extractores, arreglar la base.

**Semana 1-2:**
1. ✅ Integrar excel.py v5.8
2. ✅ Eliminar imports duplicados en `__init__.py`
3. ✅ Completar DiccionarioEmisorTitulo (40 proveedores)
4. ✅ Integrar fix de RETENCIONES (ya hecho)
5. ✅ Crear extractor simple para DIA/ECOMS

**Resultado esperado:** 70-72% (+4-6 puntos)

**Semana 3-4:**
6. Migrar archivos agrupadores a individuales
7. Crear tests básicos (10 proveedores críticos)
8. Resolver MARITA COSTA (8 facturas)
9. Resolver LAVAPIES 3T (4 facturas)

**Resultado esperado:** 75-78% (+5-6 puntos)

**Semana 5-6:**
10. Implementar flujo_semanal.py (Gmail → Excel)
11. Probar generador SEPA en real
12. Ajustes finales

**Resultado esperado:** 78-80% + flujo semi-automatizado

---

### Opción B: "EXTRACTORES PRIMERO"

**Filosofía:** Maximizar facturas OK antes de refactorizar.

**Problema:** Ya lo llevas haciendo 1 mes y estás estancado en 66%.

**Por qué no la recomiendo:**
- Cada extractor nuevo es +2-3 horas
- Beneficio marginal decreciente
- La deuda técnica crece
- Riesgo de regresiones sin tests

---

### Opción C: "BIG BANG REFACTOR"

**Filosofía:** Parar todo y reescribir limpio.

**Por qué no la recomiendo:**
- Perderías semanas sin resultados visibles
- El sistema actual FUNCIONA
- Desmotivación garantizada

---

## 📋 PLAN DE ACCIÓN INMEDIATO (Hoy)

### Paso 1: Integrar excel.py v5.8
```cmd
copy C:\[ruta]\excel.py C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\salidas\
rmdir /s /q C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\salidas\__pycache__
```

### Paso 2: Verificar versión
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python main.py --version
python -c "from extractores import listar_extractores; print(len(listar_extractores()), 'extractores')"
```

### Paso 3: Probar con 4T25
```cmd
python main.py -i "C:\...\4 TRI 2025" -o test_v58.xlsx
```

### Paso 4: Verificar que genera las 2 hojas (Lineas + Facturas)

---

## 📊 MÉTRICAS DE ÉXITO

| Hito | Métrica | Fecha objetivo |
|------|---------|----------------|
| Consolidación básica | 70% cuadre | 15/01/2026 |
| Tests funcionando | 10 proveedores con test | 22/01/2026 |
| Objetivo 80% | 80% cuadre | 31/01/2026 |
| Flujo semi-auto | Gmail → Excel funcionando | 15/02/2026 |

---

## 🚫 LO QUE NO HACER

1. **No crear más extractores** hasta consolidar (excepto DIA/ECOMS que es quick win)
2. **No tocar JIMELUZ** - Es complejo y no prioritario
3. **No reescribir desde cero** - El sistema funciona
4. **No saltar pasos** - Primero integrar, luego probar, luego siguiente

---

## 💡 CONCLUSIÓN FINAL

**El proyecto está más cerca del 80% de lo que parece.** El problema no es falta de extractores, sino:

1. Trabajo hecho pero no integrado (excel.py, RETENCIONES)
2. Deuda técnica que frena (duplicados, agrupadores)
3. Proveedores "zombi" que nadie decide cerrar

**Con 20h/semana y el enfoque correcto, llegarás al 80% en 4 semanas.**

La clave es **parar de añadir y empezar a consolidar**.

---

*Análisis generado: 02/01/2026*  
*Próxima revisión: 15/01/2026 (tras completar consolidación básica)*

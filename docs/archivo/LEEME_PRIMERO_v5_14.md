# LEEME PRIMERO - ParsearFacturas

**Versión:** v5.14  
**Fecha:** 07/01/2026  
**Autor:** Tasca Barea + Claude  

---

## ⚠️ IMPORTANTE - ANTES DE EJECUTAR

### Pasos para actualizar a v5.14:

```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# 1. Copiar extractores corregidos v5.14
copy silva_cordero.py extractores\
copy la_alacena.py extractores\

# 2. Ejecutar
python main.py -i "C:\Facturas\1 TRI 2026"
```

**Nota:** No hay cambios en main.py para esta versión. Solo extractores.

---

## CAMBIOS v5.14 (07/01/2026)

### Extractores corregidos

| Extractor | Cambio | Validación |
|-----------|--------|------------|
| **silva_cordero.py** | Patrón flexible D.O.P, códigos pegados, lotes 6-7 dígitos | 3/3 ✓ |
| **la_alacena.py** | Lotes largos (A240928952), descuento 100%, sin categoria_fija | 3/3 ✓ |

### Detalle de correcciones

**SILVA CORDERO:**
- ✅ Códigos con puntos ("D.O.P") ahora se capturan
- ✅ Códigos pegados ("QUESOAZULQUESO") se separan correctamente
- ✅ Lotes de 7 dígitos (antes solo 6)
- ✅ Descripción limpia (quita "D.O.P" duplicado)

**LA ALACENA:**
- ✅ Lotes largos sin espacio ("A240928952") 
- ✅ Descuento 100% → base = 0€, cantidad = X
- ✅ Líneas "Subtotal" del PDF se ignoran
- ✅ Sin categoria_fija (busca en diccionario)

---

## VERIFICACIÓN POST-ACTUALIZACIÓN

Después de ejecutar, verificar en el Excel que:

1. **SILVA CORDERO** - Todas las líneas extraídas (incluyendo D.O.P)
2. **LA ALACENA** - Productos con lote largo aparecen
3. **LA ALACENA** - Líneas con 100% descuento muestran base=0

---

## ESTADO ACTUAL (07/01/2026)

| Métrica | Valor |
|---------|-------|
| Extractores activos | ~95 |
| Tasa cuadre | **81.2%** |
| Objetivo | 80% ✅ **ALCANZADO** |

### Proveedores corregidos esta sesión

| Proveedor | Antes | Después |
|-----------|-------|---------|
| SILVA CORDERO | Fallaba con D.O.P | ✅ 3/3 OK |
| LA ALACENA | Fallaba lotes largos | ✅ 3/3 OK |

---

## ⚠️ REGLAS CRÍTICAS PARA CLAUDE

| # | Regla |
|---|-------|
| 1 | **LEER** LEEME_PRIMERO, ESTADO_PROYECTO y SESION antes de trabajar |
| 2 | **VERIFICAR** si extractor existe antes de crear nuevo |
| 3 | **SIEMPRE** archivos .py COMPLETOS, nunca parches de líneas |
| 4 | **PROBAR** con PDFs reales antes de entregar |
| 5 | **PREGUNTAR** si hay duda, no asumir |
| 6 | **PORTES**: extractor los devuelve como línea, main.py los prorratea |

---

## PENDIENTE PRÓXIMA SESIÓN

### 🟡 Proveedores pendientes

| Proveedor | Errores | Tipo | Prioridad |
|-----------|---------|------|-----------|
| JAMONES BERNAL | 6 | DESCUADRE | Media |
| JIMELUZ | 18 | OCR | Baja (aparcado) |

### 🟢 Mejoras futuras

- [ ] Probar generador SEPA con Banco Sabadell
- [ ] Automatizar descarga de Gmail
- [ ] Dashboard de métricas

---

## ARCHIVOS DE LA SESIÓN 07/01/2026

| Archivo | Destino | Estado |
|---------|---------|--------|
| `silva_cordero.py` | extractores/ | ✅ CORREGIDO |
| `la_alacena.py` | extractores/ | ✅ CORREGIDO |
| `ESTADO_PROYECTO_v5_14.md` | docs/ | ✅ NUEVO |
| `SESION_07_01_2026_v5_14.md` | docs/ | ✅ NUEVO |

---

## INFORMACIÓN DEL NEGOCIO

| Aspecto | Valor |
|---------|-------|
| Métodos de pago | ~50% transferencia, ~50% otros |
| Facturas/trimestre | ~250 |
| Tiempo semanal proceso | 1-2 horas |
| Script renombra archivos | Sí, automático |

---

## HISTORIAL

| Fecha | Versión | Cambio principal |
|-------|---------|------------------|
| **07/01/2026** | **v5.14** | **SILVA CORDERO, LA ALACENA corregidos** |
| 06/01/2026 | v5.13 | MARITA COSTA, ANGEL Y LOLI, LA BARRA DULCE, ZUCCA |
| 05/01/2026 | v5.12 | Normalización, BM simplificado, soporte importe_iva_inc |
| 04/01/2026 | v5.11 | +5 extractores, OCR, cache auto |
| 03/01/2026 | v5.9 | Fix categoria_fija |
| 01/01/2026 | v5.7 | LA ROSQUILLERIA |

---

*Última actualización: 07/01/2026*

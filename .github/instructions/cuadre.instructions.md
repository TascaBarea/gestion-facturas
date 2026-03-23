---
applyTo: cuadre/**
---

# Módulo Cuadre — Conocimiento del dominio
<!-- cuadre.py v1.7 — Actualizado 24/03/2026 -->

## Qué hace este módulo
Clasifica movimientos bancarios de un Excel (hojas Tasca / Comestibles) vinculándolos con facturas de proveedores. Genera un Excel de salida con `Categoria_Tipo` y `Categoria_Detalle` rellenas, más un log de decisiones.

## Arquitectura: función central

`buscar_factura_candidata()` — **lógica de asignación en 4 pasos, EN ESTE ORDEN**:

1. **Importe**: buscar facturas con `abs(Total - importe) <= 0.01€`
2. **Proveedor (fuzzy)**: calcular similitud con `rapidfuzz.fuzz.token_sort_ratio` usando aliases del MAESTRO_PROVEEDORES. Filtrar `>= 70%`
3. **Fecha**: ventana bidireccional `[fecha_mov - 60 días, fecha_mov + 15 días]`. La más cercana en días absolutos gana (no hay preferencia antes/después)
4. **Asignar** o marcar **REVISAR** si ninguna candidata pasa todos los filtros

**Nunca cambiar este orden sin consenso explícito.**

## Umbrales clave (constantes en el código)
```python
UMBRAL_FUZZY_MINIMO   = 0.70   # mínimo para considerar candidata
UMBRAL_FUZZY_INDICAR  = 0.85   # por debajo: mostrar %(fuzzy) en detalle
# Ventana fecha: [-60 días, +15 días] — hardcoded en buscar_factura_candidata()
```

## Clasificadores especiales (tienen lógica propia, NO pasan por buscar_factura_candidata)
| Clasificador | Trigger | Lógica especial |
|---|---|---|
| ALQUILER | `BENJAMIN ORTEGA Y JAIME` en concepto | Busca 2 facturas (Ortega + Fernández) del mismo mes |
| YOIGO | regex `Y?C\d{9,}` + `XFERA/YOIGO/MASMOVIL` | Regex en concepto bancario |
| COMUNIDAD DE VECINOS | `COM PROP` en concepto | Asigna las 2 facturas ISTA METERING más cercanas |
| Som Energia | `SOM ENERGIA` en concepto | Busca número de factura en el concepto |
| Suscripciones sin factura | SPOTIFY, NETFLIX, LOYVERSE, AMAZON PRIME | Devuelve tipo fijo, sin factura |
| Suscripciones con factura | MAKE.COM → CELONIS INC., OPENAI → OPENAI LLC | Busca factura del mismo mes |

## Estructura del Excel de entrada
- **Hoja Tasca** / **Comestibles**: columnas `Concepto`, `Importe`, `F. Valor`, `F. Operativa`, `Categoria_Tipo`, `Categoria_Detalle`
- **Hoja Facturas**: columnas `#`→`Cód.`, `TITULO`→`Título`, `TOTAL FACTURA`→`Total`, `Fec.Fac.`, `REF`→`Factura`
- **MAESTRO_PROVEEDORES.xlsx**: mapea alias del concepto bancario → título de factura. Columnas: `PROVEEDOR`, `ALIAS` (separados por coma)

## Reglas críticas — NUNCA violar
- **ESTADO_PAGO y MOV#** en el Excel COMPRAS: los rellena **únicamente `cuadre.py`**, jamás otro script
- **Excel abierto**: avisar siempre antes de escribir. El script fallará si el archivo está abierto en Excel
- **facturas_usadas**: set global que evita asignar la misma factura a dos movimientos. Se reinicia una vez al inicio, no por hoja

## Prefijos en Categoria_Detalle
- `#NNN` — asignación directa (fuzzy ≥ 85%)
- `#NNN (fuzzy XX%)` — asignada pero con baja confianza (fuzzy entre 70-85%)
- `¿#NNN TITULO? (fuzzy XX%)` — sugerencia REVISAR: candidata encontrada pero no asignada
- Texto libre — REVISAR sin candidata clara

## Estado global (variables mutadas durante el proceso)
```python
facturas_usadas: set                          # códigos de factura ya asignados
vinculos_factura_movimiento: Dict[int, List]  # factura → lista de movimientos
log_decisiones: List[str]                     # log completo de decisiones
```

## Salida generada
- `outputs/Cuadre_DDMMYY-DDMMYY.xlsx` — Excel clasificado
- `outputs/Cuadre_DDMMYY-DDMMYY_log.txt` — log de decisiones
- Hoja Facturas con columna `Origen` añadida (qué movimiento la usa)

## Métricas objetivo
- Clasificados: > 85% del total de movimientos
- REVISAR: < 15% — si es mayor, analizar el log para ver causas

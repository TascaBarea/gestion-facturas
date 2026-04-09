# SPEC — cuadre.py v2.0 (Cuadre Bancario)

> Documento de especificación para implementación en Claude Code.
> Generado: 2 de abril de 2026.
> Proyecto: gestion-facturas

---

## 1. OBJETIVO

Script CLI que cruza movimientos bancarios con facturas para generar un archivo Excel de cuadre bancario. Incluye sistema de clasificación por capas con memoria histórica que mejora con el uso.

---

## 2. ARCHIVOS DE ENTRADA

### 2.1 MOV_BANCO (obligatorio)

Archivo Excel con movimientos bancarios de Sabadell. Puede ser de cualquier año.

| Ejemplo | Descripción |
|---------|-------------|
| `Movimientos_Cuenta_26.xlsx` | Año 2026 |
| `Movimientos_Cuenta_2025.xlsx` | Año 2025 |

**Estructura:**
- Pestañas: `Tasca` y `Comestibles` (puede tener otras, ignorarlas)
- Columnas: `#`, `F. Operativa`, `Concepto`, `F. Valor`, `Importe`, `Saldo`, `Referencia 1`, `Referencia 2`
- Fechas: pueden ser datetime o string formato `DD/MM/YYYY` o `DD-MM-YY`
- Importes: float (negativos = cargo, positivos = abono)

### 2.2 FACTURAS — Provisional (opcional)

Archivo Excel generado por PARSEO con facturas del período actual.

| Ejemplo | Descripción |
|---------|-------------|
| `Facturas_1T26_Provisional.xlsx` | Trimestre actual |

**Estructura:**
- Pestaña: `Facturas`
- Columnas: `NOMBRE`, `PROVEEDOR`, `Fec.Fac.`, `Factura`, `Total`, `Origen`, `OBS`
- `NOMBRE`: nombre del archivo PDF (ej: "1T26 0101 SEGURMA RC")
- `PROVEEDOR`: nombre normalizado del proveedor
- `Total`: importe total de la factura (float, positivo)
- `Origen`: **IGNORAR contenido actual** (contiene timestamps de Gmail). Se sobreescribirá con vínculo al movimiento.

### 2.3 FACTURAS — Histórico (opcional)

Archivo Excel manual con facturas de años anteriores.

| Ejemplo | Descripción |
|---------|-------------|
| `Facturas_2025.xlsx` | Año 2025 completo |

**Estructura:**
- Pestaña: `Facturas`
- Columnas: `Cód.`, `Cuenta`, `Título`, `Fec.Fac.`, `Factura`, `Total`, `Origen`

**NORMALIZACIÓN:** Al cargar, mapear a formato Provisional:
| Histórico | → Provisional |
|-----------|---------------|
| `Cód.` | No se usa (descartar) |
| `Cuenta` | No se usa (descartar) |
| `Título` | → `PROVEEDOR` |
| `Fec.Fac.` | → `Fec.Fac.` |
| `Factura` | → `Factura` |
| `Total` | → `Total` |
| `Origen` | → `Origen` (preservar si tiene formato "T NNN" / "C NNN", limpiar si no) |
| — | `NOMBRE` = generar desde Título + Fecha |
| — | `OBS` = vacío |

### 2.4 MEMORIA HISTÓRICA (auto-generada)

Archivo JSON que se crea y crece automáticamente.

| Archivo | Ubicación |
|---------|-----------|
| `clasificaciones_historicas.json` | `gestion-facturas/datos/` |

**Estructura:**
```json
{
  "ADEUDO RECIBO SEGURMA S.A.": {
    "tipo": "SEGURMA S.A.",
    "confianza": "alta",
    "veces": 12
  },
  "TRANSFERENCIA A QUESERIA ZUCCA": {
    "tipo": "FORMAGGIARTE SL",
    "confianza": "media",
    "veces": 11,
    "alternativas": ["ZUCCA"]
  }
}
```

**Primera ejecución:** Si no existe, generarlo a partir del CUADRE de referencia (`Cuadre_020125-311225.xlsx`) con el script auxiliar `generar_memoria.py` (ver sección 7).

---

## 3. ARCHIVO DE SALIDA

### 3.1 Nombre
```
CUADRE_{DDMMYY_inicio}-{DDMMYY_fin}.xlsx
```
Ejemplo: `CUADRE_010126-310326.xlsx`

### 3.2 Pestaña "Tasca"

Movimientos de la cuenta Tasca (ES78...1844495) filtrados por rango de fechas.

| Columna | Origen |
|---------|--------|
| `#` | MOV_BANCO.# |
| `F. Operativa` | MOV_BANCO (formato DD-MM-YY) |
| `Concepto` | MOV_BANCO |
| `F. Valor` | MOV_BANCO (formato DD-MM-YY) |
| `Importe` | MOV_BANCO |
| `Saldo` | MOV_BANCO |
| `Referencia 1` | MOV_BANCO |
| `Referencia 2` | MOV_BANCO |
| `Categoria_Tipo` | **CLASIFICACIÓN** (ver sección 4) |
| `Categoria_Detalle` | **CLASIFICACIÓN** (ver sección 4) |

### 3.3 Pestaña "Comestibles"

Misma estructura que Tasca, con movimientos de la cuenta Comestibles (ES76...1992404).

### 3.4 Pestaña "Facturas"

Todas las facturas cargadas (Provisional + Histórico unificadas), formato normalizado.

| Columna | Descripción |
|---------|-------------|
| `NOMBRE` | Nombre archivo / identificador |
| `PROVEEDOR` | Nombre normalizado del proveedor |
| `Fec.Fac.` | Fecha de la factura |
| `Factura` | Número/referencia de factura |
| `Total` | Importe total |
| `Origen` | Vínculo: `T NNN` o `C NNN` (# del movimiento en pestaña Tasca/Comestibles). Vacío si no vinculada. `Pagos parciales (N)` si hay múltiples movimientos. |
| `OBS` | Observaciones |

---

## 4. SISTEMA DE CLASIFICACIÓN (3 Capas)

Para cada movimiento bancario, aplicar las capas en orden. La primera que resuelve, gana.

### Capa 1 — Reglas estructurales

Patrones fijos detectados por el campo `Concepto`. No necesitan facturas.

```python
REGLAS_ESTRUCTURALES = [
    # TPV — por número de terminal
    (r"ABONO TPV 0354272759",    "TPV TASCA",             "{terminal_id}"),
    (r"ABONO TPV 0337410674",    "TPV TASCA",             "{terminal_id}"),
    (r"ABONO TPV 0354768939",    "TPV COMESTIBLES",       "{terminal_id}"),
    (r"ABONO TPV 6304473868",    "TPV WOOCOMMERCE",       "{terminal_id}"),
    
    # Comisiones TPV
    (r"COMISIONES 0354272759",   "COMISION TPV TASCA",    "{terminal_id} ({pct})"),
    (r"COMISIONES 0337410674",   "COMISION TPV TASCA",    "{terminal_id} ({pct})"),
    (r"COMISIONES 0354768939",   "COMISION TPV COMESTIBLES", "{terminal_id} ({pct})"),
    
    # Nóminas y SS
    (r"^NOMINA A ",              "NOMINAS",               None),
    (r"^SEGUROS SOCIALES",       "SEGUROS SOCIALES",      None),
    
    # Impuestos
    (r"^IMPUESTOS",              "IMPUESTOS",             None),
    
    # Operaciones bancarias
    (r"^INGRESO EFECTIVO",       "INGRESO",               None),
    (r"^REINTEGRO",              "A CAJA",                None),
    (r"^TRASPASO",               "TRASPASO",              None),
    (r"^COMISIÓN DIVISA",        "COMISION DIVISA",       None),
    (r"^COMISIONES RECUENTO",    "COMISIONES",            None),
    
    # Servicios (extraer nombre del proveedor del concepto)
    (r"^ELECTRICIDAD (.+?)(?:\s+Factura|\s*$)", "\\1",    None),  # extraer nombre
    (r"^TELEFONOS (.+?)(?:\s+YC|\s*$)",         "\\1",    None),  # extraer nombre
]
```

**Cobertura estimada:** ~57% de movimientos (TPV+Comisiones = 54%, resto = 3%).

### Capa 2 — Memoria histórica + Cruce de facturas

Dos sub-pasos en paralelo, el mejor resultado gana:

#### 2a. Memoria histórica
1. Buscar `concepto` exacto en `clasificaciones_historicas.json`
2. Si existe con confianza "alta" → usar directamente
3. Si existe con confianza "media" → usar pero marcar en OBS: "confianza media"

**Resultado:** `Categoria_Tipo` = valor de memoria.

#### 2b. Cruce con facturas
1. Buscar en facturas cargadas (Provisional + Histórico) por:
   - `abs(Importe movimiento) == Total factura` (exacto al céntimo)
   - Fecha factura ≤ Fecha movimiento (la factura debe ser anterior o igual al pago)
   - Ventana temporal: factura no más de 90 días antes del movimiento
2. Si hay match único:
   - `Categoria_Tipo` = `PROVEEDOR` de la factura
   - `Categoria_Detalle` = `Factura` (referencia) de la factura
   - Actualizar `Origen` en pestaña Facturas con `T {#}` o `C {#}`
3. Si hay múltiples matches por importe:
   - Intentar desambiguar por nombre: fuzzy match entre Concepto y PROVEEDOR (≥70%)
   - Si sigue ambiguo → tomar el más cercano en fecha
   - Marcar en Categoria_Detalle: "(múltiples candidatos)"

#### Resolución de conflicto 2a vs 2b:
- Si 2b encuentra match con factura → **2b gana** (es más específico, tiene # de factura)
- Si solo 2a tiene resultado → usar 2a
- Si ninguno → Capa 3

**Cobertura estimada adicional:** ~25-30% de movimientos.

### Capa 3 — Sin clasificar

Todo lo que no resuelven Capas 1 y 2:
- `Categoria_Tipo` = `"REVISAR"`
- `Categoria_Detalle` = sugerencia si la hay (ej: "Concepto contiene: MAKRO")

**Estimación:** ~10-15% de movimientos.

---

## 5. INTERFAZ CLI

### 5.1 Ubicación
```
gestion-facturas/compras/cuadre.py
```

### 5.2 Uso
```bash
python cuadre.py --desde 01/01/2026 --hasta 31/03/2026 \
                 --movimientos "../Movimientos_Cuenta_26.xlsx" \
                 --facturas-provisional "../1T26/Facturas_1T26_Provisional.xlsx" \
                 --facturas-historico "../Facturas_2025.xlsx" \
                 --output "../CUADRE_010126-310326.xlsx"
```

### 5.3 Argumentos

| Argumento | Obligatorio | Descripción |
|-----------|-------------|-------------|
| `--desde` | Sí | Fecha inicio DD/MM/YYYY |
| `--hasta` | Sí | Fecha fin DD/MM/YYYY |
| `--movimientos` | Sí | Ruta al Excel de MOV_BANCO |
| `--facturas-provisional` | No | Ruta al Excel provisional |
| `--facturas-historico` | No | Ruta al Excel histórico |
| `--memoria` | No | Ruta al JSON de memoria (default: `../datos/clasificaciones_historicas.json`) |
| `--output` | No | Ruta de salida (default: auto-generado por fechas) |
| `--aprender` | No | Ruta a un CUADRE corregido para actualizar la memoria |
| `--verbose` | No | Mostrar detalle de clasificación |

### 5.4 Modo aprender
```bash
python cuadre.py --aprender "../CUADRE_010126-310326_corregido.xlsx"
```
Lee el CUADRE corregido manualmente y actualiza `clasificaciones_historicas.json` con las nuevas clasificaciones. No genera output, solo actualiza la memoria.

### 5.5 Output en consola
```
CUADRE BANCARIO v2.0
====================
Período: 01/01/2026 – 31/03/2026
MOV_BANCO: Movimientos_Cuenta_26.xlsx
  Tasca: 287 movimientos en rango (de 928 total)
  Comestibles: 156 movimientos en rango (de 513 total)
Facturas: 1.197 provisional + 1.178 histórico = 2.375 total
Memoria: 2.608 conceptos cargados

CLASIFICACIÓN:
  Capa 1 (reglas):    252 movimientos (56.9%)
  Capa 2a (memoria):   98 movimientos (22.1%)
  Capa 2b (facturas):  55 movimientos (12.4%)
  Capa 3 (REVISAR):    38 movimientos (8.6%)

VINCULACIÓN FACTURAS:
  Vinculadas a movimiento: 153 facturas
  Sin vincular: 2.222 facturas

Output: CUADRE_010126-310326.xlsx
```

---

## 6. INTERFAZ STREAMLIT

Página dentro de la app existente (`streamlit_app/`). Accesible por rol `admin` y `socio`.

### 6.1 Elementos de la página

1. **Selectores de fecha** — `st.date_input` para "Desde" y "Hasta"
2. **Selectores de archivo** — `st.file_uploader` para MOV_BANCO, Provisional, Histórico
3. **Botón "Generar Cuadre"** — ejecuta el script
4. **Resultados:**
   - Resumen de clasificación (barras horizontales por capa)
   - Tabla interactiva de movimientos clasificados (filtrable por Cuenta, Categoria_Tipo)
   - Tabla de facturas vinculadas
   - Botón de descarga del Excel generado
5. **Estadísticas:**
   - % de cobertura automática
   - Top 10 categorías por importe
   - Movimientos pendientes de revisar

### 6.2 Nota de implementación
La lógica de clasificación debe estar en un módulo importable (`cuadre_engine.py`) que usen tanto el CLI como Streamlit. El CLI es un wrapper fino sobre el engine.

---

## 7. SCRIPTS AUXILIARES

### 7.1 generar_memoria.py
```bash
python generar_memoria.py --cuadre "../Cuadre_020125-311225.xlsx" \
                          --output "../datos/clasificaciones_historicas.json"
```
Lee un CUADRE existente (con las pestañas Tasca, Comestibles clasificadas) y genera el JSON de memoria. Para cada concepto:
- Si siempre fue clasificado igual → confianza "alta"
- Si fue clasificado mayoritariamente igual (≥70%) → confianza "media" + alternativas
- Si fue ambiguo (<70%) → excluir

### 7.2 Integración con generar_memoria desde cuadre.py
El flag `--aprender` de cuadre.py hace lo mismo pero actualizando el JSON existente (merge, no overwrite):
- Nuevos conceptos → añadir
- Conceptos existentes con misma categoría → incrementar `veces`
- Conceptos existentes con categoría diferente → recalcular confianza

---

## 8. DEPENDENCIAS

```
openpyxl>=3.1.0    # lectura/escritura Excel
rapidfuzz>=3.0.0   # fuzzy matching para desambiguación Capa 2b
argparse           # CLI (stdlib)
```

---

## 9. ESTRUCTURA DE ARCHIVOS RESULTANTE

```
gestion-facturas/
├── compras/
│   ├── cuadre.py              # CLI wrapper
│   └── cuadre_engine.py       # Lógica de negocio (importable)
├── datos/
│   └── clasificaciones_historicas.json
├── scripts/
│   └── generar_memoria.py     # Generador inicial de memoria
└── streamlit_app/
    └── pages/
        └── cuadre_bancario.py # Página Streamlit
```

---

## 10. CASOS ESPECIALES A MANEJAR

1. **Pagos parciales:** Un movimiento de -150€ no matchea ninguna factura exacta, pero hay una factura de 300€ del mismo proveedor. No vincular automáticamente → REVISAR con nota "Posible pago parcial de [PROVEEDOR] factura [REF] por [Total]".

2. **Múltiples facturas en un pago:** Un movimiento de -526€ puede corresponder a 2 facturas del mismo proveedor sumadas. No detectar automáticamente en Fase 1 → REVISAR.

3. **Misma factura pagada desde ambas cuentas:** Verificar que una factura no se vincule a dos movimientos distintos. Primera vinculación gana.

4. **Movimientos sin clasificar en memoria pero con categoría obvia:** Los de Capa 1 siempre tienen prioridad sobre la memoria (evita que un concepto de TPV se clasifique como otra cosa por error histórico).

5. **Fechas mixtas en MOV_BANCO:** El archivo de 2025 tiene fechas como strings "DD/MM/YYYY", el de 2026 las tiene como datetime. El parser debe manejar ambos formatos.

6. **Facturas con importes negativos:** Son abonos/devoluciones. Tratar como importe normal en el cruce (buscar movimientos positivos por ese importe).

---

## 11. PRIORIDAD DE IMPLEMENTACIÓN

1. **`cuadre_engine.py`** — Módulo core con las 3 capas
2. **`cuadre.py`** — CLI wrapper
3. **`generar_memoria.py`** — Para crear la memoria inicial desde el CUADRE 2025
4. **`cuadre_bancario.py`** — Página Streamlit (después de validar que el engine funciona)

---

## 12. TESTS MÍNIMOS

Con los datos reales proporcionados:
- Cargar MOV_BANCO 2025, filtrar enero 2025 → verificar que Tasca tiene ~220 movimientos
- Clasificar con Capa 1 → verificar que TPV y COMISIONES se clasifican correctamente
- Cargar memoria y clasificar → verificar que ≥80% se resuelve
- Cruzar con Facturas_2025.xlsx → verificar vinculaciones Origen = "T NNN"
- Generar Excel → verificar 3 pestañas con formato correcto

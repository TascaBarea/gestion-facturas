# ESQUEMA COMPLETO DEL PROYECTO - ParsearFacturas

**Versión:** v5.16  
**Fecha:** 07/01/2026  
**Propósito:** Documento de referencia para Claude - estructura del proyecto

---

## 🏢 CONTEXTO DEL NEGOCIO

```
TASCA BAREA S.L.L.
├── TASCA (Restaurante)
│   └── Categorías de compra propias (menos artículos)
│
└── COMESTIBLES BAREA (Distribución gourmet)
    └── Categorías de compra propias (más artículos)
```

**Objetivo del sistema:** Automatizar el procesamiento semanal de facturas de proveedores:
1. Extraer datos de PDFs
2. Categorizar productos
3. Generar Excel para contabilidad
4. (Futuro) Generar ficheros SEPA para pagos

---

## 📁 ESTRUCTURA DE CARPETAS

```
ParsearFacturas/
│
├── 📄 main.py                    # ⭐ SCRIPT PRINCIPAL (v5.16, ~1500 líneas)
│                                  #    - Orquesta todo el flujo
│                                  #    - Contiene ALIAS_DICCIONARIO
│                                  #    - Función prorratear_portes()
│                                  #    - Busca subcarpeta ATRASADAS automáticamente
│
├── 📂 extractores/               # ⭐ UN ARCHIVO POR PROVEEDOR (~95 archivos)
│   ├── __init__.py               #    - Registro automático con @registrar
│   ├── base.py                   #    - Clase base ExtractorBase
│   ├── generico.py               #    - Extractor fallback
│   └── ... (~95 más)
│
├── 📂 nucleo/                    # LÓGICA CORE
│   ├── factura.py                #    - Clases Factura, LineaFactura
│   ├── parser.py                 #    - ⭐ Funciones de parsing (incluye TEMP y ATRASADAS)
│   ├── pdf.py                    #    - Extracción de texto (pdfplumber/OCR)
│   └── validacion.py             #    - Validación de cuadre
│
├── 📂 salidas/                   # GENERACIÓN DE OUTPUTS
│   └── excel.py                  #    - Genera Excel con hojas Lineas/Facturas
│
├── 📂 config/                    # CONFIGURACIÓN
│   └── settings.py               #    - VERSION, CIF_PROPIO, rutas
│
├── 📂 datos/                     # ⚠️ DATOS MAESTROS (NO MODIFICAR)
│   ├── DiccionarioProveedoresCategoria.xlsx  # Artículos + categorías
│   ├── DiccionarioEmisorTitulo.xlsx          # Cuentas contables
│   └── MAESTROS.xlsx                         # Proveedores + IBANs
│
└── 📂 docs/                      # DOCUMENTACIÓN
    ├── LEEME_PRIMERO_v5_XX.md
    ├── ESTADO_PROYECTO_v5_XX.md
    ├── ESQUEMA_PROYECTO.md       # ⭐ ESTE ARCHIVO
    └── SESION_DDMMAAAA_v5_XX.md
```

---

## 📋 CAMPO # (NÚMERO DE FACTURA) - REGLAS COMPLETAS

### Origen
El campo **#** es el número correlativo de gestoría - identificador asignado por la asesoría fiscal.

### Tipos de valores

| Tipo | Formato # | Ejemplo archivo | Regla |
|------|-----------|-----------------|-------|
| **Normal** | `XXXX` (4 dígitos) | `4006_4T25_1020_EMBUTIDOS_TF.pdf` | Siempre 4 dígitos |
| **Atrasada** | `XXX ATRASADA` | `460 ATRASADA 1T25 0326 SWITCHBOT TJ.pdf` | Siempre 3 dígitos |
| **Sin numerar** | `TEMPXXX_XTxx` | `4T25 1020 EMBUTIDOS FERRIOL TF.pdf` | Archivo sin # de gestoría |
| **Ignorar** | `0` | `Z DUPLICADO...`, `NO ES FACTURA...` | No procesar |
| **Error** | `ERROR_3DIG_XXX` | 3 dígitos sin palabra ATRASADA en carpeta principal | Requiere corrección |

### Reglas de detección

```
SI archivo empieza con 4 dígitos:
    → # = número (ej: 4006)
    
SI archivo empieza con 3 dígitos:
    SI tiene palabra "ATRASADA" en nombre:
        → # = "XXX ATRASADA" (ej: "460 ATRASADA")
    SI NO tiene palabra pero está en carpeta ATRASADAS:
        → # = "XXX ATRASADA"
    SI NO tiene palabra y NO está en carpeta ATRASADAS:
        → # = "ERROR_3DIG_XXX" (marcar error)
        
SI archivo empieza con código trimestre (4T25, 1T26...):
    → # = "TEMPXXX_XTxx" (ej: "TEMP001_4T25")
    → Contador reinicia por trimestre en cada ejecución
    
SI archivo empieza con Z, NO ES FACTURA, etc:
    → # = 0 (ignorar)
```

### Rangos de numeración

| Serie | Rango | Uso |
|-------|-------|-----|
| Normal | 1001-9999 | Facturas del trimestre actual |
| Atrasadas | 900-999 (prioritario) | Facturas de trimestres anteriores |
| Atrasadas | 400-499 (secundario) | Si se agota el 900 |

### Unicidad
- El # es **único por año** (no por trimestre)
- Nunca colisionan normales (4 dígitos) con atrasadas (3 dígitos)

---

## 📂 CARPETA ATRASADAS

### Ubicación
```
FACTURAS 2025/
├── 1 TRI 2025/
│   ├── [facturas normales]
│   └── ATRASADAS/           # ← Subcarpeta fija
│       └── [facturas atrasadas]
├── 2 TRI 2025/
│   └── ATRASADAS/
├── 3 TRI 2025/
│   └── ATRASADAS/
└── 4 TRI 2025/
    └── ATRASADAS/
```

### Reglas
- Nombre siempre: `ATRASADAS` (mayúsculas, exacto)
- Solo un nivel de profundidad (sin subcarpetas anidadas)
- main.py busca esta subcarpeta automáticamente
- Contiene facturas de trimestres anteriores contabilizadas en el actual

### Formato nombre archivo atrasada
```
XXX ATRASADA [TRIMESTRE_ORIGEN] MMDD PROVEEDOR TIPO.pdf
│   │        │                  │    │         │
│   │        │                  │    │         └── TF/RC/TJ/EF/TR
│   │        │                  │    └── Nombre proveedor
│   │        │                  └── Fecha (mes+día)
│   │        └── Trimestre original de la factura (opcional)
│   └── Palabra ATRASADA (puede faltar si está en carpeta)
└── 3 dígitos (rango 900-999 o 400-499)
```

### Ejemplos válidos
```
460 ATRASADA 1T25 0326 SWITCHBOT TJ.pdf     ✓ Completo
946 T25 0619 DE LUIS SABORES UNICOS TF.pdf  ✓ Sin palabra (en carpeta ATRASADAS)
401 ATRASADAS 0710 BM TJ.pdf                ✓ Sin trimestre origen
488 ATRASADA 4T24 1214 LICORES MADRUEÑO.pdf ✓ Año anterior (IVA puede ser 2%)
```

---

## 🔢 IVA - CASOS ESPECIALES

### IVA superreducido 2024
- En 2024 existió IVA 2% para productos básicos (aceite, pan, leche, etc.)
- En 2025 volvió al 4%
- **Regla:** Si factura atrasada es de trimestre 2024 (1T24, 2T24, 3T24, 4T24), el extractor puede encontrar IVA 2% - es válido, no es error

### Tipos de IVA válidos
| % | Productos |
|---|-----------|
| 2% | Solo facturas 2024 - alimentos básicos |
| 4% | Alimentos básicos (pan, leche, aceite, frutas, verduras) |
| 10% | Alimentación general |
| 21% | Servicios, no alimentación |

---

## 📊 EXCEL DE SALIDA - ORDEN DE FILAS

### Hoja "Lineas"
1. Primero: Facturas normales (# = 1001-9999) ordenadas por #
2. Después: Facturas atrasadas (# = "XXX ATRASADA") ordenadas por #
3. Final: TEMP si existen

### Columnas hoja "Lineas"
| Columna | Descripción |
|---------|-------------|
| # | Número correlativo gestoría / TEMP / XXX ATRASADA |
| FECHA | Fecha factura |
| REF | Referencia/número factura |
| PROVEEDOR | Nombre normalizado |
| ARTICULO | Descripción producto |
| CATEGORIA | Categoría asignada |
| CANTIDAD | Unidades/kg |
| PRECIO_UD | Precio unitario |
| TIPO IVA | 2, 4, 10, 21 |
| BASE (€) | Importe sin IVA |
| CUOTA IVA | Importe IVA |
| TOTAL FAC | Total factura |
| CUADRE | OK / DESCUADRE_XX |
| ARCHIVO | Nombre PDF |
| EXTRACTOR | Clase usada |

---

## 🔄 FLUJO DE DATOS

```
┌─────────────────────┐
│  Carpeta trimestre  │  Ej: "4 TRI 2025"
│  + subcarpeta       │      └── ATRASADAS/
│    ATRASADAS        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│     main.py         │  1. Busca PDFs en carpeta principal
│                     │  2. Busca PDFs en subcarpeta ATRASADAS
│                     │  3. Detecta tipo por nombre archivo
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   parser.py         │  4. parsear_nombre_archivo()
│                     │     - 4 dígitos → normal
│                     │     - 3 dígitos → atrasada
│                     │     - XTxx inicio → TEMP
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   extractor/        │  5. Extrae líneas, total, fecha
│   proveedor.py      │  6. IVA 2% válido si año 2024
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   excel.py          │  7. Genera Excel
│                     │     - Normales primero
│                     │     - Atrasadas después
└─────────────────────┘
```

---

## ⚠️ REGLAS CRÍTICAS

### Para Claude:
1. **LEER** docs/LEEME, ESTADO, ESQUEMA, SESION antes de trabajar
2. **VERIFICAR** si extractor existe antes de crear
3. **SIEMPRE** archivos .py COMPLETOS
4. **PROBAR** con PDFs reales antes de entregar
5. **PREGUNTAR** si hay duda
6. **PORTES**: extractor devuelve línea, main.py prorratea

### Para el código:
1. **3 dígitos = ATRASADA** (si tiene palabra o está en carpeta ATRASADAS)
2. **3 dígitos sin ATRASADA fuera de carpeta = ERROR**
3. **IVA 2% válido** para facturas año 2024
4. **Contador TEMP** reinicia por trimestre en cada ejecución
5. **Limpiar __pycache__** antes de probar (main.py lo hace auto)

---

## 📈 MÉTRICAS ACTUALES (v5.16)

| Métrica | Valor |
|---------|-------|
| Extractores | ~95 |
| Proveedores activos | ~90 |
| Tasa cuadre | 81.2% |
| Objetivo | 80% ✅ |
| Facturas/trimestre | ~250 |

---

## 🔗 ARCHIVOS QUE NO DEBO MODIFICAR

| Archivo | Motivo |
|---------|--------|
| datos/MAESTROS.xlsx | Usuario lo edita manualmente |
| datos/DiccionarioProveedoresCategoria.xlsx | Usuario lo edita |
| datos/DiccionarioEmisorTitulo.xlsx | Cuentas contables |

---

*Documento actualizado: 07/01/2026*
*Para uso interno de Claude en sesiones futuras*

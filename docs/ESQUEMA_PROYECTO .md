# ESQUEMA DEL PROYECTO - GESTIÓN FACTURAS

**Versión:** 2.1  
**Última actualización:** 08/01/2026  
**Propósito:** Documento maestro de referencia para Claude y usuarios

---

## 1. CONTEXTO DEL NEGOCIO

### 1.1 Entidad jurídica
```
TASCA BAREA S.L.L.
CIF: B87760575
├── TASCA (Tasca) - Calle Rodas
│   └── Cuenta Sabadell: 0001844495
│
└── COMESTIBLES BAREA (Tienda gourmet) - Calle Embajadores 38
    └── Cuenta Sabadell: 0001992404
```

- **Una sola personalidad jurídica:** Todas las facturas se emiten/reciben por TASCA BAREA S.L.L.
- **Dos centros operativos:** Se distinguen cuando es relevante (movimientos banco, TPV)
- **Gestoría:** Kinema (acceso a carpetas Dropbox, asigna números de factura y CUENTA)

### 1.2 Cuentas bancarias y TPV
| Cuenta | Centro | Uso |
|--------|--------|-----|
| 0001844495 | TASCA | Cuenta principal tasca |
| 0001992404 | COMESTIBLES | Cuenta principal tienda |

| Nº Comercio TPV | Centro |
|-----------------|--------|
| 0337410674 | TASCA |
| 0354768939 | COMESTIBLES |
| 0354272759 | TALLERES |

---

## 2. OBJETIVO DEL SISTEMA

Automatizar el ciclo contable completo:

```
ENTRADA AUTOMÁTICA ───────────────────────────────────────────┐
  │ Script Gmail (viernes)                                    │
  │ → Detecta facturas en email                               │
  │ → Renombra y sube a Dropbox                               │
  │ → Genera SEPA si es transferencia                         │
  │                                                           │
COMPRAS ──────────────────────────────────────────────────────┤
  │ PDFs facturas proveedores                                 │
  │ → ParsearFacturas (main.py)                               │
  │ → COMPRAS_XTxx.xlsx                                       │
  │                                                           │
VENTAS ───────────────────────────────────────────────────────┤
  │ Loyverse (tickets tienda)                                 │
  │ WooCommerce (pedidos online)                              │
  │ → Parser ventas (ventas.py)                               │
  │ → VENTAS_XTxx.xlsx                                        │
  │                                                           ├──→ CUADRE
BANCO ────────────────────────────────────────────────────────┤
  │ Ficheros N43 Sabadell                                     │
  │ → Parser N43                                              │
  │ → Clasificador movimientos (clasificador.py)              │
  │ → MOVIMIENTOS_XTxx.xlsx                                   │
  │                                                           │
MAESTROS ─────────────────────────────────────────────────────┘
  │ Proveedores, artículos, diccionarios
  │ → Fuente de verdad compartida
```

---

## 3. ESTRUCTURA DE CARPETAS

### 3.1 Repositorio (GitHub: gestion-facturas)
```
C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\
│
├── 📄 main.py                      # Script principal - Compras (ParsearFacturas)
├── 📄 clasificador.py              # Script principal - Movimientos banco
├── 📄 ventas.py                    # Script principal - Ventas (futuro)
├── 📄 cuadre.py                    # Script cuadre Compras↔Banco (futuro)
├── 📄 gmail_facturas.py            # Script Gmail → Dropbox → SEPA (futuro)
│
├── 📂 extractores/                 # Extractores de facturas (~95)
│   ├── __init__.py
│   ├── base.py
│   └── [proveedor].py
│
├── 📂 nucleo/                      # Lógica core
│   ├── factura.py
│   ├── parser.py
│   ├── pdf.py
│   └── validacion.py
│
├── 📂 salidas/                     # Generación de outputs
│   └── excel.py
│
├── 📂 banco/                       # Módulo movimientos bancarios
│   ├── parser_n43.py               # Lee ficheros Norma 43
│   ├── router.py                   # Enruta al clasificador
│   └── clasificadores/
│       ├── tpv.py
│       ├── transferencia.py
│       ├── compra_tarjeta.py
│       ├── adeudo_recibo.py
│       ├── energia_som.py
│       ├── telefono_yoigo.py
│       └── casos_simples.py
│
├── 📂 ventas/                      # Módulo ventas (futuro)
│   ├── parser_loyverse.py
│   └── parser_woocommerce.py
│
├── 📂 gmail/                       # Módulo Gmail (futuro)
│   ├── buscador.py                 # Busca facturas en Gmail
│   ├── renombrador.py              # Renombra según formato
│   └── sepa.py                     # Genera ficheros SEPA
│
├── 📂 datos/                       # Archivos maestros
│   ├── MAESTRO_PROVEEDORES.xlsx    # ⭐ Fuente única de proveedores
│   ├── DICCIONARIO_SINONIMOS.xlsx  # Nombre banco → Nombre oficial
│   └── DICCIONARIO_CATEGORIAS.xlsx # Artículo → Categoría
│
├── 📂 banco_datos/                 # Datos bancarios (local, no Dropbox)
│   ├── N43/
│   │   ├── TASCA/                  # Ficheros N43 cuenta 0001844495
│   │   └── COMESTIBLES/            # Ficheros N43 cuenta 0001992404
│   └── SEPA/                       # Ficheros SEPA generados
│       └── SEPA_YYYYMMDD.xml
│
├── 📂 outputs/                     # Salidas generadas
│   ├── COMPRAS_XTxx.xlsx
│   ├── MOVIMIENTOS_XTxx.xlsx
│   ├── VENTAS_XTxx.xlsx
│   └── REVISAR_XTxx.txt
│
├── 📂 docs/                        # Documentación
│   ├── ESQUEMA_PROYECTO.md         # ⭐ ESTE ARCHIVO
│   ├── LEEME_PRIMERO.md
│   ├── ESTADO_PROYECTO.md
│   ├── MANUAL_USUARIO.md
│   ├── PROTOCOLO_SESIONES_CLAUDE.md
│   └── sesiones/
│       └── YYYY-MM-DD_descripcion.md
│
└── 📂 config/
    └── settings.py
```

### 3.2 Carpetas Dropbox (datos externos)
```
C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\
│
├── FACTURAS 2025\
│   ├── FACTURAS EMITIDAS\          # Fuera del alcance (manual)
│   │   ├── 1 TRI 2025\
│   │   ├── 2 TRI 2025\
│   │   ├── 3 TRI 2025\
│   │   └── 4 TRI 2025\
│   │
│   └── FACTURAS RECIBIDAS\         # ⭐ Entrada de ParsearFacturas
│       ├── 1 TRI 2025\
│       │   ├── [facturas normales].pdf
│       │   └── ATRASADAS\
│       │       └── [facturas atrasadas].pdf
│       ├── 2 TRI 2025\
│       │   └── ATRASADAS\
│       ├── 3 TRI 2025\
│       │   └── ATRASADAS\
│       └── 4 TRI 2025\
│           └── ATRASADAS\
│
└── FACTURAS 2026\
    └── FACTURAS RECIBIDAS\
        └── 1 TRIMESTRE 2026\
            └── ATRASADAS\
```

---

## 4. ARCHIVOS MAESTROS

### 4.1 MAESTRO_PROVEEDORES.xlsx
**Ubicación:** `datos/MAESTRO_PROVEEDORES.xlsx`  
**Propósito:** Fuente ÚNICA de verdad para proveedores  
**Origen datos:** Fusión de archivos existentes + listado Kinema

| Campo | Tipo | Descripción | Origen |
|-------|------|-------------|--------|
| CUENTA | Texto | Código contable (40000XXX) | Kinema |
| PROVEEDOR | Texto | Nombre oficial (el de Kinema) | Kinema |
| CIF | Texto | CIF/NIF del proveedor | Usuario |
| IBAN | Texto | Para pagos por transferencia | Usuario |
| FORMA_PAGO | Texto | TF/TR/TJ/RC/EF | Usuario |
| EMAIL | Texto | Email del remitente (para Gmail) | Usuario |
| TIENE_EXTRACTOR | Sí/No | Si tiene extractor Python | Sistema |
| ARCHIVO_EXTRACTOR | Texto | Nombre del archivo .py | Sistema |
| TIPO_CATEGORIA | Texto | HARDCODED / DICCIONARIO | Sistema |
| CATEGORIA_FIJA | Texto | Si HARDCODED, categoría asignada | Sistema |
| ACTIVO | Sí/No | Si está activo | Usuario |
| NOTAS | Texto | Observaciones | Usuario |

**Nota:** Este archivo unifica:
- `Maestro_Proveedores_ACTUALIZADO.xlsx` (53 proveedores con IBAN)
- `EXTRACTORES_COMPLETO.xlsx` (91 proveedores con extractores)
- `DiccionarioEmisorTitulo.xlsx` Hoja1 (183 proveedores de Kinema)

### 4.2 DICCIONARIO_SINONIMOS.xlsx
**Ubicación:** `datos/DICCIONARIO_SINONIMOS.xlsx`  
**Propósito:** Mapear nombres del banco/email al nombre oficial  
**Usado por:** Clasificador de movimientos, Script Gmail

| Campo | Tipo | Descripción |
|-------|------|-------------|
| NOMBRE_VARIANTE | Texto | Como aparece en banco/email/PDF |
| PROVEEDOR | Texto | Nombre oficial (debe existir en MAESTRO_PROVEEDORES) |

**Ejemplos:**
| NOMBRE_VARIANTE | PROVEEDOR |
|-----------------|-----------|
| EMBUTIDOS FERRIOL | EMBUTIDOS FERRIOL SL |
| PANIFIESTO LAVAPIES | PANIFIESTO LAVAPIES SL |
| AY MADRE LA FRUTA | GARCIA VIVAS JULIO |
| FELISA GOURMET | PESCADOS DON FELIX SL |
| BODEGAS BORBOTON | BORBOTON FINCA Y BODEGA SLU |

### 4.3 DICCIONARIO_CATEGORIAS.xlsx
**Ubicación:** `datos/DICCIONARIO_CATEGORIAS.xlsx`  
**Propósito:** Asignar categoría a artículos de compra  
**Usado por:** ParsearFacturas

**Hoja "Articulos"** (1,306 filas):
| Campo | Tipo | Descripción |
|-------|------|-------------|
| PROVEEDOR | Texto | Proveedor del artículo |
| ARTICULO | Texto | Nombre del artículo |
| CATEGORIA | Texto | Categoría asignada |
| TIPO_IVA | Número | 4, 10, 21 |
| COD_LOYVERSE | Texto | Código en Loyverse (si aplica) |

**Hoja "Categorias"** (153 filas):
| Campo | Tipo | Descripción |
|-------|------|-------------|
| CATEGORIA | Texto | Nombre de la categoría |
| AMBITO | Texto | TASCA / COMESTIBLES / AMBOS |

---

## 5. ARCHIVOS DE SALIDA

### 5.1 COMPRAS_XTxx.xlsx (genera ParsearFacturas)

**Hoja "Lineas"** - Detalle de artículos:
| Campo | Descripción |
|-------|-------------|
| # | Número de gestoría (4006, "460 ATRASADA", "TEMP001_4T25") |
| FECHA | Fecha factura |
| REF | Número/referencia factura |
| PROVEEDOR | Nombre oficial |
| ARTICULO | Descripción producto |
| CATEGORIA | Categoría asignada |
| CANTIDAD | Unidades/kg |
| PRECIO_UD | Precio unitario |
| TIPO_IVA | 4, 10, 21 (o 2 si es 2024) |
| BASE | Importe sin IVA |
| CUOTA_IVA | Importe IVA |
| TOTAL_FAC | Total factura |
| CUADRE | OK / DESCUADRE_XX |
| ARCHIVO | Nombre PDF |
| EXTRACTOR | Clase usada |

**Hoja "Facturas"** - Resumen por factura:
| Campo | Descripción |
|-------|-------------|
| # | Número de gestoría |
| ARCHIVO | Nombre PDF (sin extensión) |
| CUENTA | Código contable proveedor |
| PROVEEDOR | Nombre oficial |
| FECHA | Fecha factura |
| REF | Número/referencia factura |
| TOTAL_FACTURA | Total extraído del PDF |
| TOTAL_CALCULADO | Suma de líneas |
| ESTADO_PAGO | PAGADA / PENDIENTE / PARCIAL |
| MOVIMIENTO_# | Fila en MOVIMIENTOS_XTxx.xlsx |
| OBSERVACIONES | Notas |

### 5.2 MOVIMIENTOS_XTxx.xlsx (genera clasificador.py)

| Campo | Descripción |
|-------|-------------|
| # | Número secuencial |
| F_OPERATIVA | Fecha operación |
| F_VALOR | Fecha valor |
| CONCEPTO | Descripción del movimiento |
| IMPORTE | Importe con signo |
| CENTRO | TASCA / COMESTIBLES |
| CLASIFICACION_TIPO | Código factura o tipo (TPV, NOMINAS, REVISAR...) |
| CLASIFICACION_DETALLE | Detalle adicional |
| ARCHIVO | Fichero N43 origen |

### 5.3 VENTAS_XTxx.xlsx (genera ventas.py - futuro)

**Hoja "Tickets"**:
| Campo | Descripción |
|-------|-------------|
| FECHA | Fecha y hora |
| NUMERO_RECIBO | Número de Loyverse |
| TIPO | Venta / Devolución |
| VENTAS_BRUTAS | Importe bruto |
| DESCUENTOS | Descuentos aplicados |
| VENTAS_NETAS | Importe neto |
| IMPUESTOS | IVA |
| TIPO_PAGO | Card / Cash |
| TIENDA | COMESTIBLES BAREA |

**Hoja "Lineas"**:
| Campo | Descripción |
|-------|-------------|
| NUMERO_RECIBO | Enlace con ticket |
| CATEGORIA | Categoría Loyverse |
| REF | Código artículo |
| ARTICULO | Nombre |
| CANTIDAD | Unidades/kg |
| PRECIO | Importe |
| IVA | Tipo IVA |

### 5.4 REVISAR_XTxx.txt (genera ambos sistemas)

```
REVISAR - Generado: DD/MM/AAAA
==========================================

MOVIMIENTOS SIN CLASIFICAR: X
------------------------------------------
Fila XX: [concepto] | [importe] | [motivo]

FACTURAS SIN CUADRAR: X
------------------------------------------
#XXXX: [proveedor] | [descuadre]

ACCIÓN REQUERIDA: Revisar X elementos
```

---

## 6. CAMPO # (NÚMERO DE GESTORÍA)

### 6.1 Tipos de valores
| Tipo | Formato | Ejemplo archivo | Regla |
|------|---------|-----------------|-------|
| Normal | XXXX (4 dígitos) | `4006 4T25 1020 EMBUTIDOS TF.pdf` | Numerado por Kinema |
| Atrasada | XXX ATRASADA | `460 ATRASADA 1T25 0326 SWITCHBOT TJ.pdf` | 3 dígitos |
| Sin numerar | TEMPXXX_XTxx | `4T25 1020 EMBUTIDOS FERRIOL TF.pdf` | Pendiente de Kinema |
| Ignorar | 0 | `Z DUPLICADO...` | No procesar |
| Error | ERROR_3DIG_XXX | 3 dígitos sin ATRASADA | Requiere corrección |

### 6.2 Reglas de detección
```
SI archivo empieza con 4 dígitos:
    → # = número (ej: 4006)
    
SI archivo empieza con 3 dígitos:
    SI tiene "ATRASADA" en nombre O está en carpeta ATRASADAS:
        → # = "XXX ATRASADA"
    SI NO:
        → # = "ERROR_3DIG_XXX"
        
SI archivo empieza con código trimestre (4T25, 1T26...):
    → # = "TEMPXXX_XTxx" (contador reinicia por trimestre)
    
SI archivo empieza con Z, "NO ES FACTURA":
    → # = 0 (ignorar)
```

### 6.3 Resolución de TEMP
- Kinema numera TODAS las facturas del trimestre
- Plazo máximo: 15 días después de cerrar trimestre
- Kinema RENOMBRA el PDF añadiendo el número al inicio
- Sistema detecta el cambio en siguiente ejecución

### 6.4 Rangos de numeración
| Serie | Rango | Uso |
|-------|-------|-----|
| Normal | 1001-9999 | Facturas del trimestre actual |
| Atrasadas | 900-999 | Facturas de trimestres anteriores |
| Atrasadas | 400-499 | Secundario si se agota 900 |

---

## 7. CÓDIGOS DE FORMA DE PAGO

| Código | Significado | Rastro bancario | Genera SEPA |
|--------|-------------|-----------------|-------------|
| TF | Transferencia | Sí (TRANSFERENCIA A) | ✅ Sí |
| TR | Transferencia | Sí (TRANSFERENCIA A) | ✅ Sí |
| TJ | Tarjeta | Sí (COMPRA TARJ.) | ❌ No |
| RC | Recibo/Adeudo | Sí (ADEUDO RECIBO) | ❌ No |
| EF | Efectivo | No | ❌ No |

---

## 8. CLASIFICACIÓN DE MOVIMIENTOS BANCARIOS

### 8.1 Router de clasificación
```python
if concepto.startswith("COMPRA TARJ"):       → compra_tarjeta.py
if concepto.startswith("ABONO TPV"):         → tpv.py
if concepto.startswith("COMISIONES"):        → tpv.py
if concepto.startswith("TRANSFERENCIA A"):   → transferencia.py
if concepto.startswith("TRANSFERENC. A"):    → transferencia.py
if concepto.startswith("ADEUDO RECIBO"):     → adeudo_recibo.py
if "YOIGO" in concepto:                      → telefono_yoigo.py
if "SOM ENERGIA" in concepto:                → energia_som.py
else:                                        → casos_simples.py
```

### 8.2 Movimientos SIN factura requerida
| Tipo movimiento | CLASIFICACION_TIPO | Requiere factura |
|-----------------|-------------------|------------------|
| Seguros | SEGUROS | ❌ |
| Comunidad de vecinos | COMUNIDAD | ❌ |
| Impuestos (AEAT, Ayto) | IMPUESTOS | ❌ |
| Seguros Sociales (TGSS) | SEGUROS SOCIALES | ❌ |
| Nóminas | NOMINAS | ❌ |
| IRPF/Retenciones | NOMINAS | ❌ |
| Finiquitos | NOMINAS | ❌ |
| Adelantos empleados | NOMINAS | ❌ |
| Comisiones bancarias | COMISIONES BANCO | ❌ |
| TPV abonos | TPV [CENTRO] | ❌ (es ingreso) |
| TPV comisiones | COMISIONES TPV | ❌ |
| Traspasos entre cuentas | TRASPASO | ❌ |
| Asociaciones (SGAE, comerciantes) | ASOCIACIONES | ❌ |
| Alquiler local | (buscar factura) | ✅ SÍ |

### 8.3 Cruce con facturas
1. Buscar en COMPRAS_XTxx.xlsx por importe exacto (±0.01€)
2. Si hay una coincidencia → asignar
3. Si hay varias → filtrar por PROVEEDOR con fuzzy matching (≥0.6)
4. Si no hay coincidencia clara → CLASIFICACION_TIPO = "REVISAR"

---

## 9. FICHEROS N43 (NORMA 43)

### 9.1 Estructura del fichero
```
Registro 11: Cabecera de cuenta
Registro 22: Movimiento (fecha, importe, signo)
Registro 23: Concepto (descripción)
Registro 33: Final de cuenta
Registro 88: Final de fichero
```

### 9.2 Campos extraídos
| Campo | Posición Reg 22 | Descripción |
|-------|-----------------|-------------|
| F_OPERATIVA | 11-16 | Fecha operación (AAMMDD) |
| F_VALOR | 17-22 | Fecha valor (AAMMDD) |
| IMPORTE | 29-42 | Importe en céntimos |
| SIGNO | 28 | 1=Cargo (negativo), 2=Abono (positivo) |
| CONCEPTO | Reg 23 | Descripción del movimiento |

### 9.3 Nomenclatura ficheros
```
0259_[CUENTA]_[FECHA].n43

Ejemplos:
0259_0001844495_01122025.n43  → TASCA, Dic 2025
0259_0001992404_01012026.n43  → COMESTIBLES, Ene 2026
```

---

## 10. SCRIPT GMAIL → DROPBOX → SEPA

### 10.1 Flujo automático (viernes)
```
┌─────────────────────────────────────────────────────────────┐
│ 1. BUSCAR en Gmail                                          │
│    - Emails última semana                                   │
│    - Asunto contiene: "factura", "invoice", "proforma"      │
│    - Con adjuntos PDF                                       │
│                                                             │
│ 2. IDENTIFICAR proveedor                                    │
│    - Buscar remitente en MAESTRO_PROVEEDORES (columna EMAIL)│
│    - Si no existe → guardar en carpeta "REVISAR_GMAIL/"     │
│                                                             │
│ 3. EXTRAER fecha de factura                                 │
│    - Ejecutar extractor del proveedor                       │
│    - Obtener fecha de la factura del PDF                    │
│                                                             │
│ 4. RENOMBRAR archivo                                        │
│    - Formato: [XTxx] [MMDD] [PROVEEDOR] [FORMA_PAGO].pdf    │
│    - Ejemplo: 4T25 1215 EMBUTIDOS FERRIOL TF.pdf            │
│    - SIN número (Kinema lo añadirá)                         │
│                                                             │
│ 5. SUBIR a Dropbox                                          │
│    - Ruta: FACTURAS 20XX/FACTURAS RECIBIDAS/X TRI 20XX/     │
│    - Calcula trimestre de la fecha de factura               │
│                                                             │
│ 6. GENERAR SEPA (si FORMA_PAGO = TF o TR)                   │
│    - Agrupar transferencias de la semana                    │
│    - Datos: IBAN, importe, concepto                         │
│    - Fichero: banco_datos/SEPA/SEPA_YYYYMMDD.xml            │
│    - Subida manual al banco Sabadell                        │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Detección de facturas en email
Palabras clave en asunto:
- factura
- invoice
- proforma
- fra.
- fac.

### 10.3 Ficheros SEPA
**Ubicación:** `banco_datos/SEPA/SEPA_YYYYMMDD.xml`  
**Formato:** ISO 20022 (pain.001.001.03)  
**Contenido:** Todas las transferencias de la semana agrupadas  
**Proceso:** Subida manual a BS Online Empresa (Sabadell)

---

## 11. VENTAS (FASE 3)

### 11.1 Fuentes de datos
| Sistema | Tipo | Archivos |
|---------|------|----------|
| Loyverse | Tickets tienda | `receipts-*.csv`, `receipts-by-item-*.csv` |
| WooCommerce | Pedidos online | (pendiente definir formato) |

### 11.2 Estructura Loyverse
**receipts-*.csv** (tickets):
- Fecha, Número de recibo, Tipo, Ventas brutas/netas, Tipo pago, Tienda

**receipts-by-item-*.csv** (líneas):
- Fecha, Número de recibo, Categoría, REF, Artículo, Cantidad, Precio, IVA

**export_items_*.csv** (catálogo):
- Handle, REF, Nombre, Categoría, Coste, Precio, IVA

### 11.3 Integración prevista
- API Loyverse para automatizar descarga
- Cruce con abonos TPV en banco
- Análisis de márgenes (coste vs precio venta)

---

## 12. PROCESO DE CUADRE

### 12.1 Cuadre Compras ↔ Banco
Se ejecuta con `python cuadre.py` (manual).

**Resultado:** Actualiza COMPRAS_XTxx.xlsx con:
- ESTADO_PAGO: PAGADA / PENDIENTE / PARCIAL
- MOVIMIENTO_#: Fila correspondiente en MOVIMIENTOS_XTxx.xlsx

### 12.2 Cuadre Ventas ↔ Banco (futuro)
Cruzar abonos TPV con totales de tickets Loyverse.

---

## 13. FLUJO DE TRABAJO CON KINEMA

### 13.1 Flujo de facturas (manual)
```
1. Recibes factura (email/física)
2. Renombras PDF: [XTxx] [MMDD] [PROVEEDOR] [FORMA_PAGO].pdf
3. Subes a Dropbox: FACTURAS 20XX/FACTURAS RECIBIDAS/X TRI 20XX/
4. Kinema accede y contabiliza
5. Kinema renombra añadiendo # (####_XTxx_MMDD_PROVEEDOR_TIPO.pdf)
6. Ejecutas ParsearFacturas → COMPRAS_XTxx.xlsx
```

### 13.2 Flujo de facturas (automático - futuro)
```
1. Factura llega por email
2. Script Gmail (viernes) la detecta, renombra y sube a Dropbox
3. Si es transferencia, genera SEPA
4. Kinema accede y contabiliza
5. Kinema renombra añadiendo #
6. Ejecutas ParsearFacturas → COMPRAS_XTxx.xlsx
```

### 13.3 Comparación trimestral
- Una vez al trimestre comparas con listado de Kinema
- Diferencias se resuelven caso a caso
- Facturas que faltan → subes a ATRASADAS del trimestre actual

### 13.4 Plazos
- Kinema numera facturas: máximo 15 días después de cerrar trimestre
- Ejemplo: Facturas 4T25 → numeradas antes del 15/01/2026

---

## 14. GESTIÓN DE ERRORES

### 14.1 Elementos a REVISAR
Se marcan con CLASIFICACION_TIPO = "REVISAR" o CUADRE = "DESCUADRE_XX"

### 14.2 Comportamiento ante errores graves
- **Archivo corrupto:** Continuar con el resto, registrar error
- **Formato inesperado:** Marcar REVISAR, no inventar
- **Proveedor desconocido:** Marcar REVISAR
- **Nunca parar todo** por un error individual

---

## 15. DOCUMENTACIÓN

### 15.1 Archivos de documentación
| Archivo | Propósito | Actualización |
|---------|-----------|---------------|
| ESQUEMA_PROYECTO.md | Documento maestro (este) | Cada sesión si hay cambios |
| LEEME_PRIMERO.md | Guía rápida de uso | Si cambia el uso |
| ESTADO_PROYECTO.md | Métricas, pendientes | Cada sesión |
| MANUAL_USUARIO.md | Para usuario/colaborador | Cuando esté estable |
| PROTOCOLO_SESIONES_CLAUDE.md | Instrucciones para Claude | Si cambia el proceso |
| sesiones/YYYY-MM-DD_*.md | Registro de cada sesión | Cada sesión |

### 15.2 Protocolo de sesiones con Claude
```
AL INICIO:
1. Claude LEE: ESQUEMA_PROYECTO.md (obligatorio)
2. Claude LEE: ESTADO_PROYECTO.md (ver pendientes)
3. Claude LEE: Última sesión (contexto reciente)

AL FINAL:
1. Claude ACTUALIZA: ESQUEMA_PROYECTO.md (si hay cambios estructurales)
2. Claude ACTUALIZA: ESTADO_PROYECTO.md (siempre)
3. Claude CREA: sesiones/YYYY-MM-DD_descripcion.md (siempre)
4. Claude ENTREGA: Archivos según corresponda
```

---

## 16. MÉTRICAS Y OBJETIVOS

| Métrica | Objetivo | Actual |
|---------|----------|--------|
| Tasa cuadre ParsearFacturas | ≥80% | 81.2% ✅ |
| Tasa clasificación movimientos | ≥80% | ~70% (estimado) |
| Movimientos REVISAR | ≤20% | ~30% (estimado) |
| Facturas/trimestre | ~250 | ~250 |
| Movimientos/trimestre | ~400 | ~400 |

---

## 17. FASES DE DESARROLLO

### FASE 1 - Cimientos ✅ EN CURSO
- [x] Análisis y definición funcional
- [x] ESQUEMA_PROYECTO.md definitivo
- [ ] Crear repositorio GitHub unificado
- [ ] Organizar estructura de carpetas
- [ ] Crear MAESTRO_PROVEEDORES.xlsx unificado

### FASE 2 - Consolidar existente
- [ ] clasificador.py con menú interactivo
- [ ] Integrar parser_n43.py (ya creado)
- [ ] Añadir ESTADO_PAGO y MOVIMIENTO_# a Facturas
- [ ] Generar REVISAR_XTxx.txt

### FASE 3 - Ventas
- [ ] Parser Loyverse
- [ ] Parser WooCommerce
- [ ] VENTAS_XTxx.xlsx

### FASE 4 - Cuadre completo
- [ ] cuadre.py (Compras ↔ Banco)
- [ ] Cuadre Ventas ↔ Banco (TPV)
- [ ] Informes consolidados

### FASE 5 - Automatización Gmail
- [ ] gmail_facturas.py
- [ ] Detección facturas en email
- [ ] Renombrado automático
- [ ] Subida a Dropbox
- [ ] Generación SEPA
- [ ] Ejecución automática viernes

---

## 18. REGLAS CRÍTICAS PARA CLAUDE

1. **LEER** este documento completo antes de trabajar
2. **VERIFICAR** si existe antes de crear (extractores, clasificadores)
3. **SIEMPRE** entregar archivos .py COMPLETOS
4. **PROBAR** antes de entregar
5. **PREGUNTAR** si hay duda
6. **NUNCA INVENTAR** - si no hay coincidencia clara → REVISAR
7. **ACTUALIZAR** documentación al final de cada sesión

---

*Documento maestro v2.1 - Actualizar en cada sesión con cambios estructurales*
*Última actualización: 08/01/2026*

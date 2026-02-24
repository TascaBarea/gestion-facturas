# 📐 ESQUEMA PROYECTO GESTIÓN-FACTURAS

**Versión:** 2.5  
**Fecha:** 14/02/2026  
**Estado:** DEFINITIVO - Base para desarrollo

---

## 1. VISIÓN GENERAL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GESTIÓN-FACTURAS                                    │
│                    Sistema Integrado de Facturación                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│   │    Ⓐ    │    │    Ⓑ    │    │    Ⓒ    │    │    Ⓓ    │                 │
│   │ PARSEO  │    │  GMAIL  │    │ VENTAS  │    │ CUADRE  │                 │
│   │  ✅ 85% │    │  ✅ 97% │    │  ❌ 0%  │    │  ✅ 70% │                 │
│   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘                 │
│        │              │              │              │                       │
│        ▼              ▼              ▼              ▼                       │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│   │ COMPRAS │    │  PAGOS  │    │ VENTAS  │    │ COMPRAS │                 │
│   │  .xlsx  │    │  .xlsx  │    │  .xlsx  │    │ CUADRADO│                 │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DOCUMENTOS DEL SISTEMA (6 Excel)

| # | Nombre | Archivo Ejemplo | Pestañas | Generado por | Usado por |
|---|--------|-----------------|----------|--------------|-----------|
| ① | **COMPRAS** | COMPRAS_1T26v1.xlsx | Lineas + Facturas | Ⓐ PARSEO | Ⓓ CUADRE |
| ② | **PAGOS_GMAIL** | PAGOS_Gmail_1T26.xlsx | FACTURAS + SEPA | Ⓑ GMAIL | Control pagos |
| ②b | **FACTURAS_PROV** | Facturas 1T26 Provisional.xlsx | Facturas | Ⓑ GMAIL | Gestoría |
| ③ | **VENTAS** | VENTAS_1T26.xlsx | TASCA + COMESTIBLES + WOO | Ⓒ VENTAS | Informes |
| ④ | **PROVEEDORES** | MAESTRO_PROVEEDORES.xlsx | 1 | MANUAL | Ⓐ Ⓑ Ⓓ |
| ⑤ | **MOVIMIENTOS_BANCO** | MOV_BANCO_1T26.xlsx | TASCA + COMESTIBLES | NORMA43/Excel Sabadell | Ⓓ CUADRE |
| ⑥ | **ARTICULOS** | ARTICULOS.xlsx | 1-2 | LOYVERSE (manual) | Ⓒ VENTAS |

---

## 3. FUNCIONES DEL SISTEMA (4 principales)

### Ⓐ PARSEO (85% completado)
```
UBICACIÓN:     C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\
ENTRADA:       Carpeta con PDFs de facturas + MAESTRO_PROVEEDORES
SALIDA:        COMPRAS_XTxx.xlsx (Lineas + Facturas)
INICIO:        MANUAL (menú)
FRECUENCIA:    Mensual/Trimestral
ESTADO:        ✅ Funciona - 97 extractores dedicados
```

### Ⓑ GMAIL (97% completado) ✅ v1.6
```
UBICACIÓN:     C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\
ENTRADA:       Gmail (etiqueta FACTURAS) + MAESTRO_PROVEEDORES
SALIDA:        - PDFs descargados y renombrados en Dropbox local
               - PAGOS_Gmail_XTxx.xlsx (FACTURAS + SEPA)
               - PROVEEDORES_NUEVOS_*.txt (sugerencias)
               - ⚠️_IBANS_SUGERIDOS_*.xlsx (verificación)
INICIO:        AUTOMÁTICO (viernes 03:00) o MANUAL
FRECUENCIA:    Semanal
ESTADO:        ✅ v1.6 - Anti-duplicados, auto-reconexión, anti-suspensión
NOVEDADES v1.6:
               P1 - ANTI-DUPLICADOS:
               - JSON se guarda atómicamente tras CADA email (no al final)
               - Emails se mueven a PROCESADAS ANTES de procesar
               - Emails sin adjuntos/reenvíos/errores se registran en JSON
               - Retry con backoff exponencial para mover emails
               P2 - AUTO-RECONEXIÓN:
               - Detecta WinError 10054 y errores de red
               - Reconecta automáticamente Gmail API con refresco de credenciales
               - 5 métodos API protegidos con _api_call wrapper
               P3 - SANITIZACIÓN NOMBRES:
               - Limpieza de puntos/comas tras eliminar S.A., S.L.
               - Caracteres Windows prohibidos eliminados (" * : < > ? |)
               - Extrae email real de display names con comillas
               P4 - EXTRACTORES CORREGIDOS:
               - sabores_paterna.py: fallback TOTAL: para facturas sin IRPF
               - gredales.py: regex acepta punto decimal (283.14€)
               - Extractor genérico: refs mínimo 3 chars + blacklist basura
               - Fallback OCR en _usar_extractor_dedicado para PDFs imagen
               P5 - ANTI-SUSPENSIÓN:
               - gmail_auto.bat desactiva suspensión con powercfg
               - ping wait en vez de timeout /t (no se pausa)
               - Restaura suspensión al finalizar (siempre)
NOVEDADES v1.5:
               - Mover TODOS los emails a FACTURAS_PROCESADAS (reenvíos, sin adjuntos, errores)
               - Evita reprocesar los mismos emails cada semana
               - gmail_auto.bat mejorado (espera 60s, timestamps, verificaciones red/token)
NOVEDADES v1.4:
               - Integración 97 extractores PARSEO
               - LocalDropboxClient (copia directa a carpeta sincronizada)
               - ATRASADAS detecta facturas de trimestres anteriores
               - Pestaña SEPA con IBANs y datos para pagos
               - Emails marcados como leídos
```

### Ⓒ VENTAS (0% - CREAR)
```
UBICACIÓN:     gestion-facturas/ventas/
ENTRADA:       - CSV Loyverse (TASCA + COMESTIBLES)
               - CSV/API Woocommerce (cursos)
               - ARTICULOS.xlsx (catálogo)
SALIDA:        VENTAS_XTxx.xlsx (3 pestañas)
INICIO:        MANUAL → futuro AUTOMÁTICO
FRECUENCIA:    Mensual
ESTADO:        ❌ Por crear
```

### Ⓓ CUADRE (70% - FUNCIONAL)
```
UBICACIÓN:     gestion-facturas/cuadre/banco/cuadre.py
ENTRADA:       - Excel gestoría (Tasca + Comestibles + Facturas)
               - MAESTRO_PROVEEDORES.xlsx
SALIDA:        - Excel con Categoria_Tipo + Categoria_Detalle
               - Columna Origen en hoja Facturas
               - Archivo LOG con decisiones
INICIO:        MANUAL (GUI selección archivo)
FRECUENCIA:    Mensual/Trimestral
VERSIÓN:       v1.4
ESTADO:        ✅ Funciona - Pendiente clasificadores adicionales
```

---

## 4. ESTRUCTURA DE CARPETAS

```
C:\_ARCHIVOS\TRABAJO\Facturas\
│
├── Parseo\                          ← Ⓐ PARSEO (FUNCIONA)
│   ├── extractores\                 ← 97 extractores específicos
│   ├── nucleo\
│   ├── salidas\
│   ├── outputs\
│   └── main.py
│
├── gestion-facturas\                ← PROYECTO UNIFICADO
│   │
│   ├── gmail\                       ← Ⓑ GMAIL (✅ v1.6)
│   │   ├── gmail.py                 ← Módulo principal v1.6 (~2130 líneas)
│   │   ├── credentials.json         ← OAuth Google
│   │   ├── token.json               ← Token Gmail (generado)
│   │   ├── gmail_auto.bat           ← Script automatización v1.6 (anti-suspensión+powercfg)
│   │   └── generar_sepa.py          ← Generador XML SEPA
│   │
│   ├── ventas\                      ← Ⓒ VENTAS (por crear)
│   │   ├── loyverse.py
│   │   ├── woocommerce.py
│   │   └── consolidar.py
│   │
│   ├── cuadre\                      ← Ⓓ CUADRE (v1.4)
│   │   └── banco\
│   │       └── cuadre.py
│   │
│   ├── datos\                       ← Documentos maestros
│   │   ├── MAESTRO_PROVEEDORES.xlsx ← 185+ proveedores
│   │   ├── DiccionarioProveedoresCategoria.xlsx
│   │   └── emails_procesados.json   ← Control duplicados Gmail
│   │
│   ├── src\                         ← Código compartido
│   │   └── extractores\             ← (vacío, usa Parseo/extractores)
│   │
│   ├── inputs\                      ← Archivos de entrada
│   │   ├── facturas\
│   │   ├── banco\
│   │   └── loyverse\
│   │
│   └── outputs\                     ← Archivos generados
│       ├── PAGOS_Gmail_XTxx.xlsx
│       ├── PROVEEDORES_NUEVOS_*.txt
│       ├── ⚠️_IBANS_SUGERIDOS_*.xlsx
│       ├── logs_gmail\
│       └── backups\
│
└── _archivo\                        ← Histórico/backup
```

---

## 5. Ⓐ PARSEO - EXTRACTORES (97 total)

### 5.1 Estado de Extractores

| Categoría | Extractores | Tasa Éxito | Notas |
|-----------|-------------|------------|-------|
| **Alimentación** | 45 | 95% | BERNAL, ECOFICUS, MRM, PORVAZ... |
| **Bebidas** | 18 | 90% | Cervezas, vinos, refrescos |
| **Servicios** | 15 | 85% | Telefonía, energía, seguros |
| **Material** | 12 | 80% | Papelería, envases |
| **OCR** | 7 | 75% | LA LLILDIRIA, CASA DEL DUQUE... |

### 5.2 Extractores Corregidos (13/02/2026 - v1.6)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **SABORES PATERNA** | `extraer_total` solo buscaba IRPF, no TOTAL: | Fallback `TOTAL: XXX,XX` | 100% |
| **GREDALES** | `extraer_total` regex no aceptaba punto decimal | `[\d,]+` → `[\d.,]+` | 100% |
| **LA LLILDIRIA** | gmail.py ignoraba `metodo_pdf='ocr'` → texto vacío | Fallback OCR en `_usar_extractor_dedicado` | 100% |
| **Genérico** | Refs basura: "erence", "R", "PEDIDO" | Mínimo 3 chars + blacklist `REF_INVALIDAS` | 90% |

### 5.3 Extractores Corregidos (06/02/2026)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **BERNAL** | No extraía total (multilínea) ni ref | Regex multilínea `Total Factura:\n...\nXXX €` + `Factura X Fecha` | 100% |
| **DE LUIS** | No extraía ref (encoding ú) | `N[úu]mero` + fallback `Concepto:` | 100% |
| **TERRITORIO CAMPERO** | No extraía ref (`NUMERO` sin acento) | `N[ÚU]MERO DE FACTURA:` | 100% |
| **YOIGO** | No extraía ref (encoding) | Búsqueda directa `YC\d{10,15}` | 100% |

### 5.4 Extractores Corregidos (03/02/2026)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **YOIGO** | Encoding `(cid:128)` vs `€` | Eliminar € de patrones | 100% |
| **MRM** | Patrón muy complejo | Simplificado | 100% |
| **BERNAL** | Portes IVA 21% no distribuidos | Reparto proporcional | 100% |
| **LA MOLIENDA VERDE** | 2× líneas de portes | Suma + reparto | 100% |
| **ECOFICUS** | IVA mixto (4%/10%/21%) + encoding | Reparto por grupo IVA | 100% |
| **PORVAZ** | Descuento 3% como línea negativa | Patrón con `%` | 100% |
| **LA LLILDIRIA** | OCR + formatos variados | Patrón flexible | 100% |

### 5.5 Fórmula Distribución Portes (IVA diferente)

```python
# Cuando portes tienen IVA diferente al de productos:
portes_equiv = (portes_base × (1 + IVA_portes/100)) / (1 + IVA_productos/100)

# Ejemplo: Portes 10€ al 21%, productos al 10%
portes_equiv = (10 × 1.21) / 1.10 = 11€ base equivalente al 10%

# Si hay IVA mixto (4% y 10%), ponderar por grupo:
proporcion_4 = suma_base_4% / suma_total
proporcion_10 = suma_base_10% / suma_total
portes_equiv_4 = (portes_con_iva × proporcion_4) / 1.04
portes_equiv_10 = (portes_con_iva × proporcion_10) / 1.10
```

---

## 5.6 ARQUITECTURA DE EXTRACTORES

### 5.6.1 Estructura del Paquete

```
Parseo/extractores/
├── __init__.py          ← Carga automática + registro global + obtener_extractor()
├── base.py              ← ExtractorBase (clase abstracta, métodos genéricos)
├── _plantilla.py        ← Plantilla para crear extractores nuevos
├── generico.py          ← Extractor fallback (menor prioridad, se carga último)
├── abbati.py            ← 90 extractores dedicados...
├── bernal.py
├── ...
└── zucca.py
```

### 5.6.2 Flujo de Carga

`__init__.py` carga **automáticamente** todos los `.py` de la carpeta (excepto `base.py`, `generico.py`, `_plantilla.py`). Cada archivo se registra con `@registrar('NOMBRE1', 'NOMBRE2', ...)`. Al buscar un proveedor, `obtener_extractor()` hace búsqueda exacta primero, luego parcial.

### 5.6.3 Clase Base: ExtractorBase

```python
class ExtractorBase(ABC):
    # ATRIBUTOS DE CLASE (obligatorios en subclases)
    nombre: str       # Nombre del proveedor
    cif: str          # CIF del proveedor
    iban: str         # IBAN (vacío si pago tarjeta/efectivo)
    metodo_pdf: str   # 'pdfplumber' | 'ocr' | 'hibrido'

    # MÉTODO ABSTRACTO (obligatorio implementar)
    def extraer_lineas(self, texto) -> List[Dict]    # Líneas de producto

    # MÉTODOS OPCIONALES (sobrescribir si formato especial)
    def extraer_total(self, texto) -> float           # Por defecto: patrones genéricos
    def extraer_fecha(self, texto) -> str             # Por defecto: DD/MM/YYYY
    def extraer_referencia(self, texto) -> str        # Por defecto: patrones genéricos
    def extraer_numero_factura(self, texto) -> str    # Alias, prioridad sobre extraer_referencia

    # UTILIDADES HEREDADAS
    def _convertir_importe(self, texto) -> float      # Español/americano → float
    def _calcular_base_desde_total(total, iva)        # Total con IVA → base
    def _calcular_total_desde_base(base, iva)         # Base → total con IVA
    def _limpiar_texto(texto) -> str                  # Limpiar espacios/saltos
    def _es_referencia_valida(ref) -> bool             # Filtro anti-falsos positivos
```

### 5.6.4 Formato del Dict de Línea (extraer_lineas)

```python
{
    'articulo': str,      # Nombre del producto (OBLIGATORIO)
    'base': float,        # Importe SIN IVA (OBLIGATORIO)
    'iva': int,           # Porcentaje IVA: 4, 10 o 21 (OBLIGATORIO)
    'codigo': str,        # Código producto (opcional)
    'cantidad': float,    # Cantidad (opcional)
    'precio_ud': float,   # Precio unitario (opcional)
    'categoria': str,     # Categoría forzada (opcional, raro)
}
```

### 5.6.5 Estadísticas (90 extractores)

| Concepto | Valor |
|---|---|
| Total extractores | 90 |
| Método pdfplumber | 81 (90%) |
| Método OCR | 7 (8%): fishgourmet, gaditaun, jimeluz, la_cuchara, la_lleidiria, manipulados_abellan, tirso |
| Método híbrido | 2 (2%): angel_borja, casa_del_duque |
| Con extraer_total propio | 90 (100%) |
| Con extraer_fecha propio | 90 (100%) |
| Con extraer_referencia o extraer_numero_factura | 89 (~99%) |
| Con distribución de portes | 11: angel_loli, arganza, bernal, ecoficus, felisa, fernando_moro, molienda_verde, montbrione, pago_de_las_olmas, porvaz, zucca |
| Con categoría fija | 43 (~48%) |
| IVA 4% (alimentación básica) | 7 extractores |
| IVA 10% (alimentación) | 18 extractores |
| IVA 21% (servicios/general) | 36 extractores |

### 5.6.6 Reglas de Negocio

**PORTES/ENVÍO:** SIEMPRE distribuir proporcionalmente entre productos. NUNCA línea separada.
```python
# Fórmula cuando portes tienen IVA diferente al de productos:
portes_equiv = (portes_base × (1 + IVA_portes/100)) / (1 + IVA_productos/100)
# Si IVA mixto (4% y 10%), ponderar por peso de cada grupo
```

**IVA:** Usar tipo real del producto (4% lácteos/pan, 10% alimentación, 21% servicios/bebidas alcohólicas). Cada extractor define el IVA de sus productos.

**REFERENCIA:** Filtro anti-falsos positivos en `_es_referencia_valida()`: excluye teléfonos, CIFs, fechas, números de cliente, palabras sueltas. Mínimo 3 caracteres y 2 dígitos.

**OCR:** Para PDFs imagen (sin texto extraíble). Usa `pytesseract` + `pdf2image` con `lang='spa'`. Los extractores OCR definen `metodo_pdf = 'ocr'`.

**CATEGORÍA FIJA:** 43 extractores asignan categoría automáticamente (ej: `categoria_fija = 'QUESOS'`). El resto usa el DiccionarioProveedoresCategoria.

### 5.6.7 Cómo Crear un Extractor Nuevo

```
PASO 1: Copiar plantilla
   cp extractores/_plantilla.py → extractores/nuevo_proveedor.py

PASO 2: Configurar atributos
   @registrar('NOMBRE PROVEEDOR', 'ALIAS1', 'ALIAS2')
   class ExtractorNuevoProveedor(ExtractorBase):
       nombre = 'NOMBRE PROVEEDOR'
       cif = 'B12345678'
       iban = 'ES00 0000 0000 00'
       metodo_pdf = 'pdfplumber'       # o 'ocr' si es imagen

PASO 3: Implementar extraer_lineas()
   - Analizar el texto del PDF (imprimir texto crudo primero)
   - Escribir regex para capturar líneas de producto
   - Devolver lista de dicts con articulo, base, iva

PASO 4: Sobrescribir métodos opcionales (si formato especial)
   - extraer_total() si el total no sigue patrón genérico
   - extraer_fecha() si la fecha no es DD/MM/YYYY
   - extraer_numero_factura() si la referencia es especial

PASO 5: Probar
   python tests/probar_extractor.py "NUEVO PROVEEDOR" factura.pdf

PASO 6: El extractor se carga automáticamente (sin tocar __init__.py)
```

### 5.6.8 Convenciones de Código

- Archivo: `nombre_proveedor.py` (snake_case, sin tildes)
- Clase: `ExtractorNombreProveedor` (CamelCase)
- Imports: `from extractores.base import ExtractorBase` + `from extractores import registrar`
- Docstring: Describir formato factura, IVA, productos, fecha creación
- `@registrar()`: Incluir nombre oficial + alias comunes (mayúsculas)
- Método `_convertir_europeo()`: Privado si el extractor necesita conversión propia
- PORTES: Detectar línea de portes, calcular equivalente, distribuir proporcionalmente


---

## 6. Ⓑ GMAIL v1.6 - DETALLE TÉCNICO

### 6.1 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Ⓑ GMAIL MODULE v1.6                               │
│                                                                             │
│  ┌──────────────┐                                                           │
│  │   GMAIL API  │                                                           │
│  │  (FACTURAS)  │                                                           │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ P1: ¿Ya en   │ SÍ  │   SALTAR    │ (emails_procesados.json)             │
│  │ JSON?        │────►│  (no dupl.) │                                      │
│  └──────┬───────┘     └──────────────┘                                      │
│         │ NO                                                                │
│         ▼                                                                   │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ Filtrar      │     │   EMAILS     │                                      │
│  │ Reenvíos     │────►│  IGNORAR     │ (tascabarea@gmail.com)               │
│  └──────┬───────┘     └──────────────┘                                      │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐                                                           │
│  │ MOVER A      │ ← P1: mover ANTES de procesar                           │
│  │ PROCESADAS   │    (retry con backoff exponencial)                       │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ Identificar  │◄───►│   MAESTRO    │                                      │
│  │ Proveedor    │     │ PROVEEDORES  │                                      │
│  └──────┬───────┘     └──────────────┘                                      │
│         │                                                                   │
│         ├──────────────────┬──────────────────┐                             │
│         ▼                  ▼                  ▼                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                     │
│  │ IDENTIFICADO │   │  ATRASADA    │   │ DESCONOCIDO  │                     │
│  │ TF/RC/EF...  │   │ Trim < actual│   │ Prov nuevo   │                     │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                     │
│         │                  │                  │                             │
│         ▼                  ▼                  ▼                             │
│  ┌──────────────────────────────────────────────────────┐                   │
│  │              Descargar PDFs → Dropbox                │                   │
│  │  TRIM_MMDD_PROVEEDOR_TIPO.pdf                        │                   │
│  │  ATRASADA_MMDD_PROVEEDOR_TIPO.pdf (en subcarpeta)    │                   │
│  └──────────────────────────────────────────────────────┘                   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────────────────────────────────────────┐                   │
│  │  P1: Registrar en JSON + guardar atómicamente       │                   │
│  │  P2: Auto-reconexión si WinError 10054              │                   │
│  └──────────────────────────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Ⓓ CUADRE v1.4 - DETALLE

### 7.1 Clasificadores Implementados

| Clasificador | Detecta | Categoria_Tipo | Categoria_Detalle |
|--------------|---------|----------------|-------------------|
| **TPV** | `ABONO TPV`, `COMISIONES` | TPV TASCA / COMISION TPV | Número remesa |
| **Transferencia** | `TRANSFERENCIA A` | Proveedor | #factura |
| **Compra tarjeta** | `COMPRA TARJ` | Proveedor | #factura |
| **Adeudo/Recibo** | `ADEUDO RECIBO` | Proveedor | #factura (ref) |
| **Som Energia** | `SOM ENERGIA` | SOM ENERGIA SCCL | #factura (FExxxxxx) |
| **Yoigo** | `YOIGO` | XFERA MOVILES SAU | #factura |
| **Comunidad** | `COM PROP` | COMUNIDAD DE VECINOS | Dirección |
| **Suscripciones** | `LOYVERSE`, `SPOTIFY` | GASTOS VARIOS | Sin factura |
| **Alquiler** | `BENJAMIN ORTEGA` | ALQUILER | Local |

---

## 8. FLUJO DE TRABAJO COMPLETO

```
                    SEMANAL                         MENSUAL
                       │                               │
                       ▼                               ▼
              ┌────────────────┐              ┌────────────────┐
              │   Ⓑ GMAIL     │              │   Ⓐ PARSEO    │
              │ Descargar PDFs │              │ Procesar PDFs  │
              │ (automático)   │              │ (manual)       │
              └───────┬────────┘              └───────┬────────┘
                      │                               │
                      ▼                               ▼
              ┌────────────────┐              ┌────────────────┐
              │ PAGOS_Gmail    │              │    COMPRAS     │
              │ _XTxx.xlsx     │              │   _XTxx.xlsx   │
              └───────┬────────┘              └───────┬────────┘
                      │                               │
                      ▼                               │
              ┌────────────────┐                      │
              │ Revisar +      │                      │
              │ Pagar TF       │                      │
              └───────┬────────┘                      │
                      │                               │
                      ▼                               ▼
              ┌────────────────┐              ┌────────────────┐
              │ Movimientos    │              │   Ⓓ CUADRE    │◀── MOV_BANCO
              │ Banco          │─────────────►│ Marcar pagadas │
              └────────────────┘              └───────┬────────┘
                                                      │
                                                      ▼
                                              ┌────────────────┐
                                              │   COMPRAS      │
                                              │   CUADRADO     │
                                              └────────────────┘
```

---

## 9. PRIORIDADES DE DESARROLLO

| Prioridad | Función | Descripción | Estado |
|-----------|---------|-------------|--------|
| ~~1️⃣~~ | ~~Ⓑ GMAIL~~ | ~~Descargar + renombrar~~ | ✅ **v1.6** |
| ~~2️⃣~~ | ~~Extractores PARSEO~~ | ~~Mejorar tasa de éxito (85%→95%)~~ | ✅ **97 extractores** |
| 3️⃣ | Ⓓ CUADRE integración | Conectar con COMPRAS (ESTADO_PAGO) | 🟡 Pendiente |
| 4️⃣ | Ⓒ VENTAS | Loyverse + Woocommerce | ❌ Por crear |
| 5️⃣ | Integrar | Mover PARSEO a gestion-facturas | ❌ Futuro |
| 6️⃣ | Informes | Dashboards y análisis | ❌ Futuro |

---

## 10. CUENTAS BANCARIAS

| Cuenta | IBAN | Empresa | Uso |
|--------|------|---------|-----|
| TASCA | REDACTED_IBAN | TASCA BAREA SLL | Bar |
| COMESTIBLES | REDACTED_IBAN | COMESTIBLES BAREA | Tienda |
| BIC | REDACTED_BIC | Banco Sabadell | Ambas |

---

## 11. NOMENCLATURA ARCHIVOS

```
COMPRAS_1T26v1.xlsx        → Compras 1er trimestre 2026, versión 1
PAGOS_Gmail_1T26.xlsx      → Pagos Gmail 1er trimestre 2026
VENTAS_2T26.xlsx           → Ventas 2do trimestre 2026
MOV_BANCO_1T26.xlsx        → Movimientos banco 1er trimestre 2026
Cuadre_011025-020126.xlsx  → Cuadre del 01/10/25 al 02/01/26
```

---

## 12. DROPBOX - ESTRUCTURA

```
C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\
│
├── FACTURAS 2025\
│   └── FACTURAS RECIBIDAS\
│       ├── 1 TRIMESTRE 2025\
│       ├── 2 TRIMESTRE 2025\
│       ├── 3 TRIMESTRE 2025\
│       └── 4 TRIMESTRE 2025\
│
└── FACTURAS 2026\
    └── FACTURAS RECIBIDAS\
        ├── 1 TRIMESTRE 2026\          ← PDFs de Gmail van aquí
        │   ├── 1T26 0115 ACEITES JALEO TF.pdf
        │   ├── 1T26 0120 CERES CERVEZA SL RC.pdf
        │   ├── ATRASADAS\             ← Facturas de trimestres anteriores
        │   │   └── 4T25\
        │   │       └── ATRASADA 4T25 1230 CONSERVERA TF.pdf
        │   └── ...
        ├── 2 TRIMESTRE 2026\
        ├── 3 TRIMESTRE 2026\
        └── 4 TRIMESTRE 2026\
```

---

## CHANGELOG

### v2.5 (14/02/2026)
- ✅ **Documentación extractores**: Nueva sección 5.6 con arquitectura completa
  - Estructura del paquete, flujo de carga, clase base
  - Formato del dict de línea, estadísticas (90 extractores)
  - Reglas de negocio (portes, IVA, OCR, categorías)
  - Guía paso a paso para crear extractor nuevo
  - Convenciones de código
- ✅ **Nuevo Excel de salida**: `Facturas 1T26 Provisional.xlsx` (6+1 columnas)
  - Se genera ADEMÁS del PAGOS_Gmail
  - Detección de duplicados por NOMBRE → columna OBS="DUPLICADO"
  - Formato: NOMBRE | PROVEEDOR | Fec.Fac. | Factura | Total | Origen | OBS

### v2.4 (13/02/2026)
- ✅ **GMAIL actualizado a v1.6** — 5 parches (P1-P5) basados en diagnóstico de 6 logs de producción
- ✅ **P1 Anti-duplicados**: JSON atómico tras cada email, mover a PROCESADAS antes de procesar, registro de emails sin adjuntos/reenvíos/errores, retry con backoff exponencial
- ✅ **P2 Auto-reconexión**: Detecta WinError 10054, reconecta Gmail API automáticamente, 5 métodos protegidos con wrapper `_api_call`
- ✅ **P3 Sanitización nombres**: Limpieza puntos/comas S.A./S.L., chars Windows prohibidos, extracción email real de display names
- ✅ **P4 Extractores corregidos**:
  - sabores_paterna.py: fallback `TOTAL:` para facturas sin IRPF
  - gredales.py: regex acepta punto decimal (283.14€)
  - Extractor genérico: refs mínimo 3 chars + blacklist `REF_INVALIDAS`
  - Fallback OCR en `_usar_extractor_dedicado` para PDFs imagen (La Llildiria)
- ✅ **P5 Anti-suspensión**: `powercfg` desactiva standby durante ejecución (AC=0/DC=0), `ping wait` en vez de `timeout /t`, restaura valores originales (AC=5min/DC=3min) al finalizar
- ⚠️ **Pendiente MAESTRO**: Dar de alta ALTO LANDÓN, HORNO SANTO CRISTO, LIDL, BODEGAS FIGUEROA + 7 alias de emails
- ⚠️ **Pendiente extractores**: MOLLETES ARTESANOS y GARUA (poner TIENE_EXTRACTOR=NO o crear)
- ⚠️ **Pendiente extractores nuevos**: ODOO, ISIFAR, ACHILIPÚ, ALTO LANDÓN, IKEA (necesitan PDFs de ejemplo)

### v2.3 (06/02/2026)
- ✅ **GMAIL actualizado a v1.5**: Mover TODOS los emails a FACTURAS_PROCESADAS
  - Reenvíos, sin adjuntos, imágenes, errores → todos salen de FACTURAS
  - Evita reprocesar 50 emails repetidos cada semana
- ✅ **gmail_auto.bat v1.5**: Espera 60s al inicio, timestamps detallados, verificaciones (Python, token, internet)
- ✅ **Token OAuth investigado**: Causa probable = encoding/sesión. Con ejecución semanal no volverá a expirar
- ✅ **BERNAL corregido**: extraer_total (multilínea) + extraer_referencia (Factura X Fecha)
- ✅ **DE LUIS corregido**: extraer_referencia (`N[úu]mero` + fallback Concepto)
- ✅ **TERRITORIO CAMPERO corregido**: extraer_referencia (`N[ÚU]MERO` sin acento)
- ✅ **YOIGO corregido**: extraer_referencia (búsqueda directa YC + dígitos)
- ✅ **MAESTRO actualizado**: Añadidos emails de LA CAMPERA ANDALUZA, LA BARRA DULCE, JULIO GARCIA VIVAS
- ⚠️ **Pendiente dar de alta**: ALTO LANDÓN, HORNO SANTO CRISTO en MAESTRO
- ⚠️ **Pendiente verificar**: Email real de MOLLETES ARTESANOS (¿distinto de info@?)
- ⚠️ **Pendiente**: Extractores sin total (LA LLILDIRIA, GARUA, GREDALES, ISIFAR, ODOO, ACHILIPÚ)

### v2.2 (03/02/2026)
- ✅ **PARSEO mejorado: 91→97 extractores** (+6 nuevos/corregidos)
- ✅ Corregido YOIGO (encoding €)
- ✅ Corregido MRM (patrón simplificado)
- ✅ Corregido BERNAL (portes IVA 21% distribuidos)
- ✅ Corregido LA MOLIENDA VERDE (2× portes sumados)
- ✅ Corregido ECOFICUS (IVA mixto 4%/10%/21%)
- ✅ Corregido PORVAZ (descuento 3% negativo)
- ✅ Corregido LA LLILDIRIA (OCR + patrón flexible)
- ✅ Documentada fórmula distribución portes IVA diferente
- ✅ Validación completa: 22/22 facturas OK

### v2.1 (02/02/2026)
- ✅ Gmail actualizado a v1.4
- ✅ Integración 91 extractores PARSEO
- ✅ LocalDropboxClient (carpeta sincronizada)
- ✅ Pestaña SEPA para pagos
- ✅ Lógica ATRASADAS corregida
- ✅ Emails marcados como leídos
- ✅ Automatización viernes 03:00
- ✅ Estadísticas actualizadas (50% éxito)

### v2.0 (30/01/2026)
- ✅ Añadido Ⓑ GMAIL como módulo funcional (80% éxito)
- ✅ Documentada estructura completa de GMAIL
- ✅ Actualizado MAESTRO_PROVEEDORES con nuevas columnas
- ✅ Añadida estructura Dropbox
- ✅ Eliminado SEPA del esquema
- ✅ Actualizado estado de funciones

### v1.1 (28/01/2026)
- Ampliado detalle de Ⓓ CUADRE (sección 7)

### v1.0 (27/01/2026)
- Versión inicial del esquema

---

**Documento de referencia para todas las sesiones futuras.**

✅ **APROBADO POR:** Tasca  
📅 **FECHA:** 14/02/2026

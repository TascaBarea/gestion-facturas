# ESQUEMA COMPLETO DEL PROYECTO - ParsearFacturas

**Versión:** v5.14  
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
├── 📄 main.py                    # ⭐ SCRIPT PRINCIPAL (v5.12, ~1500 líneas)
│                                  #    - Orquesta todo el flujo
│                                  #    - Contiene ALIAS_DICCIONARIO
│                                  #    - Función prorratear_portes()
│
├── 📁 extractores/               # ⭐ UN ARCHIVO POR PROVEEDOR (~95 archivos)
│   ├── __init__.py               #    - Registro automático con @registrar
│   ├── base.py                   #    - Clase base ExtractorBase
│   ├── generico.py               #    - Extractor fallback
│   ├── silva_cordero.py          #    - Ejemplo: quesos
│   ├── la_alacena.py             #    - Ejemplo: conservas
│   ├── zucca.py                  #    - Ejemplo: quesos italianos
│   ├── berzal.py                 #    - Ejemplo: mantequillas
│   ├── ceres.py                  #    - Ejemplo: varios
│   └── ... (~90 más)
│
├── 📁 nucleo/                    # LÓGICA CORE
│   ├── factura.py                #    - Clases Factura, LineaFactura
│   ├── parser.py                 #    - Funciones de parsing genéricas
│   ├── pdf.py                    #    - Extracción de texto (pdfplumber/OCR)
│   └── validacion.py             #    - Validación de cuadre
│
├── 📁 salidas/                   # GENERACIÓN DE OUTPUTS
│   └── excel.py                  #    - Genera Excel con hojas Lineas/Facturas
│
├── 📁 config/                    # CONFIGURACIÓN
│   └── settings.py               #    - VERSION, CIF_PROPIO, rutas
│
├── 📁 datos/                     # ⚠️ DATOS MAESTROS (NO MODIFICAR)
│   ├── DiccionarioProveedoresCategoria.xlsx  # Artículos + categorías
│   ├── DiccionarioEmisorTitulo.xlsx          # Cuentas contables
│   └── MAESTROS.xlsx                         # Proveedores + IBANs
│
├── 📁 docs/                      # DOCUMENTACIÓN
│   ├── LEEME_PRIMERO_v5_XX.md    #    - Leer SIEMPRE al inicio
│   ├── ESTADO_PROYECTO_v5_XX.md  #    - Estado actual
│   └── SESION_DDMMAAAA_v5_XX.md  #    - Registro de cada sesión
│
├── 📁 logs/                      # LOGS DE EJECUCIÓN
│   └── log_YYYYMMDD_HHMM.txt
│
├── 📁 legacy/                    # Código antiguo (no usar)
├── 📁 samples/                   # PDFs de ejemplo para pruebas
├── 📁 scripts/                   # Scripts auxiliares
├── 📁 tools/                     # Herramientas varias
├── 📁 out/ outputs/ outs/        # Carpetas de salida Excel
│
└── 📄 Otros archivos raíz:
    ├── requirements.txt          # Dependencias Python
    ├── CHANGELOG.md              # Historial de cambios
    ├── README.md                 # Documentación general
    └── *.bat / *.ps1             # Scripts Windows
```

---

## 🔄 FLUJO DE DATOS

```
┌─────────────────┐
│  PDFs Facturas  │  Formato: XXXX_1T25_MMDD_PROVEEDOR_TF.pdf
│  (Gmail/Dropbox)│  
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    main.py      │  1. Lee PDF
│                 │  2. Detecta proveedor (nombre archivo + CIF)
│                 │  3. Selecciona extractor
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   extractor/    │  4. Extrae: fecha, referencia, líneas, total
│   proveedor.py  │  5. Cada línea: artículo, cantidad, precio, IVA, base
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    main.py      │  6. Normaliza proveedor (ALIAS_DICCIONARIO)
│  prorratear_    │  7. Prorratea portes entre productos
│    portes()     │  8. Busca categoría en diccionario
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   validacion    │  9. Compara suma líneas vs total factura
│   cuadre        │  10. Marca OK / DESCUADRE_XX.XX
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  salidas/excel  │  11. Genera Excel con:
│                 │      - Hoja "Lineas" (detalle productos)
│                 │      - Hoja "Facturas" (cabeceras)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Facturas_      │  Archivo final para contabilidad
│  1T25.xlsx      │
└─────────────────┘
```

---

## 📋 FORMATO NOMBRE ARCHIVO

```
XXXX_1T25_MMDD_PROVEEDOR_TF.pdf
│    │    │    │         │
│    │    │    │         └── Tipo pago: TF=Transferencia
│    │    │    │                        RC/REC=Recibo (domiciliación)
│    │    │    │                        TJ=Tarjeta
│    │    │    │
│    │    │    └── Nombre proveedor
│    │    │
│    │    └── Fecha: Mes + Día (ej: 0725 = 25 julio)
│    │
│    └── Trimestre + Año: 1T25 = 1er trimestre 2025
│
└── Número correlativo gestoría (4 dígitos)
```

---

## 🔧 ESTRUCTURA DE UN EXTRACTOR

```python
# extractores/ejemplo.py

from extractores.base import ExtractorBase
from extractores import registrar

@registrar('NOMBRE_PROVEEDOR', 'ALIAS1', 'ALIAS2')  # Nombres que activan este extractor
class ExtractorEjemplo(ExtractorBase):
    
    nombre = 'NOMBRE_PROVEEDOR'           # Nombre normalizado
    cif = 'B12345678'                     # CIF del proveedor
    iban = 'ES12 1234 5678 9012 3456'     # IBAN (si tiene)
    metodo_pdf = 'pdfplumber'             # o 'ocr' para escaneados
    categoria_fija = None                 # Si todos sus productos van a una categoría
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """Extrae productos del PDF."""
        lineas = []
        # ... lógica de parsing ...
        # Cada línea debe tener:
        # {
        #     'codigo': str,
        #     'articulo': str (max 50 chars),
        #     'cantidad': float,
        #     'precio_ud': float,
        #     'iva': int (4, 10, 21),
        #     'base': float,
        #     'categoria': str (opcional si categoria_fija)
        # }
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total factura."""
        pass
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha factura (DD/MM/YYYY)."""
        pass
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número/referencia factura."""
        pass
```

---

## 📊 EXCEL DE SALIDA

### Hoja "Lineas"
| Columna | Descripción |
|---------|-------------|
| # | Número correlativo gestoría |
| FECHA | Fecha factura |
| REF | Referencia/número factura |
| PROVEEDOR | Nombre normalizado |
| ARTICULO | Descripción producto |
| CATEGORIA | Categoría asignada |
| CANTIDAD | Unidades/kg |
| PRECIO_UD | Precio unitario |
| TIPO IVA | 4, 10, 21 |
| BASE (€) | Importe sin IVA |
| CUOTA IVA | Importe IVA |
| TOTAL FAC | Total factura |
| CUADRE | OK / DESCUADRE_XX |
| ARCHIVO | Nombre PDF |
| EXTRACTOR | Clase usada |

### Hoja "Facturas"
| Columna | Descripción |
|---------|-------------|
| # | Número gestoría |
| CUENTA | Cuenta contable |
| TITULO | Nombre para contabilidad |
| Fec.Fac. | Fecha |
| REF | Referencia |
| Total | Importe total |
| OBSERVACIONES | Cuadre + notas |

---

## ⚠️ REGLAS CRÍTICAS

### Para Claude:
1. **LEER** docs/LEEME, ESTADO, SESION antes de trabajar
2. **VERIFICAR** si extractor existe antes de crear
3. **SIEMPRE** archivos .py COMPLETOS
4. **PROBAR** con PDFs reales antes de entregar
5. **PREGUNTAR** si hay duda
6. **PORTES**: extractor devuelve línea, main.py prorratea

### Para el código:
1. **PORTES** nunca como línea final en Excel
2. **categoria_fija** es fallback, diccionario tiene prioridad
3. **Limpiar __pycache__** antes de probar (main.py lo hace auto)
4. **IVA** válidos: 4 (alimentos básicos), 10 (general), 21 (servicios)

---

## 📈 MÉTRICAS ACTUALES (v5.14)

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

*Documento generado: 07/01/2026*
*Para uso interno de Claude en sesiones futuras*

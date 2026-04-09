# BENCHMARK PDF EXTRACTION - Gestion Facturas

## OBJETIVO
Comparar motores de extracción PDF (pdfplumber, PyMuPDF, pypdf, camelot, tabula) sobre facturas reales para determinar la mejor combinación/estrategia antes de refactorizar los extractores del sistema de parseo.

## ESTRUCTURA DEL PROYECTO
```
C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\
├── benchmark/                    ← ESTE PROYECTO
│   ├── CLAUDE.md                 ← Estás aquí
│   ├── benchmark_pdf.py          ← Script principal
│   └── results/                  ← Informes generados (HTML, CSV, JSON)
├── extractores/                  ← ~90 extractores actuales (NO TOCAR)
├── main.py                       ← Parser principal v5.18 (NO TOCAR)
├── datos/                        ← MAESTRO, Diccionario
└── SPEC_GESTION_FACTURAS_v3.md   ← Spec maestra (referencia)
```

## RUTAS IMPORTANTES
```
# PDFs de facturas (lectura)
DROPBOX = C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD

# Estructura por año:
{DROPBOX}\FACTURAS {AÑO}\FACTURAS RECIBIDAS\{N} TRIMESTRE {AÑO}\*.pdf
{DROPBOX}\FACTURAS {AÑO}\FACTURAS RECIBIDAS\{N} TRIMESTRE {AÑO}\ATRASADAS\*.pdf

# Años: 2025, 2026 (4 trimestres cada uno)
# Estimación: 150-300 PDFs en total

# Ground truth (xlsx):
# - Facturas_2T26_Provisional.xlsx → Tab "Facturas": NOMBRE, PROVEEDOR, Fec.Fac., Total
# - Facturas_Recibidas_25.xlsx → Tabs "AÑO 20" a "AÑO 23": #, FECHA, PROVEEDOR, BASE (líneas)
# Ubicación: donde Jaime los tenga (preguntar si no están en gestion-facturas/)
```

## NOMENCLATURA DE ARCHIVOS PDF
Los PDFs siguen estos patrones de nombre:
- **Formato A (con nº Kinema):** `1023 1T25 0307 CERES RC.pdf`
- **Formato B (sin nº):** `1T25 0307 CERES RC.pdf`  
- **Formato C (atrasada con nº):** `1023 ATRASADA 1T25 0307 CERES RC.pdf`
- **Formato D (atrasada sin nº):** `ATRASADA_1T26_0323_SABORES_DE_PATERNA_SCA_TF.pdf`

Donde: TT=trimestre, YY=año, MMDD=fecha, PROV=proveedor, MODO=TF/TR/TJ/EF/RC/Z

## QUÉ MEDIR (campos a extraer de cada PDF)
1. **TOTAL** factura (€) — cuadre con GT, tolerancia ±0.02€
2. **FECHA** factura — dd/mm/yyyy
3. **NIF/CIF** proveedor — formato español (letra + 8 dígitos o 8 dígitos + letra)
4. **LÍNEAS de producto** — descripción + CANTIDAD + PRECIO_UD + IMPORTE
5. **IVA** — tipo(s) % + importe(s)
6. **BASE IMPONIBLE** — por tipo de IVA
7. **Nº FACTURA / REF** del proveedor

## MOTORES A COMPARAR
| Motor | Tipo | Fortaleza |
|-------|------|-----------|
| pdfplumber | Texto + tablas | Tablas con bordes, coordenadas precisas |
| PyMuPDF (fitz) | Texto + bloques | Velocidad, bloques con bbox |
| pypdf | Texto básico | Ligero, rápido |
| camelot | Solo tablas | Tablas complejas (lattice + stream) |
| tabula-py | Solo tablas | Alternativa a camelot (Java) |

## ESTRATEGIAS A EVALUAR
No solo motores individuales — también combinaciones:
1. **Individual**: cada motor por separado
2. **Cascada**: pdfplumber → PyMuPDF → OCR (fallback si falla)
3. **Mejor por campo**: pdfplumber para líneas, PyMuPDF para totales, etc.
4. **Paralelo + votación**: ejecutar todos, quedarse con consenso
5. **Selector por proveedor**: registrar qué motor funciona mejor por proveedor

## GROUND TRUTH - MATCHING
- **2T26 Provisional**: match por NOMBRE (normalizado: sin extensión, underscores→espacios, UPPER)
- **Kinema histórico**: match por nº Kinema (dígitos al inicio del nombre PDF → "#" en xlsx)
- **Normalización**: quitar extensión .pdf, quitar nº Kinema inicial, _→espacio, UPPER

## FLUJO DE EJECUCIÓN
```
1. Instalar dependencias:
   pip install pdfplumber pymupdf pypdf camelot-py tabula-py openpyxl

2. Ejecutar benchmark:
   python benchmark_pdf.py --ground-truth "ruta1.xlsx" "ruta2.xlsx"
   
   Opciones:
   --sample N          Solo N PDFs aleatorios (para pruebas rápidas)
   --engines X Y Z     Solo estos motores
   --pdf-dir "ruta"    Carpeta específica en vez de Dropbox
   --years 2025 2026   Años a escanear

3. Resultados en benchmark/results/:
   - benchmark_report_TIMESTAMP.html   → Visual con ranking
   - benchmark_detail_TIMESTAMP.csv    → Cada PDF × cada motor
   - benchmark_summary_TIMESTAMP.csv   → Promedios por motor
   - benchmark_raw_TIMESTAMP.json      → Todo para análisis
```

## CRITERIO DE ÉXITO
El benchmark debe responder estas preguntas:
1. ¿Qué motor tiene mejor tasa de acierto en TOTAL?
2. ¿Qué motor extrae más líneas de producto correctamente?
3. ¿Hay proveedores donde un motor falla y otro acierta?
4. ¿La combinación cascada mejora significativamente sobre pdfplumber solo?
5. ¿Merece la pena el overhead de camelot/tabula vs los 3 básicos?

## REGLAS
- **NO MODIFICAR** nada fuera de `benchmark/`
- Los extractores existentes en `extractores/` son referencia, no los toques
- Si necesitas el MAESTRO_PROVEEDORES: está en `datos/MAESTRO_PROVEEDORES.xlsx`
- Formato decimal español: 1.234,56 (punto=miles, coma=decimales)
- Encoding: utf-8-sig para CSV (Excel España)
- Los resultados HTML deben poder abrirse directamente en navegador

## ITERACIÓN
Tras el primer benchmark:
1. Analizar los PDFs donde TODOS los motores fallan → posibles escaneados (necesitan OCR)
2. Analizar donde un motor acierta y otros no → oportunidad de cascada
3. Refinar regex de extracción genérica para los patrones más comunes
4. Proponer arquitectura final (clase PDFReader o similar)

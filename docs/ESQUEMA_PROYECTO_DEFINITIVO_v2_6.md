# 📐 ESQUEMA PROYECTO GESTIÓN-FACTURAS

**Versión:** 5.2
**Fecha:** 16/03/2026
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
│   │  ✅ 85% │    │  ✅ 97% │    │  ✅ 95% │    │  ✅ 75% │                 │
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
| ② | **PAGOS_GMAIL** | PAGOS_Gmail_1T26.xlsx | FACTURAS (15 cols) + SEPA | Ⓑ GMAIL | Control pagos |
| ②b | **FACTURAS_PROV** | Facturas 1T26 Provisional.xlsx | Facturas | Ⓑ GMAIL | Gestoría |
| ③ | **VENTAS** | Ventas Barea 2026.xlsx | TascaRecibos + TascaItems + ComesRecibos + ComesItems + WOO + GoogleBusiness | Ⓒ VENTAS | Informes |
| ④ | **PROVEEDORES** | MAESTRO_PROVEEDORES.xlsx | 1 | MANUAL | Ⓐ Ⓑ Ⓓ |
| ⑤ | **MOVIMIENTOS_BANCO** | MOV_BANCO_1T26.xlsx | TASCA + COMESTIBLES | NORMA43/Excel Sabadell | Ⓓ CUADRE |
| ⑥ | **ARTICULOS** | Articulos 26.xlsx | Comestibles (572) + Tasca (87) + Historial_Precios + Hoja1 | LOYVERSE (automático semanal) | Ⓒ VENTAS |

---

## 3. FUNCIONES DEL SISTEMA (4 principales)

### Ⓐ PARSEO (85% completado)
```
UBICACIÓN:     C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\
ENTRADA:       Carpeta con PDFs de facturas + MAESTRO_PROVEEDORES
SALIDA:        COMPRAS_XTxx.xlsx (Lineas + Facturas)
INICIO:        MANUAL (menú)
FRECUENCIA:    Mensual/Trimestral
ESTADO:        ✅ Funciona - 101 extractores dedicados
```

### Ⓑ GMAIL (99% completado) ✅ v1.14
```
UBICACIÓN:     C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\
ENTRADA:       Gmail (etiqueta FACTURAS) + MAESTRO_PROVEEDORES
SALIDA:        - PDFs descargados y renombrados en Dropbox local
               - PAGOS_Gmail_XTxx.xlsx (FACTURAS + SEPA) — 15 columnas
               - PROVEEDORES_NUEVOS_*.txt (sugerencias)
               - ⚠️_IBANS_SUGERIDOS_*.xlsx (verificación)
INICIO:        AUTOMÁTICO (viernes 03:00) o MANUAL
FRECUENCIA:    Semanal
ESTADO:        ✅ v1.14 - Fallback parcial extractores
NOVEDADES v1.14 (12/03/2026):
               P1 - FALLBACK PARCIAL EXTRACTORES:
               - Si extractor dedicado obtiene fecha pero no total (o viceversa),
                 complementa con extractor genérico (incluyendo OCR)
               - Reduce REVISAR en facturas con formatos variables o escaneadas
NOVEDADES v1.13 (07/03/2026):
               P1 - CURSOR TEMPORAL (after:YYYY/MM/DD):
               - Solo procesa emails posteriores a la última ejecución exitosa
               - Fecha guardada en emails_procesados.json como "ultima_ejecucion"
               - Filtro after: en query Gmail API (servidor) con margen -1 día
               - Emails del mismo día filtrados por control duplicados (email_id)
               - Evita reprocesar emails antiguos ya gestionados manualmente
               P2 - SCRIPT LIMPIEZA (limpiar_emails_viejos.py):
               - Script one-shot: mueve backlog de FACTURAS a PROCESADAS
               - Ejecutado 07/03/2026: 500 emails movidos, 0 errores
               - Establece cursor temporal inicial en el JSON
NOVEDADES v1.12 (07/03/2026):
               P1 - OPTIMIZACIÓN LECTURA PDF:
               - Texto del PDF se extrae una sola vez y se reutiliza (antes: hasta 3 lecturas)
               - identificar_por_pdf() acepta parámetro texto_pdf para evitar re-lectura
               P2 - PAGINACIÓN GMAIL API:
               - Antes: maxResults=50 sin nextPageToken → emails antiguos nunca se procesaban
               - Ahora: paginación completa hasta MAX_EMAILS=200
               - Elimina efecto "cola bloqueada" (emails del 02/02 procesados el 06/03)
               P3 - EXCLUIR CIF PROPIO:
               - identificar_por_pdf() excluye CIF B87760575 (Tasca Barea)
               - Evita falso positivo: PDF contiene CIF cliente + CIF proveedor
               P4 - MOTIVO_REVISION ACUMULATIVO:
               - Antes: ALERTA ROJA sobrescribía motivo anterior (ej: FECHA NO DETECTADA)
               - Ahora: se acumulan con " | " (ej: "FECHA NO DETECTADA | ALERTA ROJA")
NOVEDADES v1.11 (07/03/2026):
               P1 - IDENTIFICACIÓN POR CIF EN PDF:
               - Nuevo fallback en cascada: email → alias → fuzzy → CIF en PDF → REVISAR
               - MaestroProveedores.identificar_por_pdf(): busca CIFs españoles en texto PDF
               - Regex flexible: soporta espacios en CIF (ej: "B 99138372")
               - buscar_por_cif(): nuevo método con diccionario self.cifs
               P2 - VALIDACIÓN CIF POST-IDENTIFICACIÓN:
               - Tras identificar por email/alias/fuzzy, compara CIF del MAESTRO vs CIF del PDF
               - Si no coinciden: reasigna al proveedor correcto y marca REVISAR
               - Caso real: "La dolorosa" → PABLO RUIZ, pero PDF era de LAUTRE (CIF diferente)
               P3 - ANTI-COLISIÓN DROPBOX:
               - subir_archivo() detecta si archivo ya existe → añade sufijo " 2", " 3", etc.
               - Nombre actualizado se refleja en log y en Excel
               - Caso real: Som Energia envía 2 facturas/mes, la segunda sobrescribía la primera
               P4 - EMAILS IGNORADOS AMPLIADOS:
               - comunidadrodas2@gmail.com (comunidad de vecinos, no proveedor)
               - hola@comestiblesbarea.com (reenvíos propios)
NOVEDADES v1.10 (07/03/2026):
               P1 - CASCADA IDENTIFICACIÓN AMPLIADA:
               - Añadido paso CIF en PDF como último recurso antes de REVISAR
               - 2 de 5 facturas REVISAR ahora se auto-identifican (ej: kembetpanaderia)
NOVEDADES v1.9 (28/02/2026):
               P1 - SISTEMA PROFORMA:
               - Nuevo método es_proforma() en ExtractorBase: detecta \bPROFORMA\b en texto
               - FacturaExtraida tiene campo es_proforma: bool
               - _usar_extractor_dedicado() llama a instancia.es_proforma(texto_pdf) tras extracción
               - OBS multi-flag: "PROFORMA", "DUPLICADO", "DUPLICADO | PROFORMA"
               P2 - EXTRACTORES CORREGIDOS (4 extractores):
               - MRM: REF capturaba solo "1-2026" → ahora "1-2026-7545" (ref completa)
               - MRM: líneas con unidad "P" (peso) no se capturaban (solo "U") → [UP]
               - MOLIENDA VERDE: REF fallaba si pdfplumber extraía "Numero" sin acento → N[uú]mero
               - ECOFICUS: soporte proforma completo (REF PVT/, TOTAL PROFORMA, fecha sin colon, líneas sin lote)
               - LA LLEIDIRIA: metodo_pdf='ocr'→'pdfplumber' con fallback_ocr=True (facturas nuevas son texto)
               - LA LLEIDIRIA: formato línea actualizado: KG→(?:KG|Kg/\w+), €/KG→€/\w+
               P3 - BASE.PY MEJORADO:
               - extraer_total(): añadido patrón TOTAL PROFORMA
               - extraer_referencia(): añadidos patrones proforma (PVT/, PRF/, PRO/)
               - extraer_referencia(): "Número" con acento/colon opcionales
               - es_proforma(): nuevo método para detectar proformas
NOVEDADES v1.8 (27/02/2026):
               P1 - FIX COLUMN SHIFT:
               - _migrar_si_necesario() reescrito: solo añade col CUENTA si falta
               - Eliminada migración v1.7 de columna fantasma (ya aplicada)
               P2 - TOTAL COMO FLOAT:
               - Antes: total_str = "12,50" (string con coma) → Excel lo trata como texto
               - Ahora: total_num = 12.50 (float) → Excel lo reconoce como número
               P3 - IBAN LIMPIO:
               - Solo escribe IBANs reales (>=15 chars, empieza con 2 letras)
               - No escribe RECIBO/TARJETA/basura en la columna IBAN
               P4 - COLUMNA CUENTA (col 15):
               - Nueva columna: 'TASCA' o 'COMESTIBLES' según proveedor
               - Se lee de MAESTRO_PROVEEDORES (campo CUENTA del proveedor)
               - _migrar_si_necesario() añade la columna a Excels existentes
               P5 - ANTI-DUPLICADO CIF+REF EFECTIVO:
               - Antes: detectaba CIF+REF duplicado pero lo guardaba igualmente en Excel
               - Ahora: si es_duplicado_cif_ref → NO guarda en Dropbox NI en Excel
               - Log: "Duplicado CIF+REF: se omite Dropbox y Excel"
NOVEDADES v1.7 (20/02/2026):
               P1 - FIX ATRASADAS (fecha=None):
               - Si extractor falla al extraer fecha → factura nunca era detectada como ATRASADA
               - Fix: cuando fecha=None, activa requiere_revision=True y añade aviso en OBS:
                 "⚠️ FECHA NO DETECTADA - verificar si es ATRASADA"
               - Ya no se archiva silenciosamente con trimestre incorrecto
               P2 - COLUMN SHIFT MIGRATION:
               - _migrar_si_necesario() detecta y elimina columna fantasma del Excel existente
               - Se ejecuta automáticamente al abrir PAGOS_Gmail (1ª vez corrige, siguientes no hacen nada)
               P3 - FECHA_PROCESO:
               - Nueva columna FECHA_PROCESO en PAGOS_Gmail y Facturas Provisional
               - Registra fecha de procesado (solo fecha, sin hora)
               P4 - REF_INVALIDAS ampliada:
               - Añadidas: ERENTE, ERENCIA, RENCIA, DOS, UNO, TRES
               - Validación de REF también en extractores dedicados (no solo genérico)
               P5 - DUPLICADOS mejorado:
               - Detección por NOMBRE + TOTAL (antes solo por NOMBRE)
               - Reduce falsos positivos en proveedores con múltiples facturas iguales
               P6 - NOTIFICADOR fix:
               - Eliminado wrapper _api_call inexistente → llamada directa a API
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
               - Integración 99 extractores PARSEO
               - LocalDropboxClient (copia directa a carpeta sincronizada)
               - ATRASADAS detecta facturas de trimestres anteriores
               - Pestaña SEPA con IBANs y datos para pagos
               - Emails marcados como leídos
```

### Ⓒ VENTAS (95% - FUNCIONAL) ✅ v4.7
```
UBICACIÓN:     gestion-facturas/ventas_semana/
ENTRADA:       - API Loyverse (TASCA + COMESTIBLES) — recibos + items
               - API Woocommerce (cursos online)
               - ARTICULOS.xlsx (catálogo, actualizado automáticamente)
SALIDA:        - Ventas Barea 2026.xlsx (6 pestañas):
                 TascaRecibos (19 cols), TascaItems (23 cols),
                 ComesRecibos (19 cols), ComesItems (23 cols), WOOCOMMERCE,
                 GoogleBusiness (21 cols, métricas GBP mensuales)
               - Dashboards HTML interactivos:
                 dashboards/dashboard_comes.html (Comestibles 2025-2026)
                 dashboards/dashboard_tasca.html (Tasca 2023-2026)
               - PDFs resumen mensual:
                 dashboards/informe_barea_*.pdf (completo: Tasca + Comestibles)
                 dashboards/informe_comestibles_*.pdf (solo Comestibles)
               - GitHub Pages: DESACTIVADO (repo ahora PRIVATE, no funciona en plan gratuito)
                 Pendiente buscar alternativa (Netlify, Vercel, servidor propio)
INICIO:        AUTOMÁTICO (lunes 03:00) o MANUAL
FRECUENCIA:    Semanal (ventas + email resumen) + Mensual (dashboard + PDF + GBP)
ESTADO:        ✅ v4.7 - Dual dashboard + PDF + email semanal + anomalías IVA + Google Business Profile
CATEGORÍAS COMESTIBLES (13):
               ACEITES Y VINAGRES, BAZAR, BOCADILLOS, BODEGA, CHACINAS,
               CONSERVAS, CUPÓN REGALO, DESPENSA, DULCES, EXPERIENCIAS,
               OTROS, QUESOS, VINOS
               Mapeo Loyverse→simplificadas en CAT_MAP (generar_dashboard.py):
               APERITIVOS/SALAZONES/SALSAS→DESPENSA, CONSERVAS MAR/MONTAÑA/VEGETALES→CONSERVAS,
               BODEGA Y CERVEZAS/LICORES Y VERMÚS→BODEGA, CACHARRERIA→BAZAR, OTROS COMESTIBLES→OTROS
NOVEDADES v4.0 (01/03/2026):
               DASHBOARD TASCA (NUEVO):
               - Template: dashboard_tasca_template.html con 5 placeholders
                 ({{RAW_DATA}}, {{PBM_DATA}}, {{YEARS_DATA}}, {{SUBTITLE_YEARS}}, {{FECHA_ACT}})
               - 4 años: 2023 + 2024 + 2025 + 2026
               - Datos: TascaItems/TascaRecibos del Histórico + 2026
               - Categorías: BEBIDA, COMIDA, VINOS, MOLLETES, OTROS, PROMOCIONES
               - Chart.js: ventas mensuales, tickets, ticket medio, categorías, productos
               - Sin rotación ni rentabilidad (solo en Comestibles)
               - Funciones: cargar_datos_tasca(), calcular_RAW(), calcular_PBM_tasca()
               COMESTIBLES ACTUALIZADO:
               - Reducido a 2 años: 2025 + 2026 (eliminado 2024 por volumen bajo)
               - Template y CSS limpiados de referencias a 2024
               PDF RESUMEN MENSUAL (v4.1 - rediseño profesional):
               - matplotlib (3 gráficos línea) + reportlab (composición A4)
               - Cabecera con banda azul/verde, logos y línea dorada de acento
               - KPIs como tarjetas lado a lado con números grandes y flechas ▲▼ de color
               - Gráficos mejorados: área sombreada, etiquetas de valor, años semitransparentes
               - Tablas categorías con filas alternadas y cabeceras temáticas
               - Pie de página con fecha + número de página en cada hoja
               - PDF completo (3 págs): KPIs+Comparativa / Evolución / Categorías
               - PDF Comestibles: versión reducida solo Comestibles
               - Helpers: _setup_pdf_fonts(), _kpi_card(), _tabla_categorias_pdf()
               - Fuente Calibri, DPI 180
               EMAIL SEGMENTADO (NUEVO):
               - EMAILS_FULL (3 socios): email completo Tasca+Comestibles
                 + PDF completo + ambos dashboards HTML adjuntos
               - EMAILS_COMES_ONLY (1 socia): email solo Comestibles
                 + PDF solo Comestibles + dashboard Comestibles adjunto
               GITHUB PAGES MULTI-FILE:
               - Landing page (index.html) con cards a ambos dashboards
               - comestibles.html + tasca.html publicados automáticamente
               - Estilo dark, minimal, con fecha de actualización
NOVEDADES v3.0 (28/02/2026):
               Dashboard Comestibles + email + GitHub Pages + automatización
               (ver changelog v3.0 para detalle)
NOVEDADES v2.0 (27/02/2026):
               - Descarga semanal fija (lunes-domingo anterior), no incremental
               - Todas las columnas Loyverse: TPV, Tienda, Cajero, Cliente, Categoría
               - fetch_lookup_data(), procesar_recibos(), dedup estable
               - WooCommerce con paginación + filtro semanal
```

### Ⓓ CUADRE (80% - FUNCIONAL) ✅ v1.6
```
UBICACIÓN:     gestion-facturas/cuadre/banco/cuadre.py
ENTRADA:       - Excel gestoría (Tasca + Comestibles + Facturas)
               - MAESTRO_PROVEEDORES.xlsx (195 proveedores, ~585 aliases)
SALIDA:        - Excel con Categoria_Tipo + Categoria_Detalle
               - Columna Origen en hoja Facturas
               - Archivo LOG con decisiones
INICIO:        MANUAL (GUI selección archivo)
FRECUENCIA:    Mensual/Trimestral
VERSIÓN:       v1.6
ESTADO:        ✅ Funciona - 4 clasificadores mejorados + SERVICIO DE TPV
NOVEDADES v1.6 (12/03/2026):
               - Yoigo mejorado: regex Y?C\d{9,} (detecta con/sin prefijo Y) + fuzzy ≥90%
               - Suscripciones ampliadas: SPOTIFY/NETFLIX/AMAZON (sin factura),
                 MAKE.COM→CELONIS/OPENAI→OPENAI LLC (con factura vinculada por mes)
               - Comunidad vecinos: asigna 2 facturas ISTA METERING más cercanas en fecha
               - Alquiler: busca facturas Ortega + Fernández del mes del movimiento
               - Resultado: 3382 clasificados (85.7%), 563 REVISAR (antes 590)
NOVEDADES v1.5b (27/02/2026):
               - Nuevo clasificador: SERVICIO DE TPV (12 movimientos recuperados)
               - 16 aliases añadidos al MAESTRO (OPENAI, MAKRO, LIDL, MERCADONA, ALCAMPO...)
               - 2 proveedores nuevos: HIPER DEL EMBALAJE SL, BODEGAS R. LOPEZ DE HEREDIA
               - Resultado: 3355 clasificados (85.1%), 590 REVISAR (antes 621)
NOVEDADES v1.5 (23/02/2026):
               - buscar_factura_candidata() extraída de 3 clasificadores (~85 líneas menos)
               - buscar_mejor_alias() optimizado con dict precalculado (O(1) exact match)
               - Fix warning dayfirst en pd.to_datetime de clasificar_tpv
               - Verificado: resultado idéntico (3324 clasificados, 621 REVISAR)
```

---

## 4. ESTRUCTURA DE CARPETAS

```
C:\_ARCHIVOS\TRABAJO\Facturas\
│
├── Parseo\                          ← Ⓐ PARSEO (FUNCIONA)
│   ├── extractores\                 ← 99 extractores específicos
│   ├── nucleo\
│   ├── salidas\
│   ├── outputs\
│   └── main.py
│
├── gestion-facturas\                ← PROYECTO UNIFICADO (este repo)
│   │
│   ├── gmail\                       ← Ⓑ GMAIL (✅ v1.14)
│   │   ├── gmail.py                 ← Módulo principal v1.14 (~2500 líneas)
│   │   ├── limpiar_emails_viejos.py ← Script one-shot limpieza backlog
│   │   ├── config.py                ← Configuración (rutas, umbrales, trimestres)
│   │   ├── config_local.py          ← Overrides locales (gitignored)
│   │   ├── auth.py                  ← Autenticación Gmail API
│   │   ├── descargar.py             ← Descarga adjuntos
│   │   ├── identificar.py           ← Identificación proveedores
│   │   ├── renombrar.py             ← Renombrado de PDFs
│   │   ├── guardar.py               ← Guardado en Excel
│   │   ├── generar_sepa.py          ← Generador XML SEPA (IBANs de datos_sensibles.py)
│   │   ├── credentials.json         ← OAuth Google (gitignored)
│   │   ├── token.json               ← Token Gmail (gitignored)
│   │   ├── gmail_auto.bat           ← Script automatización v1.7 (curl HTTPS, alertas)
│   │   ├── gmail_auto_setup.bat     ← Setup tarea programada
│   │   ├── buscar_emails_proveedores.py ← Búsqueda manual de emails por proveedor
│   │   ├── renovar_token_business.py    ← Renueva token OAuth Google Business
│   │   ├── test_borboton.py             ← Test extractor Borbotón
│   │   └── test_extractores.py          ← Tests extractores PDF
│   │
│   ├── cuadre\                      ← Ⓓ CUADRE (✅ v1.6)
│   │   ├── banco\
│   │   │   ├── cuadre.py            ← Clasificador principal (~1300 líneas)
│   │   │   ├── router.py            ← Router de clasificadores
│   │   │   ├── parser_n43.py        ← Parser formato bancario N43
│   │   │   └── clasificadores\      ← Clasificadores modulares
│   │   │       ├── transferencia.py, compra_tarjeta.py, adeudo_recibo.py
│   │   │       ├── tpv.py, energia_som.py, telefono_yoigo.py
│   │   │       ├── casos_simples.py
│   │   │       └── clasificadores_mejorados\  ← Subclasificadores especiales
│   │   │           ├── alquiler.py, ay_madre.py, comunidad_ista.py
│   │   │           ├── suscripciones.py, telefono_yoigo.py
│   │   │           └── router.py
│   │   └── norma43\
│   │       ├── norma43.py            ← Parser ficheros N43 Sabadell
│   │       └── archivados\           ← Ficheros N43 procesados
│   │
│   ├── ventas_semana\               ← Ⓒ VENTAS + DASHBOARDS (✅ v4.7)
│   │   ├── script_barea.py          ← Loyverse + WooCommerce API → Excel
│   │   ├── generar_dashboard.py     ← Generador dual: Comestibles + Tasca + PDF + email
│   │   ├── dashboards\
│   │   │   ├── dashboard_comes_template.html  ← Template Comestibles (6 placeholders)
│   │   │   ├── dashboard_tasca_template.html  ← Template Tasca (5 placeholders)
│   │   │   ├── dashboard_comes.html           ← Dashboard Comestibles generado
│   │   │   ├── dashboard_tasca.html           ← Dashboard Tasca generado
│   │   │   └── informe_barea_*.pdf            ← PDF resumen mensual generado
│   │   ├── LOGO Tasca.jpg            ← Logo Tasca (para PDF)
│   │   ├── LOGO Comestibles .jpg     ← Logo Comestibles (para PDF)
│   │   ├── barea_auto.bat           ← Runner tarea programada (anti-suspensión)
│   │   ├── barea_auto_setup.bat     ← Setup tarea (1 vez, como admin)
│   │   └── .env                     ← Credenciales API (no commitear)
│   │
│   ├── src\facturas\                ← Módulo PARSEO refactorizado (en desarrollo)
│   │   ├── cli.py, models.py        ← Interfaz y modelos
│   │   ├── parse_lines.py           ← Parser de líneas
│   │   ├── patterns.py              ← Patrones de extracción
│   │   ├── detect_blocks.py         ← Detección de bloques
│   │   ├── iva_logic.py             ← Lógica IVA
│   │   ├── portes_logic.py          ← Distribución portes
│   │   ├── categorias.py            ← Categorización
│   │   ├── reconcile.py             ← Reconciliación
│   │   ├── export\                  ← Excel + Master
│   │   ├── tests\                   ← Tests unitarios
│   │   └── tools\                   ← Herramientas auxiliares
│   │
│   ├── config\                      ← Configuración del proyecto
│   │   ├── proveedores.py           ← Lógica proveedores (funciones, alias, método PDF)
│   │   ├── datos_sensibles.py       ← IBANs, CIFs, DNIs, emails (gitignored, NUNCA commitear)
│   │   ├── datos_sensibles.py.example ← Plantilla para nuevos despliegues
│   │   └── settings.py              ← Versión, rutas por defecto
│   │
│   ├── datos\                       ← Documentos maestros (gitignored excepto diccionarios)
│   │   ├── MAESTRO_PROVEEDORES.xlsx ← 195 proveedores, ~585 aliases (gitignored)
│   │   ├── DiccionarioProveedoresCategoria.xlsx
│   │   ├── DiccionarioEmisorTitulo.xlsx
│   │   ├── EXTRACTORES_COMPLETO.xlsx
│   │   └── emails_procesados.json   ← Control duplicados Gmail (gitignored)
│   │
│   ├── .claude\skills\              ← 9 skills personalizadas Claude Code
│   │   ├── estado/SKILL.md          ← /estado: resumen proyecto
│   │   ├── dashboard/SKILL.md       ← /dashboard: generar dashboards
│   │   ├── log-gmail/SKILL.md       ← /log-gmail: analizar logs
│   │   ├── extractor/SKILL.md       ← /extractor: crear extractores
│   │   ├── esquema/SKILL.md         ← /esquema: actualizar ESQUEMA
│   │   ├── ventas/SKILL.md          ← /ventas: descargar ventas
│   │   ├── lecciones/SKILL.md       ← /lecciones: mostrar lessons.md y proponer reglas
│   │   ├── plan/SKILL.md            ← /plan: crear o revisar tasks/todo.md
│   │   └── revisar/SKILL.md         ← /revisar: analizar movimientos REVISAR del cuadre
│   │
│   ├── alerta_fallo.py              ← Email alerta si fallo (token refresh + scope gmail.send)
│   ├── requirements.txt             ← 16 dependencias fijadas (pip install -r)
│   ├── .gitignore                   ← Excluye credenciales, datos, outputs, tokens
│   ├── estadisticas.py              ← Generador estadísticas facturas (OK/SIN_LINEAS/SIN_CUADRAR)
│   ├── clasificador.py              ← Clasificador movimientos v2.0 (N43 + Excel interactivo)
│   ├── procesador_jpg.py            ← Procesador fallback JPG (extrae datos del nombre)
│   │
│   └── outputs\                     ← Archivos generados (NO versionados, .gitignore)
│       ├── Cuadre_*.xlsx            ← Cuadres generados
│       ├── PAGOS_Gmail_XTxx.xlsx
│       ├── PROVEEDORES_NUEVOS_*.txt
│       ├── ⚠️_IBANS_SUGERIDOS_*.xlsx
│       ├── logs_gmail\              ← Logs ejecución Gmail
│       ├── logs_barea\              ← Logs ejecución Ventas/Dashboard
│       └── backups\
│
└── _archivo\                        ← Histórico/backup
```

---

## 5. Ⓐ PARSEO - EXTRACTORES (~104 total)

### 5.1 Estado de Extractores

| Categoría | Extractores | Tasa Éxito | Notas |
|-----------|-------------|------------|-------|
| **Alimentación** | 45 | 95% | BERNAL, ECOFICUS, MRM, PORVAZ... |
| **Bebidas** | 18 | 90% | Cervezas, vinos, refrescos |
| **Servicios** | 15 | 85% | Telefonía, energía, seguros |
| **Material** | 12 | 80% | Papelería, envases |
| **OCR** | 7 | 75% | LA LLILDIRIA, CASA DEL DUQUE... |

### 5.2 Extractores Corregidos y Nuevos (07/03/2026 - v1.12)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **QUESOS DE CATI** | `_deduplicar_texto()` convertía "22/12/2025" en "2/12/2025" → fecha no detectada | `extraer_fecha()` busca primero en texto RAW (zona no duplicada), dedup solo como fallback con `\d{1,2}` + zfill | 100% |
| **QUESOS DE CATI** | `extraer_referencia()` mismo problema potencial con dígitos repetidos | Busca primero en texto RAW, dedup como fallback | 100% |
| **JULIO GARCIA** | `extraer_fecha()` capturaba "DE FECHA 01/02/2026" del albarán en vez de fecha emisión (L2) | Busca primero fecha sola en línea 2 (`^\d{2}/\d{2}/\d{4}$`), fallback `^FECHA:` anclado a inicio de línea | 100% |
| **SEGURMA** | Cabecera y valor en líneas separadas → "Fecha de factura:" en L76, "01/03/2026" en L77 | Añadido patrón con `\n` entre etiqueta y valor | 100% |
| **MOLLETES ARTESANOS** | No estaba en MAESTRO → fuzzy match sin extractor → fecha y total no extraídos | Añadido al MAESTRO con TIENE_EXTRACTOR=SI, ARCHIVO_EXTRACTOR=molletes_artesanos.py | 100% |

**NUEVOS EXTRACTORES (07/03/2026):**

| Extractor | Proveedor | CIF | IVA | Categoría |
|-----------|-----------|-----|-----|-----------|
| **lautre.py** | LAUTRE GESTION DE PROYECTOS SL | B81516981 | 21% | GASTOS VARIOS |

### 5.2b Extractores Corregidos (28/02/2026 - v1.9)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **MRM** | `extraer_referencia` solo capturaba "1-2026" (faltaba "-7545") | Regex extendido: `[\d\-]+(?:\s*-[\d.]+)?` + normalización (quita puntos) | 100% |
| **MRM** | Líneas con unidad "P" (peso) no se capturaban (solo "U") | `\s+U\s+` → `\s+[UP]\s+` | 100% |
| **MOLIENDA VERDE** | REF fallaba si pdfplumber extraía "Numero" sin acento | `Número` → `N[uú]mero` | 100% |
| **ECOFICUS** | Proformas sin soporte (REF, total, fecha, líneas) | Fallbacks: PVT/\d+, TOTAL PROFORMA, Fecha sin colon, patrón línea proforma | 100% |
| **LA LLEIDIRIA** | `metodo_pdf='ocr'` en facturas nuevas (ya son texto PDF) | Cambiado a `pdfplumber` con `fallback_ocr=True` | 100% |
| **LA LLEIDIRIA** | Formato línea cambiado: "Kg/1KG", "€/Pack" | `KG` → `(?:KG\|Kg/\w+)`, `€/KG` → `€/\w+` | 100% |
| **base.py** | Sin detección proforma ni patrones REF proforma | `es_proforma()`, TOTAL PROFORMA, PVT/PRF/PRO/, Número con acento opcional | 100% |

**VERIFICADOS SIN BUGS (28/02/2026):**

| Extractor | Facturas probadas | Resultado |
|-----------|-------------------|-----------|
| **ANTHROPIC** | 1T26_0220 | ✅ REF EXB4HCQN-0005 correcta |
| **QUESOS DE CATI** | factura con Número FRA: 532 | ✅ REF correcta |

### 5.3 Extractores Corregidos (20/02/2026 - v1.7)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **BORBOTON** | `extraer_referencia` capturaba fecha (18/02) en vez de ref (20580/26) | Saltar `dd/mm/yyyy` explícitamente antes de capturar el número | 100% |
| **LA LLILDIRIA** | No existía extractor dedicado → iba a REVISAR siempre | Creado `la_llildiria.py` con OCR, fix total (captura TOTAL no SUBTOTAL) | 100% |

**VERIFICADOS SIN BUGS (20/02/2026):**

| Extractor | Facturas probadas | Resultado |
|-----------|-------------------|-----------|
| **SABORES PATERNA** | 1T26_0219 (formato nuevo) | ✅ fecha, REF, total correctos |
| **MOLLETES ARTESANOS** | 4 facturas (1T25, 3T25×2, 1T26) | ✅ todos los campos correctos |

### 5.3 Extractores Corregidos (13/02/2026 - v1.6)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **SABORES PATERNA** | `extraer_total` solo buscaba IRPF, no TOTAL: | Fallback `TOTAL: XXX,XX` | 100% |
| **GREDALES** | `extraer_total` regex no aceptaba punto decimal | `[\d,]+` → `[\d.,]+` | 100% |
| **LA LLILDIRIA** | gmail.py ignoraba `metodo_pdf='ocr'` → texto vacío | Fallback OCR en `_usar_extractor_dedicado` | 100% |
| **Genérico** | Refs basura: "erence", "R", "PEDIDO" | Mínimo 3 chars + blacklist `REF_INVALIDAS` | 90% |

### 5.4 Extractores Corregidos (06/02/2026)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **BERNAL** | No extraía total (multilínea) ni ref | Regex multilínea `Total Factura:\n...\nXXX €` + `Factura X Fecha` | 100% |
| **DE LUIS** | No extraía ref (encoding ú) | `N[úu]mero` + fallback `Concepto:` | 100% |
| **TERRITORIO CAMPERO** | No extraía ref (`NUMERO` sin acento) | `N[ÚU]MERO DE FACTURA:` | 100% |
| **YOIGO** | No extraía ref (encoding) | Búsqueda directa `YC\d{10,15}` | 100% |

### 5.5 Extractores Corregidos (03/02/2026)

| Extractor | Problema | Solución | Tasa |
|-----------|----------|----------|------|
| **YOIGO** | Encoding `(cid:128)` vs `€` | Eliminar € de patrones | 100% |
| **MRM** | Patrón muy complejo | Simplificado | 100% |
| **BERNAL** | Portes IVA 21% no distribuidos | Reparto proporcional | 100% |
| **LA MOLIENDA VERDE** | 2× líneas de portes | Suma + reparto | 100% |
| **ECOFICUS** | IVA mixto (4%/10%/21%) + encoding | Reparto por grupo IVA | 100% |
| **PORVAZ** | Descuento 3% como línea negativa | Patrón con `%` | 100% |
| **LA LLILDIRIA** | OCR + formatos variados | Patrón flexible | 100% |

### 5.6 Fórmula Distribución Portes (IVA diferente)

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

## 5.7 ARQUITECTURA DE EXTRACTORES

### 5.7.1 Estructura del Paquete

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

### 5.7.2 Flujo de Carga

`__init__.py` carga **automáticamente** todos los `.py` de la carpeta (excepto `base.py`, `generico.py`, `_plantilla.py`). Cada archivo se registra con `@registrar('NOMBRE1', 'NOMBRE2', ...)`. Al buscar un proveedor, `obtener_extractor()` hace búsqueda exacta primero, luego parcial.

### 5.7.3 Clase Base: ExtractorBase

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
    def extraer_total(self, texto) -> float           # Por defecto: patrones genéricos (incl. PROFORMA)
    def extraer_fecha(self, texto) -> str             # Por defecto: DD/MM/YYYY
    def extraer_referencia(self, texto) -> str        # Por defecto: patrones genéricos + proforma (PVT/,PRF/,PRO/)
    def es_proforma(self, texto) -> bool              # Detecta \bPROFORMA\b en texto

    # UTILIDADES HEREDADAS
    def _convertir_importe(self, texto) -> float      # Español/americano → float (superset: €, espacios, OCR)
    def _convertir_europeo(self, texto) -> float      # Alias de _convertir_importe (compatibilidad)
    def _calcular_base_desde_total(total, iva)        # Total con IVA → base
    def _calcular_total_desde_base(base, iva)         # Base → total con IVA
    def _limpiar_texto(texto) -> str                  # Limpiar espacios/saltos
    def _es_referencia_valida(ref) -> bool             # Filtro anti-falsos positivos
```

### 5.7.4 Formato del Dict de Línea (extraer_lineas)

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

### 5.7.5 Estadísticas (~104 extractores)

| Concepto | Valor |
|---|---|
| Total extractores | ~104 |
| Método pdfplumber | 93 (92%) |
| Método OCR | 6 (6%): fishgourmet, gaditaun, jimeluz, la_cuchara, manipulados_abellan, tirso |
| Método pdfplumber+fallback_ocr | 1 (1%): la_lleidiria (facturas nuevas=texto, antiguas=imagen) |
| Método híbrido | 2 (2%): angel_borja, casa_del_duque |
| Con extraer_total propio | 90 (100%) |
| Con extraer_fecha propio | 90 (100%) |
| Con extraer_referencia | 89 (~99%) |
| Con distribución de portes | 11: angel_loli, arganza, bernal, ecoficus, felisa, fernando_moro, molienda_verde, montbrione, pago_de_las_olmas, porvaz, zucca |
| Con categoría fija | 43 (~48%) |
| IVA 4% (alimentación básica) | 7 extractores |
| IVA 10% (alimentación) | 18 extractores |
| IVA 21% (servicios/general) | 36 extractores |

### 5.7.6 Reglas de Negocio

**PORTES/ENVÍO:** SIEMPRE distribuir proporcionalmente entre productos. NUNCA línea separada.
```python
# Fórmula cuando portes tienen IVA diferente al de productos:
portes_equiv = (portes_base × (1 + IVA_portes/100)) / (1 + IVA_productos/100)
# Si IVA mixto (4% y 10%), ponderar por peso de cada grupo
```

**IVA:** Usar tipo real del producto (4% lácteos/pan, 10% alimentación, 21% servicios/bebidas alcohólicas). Cada extractor define el IVA de sus productos.

**REFERENCIA:** Método unificado `extraer_referencia()` (antes había `extraer_numero_factura()` como alias, eliminado en v5.18). Filtro anti-falsos positivos en `_es_referencia_valida()`: excluye teléfonos, CIFs, fechas, números de cliente, palabras sueltas. Mínimo 3 caracteres y 2 dígitos. Parser genérico (`nucleo/parser.py`) con patrones estrictos que requieren dígitos, blacklist de palabras inválidas (FECHA, DATOS, CLIENTE...), lookbehind `(?<!FECHA )` y filtro de fechas parciales.

**OCR:** Para PDFs imagen (sin texto extraíble). Usa `pytesseract` + `pdf2image` con `lang='spa'`. Los extractores OCR definen `metodo_pdf = 'ocr'`. Algunos usan `fallback_ocr = True` para intentar pdfplumber primero y OCR si falla.

**PROFORMA:** Documentos que no son facturas fiscales (presupuesto/pedido). Se detectan automáticamente con `es_proforma()` (busca `\bPROFORMA\b` en texto). Se marcan con "PROFORMA" en columna OBS del Excel. Patrones de REF proforma en base.py: `PVT/`, `PRF/`, `PRO/`. Extractores con soporte proforma específico: ECOFICUS.

**CATEGORÍA FIJA:** 43 extractores asignan categoría automáticamente (ej: `categoria_fija = 'QUESOS'`). El resto usa el DiccionarioProveedoresCategoria.

### 5.7.7 Cómo Crear un Extractor Nuevo

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
   - extraer_referencia() si la referencia es especial

PASO 5: Probar
   python tests/probar_extractor.py "NUEVO PROVEEDOR" factura.pdf

PASO 6: El extractor se carga automáticamente (sin tocar __init__.py)
```

### 5.7.8 Convenciones de Código

- Archivo: `nombre_proveedor.py` (snake_case, sin tildes)
- Clase: `ExtractorNombreProveedor` (CamelCase)
- Imports: `from extractores.base import ExtractorBase` + `from extractores import registrar`
- Docstring: Describir formato factura, IVA, productos, fecha creación
- `@registrar()`: Incluir nombre oficial + alias comunes (mayúsculas)
- Método `_convertir_europeo()`: Privado si el extractor necesita conversión propia
- PORTES: Detectar línea de portes, calcular equivalente, distribuir proporcionalmente


---

## 6. Ⓑ GMAIL v1.8 - DETALLE TÉCNICO

### 6.1 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Ⓑ GMAIL MODULE v1.8                               │
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

## 7. Ⓓ CUADRE v1.6 - DETALLE

### 7.1 Clasificadores Implementados

| Clasificador | Detecta | Categoria_Tipo | Categoria_Detalle |
|--------------|---------|----------------|-------------------|
| **TPV** | `ABONO TPV`, `COMISIONES` | TPV TASCA / COMISION TPV | Número remesa |
| **Transferencia** | `TRANSFERENCIA A` | Proveedor | #factura |
| **Compra tarjeta** | `COMPRA TARJ` | Proveedor | #factura |
| **Adeudo/Recibo** | `ADEUDO RECIBO` | Proveedor | #factura (ref) |
| **Som Energia** | `SOM ENERGIA` | SOM ENERGIA SCCL | #factura (FExxxxxx) |
| **Yoigo** | `YOIGO` | XFERA MOVILES SAU | #cod (ref exacta/fuzzy) |
| **Comunidad** | `COM PROP` | COMUNIDAD DE VECINOS | #cod1, #cod2 (ISTA) |
| **Suscripciones sin fac.** | `SPOTIFY`, `NETFLIX`, `AMAZON PRIME`, `LOYVERSE` | GASTOS VARIOS / LOYVERSE | Sin factura |
| **Suscripciones con fac.** | `MAKE.COM`, `OPENAI` | CELONIS INC. / OPENAI LLC | #cod proveedor |
| **Servicio TPV** | `SERVICIO DE TPV` | SERVICIO DE TPV | (cargo bancario) |
| **Alquiler** | `BENJAMIN ORTEGA Y JAIME` | ALQUILER | #cod1, #cod2 (Ortega+Fernández) |

### 7.2 Arquitectura cuadre.py (v1.6)

```
main()
 │
 ├── Cargar MAESTRO_PROVEEDORES → construir_df_fuzzy() → construir_indice_aliases()
 │                                 (~585 filas)           (~490 entradas, dict O(1))
 ├── Cargar Excel entrada (Tasca + Comestibles + Facturas)
 │
 └── Por cada hoja de movimientos:
      │
      └── procesar_hoja_movimientos(df_mov, df_fact, df_fuzzy, hoja, indice_aliases)
           │
           └── Por cada movimiento:
                │
                └── clasificar_movimiento() ← ROUTER
                     │
                     ├── clasificar_tpv()
                     ├── clasificar_compra_tarjeta()  ──┐
                     ├── clasificar_transferencia()   ──┤── buscar_mejor_alias(indice_aliases)
                     ├── clasificar_adeudo_recibo()   ──┘   + buscar_factura_candidata()
                     ├── clasificar_som_energia()
                     ├── clasificar_yoigo()
                     └── clasificar_casos_simples()
```

### 7.3 Función extraída: buscar_factura_candidata() (v1.5)

Lógica común a transferencias, compra_tarjeta y adeudo_recibo (~40 líneas cada uno → 1 función):

```
1. Buscar facturas por importe (±0.01€)
2. Calcular fuzzy scores con aliases (calcular_similitud_con_aliases)
3. Filtrar por umbral ≥70%
4. Filtrar facturas ya usadas (facturas_usadas global)
5. Desempatar por fecha: factura anterior más cercana ≤60 días
6. Fallback: mejor fuzzy si no hay fecha válida
```

**Parámetros que diferencian los 3 clasificadores:**

| Parámetro | transferencia | compra_tarjeta | adeudo_recibo |
|---|---|---|---|
| `fecha_operativa` fallback | Sí | Sí | No (solo fecha_valor) |
| `incluir_ref` (campo Factura) | No | No | Sí |
| `log_candidatas` | Sí | No | Sí |

### 7.4 Optimización buscar_mejor_alias() (v1.5)

**Antes (v1.4):** `df_fuzzy.iterrows()` por cada movimiento → 565 filas × 3945 mov = 2.2M comparaciones pandas

**Después (v1.5):** `construir_indice_aliases()` genera `Dict[str, str]` una sola vez:
- Match exacto: `dict.get()` → O(1) en lugar de filtro DataFrame
- Match fuzzy: itera `dict.items()` → sin overhead pandas (~10x más rápido)

### 7.5 Resultados verificados (Prueba Año 25.xlsx)

| Métrica | v1.5 | v1.5b | v1.6 |
|---|---|---|---|
| Total movimientos | 3945 | 3945 | 3945 |
| Clasificados | 3324 (84.3%) | 3355 (85.1%) | 3382 (85.7%) |
| REVISAR | 621 (15.7%) | 590 (14.9%) | 563 (14.3%) |
| MAESTRO aliases | 565 filas | ~585 filas | ~585 filas |

**Mejoras v1.6:** +27 movimientos clasificados (Yoigo: 8 rescatados, suscripciones: 12, comunidad+alquiler: 7)
**Mejoras v1.5b:** +31 movimientos clasificados (SERVICIO DE TPV: 12, aliases nuevos: ~19)

---

## 8. FLUJO DE TRABAJO COMPLETO

```
          SEMANAL (auto)              SEMANAL (auto)              MENSUAL
               │                           │                         │
               ▼                           ▼                         ▼
      ┌────────────────┐          ┌────────────────┐        ┌────────────────┐
      │   Ⓑ GMAIL     │          │  Ⓒ VENTAS     │        │   Ⓐ PARSEO    │
      │ Descargar PDFs │          │ Loyverse + Woo │        │ Procesar PDFs  │
      │ (vie 03:00)    │          │ (lun 03:00)    │        │ (manual)       │
      └───────┬────────┘          └───────┬────────┘        └───────┬────────┘
              │                           │                         │
              ▼                           ▼                         ▼
      ┌────────────────┐          ┌────────────────┐        ┌────────────────┐
      │ PAGOS_Gmail    │          │ Ventas Barea   │        │    COMPRAS     │
      │ _XTxx.xlsx     │          │ 2026.xlsx      │        │   _XTxx.xlsx   │
      └───────┬────────┘          └───────┬────────┘        └───────┬────────┘
              │                           │                         │
              ▼                           ▼                         │
      ┌────────────────┐    ┌──────────────────────────┐            │
      │ Revisar +      │    │ Dashboards:              │            │
      │ Pagar TF       │    │ Comestibles + Tasca      │            │
      └───────┬────────┘    └───────┬──────────────────┘            │
              │                     │                               │
              │               1er lunes del mes:                    │
              │                     │                               │
              │              ┌──────┼──────┐                        │
              │              ▼      ▼      ▼                        │
              │      ┌────────┐ ┌──────┐ ┌────────┐                 │
              │      │ PDF    │ │Email │ │ GitHub │                 │
              │      │resumen │ │segm. │ │ Pages  │                 │
              │      │(2 PDF) │ │(2grp)│ │(3 HTML)│                 │
              │      └────────┘ └──────┘ └────────┘                 │
              │                                                     │
              ▼                                                     ▼
      ┌────────────────┐                                   ┌────────────────┐
      │ Movimientos    │                                   │   Ⓓ CUADRE    │◀── MOV_BANCO
      │ Banco          │──────────────────────────────────►│ Marcar pagadas │
      └────────────────┘                                   └───────┬────────┘
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
| ~~1️⃣~~ | ~~Ⓑ GMAIL~~ | ~~Descargar + renombrar~~ | ✅ **v1.7** |
| ~~2️⃣~~ | ~~Extractores PARSEO~~ | ~~Mejorar tasa de éxito (85%→95%)~~ | ✅ **99 extractores** |
| 3️⃣ | Ⓓ CUADRE integración | Conectar con COMPRAS (ESTADO_PAGO) | 🟡 Pendiente |
| ~~4️⃣~~ | ~~Ⓒ VENTAS~~ | ~~Loyverse + Woocommerce~~ | ✅ **v4.7 (95%)** |
| ~~5️⃣~~ | ~~Informes~~ | ~~Dashboards + PDF + email~~ | ✅ **Comes + Tasca** |
| 6️⃣ | Limpiar WooCommerce | Reducir 69→10 columnas en pestaña WOOCOMMERCE (Ventas Barea) | 🟡 Pendiente |
| 7️⃣ | Integrar | Mover PARSEO a gestion-facturas | ❌ Futuro |
| 8️⃣ | Cruce Artículos↔Proveedores | Cruzar `Articulos 26.xlsx` con `DiccionarioProveedoresCategoria.xlsx` (pestaña Articulos) para vincular cada artículo Loyverse con su proveedor. Rellenar COD LOYVERSE (solo 83/1282 rellenos). Fuzzy matching por nombre. | 🟡 Pendiente |
| 9️⃣ | Separar Historial Precios | Mover `Historial_Precios` de `Articulos 26.xlsx` a un Excel independiente (`HISTORIAL_PRECIOS.xlsx`) con hoja por año. Evita riesgo de corrupción cruzada y permite análisis directo (gráficos evolución costes, cruce con facturas proveedores). | 🟡 Posible mejora |

---

## 10. CUENTAS BANCARIAS

Datos bancarios almacenados en `config/datos_sensibles.py` (gitignored).
Incluye: IBAN_TASCA, IBAN_COMESTIBLES, BIC_ORDENANTE, NIF_SUFIJO, CIF_PROPIO.
Ver `config/datos_sensibles.py.example` para la estructura.

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

## 13. SEGURIDAD Y ROBUSTEZ

### 13.1 Datos sensibles centralizados

Todos los datos sensibles (IBANs, CIFs, DNIs, emails de socios) están en `config/datos_sensibles.py` (gitignored).
- **Nunca** commitear este archivo. Usar `config/datos_sensibles.py.example` como plantilla.
- Los módulos importan desde `datos_sensibles` con fallback `ImportError` graceful.
- Contiene: `CIF_PROPIO`, `IBAN_TASCA`, `IBAN_COMESTIBLES`, `BIC_ORDENANTE`, `PROVEEDORES_CONOCIDOS` (146), `CIF_A_PROVEEDOR` (67), `EMAILS_FULL`, `EMAILS_COMES_ONLY`.

### 13.2 Credenciales protegidas (.gitignore)

| Archivo | Contenido | Excluido |
|---------|-----------|----------|
| `config/datos_sensibles.py` | IBANs, CIFs, DNIs, emails socios | ✅ |
| `ventas_semana/.env` | API keys WooCommerce + Loyverse | ✅ |
| `gmail/config_local.py` | App password Gmail | ✅ |
| `gmail/credentials.json` | OAuth2 client secret | ✅ |
| `gmail/token.json` | OAuth2 refresh token | ✅ |
| `datos/*.xlsx` | Datos financieros (MAESTRO, Ventas, Movimientos) | ✅ |
| `outputs/*.xlsx` | Datos financieros (IBANs, totales) | ✅ |
| `outputs/backups/` | Backups con datos sensibles | ✅ |
| `*.n43` | Extractos bancarios Norma 43 | ✅ |

### 13.3 Historial git purgado (03/03/2026)

Se ejecutó `git filter-repo` en dos pasadas para eliminar datos sensibles del historial:
- **Pasada 1** (`--invert-paths`): eliminados 73 archivos binarios/datos (Excel, N43, backups)
- **Pasada 2** (`--replace-text`): 65 patrones reemplazados (IBANs→REDACTED_IBAN, DNIs→REDACTED_DNI, emails→REDACTED_EMAIL)
- Force-push a origin/main tras limpieza
- Verificado: `git log --all -p -S "ES78..."` no devuelve resultados

### 13.4 Repositorio barea-dashboard PRIVADO

Cambiado de PUBLIC a PRIVATE el 03/03/2026 (contenía datos financieros en dashboards).
GitHub Pages **no funciona** en repos privados con plan gratuito — pendiente buscar alternativa.

### 13.5 Dependencias (requirements.txt)

16 paquetes con versiones fijadas. Instalar: `pip install -r requirements.txt`

### 13.6 Protección de datos (save_to_excel)

`script_barea.py` lee el Excel existente ANTES de abrir el writer. Si la lectura falla (fichero abierto, corrupto), **aborta** la escritura en vez de sobreescribir con datos vacíos.

### 13.7 Alertas de fallo (alerta_fallo.py)

Tanto `gmail_auto.bat` como `barea_auto.bat` envían email a `tascabarea@gmail.com` si el script Python termina con exit code ≠ 0. Usa Gmail API con scope mínimo (`gmail.send`) y token refresh automático.

### 13.8 Timeouts HTTP

Todas las llamadas a APIs externas (Loyverse, WooCommerce) tienen `timeout=30` para evitar cuelgues indefinidos en tareas programadas.

---

## 14. SKILLS DE CLAUDE CODE (/comandos)

Skills disponibles en `gestion-facturas/.claude/skills/`:

| Comando       | Acción                                                          |
|---------------|-----------------------------------------------------------------|
| `/ventas`     | Descargar ventas semanales y regenerar dashboards               |
| `/dashboard`  | Generar dashboards HTML + PDF (opciones: email, cerrados, test) |
| `/estado`     | Informe de estado: versiones, pendientes, errores recientes     |
| `/esquema`    | Actualizar este ESQUEMA con cambios de la sesión                |
| `/log-gmail`  | Analizar logs de la última ejecución Gmail                      |
| `/extractor`  | Crear nuevo extractor PDF para proveedor nuevo                  |
| `/revisar`    | Analizar movimientos REVISAR del cuadre: agrupar + diagnosticar |
| `/lecciones`  | Mostrar tasks/lessons.md y proponer nuevas reglas               |
| `/plan`       | Crear o revisar tasks/todo.md para la sesión actual             |

---

## CHANGELOG

### v5.2 (16/03/2026) — EXTRACTORES: FIXES BM + JIMELUZ + DOCS ACTUALIZADAS
- ✅ **BM Supermercados v6.2** — `extraer_referencia()` tolera OCR garbled (`F\uFFFDCTURA` → regex `F.{0,3}CTURA`). Fallbacks: 17 dígitos consecutivos, alfanumérico largo. Tickets térmicos atrasados → entrada manual (SIN_TOTAL irresoluble por calidad OCR)
- ✅ **JIMELUZ v3** — 0% IVA aceptado (frutas/verduras genuinamente a 0%). Base sin separador decimal corregida (`"341"` → `3.41`). Resultado: 6/9 OK (antes 1/9)
- ✅ **FELISA GOURMET** — confirmado 100% OK desde v5.1. Sin cambios necesarios
- ✅ **LA ROSQUILLERIA** — confirmado 100% OK desde 04/01/2026. Reescrito ese día (capturaba SUBTOTAL en lugar de TOTAL)
- ✅ **ESQUEMA actualizado** — skills tree 6→9 (lecciones, plan, revisar), gmail 4 archivos añadidos, extractores 101→~104, cuadre v1.5b→v1.6, clasificadores_mejorados ubicación corregida
- ✅ **Parseo/CLAUDE.md v2.0** — creado con atributos ExtractorBase, patrones avanzados (importes_con_iva, extraer_texto() custom, Fallback MERGE), tabla OCR y proveedores prioritarios actualizados
- ✅ **Facturas/CLAUDE.md** — creado con reglas universales (Excel, archivos prohibidos, estilo Python, autonomía)
- ✅ **gestion-facturas/CLAUDE.md v4.0** — refactorizado eliminando duplicados con root CLAUDE.md

### v5.1 (13/03/2026) — PARSEO: LIMPIEZA Y CONSOLIDACIÓN
- ✅ **Consolidar `_convertir_europeo` en base.py** — 70 extractores tenían copias idénticas (~1000 líneas)
  - `_convertir_importe()` reescrito como superset: soporta €, espacios, formato ES/US, variantes OCR
  - `_convertir_europeo()` añadido como alias en base.py (compatibilidad)
  - Eliminadas las 70 copias locales → todos heredan de base.py
- ✅ **VERSION unificada** — `config/settings.py` es fuente única (5.18), `main.py` importa de ahí
  - Antes: settings.py decía 5.7, main.py decía 5.15, git decía 5.18
- ✅ **DICCIONARIO_DEFAULT corregido** — Apuntaba a `ParsearFacturas-main` (path antiguo)
- ✅ **Código muerto eliminado** — `salidas/excel.py`: bloque duplicado inalcanzable tras `return`
- ✅ **Archivos basura eliminados** — `cd`, `for`, `from`, `python`, `print(*)` (artefactos bash)
- 74 archivos modificados, -1120 líneas netas

### v5.0 (12/03/2026) — PARSEO v5.18: UNIFICACIÓN + FIXES
- ✅ **Unificación `extraer_numero_factura` → `extraer_referencia`** — 66 extractores renombrados
  - Eliminado método duplicado: todos usan `extraer_referencia()` como nombre canónico
  - Eliminado puente de compatibilidad en `base.py` (ya no existe `extraer_numero_factura`)
  - 8 archivos adicionales limpiados (aliases inversos, self-calls)
- ✅ **Fix WEBEMPRESA descuadre** — `extraer_total()` capturaba "Sub Total" en vez de "Total"
  - Solución: lookbehind negativo `(?<!Sub )` en regex
  - Resultado: 0/1 → 3/3 OK
- ✅ **Fix KINEMA descuadre** — Líneas de servicio sin código 5 dígitos no se extraían
  - Solución: segundo patrón regex para líneas sin código (ej: "CÁLCULO Y AJUSTE CUOTA AUTÓNOMOS")
  - Resultado: 2/3 → 13/13 OK
- ✅ **Fechas Excel nativas** — Antes: strings "DD/MM/YYYY" → Ahora: datetime con formato DD/MM/YYYY
  - `parsear_fecha()`: convierte strings a datetime objects
  - `_aplicar_formato_fecha()`: aplica number_format 'DD/MM/YYYY' a celdas
  - 905 celdas datetime, 0 strings, 13 vacías (esperado)
- ✅ **Fix fechas AMAZON** — Formato punto `28.03.2025` no se reconocía
  - Añadido `\.` como separador en patrones de fecha (`nucleo/parser.py`)
- ✅ **Fix REFs basura** — Genérico capturaba "Fecha", "DATOS", "DE", "erencia", "Cliente"
  - Patrones más estrictos que requieren dígitos en la referencia
  - Blacklist de palabras inválidas (FECHA, DATOS, DE, CLIENTE, ERENCIA...)
  - Lookbehind `(?<!FECHA )` para evitar capturar fechas como "Factura:"
  - Filtro de fechas parciales (`^\d{1,2}/\d{1,2}`)
  - Resultado: 206 válidas, 44 vacías, 3 cortas-pero-reales
- ✅ **`salidas/` incluido en git** — Contenía código fuente (excel.py, log.py) excluido por error en .gitignore

### v4.9 (12/03/2026) — CUADRE v1.6 + GMAIL v1.14
- ✅ **GMAIL actualizado a v1.14** — Fallback parcial: si extractor dedicado obtiene datos parciales, complementa con genérico (+ OCR)
- ✅ **Skill /revisar** — Analiza movimientos REVISAR del cuadre: agrupa, diagnostica y genera plan de acción
- ✅ **CUADRE v1.6** — Alias "ONE WORLD TRADE" para MAKE.COM/CELONIS
- ✅ **CUADRE actualizado a v1.6** — 4 clasificadores mejorados, 27 movimientos rescatados (590→563 REVISAR)
  - Yoigo: regex flexible `Y?(C\d{9,})` detecta facturas con/sin prefijo Y + fuzzy ≥90% fallback
  - Suscripciones ampliadas: SPOTIFY/NETFLIX/AMAZON PRIME (sin factura) + MAKE.COM→CELONIS/OPENAI→OPENAI LLC (con factura vinculada por mes)
  - Comunidad vecinos: asigna las 2 facturas ISTA METERING más cercanas en fecha al movimiento
  - Alquiler: busca facturas de Ortega Alonso Benjamin + Fernandez Moreno Jaime del mes del movimiento
  - 25 cambios de categoría mejorados (nombres normalizados: SPOTIFY→GASTOS VARIOS, OPEN AI→OPENAI LLC, YOIGO→XFERA MOVILES SAU, MAKE→CELONIS INC.)
  - Validado con Prueba Año 25.xlsx (3945 mov): 0 regresiones en Comestibles, solo mejoras en Tasca
- ✅ **ESQUEMA actualizado a v4.9** — Poda changelog (compactado v1.0-v3.0), sección 7 actualizada
- ✅ **Conflicto de versión resuelto** — cuadre.py header decía v1.4 mientras ESQUEMA ya tenía v1.5/v1.5b; ahora alineados en v1.6

### v4.8 (12/03/2026) — HARDENING: EXCEPCIONES + PROTECCIÓN EXCEL + CLAUDE.md
- ✅ **12 bare `except:` eliminados** — Reemplazados por excepciones específicas en 6 archivos
  - `gmail/gmail.py` (4), `gmail/auth.py` (2), `gmail/generar_sepa.py` (2),
    `nucleo/parser.py` (2), `cuadre/banco/cuadre.py` (1), `cuadre/banco/clasificadores/compra_tarjeta.py` (1)
- ✅ **Detección Excel abierto** — `_verificar_archivo_no_abierto()` antes de cada escritura
  - Integrado en `script_barea.py:save_to_excel()` y `salidas/excel.py` (2 funciones)
  - Captura `PermissionError` y aborta con mensaje claro en español
- ✅ **Auto pip install eliminado** de `script_barea.py` — Sustituido por ImportError claro
- ✅ **requirements.txt actualizado** — Añadido `Pillow==11.2.1` (dependencia de pdf2image/reportlab)
- ✅ **CLAUDE.md creado** en raíz del proyecto — Contexto, convenciones, reglas y skills para Claude Code
- ✅ **Plan de mejora documentado** — 4 fases (Quick wins → Estabilidad → Features → Arquitectura)
- ✅ **Logging en script_barea.py** — ~50 prints reemplazados por `logging` (módulo estándar)
  - Logger `barea`: archivo (`outputs/logs_ventas/YYYY-MM-DD.log`, DEBUG) + consola (INFO)
  - Archivo con formato `HH:MM:SS [LEVEL] mensaje`, consola solo mensaje limpio
  - Niveles: info (progreso), warning (problemas no críticos), error (fallos que abortan)
- ✅ **Backup automático de Excel** — `_backup_excel()` en `save_to_excel()`
  - Copia el Excel a `datos/backups/` antes de la primera escritura de cada ejecución
  - Formato: `NombreArchivo_YYYYMMDD_HHMMSS.xlsx`
  - Una sola copia por archivo por ejecución (set `_backed_up`)
- ✅ **Smoke tests** — `tests/test_script_barea.py` con 52 tests (pytest)
  - Funciones puras: `_to_float`, `_fmt_eur`, `_fmt_num`, `_pct_var`, `_var_html`, `_parse_gbp_num`
  - Fechas: `calcular_semana_anterior`, `_semana_equivalente_año_anterior`, `parse_fecha`
  - Lookups: `resolve`
  - Recibos: `procesar_recibos` (5 casos: normal, vacío, cancelado, columnas)
  - Excel: `save_to_excel` (4 casos: nuevo, dedup, vacío, sin unique_col)
  - IVA: `check_iva_anomalies` (5 casos: normal, multi-iva, bajas, vinos-21%, no existe)
  - Backup: `_backup_excel` (no existe, no duplica)

### v4.7 (10/03/2026) — GOOGLE BUSINESS PROFILE
- ✅ **Recogida automática datos GBP** — Nuevo paso 5 en `script_barea.py` (1er lunes de mes)
  - `recoger_google_business(target_year)`: parsea emails mensuales de Google Business Profile
  - Métricas: interacciones, llamadas, chat, indicaciones, visitas web, vistas perfil, búsquedas, menú
  - Variaciones % mes a mes para cada métrica principal
  - Top 3 términos de búsqueda con volumen
  - Guarda en pestaña `GoogleBusiness` de `Ventas Barea 2026.xlsx` (21 columnas)
  - Dedup por mes (unique_col="Mes")
- ✅ **Parser HTML emails GBP** — `_parse_gbp_email()` + `_parse_gbp_num()`
  - Extrae datos del email mensual "informe de rendimiento" de Google
  - Limpieza HTML→texto con separadores pipe, regex para cada métrica
  - Detección automática de mes/año desde el subject del email
- ✅ **Histórico GBP 2025** — 12 meses guardados en `Ventas Barea Historico.xlsx` → `GoogleBusiness25`
  - Emails reenviados desde benjaimes@gmail.com → tascabarea@gmail.com (filtro Gmail)
  - Token OAuth renovado con scope `business.manage` (`renovar_token_business.py`)
- ✅ **Flujo completo actualizado**: 1.WooCommerce → 2.Loyverse → 3.Artículos → 3b.IVA → 4.Dashboards → 5.GBP → 6.Email semanal

### v4.6 (09/03/2026) — DETECCIÓN ANOMALÍAS IVA + EMAIL RESUMEN SEMANAL
- ✅ **Email resumen semanal** — Nuevo paso 5 en `script_barea.py` (cada lunes tras dashboards)
  - `enviar_email_semanal()`: genera y envía HTML con resumen de ventas
  - KPIs por tienda (Tasca + Comestibles): ventas netas, tickets, ticket medio
  - Comparativa triple: vs semana anterior + vs misma semana año anterior
  - YTD acumulado vs mismo periodo año anterior
  - Top 10 productos por facturación y por unidades, con variaciones
  - WooCommerce incluido si hubo pedidos
  - Datos históricos desde `Ventas Barea Historico.xlsx` (2023-2025) + año actual
  - Manejo formato decimal español (datos 2024 con comas)
  - Destinatarios en `EMAILS_RESUMEN_SEMANAL` (fácil de ampliar)
  - HTML profesional: cabecera azul, tablas con flechas ▲▼ coloreadas, filas alternadas
- ✅ **Detección anomalías IVA** — Nuevo paso 3b en `script_barea.py` (proceso semanal)
  - `check_iva_anomalies()`: se ejecuta tras `update_articles_history()` para cada tienda
  - Detecta: artículos con varios IVA simultáneos (MULTI-IVA), IVA al 0%, IVA 21% en categorías no permitidas
  - Categorías permitidas 21%: VINOS, BODEGA, LICORES, VERMÚS, CACHARRERÍA, BAZAR, EXPERIENCIAS
  - Resultado en log semanal (warnings o "sin anomalías")
- ✅ **Prioridades 8 y 9 añadidas** al roadmap (sección 9)
  - 8️⃣ Cruce Artículos↔Proveedores via `DiccionarioProveedoresCategoria.xlsx` (pendiente)
  - 9️⃣ Separar Historial_Precios a Excel independiente (posible mejora)
- ✅ **ARTICULOS documentado** — Tabla documentos actualizada
  - `Articulos 26.xlsx`: 4 hojas (Comestibles 572, Tasca 87, Historial_Precios, Hoja1)
  - Columnas clave: Handle, REF, Nombre, Categoria, Coste, Precio, IVA (0/4/10/21%), ESTADO, FECHA_BAJA
  - Actualización automática semanal via Loyverse API (altas, bajas, cambios precio)
  - `DiccionarioProveedoresCategoria.xlsx`: 1282 artículos×proveedor (69 proveedores, 131 categorías)

### v4.3 (03/03/2026) — CATEGORÍAS SIMPLIFICADAS
- ✅ **Categorías Comestibles reducidas de 21 a 13** — Mapeo en `generar_dashboard.py`
  - Nuevo `CAT_MAP`: diccionario de 10 categorías Loyverse que se fusionan al cargar datos
  - Nueva función `_remapear_categorias(df)`: aplica `CAT_MAP` a columna Categoria
  - Llamada en `cargar_datos()` para datos 2025 (histórico) y 2026 (actual)
  - Fusiones: APERITIVOS/SALAZONES/SALSAS→DESPENSA, CONSERVAS MAR/MONTAÑA/VEGETALES→CONSERVAS,
    BODEGA Y CERVEZAS/LICORES Y VERMÚS→BODEGA, CACHARRERIA→BAZAR, OTROS COMESTIBLES→OTROS
  - `CAT_COLORS` actualizado: 22 entradas → 13 (colores heredados de categoría principal)
  - Loyverse no se toca: el mapeo se aplica solo al generar dashboards
  - Tasca no afectada (tiene sus propias categorías)

### v4.2 (03/03/2026) — AUDITORÍA DE SEGURIDAD
- ✅ **Datos sensibles externalizados** — Creado `config/datos_sensibles.py` (gitignored)
  - IBANs empresa (TASCA, COMESTIBLES), BIC, NIF_SUFIJO, CIF_PROPIO
  - 146 proveedores con IBAN/CIF/DNI (`PROVEEDORES_CONOCIDOS`)
  - 67 mapeos CIF→proveedor (`CIF_A_PROVEEDOR`)
  - Emails socios (`EMAILS_FULL`, `EMAILS_COMES_ONLY`)
  - Plantilla `datos_sensibles.py.example` para nuevos despliegues
  - Módulos modificados: `proveedores.py`, `settings.py`, `gmail.py`, `generar_sepa.py`,
    `parser.py`, `generar_dashboard.py`, `README.md`
- ✅ **68 archivos financieros desrastreados** — `git rm --cached`
  - 55+ archivos en `outputs/` (Excel, backups, logs, TSV, CSV, TXT)
  - Datos maestros: MAESTRO_PROVEEDORES, emails_procesados.json, Ventas, Artículos, Movimientos
  - `.gitignore` ampliado: `datos/*.xlsx`, `*.n43`, `desktop.ini`, `datos_sensibles.py`
- ✅ **Historial git purgado** — `git filter-repo` en 2 pasadas
  - Pasada 1: 73 archivos binarios eliminados del historial
  - Pasada 2: 65 patrones texto reemplazados (IBANs, DNIs, emails → REDACTED_*)
  - Force-push a origin/main
- ✅ **barea-dashboard → PRIVATE** — Repo contenía datos financieros expuestos públicamente
  - `gh repo edit TascaBarea/barea-dashboard --visibility private`
  - GitHub Pages desactivado (no funciona en plan gratuito con repo privado)
- ✅ **alerta_fallo.py mejorado** — Scope reducido + token refresh
  - Scope: `gmail.modify` → `gmail.send` (principio de menor privilegio)
  - Token refresh automático con `google.auth.transport.requests.Request`
  - Email destino: `tascabarea@gmail.com`
- ✅ **GitHub CLI instalado** — `gh` para gestión repos desde terminal
  - Autenticado con device flow (browser)
  - Usado para cambiar visibilidad repo, verificar estado
- ✅ **6 skills Claude Code creadas** — `.claude/skills/` (estado, dashboard, log-gmail, extractor, esquema, ventas)
- ✅ **Automatización bat files corregidos** — curl con HTTPS, alertas email, encoding UTF-8

### v4.1 (01/03/2026)
- ✅ **Rediseño profesional PDF** — Informes mensuales con diseño visual mejorado
  - Cabecera: banda azul oscuro (#1B2A4A) con título blanco, logos y línea dorada de acento
  - PDF Comestibles: banda verde (#1B5E20) con acento verde claro
  - KPIs como tarjetas lado a lado con número grande, flechas ▲▼ de color para variación
  - Gráficos matplotlib: fondo sutil, área sombreada bajo línea actual, etiquetas de valor,
    años anteriores semitransparentes, sin bordes superior/derecho, DPI 180
  - Tablas categorías con filas alternadas (#F7F8FA), cabeceras temáticas por negocio
  - Pie de página en cada hoja: línea separadora + fecha generación + número de página
  - Estructura 3 páginas (PDF completo): KPIs+Comparativa / Evolución / Categorías
  - Helpers extraídos: `_setup_pdf_fonts()`, `_kpi_card()`, `_tabla_categorias_pdf()`

### v4.0 (01/03/2026)
- ✅ **DASHBOARD TASCA implementado** — Dashboard interactivo Tasca con Chart.js (4 años: 2023-2026)
  - `dashboard_tasca_template.html`: 5 placeholders (`{{RAW_DATA}}`, `{{PBM_DATA}}`, etc.)
  - Creado a partir de `dashboard_tasca_v2.html` (estático) → templatizado
  - Funciones: `cargar_datos_tasca()`, `calcular_RAW()`, `calcular_PBM_tasca()`, `generar_html_tasca()`
  - 6 categorías: BEBIDA, COMIDA, VINOS, MOLLETES, OTROS, PROMOCIONES
  - Sin rotación ni rentabilidad (solo Comestibles tiene esos datos)
- ✅ **Comestibles reducido a 2025-2026** — Eliminado 2024 por volumen bajo
  - `YEAR_LIST` de `["2024","2025","2026"]` → `["2025","2026"]`
  - `cargar_datos()`: eliminada lectura de hojas `ComestiblesItem24`/`ComestiblesRecibos24`
  - Template CSS limpiado de `--c24`, `.year-tab[data-yr="2024"]`
- ✅ **PDF resumen mensual** — matplotlib + reportlab (rediseñado en v4.1)
  - `generar_pdf_resumen()`: PDF completo A4 (Tasca + Comestibles)
  - `generar_pdf_comestibles()`: PDF solo Comestibles (para socios parciales)
  - Ver changelog v4.1 para detalle del diseño actual
- ✅ **Email segmentado** — Dos grupos de destinatarios
  - `EMAILS_FULL` (3 socios): Roberto, Benjamín, Jaime → email completo + PDF completo
    + ambos dashboards HTML adjuntos + links GitHub Pages Tasca + Comestibles
  - `EMAILS_COMES_ONLY` (1 socia): Elena → email solo Comestibles + PDF solo Comestibles
    + solo dashboard Comestibles HTML adjunto
  - Refactorizado: `_conectar_gmail()`, `_enviar_mensaje()`, `_kpis_variacion_html()`
- ✅ **GitHub Pages multi-file** — Landing page + ambos dashboards
  - `index.html`: estilo dark con cards a Tasca y Comestibles
  - `comestibles.html` + `tasca.html`: dashboards publicados
  - `publicar_github_pages()` reescrito para 3 archivos
- ✅ **Dependencias actualizadas** — matplotlib==3.10.0 + reportlab==4.4.0 añadidos
  - `requirements.txt` actualizado (16 dependencias)
  - `script_barea.py:install_requirements()` actualizado
  - `NumpyEncoder` para serialización JSON de tipos numpy (int64/float64)
- ✅ **VENTAS subido a v4.0** (antes v3.0, 90% → 95%)

### v3.0 (28/02/2026) — DASHBOARD COMESTIBLES + EMAIL + GITHUB PAGES + AUTOMATIZACIÓN
- ✅ Dashboard HTML Comestibles con Chart.js (rotación, rentabilidad, WooCommerce)
- ✅ Email socios via Gmail API + GitHub Pages (barea-dashboard)
- ✅ Automatización Windows: barea_auto.bat (lunes 03:00, 1er lunes → dashboard mensual)
- ✅ HARDENING: .gitignore, requirements.txt, save_to_excel seguro, timeouts HTTP, alerta_fallo.py, rutas relativas .bat

### v2.5-v2.9 (14/02 - 28/02/2026) — GMAIL v1.5-v1.8 + EXTRACTORES + PROFORMAS
- v2.9: Sistema proforma (es_proforma, OBS multi-flag) + 6 extractores corregidos (MRM, ECOFICUS, LA LLEIDIRIA...)
- v2.8: Gmail v1.8 (5 fixes) + Cuadre v1.5b (SERVICIO DE TPV, +16 aliases) + Ventas v2.0 (reescrito)
- v2.7: Cuadre v1.5 (refactoring: buscar_factura_candidata, indice_aliases O(1)) + estructura carpetas
- v2.6: Gmail v1.7 (6 parches 1ª ejecución prod) + la_llildiria.py + borboton.py fix + Claude Code instalado
- v2.5: Documentación extractores (sección 5.6) + Facturas Provisional.xlsx

### v2.0-v2.4 (30/01 - 13/02/2026) — GMAIL v1.4-v1.6 + PARSEO 91→99 EXTRACTORES
- v2.4: Gmail v1.6 (anti-duplicados, auto-reconexión, sanitización, anti-suspensión)
- v2.3: Gmail v1.5 (mover todos a PROCESADAS) + 4 extractores corregidos (BERNAL, DE LUIS, TERRITORIO CAMPERO, YOIGO)
- v2.2: PARSEO 91→99 extractores + fórmula distribución portes IVA
- v2.1: Gmail v1.4, 91 extractores, LocalDropboxClient, SEPA, ATRASADAS
- v2.0: Ⓑ GMAIL como módulo funcional + MAESTRO actualizado

### v1.0-v1.1 (27-28/01/2026) — VERSIÓN INICIAL
- Esquema inicial + detalle Ⓓ CUADRE

---

**Documento de referencia para todas las sesiones futuras.**

✅ **APROBADO POR:** Tasca
📅 **FECHA:** 13/03/2026

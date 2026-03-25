1
# 📐 ESQUEMA PROYECTO GESTIÓN-FACTURAS

**Versión:** 5.0
**Fecha:** 25/03/2026
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
│   │  ✅ 85% │    │  ✅ 98% │    │  ✅ 95% │    │  ✅ 75% │                 │
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
| ③ | **VENTAS** | Ventas Barea 2026.xlsx | TascaRecibos + TascaItems + ComesRecibos + ComesItems + WOO | Ⓒ VENTAS | Informes |
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
ESTADO:        ✅ Funciona - 99 extractores dedicados
```

### Ⓑ GMAIL (98% completado) ✅ v1.14
```
UBICACIÓN:     C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\
ENTRADA:       Gmail (etiqueta FACTURAS) + MAESTRO_PROVEEDORES
SALIDA:        - PDFs descargados y renombrados en Dropbox local
               - PAGOS_Gmail_XTxx.xlsx (FACTURAS + SEPA) — 15 columnas
               - PROVEEDORES_NUEVOS_*.txt (sugerencias)
               - ⚠️_IBANS_SUGERIDOS_*.xlsx (verificación)
INICIO:        AUTOMÁTICO (viernes 03:00) o MANUAL
FRECUENCIA:    Semanal
ESTADO:        ✅ v1.14 - Fallback parcial extractores + cuadre alias MAKE.COM
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
SALIDA:        - Ventas Barea 2026.xlsx (5 pestañas):
                 TascaRecibos (19 cols), TascaItems (23 cols),
                 ComesRecibos (19 cols), ComesItems (23 cols), WOOCOMMERCE
               - Dashboards HTML interactivos:
                 dashboards/dashboard_comes.html (Comestibles 2025-2026)
                 dashboards/dashboard_tasca.html (Tasca 2023-2026)
               - PDFs resumen mensual:
                 dashboards/informe_barea_*.pdf (completo: Tasca + Comestibles)
                 dashboards/informe_comestibles_*.pdf (solo Comestibles)
               - GitHub Pages: DESACTIVADO (alternativa: Netlify para datos JSON)
               - Streamlit app: tascabarea.streamlit.app (multi-usuario con roles)
INICIO:        AUTOMÁTICO (lunes 03:00) o MANUAL
FRECUENCIA:    Semanal (ventas) + Mensual (dashboard cerrado + email + PDF)
ESTADO:        ✅ v4.7 - Dual dashboard + PDF + email + Streamlit app multi-usuario
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

### Ⓓ CUADRE (75% - FUNCIONAL) ✅ v1.7
```
UBICACIÓN:     gestion-facturas/cuadre/banco/cuadre.py
ENTRADA:       - Excel gestoría (Tasca + Comestibles + Facturas)
               - MAESTRO_PROVEEDORES.xlsx (195 proveedores, ~585 aliases)
SALIDA:        - Excel con Categoria_Tipo + Categoria_Detalle
               - Columna Origen en hoja Facturas
               - Archivo LOG con decisiones
INICIO:        MANUAL (GUI selección archivo)
FRECUENCIA:    Mensual/Trimestral
VERSIÓN:       v1.7
ESTADO:        ✅ Funciona - SERVICIO DE TPV + aliases nuevos
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
│   │   ├── gmail.py                 ← Módulo principal v1.14 (~2200 líneas)
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
│   │   └── gmail_auto_setup.bat     ← Setup tarea programada
│   │
│   ├── cuadre\                      ← Ⓓ CUADRE (✅ v1.7)
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
│   ├── streamlit_app\               ← 🌐 APP WEB multi-usuario (✅ Fase 1)
│   │   ├── app.py                   ← Login + st.navigation() por rol
│   │   ├── pages\
│   │   │   ├── alta_evento.py       ← Crear eventos WooCommerce
│   │   │   ├── calendario_eventos.py ← Eventos futuros + asistentes + Excel
│   │   │   ├── ventas.py            ← Dashboard Ventas (placeholder Fase 2)
│   │   │   ├── cuadre.py            ← Cuadre Bancario (placeholder Fase 2)
│   │   │   ├── log_gmail.py         ← Log Gmail (placeholder Fase 2)
│   │   │   └── monitor.py           ← Monitor Sistema (placeholder Fase 2)
│   │   ├── utils\
│   │   │   ├── auth.py              ← Roles, require_role(), check_login()
│   │   │   └── wc_client.py         ← Wrapper WC API + funciones eventos
│   │   ├── requirements.txt         ← streamlit, WooCommerce, pandas, openpyxl
│   │   └── .streamlit\
│   │       ├── config.toml          ← Tema verde (#2E7D32)
│   │       └── secrets.toml         ← Users + WC keys (gitignored)
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
│   ├── .claude\skills\              ← 6 skills personalizadas Claude Code
│   │   ├── estado/SKILL.md          ← /estado: resumen proyecto
│   │   ├── dashboard/SKILL.md       ← /dashboard: generar dashboards
│   │   ├── log-gmail/SKILL.md       ← /log-gmail: analizar logs
│   │   ├── extractor/SKILL.md       ← /extractor: crear extractores
│   │   ├── esquema/SKILL.md         ← /esquema: actualizar ESQUEMA
│   │   └── ventas/SKILL.md          ← /ventas: descargar ventas
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

## 5. Ⓐ PARSEO - EXTRACTORES (99 total)

### 5.1 Estado de Extractores

| Categoría | Extractores | Tasa Éxito | Notas |
|-----------|-------------|------------|-------|
| **Alimentación** | 45 | 95% | BERNAL, ECOFICUS, MRM, PORVAZ... |
| **Bebidas** | 18 | 90% | Cervezas, vinos, refrescos |
| **Servicios** | 15 | 85% | Telefonía, energía, seguros |
| **Material** | 12 | 80% | Papelería, envases |
| **OCR** | 7 | 75% | LA LLILDIRIA, CASA DEL DUQUE... |

### 5.2 Extractores Corregidos (28/02/2026 - v1.9)

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
    def extraer_numero_factura(self, texto) -> str    # Alias, prioridad sobre extraer_referencia
    def es_proforma(self, texto) -> bool              # Detecta \bPROFORMA\b en texto

    # UTILIDADES HEREDADAS
    def _convertir_importe(self, texto) -> float      # Español/americano → float
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

### 5.7.5 Estadísticas (99 extractores)

| Concepto | Valor |
|---|---|
| Total extractores | 99 |
| Método pdfplumber | 91 (92%) |
| Método OCR | 6 (6%): fishgourmet, gaditaun, jimeluz, la_cuchara, manipulados_abellan, tirso |
| Método pdfplumber+fallback_ocr | 1 (1%): la_lleidiria (facturas nuevas=texto, antiguas=imagen) |
| Método híbrido | 2 (2%): angel_borja, casa_del_duque |
| Con extraer_total propio | 90 (100%) |
| Con extraer_fecha propio | 90 (100%) |
| Con extraer_referencia o extraer_numero_factura | 89 (~99%) |
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

**REFERENCIA:** Filtro anti-falsos positivos en `_es_referencia_valida()`: excluye teléfonos, CIFs, fechas, números de cliente, palabras sueltas. Mínimo 3 caracteres y 2 dígitos.

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
   - extraer_numero_factura() si la referencia es especial

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

## 6. Ⓑ GMAIL v1.14 - DETALLE TÉCNICO

### 6.1 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Ⓑ GMAIL MODULE v1.14                              │
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

## 7. Ⓓ CUADRE v1.7 - DETALLE

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
| **Servicio TPV** | `SERVICIO DE TPV` | SERVICIO DE TPV | (cargo bancario) |
| **Alquiler** | `BENJAMIN ORTEGA` | ALQUILER | Local |

### 7.2 Arquitectura cuadre.py (v1.7)

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

### 7.5 Resultados verificados (Movimientos Cuenta 2025.xlsx)

| Métrica | v1.5 | v1.5b |
|---|---|---|
| Total movimientos | 3945 | 3945 |
| Clasificados | 3324 (84.3%) | 3355 (85.1%) |
| REVISAR | 621 (15.7%) | 590 (14.9%) |
| MAESTRO aliases | 565 filas | ~585 filas |

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
| ~~4️⃣~~ | ~~Ⓒ VENTAS~~ | ~~Loyverse + Woocommerce~~ | ✅ **v4.0 (95%)** |
| ~~5️⃣~~ | ~~Informes~~ | ~~Dashboards + PDF + email~~ | ✅ **Comes + Tasca** |
| 6️⃣ | Limpiar WooCommerce | Reducir 69→10 columnas en pestaña WOOCOMMERCE (Ventas Barea) | 🟡 Pendiente |
| 7️⃣ | Integrar | Mover PARSEO a gestion-facturas | ❌ Futuro |

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

## CHANGELOG

### v5.0 (25/03/2026) — APP STREAMLIT MULTI-USUARIO + SYNC VERSIONES
- ✅ **Streamlit app multi-usuario** — tascabarea.streamlit.app (Fase 1 completada)
  - Login con usuario+contraseña, 4 roles: admin, socio, comes, eventos
  - `st.navigation()` filtra páginas por rol (Streamlit >=1.32)
  - `utils/auth.py`: check_login(), require_role(), ROLE_PAGES
  - `utils/wc_client.py`: funciones eventos WC (tipos, futuros, pedidos)
  - Usuarios: Jaime (admin), Roberto (socio), Elena (comes), Benjamin (eventos)
- ✅ **Alta de Evento mejorada** — Selectbox con nombres reales de cursos WC
  - Carga productos tipo `ticket-event` de WooCommerce API
  - Opción "Otro (escribir)" para texto libre
  - Validación plazas 1-30 con aviso fuera de rango 7-11
- ✅ **Calendario de Eventos** — Nueva página con asistentes y export Excel
  - Eventos futuros con fechas extraídas del nombre HTML del producto
  - Asistentes: nombre, email, teléfono, tickets, fecha compra
  - Métricas: total personas, tickets vendidos, plazas libres
  - Exportación Excel con openpyxl y columnas auto-ajustadas
- ✅ **Repo PUBLIC** — Necesario para Streamlit Community Cloud (free tier)
  - Auditoría de seguridad completada antes de hacer público
  - TASCA_BAREA_CONTEXT.md eliminado + purgado del historial git
  - WooCommerce API keys rotadas (antiguas revocadas)
- ✅ **Versiones sincronizadas** — ESQUEMA alineado con código fuente
  - Gmail: v1.9 → v1.14 | Ventas: v4.2 → v4.7 | Cuadre: v1.5b → v1.7
- ✅ **14 skills Claude Code** — 8 nuevas desde v4.3
  - Nuevas: /cuadre, /debug-extractor, /nuevo-proveedor, /validar-patrones,
    /lecciones, /plan, /revisar, /log-gmail

### v4.4 (20/03/2026) — DOCUMENTACIÓN IA + VERSIONES REVISADAS
- ✅ **CLAUDE.md actualizado a v4.0** — Skills, prioridades, errores conocidos
- ✅ **Gmail v1.14** — Fallback parcial extractores + cuadre alias MAKE.COM
- ✅ **Versión ESQUEMA corregida** (referencia incorrecta v5.3 → v4.4)

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

### v3.0 (28/02/2026)
- ✅ **DASHBOARD COMESTIBLES implementado** — Dashboard HTML interactivo con Chart.js
  - `generar_dashboard.py`: lee Excel (3 años: 2024-2026), genera HTML con datos JSON inyectados
  - Template-based: `dashboard_comes_template.html` con placeholders `{{D_DATA}}`, `{{MD_DATA}}`, etc.
  - Gráficas: ventas mensuales, categorías, ticket medio, comparativa interanual
  - Análisis rotación productos: alta/baja/todos con umbral dinámico `Math.max(0.3, 1/_n + 0.01)`
  - Rentabilidad (margen €/kg) por producto con datos del MAESTRO
  - WooCommerce integrado (cursos online) con filtrado por año
  - Manejo formato decimal español 2024 ("3,51" string → 3.51 float)
- ✅ **Filtrado meses cerrados** — Flag `--solo-cerrados` excluye mes en curso
  - `_filtrar_meses_cerrados()`: filtra items, recibos y WooCommerce del año actual
  - Años históricos (2024, 2025) no se tocan (ya cerrados)
- ✅ **Email socios via Gmail API** — Flag `--email` envía resumen KPI
  - Reutiliza OAuth2 existente de Ⓑ GMAIL (credentials.json + token.json)
  - HTML con tabla KPIs: ventas, tickets, ticket medio, top categoría
  - Comparativa con mismo mes del año anterior (si existe)
  - Dashboard HTML como archivo adjunto + link GitHub Pages
  - 4 destinatarios configurados: Roberto, Benjamín, Jaime, Elena
- ✅ **GitHub Pages** — Dashboard público con URL fija
  - Repo: `TascaBarea/barea-dashboard` (creado y configurado via API)
  - URL: https://tascabarea.github.io/barea-dashboard/
  - Push automático: copia HTML → `index.html` → git add/commit/push
- ✅ **Automatización Windows** — Tarea programada semanal
  - `barea_auto.bat`: anti-suspensión, verificaciones, logging
  - `barea_auto_setup.bat`: crea tarea `Ventas_Barea_Semanal` (lunes 03:00, WakeToRun)
  - Cada lunes: descarga ventas + regenera dashboard
  - 1er lunes del mes (día ≤ 7): `--dashboard-mensual` → meses cerrados + email socios
  - `script_barea.py`: nuevo flag `--dashboard-mensual` integrado
- ✅ **VENTAS subido a v3.0** (antes v2.0, 80% → 90%)
- ✅ **HARDENING: 6 mejoras de robustez del proyecto**
  - H1 `.gitignore` completo: excluye `.env`, `config_local.py`, `credentials.json`,
    `token.json`, `outputs/*.xlsx`, `outputs/*.json`, `outputs/backups/`, `outputs/logs_*/`
  - H2 `requirements.txt` creado: 14 dependencias con versiones fijadas (pandas==2.3.0, etc.)
  - H3 Fix `save_to_excel()` en `script_barea.py`: lee datos existentes ANTES de abrir el writer;
    si la lectura falla (Excel abierto, fichero corrupto), ABORTA en vez de sobreescribir con datos vacíos
    (antes: `except Exception` destruía silenciosamente todo el histórico)
  - H4 `timeout=30` en todas las llamadas HTTP: `requests.get()` Loyverse + WooCommerce API.
    Evita cuelgues indefinidos si la API no responde
  - H5 `alerta_fallo.py` (nuevo): envía email de alerta a jaimefermo@gmail.com cuando una tarea
    programada falla. Integrado en `gmail_auto.bat` y `barea_auto.bat` (si exit code ≠ 0).
    Fix captura exit code en `barea_auto.bat` (`set EXIT_CODE=%ERRORLEVEL%` inmediato)
  - H6 Rutas relativas en todos los `.bat`: `%~dp0` + `for %%i in ("%~dp0\..") do set PROJECT_ROOT=%%~fi`
    en vez de rutas absolutas hardcodeadas. Portabilidad: mover el proyecto no requiere editar .bat
- ✅ **Outputs eliminados del tracking git** — ficheros financieros (Excel con IBANs, backups, logs)
  ya no se versionan; quedan solo en local

### v2.9 (28/02/2026)
- ✅ **SISTEMA PROFORMA implementado** — Detección y marcado automático de proformas
  - `ExtractorBase.es_proforma()`: detecta `\bPROFORMA\b` en texto del PDF
  - `FacturaExtraida.es_proforma`: nuevo campo bool propagado por todo el pipeline
  - Columna OBS multi-flag: "PROFORMA", "DUPLICADO", "DUPLICADO | PROFORMA"
  - Patrones REF proforma genéricos: PVT/, PRF/, PRO/ (en base.py)
  - Patrón TOTAL PROFORMA añadido a `extraer_total()` genérico
  - `extraer_referencia()`: patrón `Número` con acento y colon opcionales
- ✅ **6 extractores corregidos** (análisis con PDFs reales):
  - MRM: REF completa "1-2026-7545" (antes solo "1-2026") + soporte unidad "P" (peso)
  - MOLIENDA VERDE: `N[uú]mero` para manejar acento variable de pdfplumber
  - ECOFICUS: soporte proforma completo (REF PVT/, TOTAL PROFORMA, fecha sin colon, líneas sin lote)
  - LA LLEIDIRIA: `metodo_pdf='pdfplumber'` con `fallback_ocr=True` (facturas nuevas son texto)
  - LA LLEIDIRIA: formato línea actualizado (`Kg/\w+`, `€/\w+`) para facturas 2026
  - base.py: 4 mejoras (es_proforma, TOTAL PROFORMA, patrones proforma, Número flexible)
- ✅ **ANTHROPIC y QUESOS DE CATI verificados** — sin bugs en extractores
- ✅ **Estadísticas corregidas**: sección 5.7.5 actualizada de 91→99 extractores, LA LLEIDIRIA movida de OCR a pdfplumber+fallback

### v2.8 (27/02/2026)
- ✅ **GMAIL actualizado a v1.8** — 5 fixes basados en diagnóstico de PAGOS_Gmail_1T26.xlsx
  - P1 Fix column shift: `_migrar_si_necesario()` reescrito (solo añade CUENTA, eliminada migración fantasma)
  - P2 TOTAL como float: antes string "12,50" → ahora float 12.50 (Excel lo reconoce como número)
  - P3 IBAN limpio: solo escribe IBANs reales (>=15 chars, 2 letras iniciales), no RECIBO/TARJETA
  - P4 CUENTA (col 15): nueva columna con 'TASCA'/'COMESTIBLES' leída del MAESTRO_PROVEEDORES
  - P5 Anti-duplicado CIF+REF efectivo: antes detectaba pero guardaba → ahora omite Dropbox y Excel
- ✅ **CUADRE actualizado a v1.5b** — +31 movimientos clasificados (621→590 REVISAR)
  - Nuevo clasificador: SERVICIO DE TPV (12 movimientos de cargo bancario por datáfono)
  - 16 aliases añadidos al MAESTRO (OPENAI, MAKRO, LIDL, MERCADONA, ALCAMPO, ANTHROPIC...)
  - 2 proveedores nuevos: HIPER DEL EMBALAJE SL, BODEGAS R. LOPEZ DE HEREDIA VINA TONDONIA SA
  - MAESTRO: 193→195 proveedores, 565→~585 aliases
- ✅ **VENTAS reescrito a v2.0** — script_barea.py completamente reescrito
  - Descarga semanal fija (lunes→domingo anterior) en vez de incremental
  - Todas las columnas Loyverse con resolución de IDs: TPV, Tienda, Cajero, Cliente, Categoría, Tipo de pago
  - 5 pestañas: TascaRecibos (19 cols), TascaItems (23 cols), ComesRecibos, ComesItems, WOOCOMMERCE
  - WooCommerce con paginación y filtro semanal
  - Dedup estable con unique_id, normalización columnas antiguas (_COL_RENAMES)
  - Datos reparados desde ejemplo Loyverse: 3274 recibos Tasca, 11199 items Tasca, 804 recibos Comes
- ✅ **borboton.py**: archivo eliminado del proyecto (SyntaxWarning ya no aplica)

### v2.7 (23/02/2026)
- ✅ **CUADRE actualizado a v1.5** — Refactorización de calidad (sin cambio funcional)
  - `buscar_factura_candidata()` extraída de 3 clasificadores (~85 líneas de código duplicado eliminadas)
  - `buscar_mejor_alias()` optimizado con dict precalculado: match exacto O(1), fuzzy ~10x más rápido
  - Fix warning `dayfirst=True` en `pd.to_datetime` de `clasificar_tpv`
  - Nuevo `construir_indice_aliases()`: se ejecuta 1 vez al cargar (470 entradas)
  - `indice_aliases` propagado por toda la cadena: main → procesar_hoja → clasificar_movimiento → clasificadores
  - Verificado: resultado **idéntico** a v1.4 (3324 clasificados, 621 REVISAR sobre 3945 movimientos)
- ✅ **Documento actualizado**: Estructura de carpetas refleja estado real del proyecto
  - Añadidos: cuadre/banco/clasificadores/, cuadre/norma43/, ventas_semana/, src/facturas/
  - Añadidos: estadisticas.py, clasificador.py, procesador_jpg.py
  - MAESTRO actualizado: 193 proveedores, 565 aliases
  - Corregida numeración duplicada secciones 5.x
  - Nueva sección 7.2-7.5: arquitectura cuadre.py, función extraída, optimización, resultados

### v2.6 (20/02/2026)
- ✅ **GMAIL actualizado a v1.7** — 6 parches basados en primera ejecución producción (27 emails, 15 exitosos)
  - P1 Fix ATRASADAS: cuando fecha=None → `requiere_revision=True` + aviso OBS "⚠️ FECHA NO DETECTADA"
  - P2 Column shift migration: `_migrar_si_necesario()` corrige Excel existente automáticamente
  - P3 FECHA_PROCESO: nueva columna en PAGOS_Gmail y Facturas Provisional
  - P4 REF_INVALIDAS ampliada: ERENTE, ERENCIA, RENCIA, DOS, UNO, TRES + validación en extractores dedicados
  - P5 Duplicados mejorado: detección por NOMBRE+TOTAL (antes solo NOMBRE)
  - P6 Notificador fix: eliminado wrapper `_api_call` inexistente
- ✅ **borboton.py corregido**: `extraer_referencia` capturaba fecha (18/02) en vez de número (20580/26)
  - Causa: `NUM.\n18/02/2026 20580/26` → `\s*` cruzaba salto de línea → capturaba fecha
  - Fix: saltar `dd/mm/yyyy` explícitamente antes del número
- ✅ **la_llildiria.py CREADO** (nuevo extractor, antes iba a REVISAR siempre)
  - Quesos artesanos de Cantabria, CIF B42953455, IVA 4%
  - `metodo_pdf = 'ocr'` (PDF es imagen escaneada)
  - Fix crítico en `extraer_total`: captura TOTAL (último €) no SUBTOTAL (primer €)
  - Probado con 2 facturas: LL368 (164,06€) y LL2026-00017 (250,95€) ✅
- ✅ **sabores_paterna.py y molletes_artesanos.py verificados** — sin bugs
- ✅ **Primera ejecución producción documentada** (20/02/2026 10:52-10:53)
  - 27 emails procesados, 15 exitosos, 12 requieren revisión, 0 errores sistema
  - El script se ejecutó al abrir la tapa (estaba esperando desde las 3:30 AM)
  - Solución: activar "Reactivar equipo" en Task Scheduler (Condiciones → ✅ Reactivar el equipo)
- ✅ **Claude Code instalado** (v2.1.49, Opus 4.6, Claude Max)
  - Acceso directo al disco duro desde terminal
  - Ruta: `cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas` → `claude`
- ⚠️ **Pendiente MAESTRO**: ALTO LANDÓN, HORNO SANTO CRISTO, LIDL, BODEGAS FIGUEROA + 7 alias emails
- ⚠️ **Pendiente revisión manual**: DROMEDARIO (proveedor no identificado), ABELLAN (OCR falla total), FABEIRO (2ª factura sin total), FIGUEROA CARRERO (sin total), ORGANIA OLEUM (sin total)
- ⚠️ **Pendiente PAGOS_Gmail Excel**: Revisar resultado de prueba de gmail.py (columnas)

### v2.5 (14/02/2026)
- ✅ **Documentación extractores**: Nueva sección 5.6 con arquitectura completa
  - Estructura del paquete, flujo de carga, clase base
  - Formato del dict de línea, estadísticas (90 extractores)
  - Reglas de negocio (portes, IVA, OCR, categorías)
  - Guía paso a paso para crear extractor nuevo
  - Convenciones de código
- ✅ **Nuevo Excel de salida**: `Facturas 1T26 Provisional.xlsx` (6+1 columnas)
  - Se genera ADEMÁS del PAGOS_Gmail
  - Columna OBS multi-flag: "DUPLICADO", "PROFORMA", "DUPLICADO | PROFORMA"
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
- ✅ **PARSEO mejorado: 91→99 extractores** (+8 nuevos/corregidos)
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
📅 **FECHA:** 03/03/2026

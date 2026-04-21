# SPEC GESTION-FACTURAS v4.5

> Documento maestro unificado — actualizado 20/04/2026
> Consolida: SPEC v3.0 (28/03) + ESQUEMA DEFINITIVO v5.4 (28/03) + Propuesta Migración Cloud (29/03)
> Ruta local: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\`

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
│   │  ✅ 85% │    │  ✅ 99% │    │  ✅ 95% │    │  ✅ 80% │                 │
│   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘                 │
│        ▼              ▼              ▼              ▼                       │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│   │ COMPRAS │    │  PAGOS  │    │ VENTAS  │    │ CUADRE  │                 │
│   │  .xlsx  │    │  .xlsx  │    │  .xlsx  │    │  .xlsx  │                 │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Tres áreas funcionales + scripts independientes + infraestructura web + migración cloud en curso.

---

## 2. ESTRUCTURA DEL PROYECTO

```
gestion-facturas/
├── ventas_semana/             # Todo lo que ENTRA (ingresos)
│   ├── script_barea.py        # Loyverse Tasca + Comestibles + WooCommerce (v4.7, 1.822 líneas)
│   ├── generar_dashboard.py   # Generador dual: Comestibles + Tasca + PDF + email
│   ├── dashboards/            # Templates HTML + dashboards generados + PDFs
│   ├── barea_auto.bat         # Runner tarea programada (anti-suspensión)
│   └── .env                   # Credenciales API (gitignored)
│
├── compras/                   # Todo lo que SALE (gastos proveedores)
│   ├── gmail.py               # Descarga PDFs + genera SEPA (v1.17, ~2.200 líneas)
│   ├── auth.py, descargar.py, identificar.py, renombrar.py, guardar.py
│   ├── generar_sepa.py        # Generador XML SEPA
│   ├── config.py, config_local.py  # Configuración (rutas, trimestres, overrides locales)
│   ├── credentials.json       # OAuth Google (gitignored)
│   ├── token.json             # Token Gmail (gitignored)
│   ├── gmail_auto.bat         # Script automatización v1.7
│   ├── main.py                # PARSEO — extrae datos de facturas (v5.18, ~6.000 líneas, 104 extractores)
│   ├── validacion.py          # Cruce PARSEO ↔ Kinema (POR CONSTRUIR)
│   └── cuadre.py              # Clasificación movimientos + conciliación (v1.7, ~1.300 líneas)
│       ├── banco/             # Router, parser N43, clasificadores modulares
│       └── norma43/           # Parser ficheros N43 Sabadell
│
├── datos/                     # Datos de referencia (estáticos)
│   ├── MAESTRO_PROVEEDORES.xlsx       # 195 proveedores, ~585 aliases
│   ├── DiccionarioProveedoresCategoria.xlsx  # ~1.254 artículos (ARTICULOS)
│   ├── DiccionarioEmisorTitulo.xlsx
│   ├── EXTRACTORES_COMPLETO.xlsx
│   └── emails_procesados.json          # Control duplicados Gmail
│
├── scripts/                   # Herramientas permanentes e independientes
│   ├── tickets/               # Módulo unificado tickets de proveedores
│   │   ├── __init__.py        # Descripción del módulo
│   │   ├── comun.py           # Lógica compartida (trimestre, registro, logging)
│   │   ├── dia.py             # DIA: API + Playwright login, anti-duplicación
│   │   ├── bm.py              # BM Supermercados: semi-manual (PDFs app BM+)
│   │   └── makro.py           # Makro (placeholder)
│   ├── dia_explorar.py        # Exploración endpoints DIA (referencia)
│   ├── mov_banco.py           # Análisis movimientos bancarios
│   ├── investigacion.py       # Pipeline investigación YouTube/web/Reddit
│   └── backup_cifrado.py      # Backup AES-256 archivos críticos
│
├── nucleo/                    # Módulo core compartido
│   ├── maestro.py             # MaestroProveedores + cache singleton (obtener_maestro)
│   ├── utils.py               # fmt_eur, fmt_num, to_float, NumpyEncoder
│   ├── logging_config.py      # Logging centralizado (RotatingFileHandler 5MB×5)
│   ├── parser.py              # Extracción fecha/total/ref de PDFs
│   └── sync_drive.py          # Google Drive sync
│
├── api/                       # API REST (FastAPI, puerto 8000)
│   ├── server.py              # Endpoints: health, status, alerts, data, scripts, maestro, cuadre, gmail
│   ├── auth.py                # RBAC: require_api_key (readonly) + require_admin_key (mutación)
│   ├── runner.py              # Ejecución scripts en background (jobs)
│   ├── maestro.py             # CRUD MAESTRO_PROVEEDORES
│   ├── config.py              # Rutas, CORS_ORIGINS, API keys desde .env
│   └── barea_api.bat          # Watchdog: auto-restart si crash
│
├── streamlit_app/             # APP WEB multi-usuario
│   ├── app.py                 # Login + st.navigation() + CSS corporativo
│   ├── pages/                 # alta_evento, calendario_eventos, ventas, maestro, cuadre, log_gmail, monitor, ejecutar, documentos
│   ├── utils/                 # auth.py, data_client.py, wc_client.py
│   ├── .streamlit/            # config.toml + secrets.toml
│   └── requirements.txt
│
├── config/                    # Configuración sensible
│   ├── datos_sensibles.py     # IBANs, CIFs, DNIs, emails (gitignored)
│   ├── datos_sensibles.py.example
│   ├── proveedores.py         # Lógica proveedores (funciones, alias, método PDF)
│   └── settings.py            # Versión, rutas por defecto
│
├── tests/                     # 136 tests (pytest)
│   ├── conftest.py            # Fixtures: api_client, temp_excel, sample_maestro
│   ├── unit/                  # test_api_security (22), test_nucleo (48), test_maestro (46), test_runner (20)
│   └── integration/           # (pendiente)
│
├── docs/                      # Documentación
│   └── SPEC_GESTION_FACTURAS_v4.md  ← ESTE DOCUMENTO
│
├── .claude/skills/            # 15 skills personalizadas Claude Code
├── .github/workflows/tests.yml # CI: pytest + coverage en push/PR a main
├── alerta_fallo.py            # Email alerta si fallo
├── requirements.txt           # 16 dependencias fijadas
├── pyproject.toml             # Config pytest, markers
└── outputs/                   # Archivos generados (gitignored)
```

**Decisión arquitectónica:** CUADRE vive en `compras/`. El ciclo de vida completo de una factura está en un solo sitio: Gmail → Parseo → Validación → Cuadre.

**PARSEO** existe también en `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\` con 99 extractores en `extractores/` y `main.py`. El proyecto unificado apunta ahí.

---

## 3. ARCHIVOS DEL SISTEMA

### 3.1 Archivos generados (outputs)

| # | Archivo | Generado por | Ubicación | Frecuencia |
|---|---------|-------------|-----------|------------|
| ① | `COMPRAS_XTxx.xlsx` (Lineas + Facturas) | main.py (PARSEO) | compras/XTxx/ | Mensual/trimestral |
| ② | `PAGOS_Gmail_XTxx.xlsx` (FACTURAS 15 cols + SEPA) | gmail.py v1.17 | outputs/ | Semanal |
| ②b | `Facturas XTxx Provisional.xlsx` (6+1 cols) | gmail.py | outputs/ | Semanal |
| ③ | `Ventas Barea YYYY.xlsx` (5 pestañas) | script_barea.py | ventas_semana/ | Semanal (lunes 03:00) |
| ④ | `CUADRE_XTxx_YYYYMMDD.xlsx` (3 pestañas) | cuadre.py | compras/XTxx/ | Bajo demanda |
| ⑤ | `MOV_BANCO_YYYY.xlsx` (tabs por trimestre) | Script MOV_BANCO | compras/ | Semanal |
| ⑥ | Dashboards HTML + PDFs resumen | generar_dashboard.py | ventas_semana/dashboards/ | Mensual |

### 3.2 Archivos fuente (inputs manuales)

| Archivo | Origen | Frecuencia |
|---------|--------|------------|
| Excel movimientos Sabadell | Descarga manual web Sabadell | Semanal |
| Archivos N43 | Descarga manual Sabadell | Semanal |
| Facturas_Proveedores_XTxx.xlsx | Kinema (gestoría) | Trimestral |
| PDFs de facturas | Gmail (automático) | Semanal (viernes 03:00) |
| CSV Loyverse | API automática | Semanal |

### 3.3 Archivos de referencia (datos/)

| Archivo | Registros | Columnas clave |
|---------|-----------|----------------|
| MAESTRO_PROVEEDORES.xlsx | ~195 proveedores | CUENTA, PROVEEDOR, CIF, IBAN, METODO_PDF, TIENE_EXTRACTOR, PAGO_PARCIAL, ~585 aliases |
| DiccionarioProveedoresCategoria.xlsx | ~1.254 artículos | PROVEEDOR, ARTICULO, CATEGORIA, TIPO_IVA |

**Campo PAGO_PARCIAL** (sí/no) por proveedor. CUADRE consulta este campo para decidir si busca combinaciones de movimientos que sumen el total de una factura.

---

## 4. CONVENCIÓN DE NOMBRES Y CARPETAS

**Regla: lo que está en raíz es la verdad. Lo que está en provisionales/ son snapshots del proceso.**

```
compras/
  1T25/
    COMPRAS_1T25.xlsx              ← EL DEFINITIVO (siempre el actual)
    CUADRE_1T25_20260328.xlsx      ← Último cuadre ejecutado
    provisionales/
      COMPRAS_1T25_parseo.xlsx     ← Salida directa de PARSEO
      COMPRAS_1T25_kinema.xlsx     ← Post-validación Kinema
  2T25/
    ...
```

### 4.1 Nomenclatura de archivos de facturas

**Formato:** `[PREFIJO] TTYY MMDD PROVEEDOR [N] MODO.ext`

| Componente | Valores | Ejemplo |
|-----------|---------|---------|
| PREFIJO | ATRASADA (si fecha < trimestre actual) | `ATRASADA 4T25 0307 CERES RC.pdf` |
| TTYY | Trimestre+año de la fecha de factura | `1T26` |
| MMDD | Mes+día de la fecha de factura | `0307` |
| PROVEEDOR | Nombre abreviado (≤25 chars, sin sufijo SL/SA) | `CERES CERVEZA` |
| N | Contador duplicados (si >1 factura mismo proveedor+fecha) | `1`, `2` |
| MODO | Modo de pago del MAESTRO | `RC`, `TF`, `TJ`, `EF` |

**Modos de pago:** RC (Recibo/domiciliación), TF (Transferencia), TJ (Tarjeta), EF (Efectivo)

### 4.2 Nomenclatura general de archivos

```
COMPRAS_1T26v1.xlsx        → Compras 1er trimestre 2026, versión 1
PAGOS_Gmail_1T26.xlsx      → Pagos Gmail 1er trimestre 2026
Ventas Barea 2026.xlsx     → Ventas anuales
MOV_BANCO_2025.xlsx        → Movimientos banco anuales
Cuadre_011025-020126.xlsx  → Cuadre del 01/10/25 al 02/01/26
```

---

## 5. MÓDULO VENTAS (v4.7) — ✅ 95%

**Script:** `ventas_semana/script_barea.py` (1.822 líneas)
**Dashboard:** `ventas_semana/generar_dashboard.py`
**Automatización:** Cada lunes (Programador de Tareas Windows → migración a cron/nube en Fase 2 cloud)

### 5.1 Flujo semanal (9 pasos automáticos)

1. **WooCommerce** → descarga pedidos semana anterior (retry + backoff)
2. **Loyverse Tasca** → descarga recibos + items semana anterior
3. **Loyverse Comestibles** → ídem
4. **Actualiza ARTICULOS** → catálogo completo + chequeo anomalías IVA
5. **Regenera dashboards HTML** (Tasca + Comestibles)
6. **Google Business Profile** (solo 1er lunes del mes)
7. **Inventario talleres** (WooCommerce experiencias)
8. **Email resumen semanal** → enviado via Gmail OAuth a socios (segmentado: FULL 3 socios + COMES_ONLY 1 socia)
9. **Sync Google Drive** → copia Excel + dashboards HTML

**1er lunes del mes (día ≤ 7):** `--dashboard-mensual` → meses cerrados + email socios + PDF resumen
**Meses cerrados (default):** Dashboards HTML y JSON Streamlit excluyen siempre el mes en curso (`solo_meses_cerrados=True`). Usar `--incluir-parcial` para incluirlo.

### 5.2 Output

**Excel acumulativo anual:** `Ventas Barea YYYY.xlsx`
- `TascaRecibos` (19 cols), `TascaItems` (23 cols)
- `ComesRecibos` (19 cols), `ComesItems` (23 cols)
- `WOOCOMMERCE`

**Dashboards:** Template-based con Chart.js
- `dashboard_comes_template.html` (6 placeholders) — 2 años (2025-2026), 13 categorías, rotación productos, rentabilidad margen €/kg. Donut categorías promovido (220×220px), gráfico Nº Tickets eliminado. WooCommerce integrado con criterio de devengo (fecha de celebración)
- `dashboard_tasca_template.html` (5 placeholders) — 4 años (2023-2026), 6 categorías (BEBIDA, COMIDA, VINOS, MOLLETES, OTROS, PROMOCIONES)
- **Despliegue:** Streamlit Cloud (producción, auto-deploy on push). Cloudflare Tunnel solo para desarrollo local. Ver `docs/FLUJO_DESPLIEGUE_DASHBOARDS.md`

**PDF resumen mensual:** matplotlib + reportlab
- Completo (3 págs): KPIs + Comparativa / Evolución / Categorías
- Solo Comestibles: versión reducida

**Categorías Comestibles (13):** ACEITES Y VINAGRES, BAZAR, BOCADILLOS, BODEGA, CHACINAS, CONSERVAS, CUPÓN REGALO, DESPENSA, DULCES, EXPERIENCIAS, OTROS, QUESOS, VINOS

---

## 6. MÓDULO COMPRAS

### 6.1 GMAIL (v1.18) — ✅ 99%

**Script:** `gmail/gmail.py` (~2.500 líneas, Google API)
**Módulos:** auth.py, descargar.py, identificar.py, renombrar.py, guardar.py, generar_sepa.py, dropbox_api.py, dropbox_selector.py
**Automatización:** Cada viernes 03:00 (VPS Contabo, cron)

#### Flujo semanal

```
GMAIL API (FACTURAS)
     │
     ▼
¿Ya en JSON? ─SÍ─→ SALTAR (anti-duplicados)
     │ NO
     ▼
Filtrar reenvíos ─→ IGNORAR
     │
     ▼
MOVER A PROCESADAS (antes de procesar, retry backoff)
     │
     ▼
Identificar proveedor ◄──► MAESTRO (3 puntos + fuzzy ≥85%)
     │
     ├── IDENTIFICADO → Descargar PDF → Renombrar
     │      │
     │      ▼
     │   determinar_destino_factura(fecha_factura, fecha_proceso)
     │      │
     │      ├── NORMAL   → Carpeta trimestre actual → Dropbox → Excel
     │      ├── GRACIA   → Carpeta trimestre ANTERIOR (días 1-11) → Dropbox → Excel
     │      ├── PENDIENTE → Cola JSON + PDF temporal (días 12-20, --produccion)
     │      │               o pregunta terminal (modo manual)
     │      └── ATRASADA  → Subcarpeta ATRASADAS/ (día 21+ o mes 2/3)
     │
     └── DESCONOCIDO → PROVEEDORES_NUEVOS_*.txt
```

#### Ventana de gracia trimestral (v1.18)

Kinema acepta facturas del trimestre anterior durante los primeros días del nuevo trimestre.

| Día del 1er mes | Destino | Acción |
|-----------------|---------|--------|
| 1-11 | GRACIA | Subir a carpeta del trimestre de la factura, sin prefijo ATRASADA |
| 12-20 | PENDIENTE_UBICACION | Automático: cola JSON + PDF temporal. Manual: pregunta terminal |
| 21+ | ATRASADA | Comportamiento original |
| Mes 2/3 del trimestre | ATRASADA | Sin ventana de gracia |

Solo aplica al trimestre **inmediatamente anterior**. Facturas más antiguas siempre ATRASADA.

**Cola pendientes:** `datos/facturas_pendientes.json` + PDFs en `datos/pendientes/`
**Resolución:** Streamlit (`Log Gmail` → sección pendientes) o gmail.py en modo manual.

**Sistema de identificación:** 3 puntos (PDF + Asunto + Remitente). Si 2+ coinciden → confianza ALTA (automático). Si 0-1 → confianza BAJA (preguntar). Usa MAESTRO + alias + fuzzy ≥85%.

**Extractores en Gmail:** Si existe extractor dedicado → usa ese. Fallback parcial v1.17: si dedicado obtiene fecha pero no total, complementa con genérico. Errores de extractores dedicados logean a WARNING (v1.17). Validación REF anti-basura: min 3 chars, requiere dígito en genérico.

**Validaciones de negocio (v1.18.2):**
- Total sospechoso: alerta si < 0,50€ o > 50.000€
- Detección abonos: total negativo → marca POSIBLE ABONO
- Fecha antigua: alerta si > 2 años
- Multi-PDF: procesa TODOS los PDFs adjuntos (antes solo el primero)

**Output:**
- PDFs descargados y renombrados en Dropbox
- `PAGOS_Gmail_XTxx.xlsx` (FACTURAS 15 cols + SEPA) — verificado 2T26: #, ARCHIVO, PROVEEDOR, CIF, FECHA_FACTURA, REF, TOTAL, IBAN, FORMA_PAGO, ESTADO_PAGO, MOV#, OBS, REMITENTE, FECHA_PROCESO, CUENTA
- `Facturas XTxx Provisional.xlsx` (6+1 cols: NOMBRE, PROVEEDOR, Fec.Fac., Factura, Total, Origen, OBS)
- `PROVEEDORES_NUEVOS_*.txt`
- `⚠️_IBANS_SUGERIDOS_*.xlsx`

#### Estructura Dropbox

```
Dropbox/.../CONTABILIDAD/
  FACTURAS 2026/
    FACTURAS RECIBIDAS/
      1 TRIMESTRE 2026/
        ATRASADAS/               ← facturas con fecha < 1T26
        1T26 0101 SEGURMA RC.pdf
        ...
```

**Ruta local:** `C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\`

### 6.2 PARSEO (v5.18) — ✅ 85%

**Script:** `compras/main.py` (~6.000 líneas)
**Ejecución:** Manual (menú). Se queda en PC local (ver §12 Migración Cloud).

#### Dependencia Kinema (numeración)

```
Gmail (viernes)  → Dropbox: "1T25 0101 BERZAL TF.pdf"         (sin #)
PARSEO (manual)  → COMPRAS provisional: # vacío
Kinema (trimest) → Dropbox: "1001 1T25 0101 BERZAL TF.pdf"    (con #)
PARSEO (manual)  → COMPRAS con #: 1001
```

#### Output: COMPRAS_XTxx.xlsx

**Pestaña Lineas** (919 filas en 1T25): #, FECHA, REF, PROVEEDOR, ARTICULO, CATEGORIA, CANTIDAD, PRECIO_UD, TIPO IVA, BASE (€), CUOTA IVA, TOTAL FAC, CUADRE, ARCHIVO, EXTRACTOR

**Pestaña Facturas** (259 facturas en 1T25): #, ARCHIVO, CUENTA, Fec.Fac., TITULO, REF, TOTAL FACTURA, Total Parseo, OBSERVACIONES

#### Extractores: 104 activos

| Concepto | Valor |
|---|---|
| Total extractores | 104 (99 en carpeta + 5 nuevos) |
| Método pdfplumber | ~92% |
| Método OCR | ~6% (fishgourmet, gaditaun, jimeluz, la_cuchara, manipulados_abellan, tirso) |
| Método pdfplumber+fallback_ocr | ~1% (la_lleidiria) |
| Método híbrido | ~2% (angel_borja, casa_del_duque) |
| Con distribución de portes | 11 extractores |
| Con categoría fija | ~48% |
| Extraen CANTIDAD+PRECIO_UD | 41 (46%) — pendientes: ~50 |

#### Reglas invariables

- **Portes/envío:** SIEMPRE distribuir proporcionalmente entre productos. Fórmula IVA diferente: `portes_equiv = (portes_base × (1 + IVA_portes/100)) / (1 + IVA_productos/100)`. Si IVA mixto, ponderar por grupo.
- **JPG:** Procesar si extractable; si no, rellenar mínimos → CUADRE=MINIMOS_JPG
- **Datos incompletos:** Nunca rechazar; rellenar mínimos
- **ESTADO_PAGO y MOV#:** NO se rellenan en PARSEO (es cosa de CUADRE)
- **Fallback PDF:** pdfplumber → OCR tesseract (spa) si descuadre >1€ o 0 líneas
- **Proformas:** Detectadas con `es_proforma()` (busca `\bPROFORMA\b`), marcadas en OBS
- **Fuzzy matching:** Umbral ≥85% para MAESTRO lookup
- **Referencia:** Filtro anti-falsos positivos: excluye teléfonos, CIFs, fechas. Mínimo 3 chars, 2 dígitos.

#### Arquitectura extractores

```
Parseo/extractores/
├── __init__.py          ← Carga automática + registro global + obtener_extractor()
├── base.py              ← ExtractorBase (clase abstracta, métodos genéricos)
├── _plantilla.py        ← Plantilla para crear extractores nuevos
├── generico.py          ← Extractor fallback (menor prioridad)
└── [104 extractores dedicados].py
```

**Clase base:** `ExtractorBase` con atributos obligatorios (nombre, cif, iban, metodo_pdf) y métodos abstractos/opcionales (extraer_lineas, extraer_total, extraer_fecha, extraer_referencia, es_proforma).

**Crear extractor nuevo:** Copiar `_plantilla.py` → configurar atributos → implementar `extraer_lineas()` → probar → se carga automáticamente (sin tocar `__init__.py`).

### 6.3 VALIDACIÓN KINEMA — POR CONSTRUIR

**Propósito:** Cruzar COMPRAS provisional (de PARSEO) con archivo trimestral de Kinema.
**Frecuencia:** Trimestral.

**Entradas:** `COMPRAS_XTxx_parseo.xlsx` (Facturas) + `Facturas_Proveedores_XTxx.xlsx` (Kinema)

**Algoritmo:**
1. Normalizar REF en ambos (strip + lowercase + quitar ceros iniciales)
2. Match por REF normalizada exacta
3. Fallback: proveedor_fuzzy ≥85% + fecha ±N días + total exacto
4. Tolerancia total: 0,00€

**4 resultados:** match, diferencia, falta_parseo, solo_parseo

**Salida:** `COMPRAS_XTxx_kinema.xlsx` con columnas adicionales: VALIDACION, TOTAL_KINEMA, CUENTA_KINEMA, DIFERENCIA

### 6.4 CUADRE (v1.7) — ✅ 80%

**Propósito:** Clasificador completo de tesorería. Cada movimiento bancario se categoriza y los pagos se vinculan a su factura.

**Entradas:** MOV_BANCO (pestañas del trimestre) + COMPRAS (provisional o definitivo)

**Salida — 3 pestañas:**

| Pestaña | Contenido | Columnas |
|---------|-----------|----------|
| **Tasca** | Movimientos Tasca del período | #, F.Operativa, Concepto, F.Valor, Importe, Saldo, Ref1, Ref2, Categoria_Tipo, Categoria_Detalle |
| **Comestibles** | Movimientos Comestibles del período | Ídem |
| **Facturas** | Facturas Kinema con Origen | Cód, Cuenta, Título, Fec.Fac, Factura, Total, Origen |

**Vínculo bidireccional:**
- Movimiento → Factura: `Categoria_Detalle` = `#NNN (ref)` / `#NNN (pago parcial)` / `SIN FACTURA`
- Factura → Movimiento: `Origen` = `T NNN` / `C NNN` / `C 663, C 668, C 671` (múltiple)

**Clasificadores implementados:**

| Clasificador | Detecta | Categoria_Tipo |
|--------------|---------|----------------|
| TPV | `ABONO TPV`, `COMISIONES` | TPV TASCA / COMISION TPV |
| Transferencia | `TRANSFERENCIA A` | Proveedor |
| Compra tarjeta | `COMPRA TARJ` | Proveedor |
| Adeudo/Recibo | `ADEUDO RECIBO` | Proveedor |
| Som Energia | `SOM ENERGIA` | SOM ENERGIA SCCL |
| Yoigo | `YOIGO` | XFERA MOVILES SAU |
| Comunidad | `COM PROP` | COMUNIDAD DE VECINOS |
| Suscripciones | `LOYVERSE`, `SPOTIFY` | GASTOS VARIOS |
| Servicio TPV | `SERVICIO DE TPV` | SERVICIO DE TPV |
| Alquiler | `BENJAMIN ORTEGA` | ALQUILER |

**Función extraída `buscar_factura_candidata()`:** Lógica común a transferencias, compra_tarjeta y adeudo_recibo. Busca por importe (±0.01€) → fuzzy aliases ≥70% → filtra ya usadas → desempata por fecha (≤60 días) → fallback mejor fuzzy.

**Optimización `buscar_mejor_alias()`:** Dict precalculado O(1) exact match (~10x más rápido que DataFrame iterrows).

**Datos reales (2025 completo):** 3.945 movimientos (2.697 Tasca + 1.248 Comestibles), 1.178 facturas. 85,1% clasificados, 14,9% REVISAR. 201 pagos parciales.

---

## 7. MOV_BANCO

**Archivo:** `MOV_BANCO_YYYY.xlsx` (anual, pestañas por trimestre)
**Pestañas:** `1T_Tasca`, `1T_Comestibles`, `2T_Tasca`, etc.
**Columnas normalizadas:** #, F.Operativa, Concepto, F.Valor, Importe, Saldo, Referencia 1, Referencia 2

**Alimentación semanal:** Excel Sabadell (formato variable) + N43. Auto-detección formato + deduplicación automática.

**Cuentas:** TASCA ES78 0081 0259 1000 0184 4495 | COMESTIBLES ES76 0081 0259 1700 0199 2404 | BIC: BSABESBB

---

## 8. SCRIPTS INDEPENDIENTES

### 8.1 Módulo `scripts/tickets/` — Adquisición de tickets de proveedores

Módulo unificado. Lógica compartida en `comun.py` (trimestre, nomenclatura, registro anti-duplicación).
Registros en `datos/tickets_registros/`. Tickets DIA en `datos/dia_tickets/`.

| Script | Función | Modo | Estado |
|--------|---------|------|--------|
| `tickets/dia.py` | Descarga tickets DIA via API interna + Playwright login | Automático | ✅ |
| `tickets/bm.py` | BM Supermercados: procesa PDFs descargados manualmente de app BM+ | Semi-manual | ✅ |
| `tickets/makro.py` | Makro | Pendiente | Placeholder |

Uso:
```
python -m scripts.tickets.dia              # tickets DIA nuevos
python -m scripts.tickets.dia --login      # renovar sesión
python -m scripts.tickets.bm               # procesar PDFs BM
python -m scripts.tickets.bm --parsear     # procesar + parsear con main.py
```

### 8.2 Otros scripts

| Script | Función | Estado |
|--------|---------|--------|
| `dia_explorar.py` | Exploración endpoints API dia.es | ✅ (referencia) |
| `mov_banco.py` | Análisis movimientos bancarios | ✅ |
| `investigacion.py` | Pipeline: YouTube + web + Reddit → resumen → NotebookLM | ✅ |
| `backup_cifrado.py` | Backup AES-256 (Fernet + PBKDF2) de 14 archivos críticos | ✅ |

---

## 9. INFRAESTRUCTURA WEB (estado actual)

### 9.1 API REST (FastAPI, puerto 8000)

**Endpoints:** health, status, alerts, data, scripts, maestro, cuadre, gmail
**Seguridad:** RBAC 2 niveles (api_key lectura, admin_key mutación), CORS explícito, path traversal protegido, uploads validados (10MB, whitelist extensiones)
**Watchdog:** `barea_api.bat` con auto-restart

### 9.2 Streamlit App (tascabarea.streamlit.app)

**Login:** 4 roles (admin, socio, comes, eventos). Usuarios: Jaime (admin), Roberto (socio), Elena (comes), Benjamin (eventos).
**Páginas:** Alta Evento, Calendario Eventos, Ventas (Plotly), Maestro Editor (admin), Cuadre (placeholder), Log Gmail (placeholder), Monitor (placeholder), Ejecutar Scripts (placeholder), Documentos (Drive)
**Diseño:** Tipografía Syne + DM Sans, sidebar oscuro, identidad Tasca Barea (#8B0000, #FFF8F0)
**Filtro meses cerrados:** Triple barrera para excluir meses incompletos de comparativas:
1. `generar_dashboard.py` filtra DataFrames al generar datos (default `solo_meses_cerrados=True`)
2. Templates HTML (`closedMonths()` en JS) filtran al renderizar gráficos
3. `pages/ventas.py` filtra `meses_completos` al renderizar + delta interanual usa solo meses cerrados
Afecta: evolución €, tickets/mes, ticket medio/mes, categorías, márgenes, WooCommerce, delta YoY. No afecta: KPIs totales, gráficos diarios, tab Productos.

### 9.3 Google Drive Sync

Carpeta "Barea - Datos Compartidos" con subcarpetas Ventas y Facturas.
`nucleo/sync_drive.py` integrado en script_barea.py (post-ventas) y gmail.py (post-facturas).

---

## 10. CICLO DE VIDA DE UNA FACTURA

```
① Gmail descarga PDF (viernes automático)
        ↓
② PARSEO extrae datos → COMPRAS_XTxx_parseo.xlsx (provisionales/)
        ↓
③ Kinema envía su archivo (trimestral)
        ↓
④ VALIDACIÓN cruza ambos → COMPRAS_XTxx_kinema.xlsx (provisionales/)
        ↓
⑤ Usuario promueve a definitivo → COMPRAS_XTxx.xlsx (raíz)
        ↓
⑥ CUADRE clasifica movimientos + vincula pagos → CUADRE_XTxx_YYYYMMDD.xlsx
```

**Nota:** Los pasos ③-④ pueden no haber ocurrido cuando se ejecuta CUADRE. En ese caso, CUADRE trabaja sobre el provisional. Cuando llegue Kinema, se re-ejecuta desde cero.

---

## 11. AUTOMATIZACIÓN (estado actual)

| Tarea | Cuándo | Cómo | Migración prevista |
|-------|--------|------|-------------------|
| Ventas (script_barea.py) | Lunes 03:00 | Task Scheduler Windows | CRON en VPS (Fase 2 cloud) |
| Gmail (gmail.py) | Viernes 03:00 | **CRON en VPS Contabo** | ✅ Migrado (v5.10, 12/04/2026) |
| PARSEO (main.py) | Manual (menú) | — | Se queda en PC local |
| Validación Kinema | Manual (trimestral) | — | Se queda en PC local |
| CUADRE | Manual (bajo demanda) | — | Se queda en PC local |
| MOV_BANCO | Manual (semanal) | — | Se queda en PC local → Open Banking futuro |

---

## 12. MIGRACIÓN A LA NUBE

### 12.1 Modelo: Hub & Spoke

```
┌──────────────────────────┐        ┌──────────────────────────┐
│   PC LOCAL (Jaime)       │        │   VPS CONTABO (Ubuntu)   │
│                          │        │                          │
│  PARSEO (manual)         │        │  Ventas (cron lun)       │
│  CUADRE (manual)         │ rsync  │  Gmail (cron vie)        │
│  MOV_BANCO (manual)      │──────► │  Streamlit dashboard     │
│  sync_cloud.py           │        │  File storage            │
│                          │        │  Dropbox API → Kinema    │
└──────────────────────────┘        │  Caddy (HTTPS + auth)    │
                                    └──────────┬───────────────┘
                                               │
                              ┌─────────┬──────┴──────┐
                              ▼         ▼             ▼
                           Jaime   Benjamín       Roberto
                          (HTTPS + auth básica)
```

### 12.2 Qué se mueve y qué se queda

**En PC local:** PARSEO, CUADRE, MOV_BANCO, Validación Kinema (todos manuales)
**En VPS (operativo):** Gmail (cron vie, ✅ migrado v5.10), Ventas (cron lun, pendiente), Streamlit dashboard, file storage, Dropbox API
**Nuevo:** `sync_cloud.py` (rsync outputs al VPS), `.env` centralizado en VPS

### 12.3 Stack cloud

| Componente | Tecnología |
|-----------|-----------|
| VPS | Contabo Cloud VPS 10 (4 vCPU, 8 GB RAM, 75 GB NVMe) — 3,96$/mes |
| OS | Ubuntu 24.04 LTS |
| Reverse proxy | Caddy v2 (HTTPS automático Let's Encrypt, auth básica) |
| Dashboard | Streamlit (embebe dashboards existentes + descarga Excels) |
| Scheduler | cron |
| Secrets | `.env` + dotenv |
| Sync | rsync sobre SSH (PC → VPS) |
| Backup | rclone → Google Drive |
| Dropbox | API SDK Python (reemplaza LocalDropboxClient) |

### 12.4 Gestión de tokens OAuth en la nube

Todos los tokens van a `/home/deploy/.env` (permisos 600):
```
GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
LOYVERSE_TOKEN
WOO_CONSUMER_KEY, WOO_CONSUMER_SECRET
DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN
```

Scripts adaptados para leer de `os.environ` en vez de `datos_sensibles.py`.

### 12.5 Open Banking (fase futura)

**Opción:** GoCardless Bank Account Data (ex-Nordigen). Tier gratuito hasta 4 conexiones. Sabadell soportado via PSD2/REDSYS. Consentimiento se renueva cada 90 días.

**Flujo:** Autorizar → script semanal descarga movimientos → normaliza al formato MOV_BANCO → elimina descarga manual.

### 12.6 Costes estimados

| Concepto | Coste | Frecuencia |
|---------|-------|-----------|
| VPS Contabo Cloud VPS 10 | 3,96$ (~3,65€) | Mensual |
| Dominio `.es` (opcional) | ~10€ | Anual |
| GoCardless (futuro) | 0€ (tier gratuito) | — |
| **Total** | **~4,50€/mes** | — |

---

## 13. SEGURIDAD Y ROBUSTEZ

### 13.1 Datos sensibles centralizados

`config/datos_sensibles.py` (gitignored): CIF_PROPIO, IBAN_TASCA, IBAN_COMESTIBLES, BIC_ORDENANTE, NIF_SUFIJO, PROVEEDORES_CONOCIDOS (146), CIF_A_PROVEEDOR (67), EMAILS_FULL, EMAILS_COMES_ONLY.

### 13.2 Credenciales protegidas (.gitignore)

| Archivo | Contenido |
|---------|-----------|
| `config/datos_sensibles.py` | IBANs, CIFs, DNIs, emails socios |
| `ventas_semana/.env` | API keys WooCommerce + Loyverse |
| `gmail/config_local.py` | App password Gmail |
| `gmail/credentials.json` | OAuth2 client secret |
| `gmail/token.json` | OAuth2 refresh token |
| `datos/*.xlsx` | Datos financieros |
| `outputs/*.xlsx` | Datos financieros |
| `*.n43` | Extractos bancarios |

### 13.3 API Security

Path traversal (basename + realpath), CORS explícito, API key obligatoria, RBAC 2 niveles, uploads validados (10MB, whitelist, magic bytes), passwords scrypt (n=16384, r=8, p=1) + timing constante, rate limiting login (5 intentos → lockout 60s), file locking JSON Gmail.

### 13.4 Tests (136 unitarios)

- `test_api_security.py` — 22 tests
- `test_nucleo.py` — 48 tests
- `test_maestro.py` — 46 tests
- `test_runner.py` — 20 tests
- CI: GitHub Actions (`pytest tests/unit/ --cov`)

### 13.5 Logging centralizado

`nucleo/logging_config.py`: RotatingFileHandler (5MB × 5 backups, UTF-8). Formato: `HH:MM:SS | LEVEL | mensaje`. Migrado en gmail.py, script_barea.py, API.

### 13.6 Historial git purgado (03/03/2026)

`git filter-repo`: 73 archivos binarios eliminados, 65 patrones reemplazados (IBANs, DNIs, emails). Repo `barea-dashboard` cambiado a PRIVATE.

### 13.7 Alertas de fallo

`alerta_fallo.py`: email a `tascabarea@gmail.com` si exit code ≠ 0. Integrado en `gmail_auto.bat` y `barea_auto.bat`.

### 13.8 Protección de datos (save_to_excel)

`script_barea.py` lee datos existentes ANTES de abrir el writer. Si falla → aborta. Detección Excel abierto: `os.rename` temporal.

---

## 14. HOJA DE RUTA

### Desarrollo pendiente (pre-cloud)

| # | Tarea | Estimación | Bloqueado por |
|---|-------|-----------|---------------|
| ① | MOV_BANCO script | 1 sesión (Sonnet) | — |
| ② | Automatizar CUADRE | 2-3 sesiones (Sonnet+Opus) | ① |
| ③ | CANTIDAD/PRECIO_UD ~50 extractores | Paralelo (Sonnet) | — |
| ④ | `validacion.py` Kinema | 1 sesión (Sonnet) | Spec lista |
| ⑤ | SEPA generación | Futuro | — |

### Migración cloud

| Fase | Tareas | Estimación |
|------|--------|-----------|
| **0 — Preparación** | Inventariar tokens, probar .env, crear cuenta Contabo | 1 sesión |
| **1 — VPS básico** | Configurar VPS, desplegar ventas+gmail, cron, Dropbox API | 1-2 sesiones |
| **2 — Streamlit** | Dashboard read-only, auth, sync_cloud.py, probar acceso | 2-3 sesiones |
| **3 — Estabilización** | Monitorizar, ajustar, backup, documentar | 1-2 semanas uso real |
| **4 — Open Banking** | GoCardless, mov_banco_cloud.py | Tras MOV_BANCO manual |

### Tareas pendientes sueltas

- ✅ ~~Revisar Excel output de `gmail.py` (PAGOS_Gmail)~~. Completada 12/04/2026 — revisión v1.16→v1.17, 4 fixes aplicados, 15 columnas verificadas en 2T26.
- ⚠️ P5: Pasar texto PDF cacheado a extractores para evitar re-extracciones (rendimiento)
- ⚠️ P6: Decidir política multi-PDF por email (actualmente solo procesa el primer PDF)
- ⚠️ Limpiar WooCommerce: 69 → 10 columnas en pestaña WOOCOMMERCE
- ⚠️ Mover PARSEO a gestion-facturas (integración completa, futuro)

### Backlog detectado el 20/04/2026 (post fix dashboard)

| ID | Pendiente | Impacto | Acción |
|----|-----------|---------|--------|
| 20A | Google Drive sync HTTP 403 "insufficient authentication scopes" (PC+VPS) | `sync_datos()` no puede listar carpetas | Cambiar scope a `drive` (no `drive.readonly`) en `nucleo/sync_drive.py`, regenerar `token.json`, propagar al VPS |
| 20B | Ruta Windows hardcoded `C:\...\datos\Articulos 26.xlsx` falla en VPS | Script rompe en Linux | `grep` para localizar la lectura + migrar a `pathlib.Path` usando `GESTION_FACTURAS_DIR` |
| 20C | `datos/Ventas Barea Historico.xlsx` ausente en VPS | Cálculos de ventas históricas incompletos en VPS | Copiar con `scp` en próximo despliegue; decidir si va al repo, a Drive o a sync manual |
| 20D | Deploy key del VPS sin write access en GitHub | `git push origin gh-pages` falla desde VPS | Regenerar deploy key con write, o condicionar el push a que solo se ejecute desde PC (decidir y documentar) |

### TODO refactor (backlog v4.6)

- **`ventas_semana/cargar_historico_wc.py:89`** — escribe la columna total como strings `"60,00 €"`. El fix dtype de v4.5 tolera ese formato, pero la solución de raíz es escribir floats nativos al Excel, eliminando la clase entera de bugs de parseo moneda en lectores posteriores. Cuando se aborde, mantener compatibilidad de lectura con el formato antiguo para históricos ya persistidos.

---

## 15. PUNTOS ABIERTOS (a resolver empíricamente)

| Punto | Decisión pendiente |
|-------|-------------------|
| D1 — Normalización REF | Probar strip+lowercase+zeros con datos reales |
| D2 — Fallback fecha ±N días | Probar ±1 y ±3, posible regla por frecuencia de proveedor |
| D3 — Dominio propio cloud | ¿gestion.tascabarea.es o IP directa? (recomendación: sí) |
| D4 — Recrear dashboards en Streamlit | ¿Embeber HTML existente o recrear? (recomendación: embeber primero) |
| M5 — Estado del trimestre | JSON automático o pestaña resumen (más adelante) |
| Pestañas MOV_BANCO | Confirmar nomenclatura con primer archivo real |

---

## 16. FUENTES HISTÓRICAS

| Período | Fuente | Detalle |
|---------|--------|---------|
| 2020–2023 | Facturas_Recibidas_25.xlsx (manual Jaime) | 6.621 líneas, 2.658 facturas |
| 2024 (may)–2025 | Facturas_Proveedores_definitivo.xlsx (Kinema) | 1.178 facturas |
| 2024–2025 | PARSEO (sistema) | Automatizado, con trazabilidad PDF |
| 2025 | Cuadre_020125-311225.xlsx (manual Jaime) | 3.945 movimientos clasificados |

---

## 17. CUENTAS BANCARIAS

Datos en `config/datos_sensibles.py`. Incluye: IBAN_TASCA, IBAN_COMESTIBLES, BIC_ORDENANTE, NIF_SUFIJO, CIF_PROPIO.

**TPV:** 0354272759 (Tasca→Sabadell Tasca), 0354768939 (Comestibles→Sabadell Comestibles), 6304473868 (virtual WooCommerce→Sabadell Comestibles)

---

## 18. INFRAESTRUCTURA CLOUD Y ACCESO WEB

### Dominios y DNS (Cloudflare — tascabarea.com)

| Subdominio | Tipo | Destino | Proxy | Servicio |
|-----------|------|---------|-------|----------|
| tascabarea.com | A | 213.158.86.111 | Proxied | Web principal (Webempresa) |
| gestion | CNAME | Tunnel 54062b38... | Proxied | Streamlit (puerto 8501 via tunnel) |
| api | CNAME | Tunnel 54062b38... | Proxied | FastAPI gestion-facturas (puerto 8000) |
| dashboard | CNAME | Tunnel 54062b38... | Proxied | Dashboards HTML |
| controlhorario | A | 194.34.232.6 | DNS only | App Control Barea (Caddy + Let's Encrypt) |
| cpanel / ftp / mail / webmail | A | 213.158.86.111 | Varios | Hosting Webempresa |

### VPS Contabo

- **Plan:** Cloud VPS 10 — 4 vCPU, 8GB RAM, 75GB NVMe, 3,96$/mes
- **IP:** 194.34.232.6
- **OS:** Ubuntu 24.04 LTS
- **SSH:** `ssh root@194.34.232.6` (clave ed25519 configurada)
- **Docker:** 29.1.3, Docker Compose 2.40.3

**Servicios en ejecución:**

| Servicio | Puerto | Bind | Acceso externo |
|----------|--------|------|----------------|
| Streamlit (gestion-facturas) | 8501 | 127.0.0.1 | https://gestion.tascabarea.com (tunnel) |
| Control Barea API (Docker) | 8000 | Docker internal | https://controlhorario.tascabarea.com (Caddy) |
| Control Barea Caddy (Docker) | 8080 | 0.0.0.0 | Reverse proxy interno para controlhorario |
| PostgreSQL (Docker) | 5432 | Docker internal | No expuesto |
| Caddy (sistema) | 80/443 | 0.0.0.0 | TLS para controlhorario.tascabarea.com |
| cloudflared | — | — | Tunnel barea-api (gestion, api, dashboard) |
| gmail.py (cron) | — | — | Viernes 03:00, Dropbox API (✅ migrado v5.10) |

**Firewall (UFW):** 22/tcp (SSH), 80/tcp, 443/tcp. Puertos 8080, 8501, 5432 NO expuestos.

**Backups:**
- control-barea: cron diario 3:00 AM → `/root/backups/control_barea_*.sql.gz`
- gestion-facturas: `backup_cifrado.py` (AES-256) + rclone a Google Drive

**Control Barea — Docker Compose (producción):**
- Archivo: `/opt/control-barea/docker-compose.prod.yml`
- Contenedores: `barea_api` (Python/FastAPI), `barea_caddy` (reverse proxy :8080), `barea_postgres` (PostgreSQL 16)
- Frontend: build estático React → servido por Caddy interno
- Caddy interno escucha en :8080, Caddy del sistema proxea controlhorario.tascabarea.com → localhost:8080
- Admin: jaime (password en .env del servidor, NO en repo)

**Cloudflare Tunnel (barea-api):**
- ID: 54062b38-f8c9-45b3-8281-35030bf71130
- Conector: cloudflared en VPS (systemd service, auto-start)
- Rutas: gestion → localhost:8501, api → localhost:8000, dashboard → dashboards HTML
- Token instalado con `cloudflared service install`

### Dominios registrados (Webempresa)

| Dominio | Vencimiento | Nameservers |
|---------|-------------|-------------|
| tascabarea.com | 06/09/2026 | Cloudflare (emerson/irena) |
| comestiblesbarea.com | 21/10/2026 | Webempresa (ns1611/ns1612) |
| salvatierrasalvatierra.es | 25/04/2027 | Webempresa (ns1611/ns1612) |

### Acceso Streamlit

- **Local:** http://localhost:8501 (desarrollo)
- **Producción:** https://gestion.tascabarea.com (Cloudflare Tunnel)
- **Auth:** Login 4 roles (admin, socio, comes, tienda)
- **Seguridad:** Streamlit bind 0.0.0.0 en VPS; puerto 8501 cerrado en firewall → solo accesible vía Cloudflare Tunnel (`gestion.tascabarea.com`)

### Servicios systemd (VPS Contabo)

| Servicio | Archivo | Estado | Descripción |
|----------|---------|--------|-------------|
| streamlit | `/etc/systemd/system/streamlit.service` | enabled | Streamlit app puerto 8501, `Restart=on-failure`, env vars `GESTION_FACTURAS_DIR` / `PYTHONPATH` / `PARSEO_DIR` |
| cloudflared | `/etc/systemd/system/cloudflared.service` | enabled | Tunnel `54062b38-...`, ruta `gestion.tascabarea.com` → `localhost:8501` |

**Comandos útiles:**
- `systemctl status streamlit` / `systemctl restart streamlit`
- `journalctl -u streamlit -f` (logs en tiempo real)
- `systemctl status cloudflared` / `journalctl -u cloudflared --since "1 hour ago"`

### Crontab root (VPS)

```cron
# Backup PostgreSQL control-barea — diario 03:00
0 3 * * * cd /opt/control-barea && BACKUP_DIR=/root/backups COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup.sh >> /var/log/control_barea_backup.log 2>&1

# Gmail facturas — viernes 03:00
0 3 * * 5 cd /opt/gestion-facturas && PARSEO_DIR=/opt/Parseo /opt/gestion-facturas/.venv/bin/python3 gmail/gmail.py --produccion >> /opt/gestion-facturas/outputs/logs_gmail/cron_$(date +\%Y\%m\%d).log 2>&1 || /opt/gestion-facturas/.venv/bin/python3 /opt/gestion-facturas/alerta_fallo.py gmail
```

El crontab **no se versiona en git** — documentado aquí como fuente canónica. Si se pierde, restaurar con `crontab -e` pegando el bloque anterior. Pendiente: cron semanal para `ventas_semana/script_barea.py` (lunes 03:00) una vez se añadan `LOYVERSE_API_TOKEN` y credenciales WooCommerce a `config/datos_sensibles.py` del VPS.

---

## 19. WOOCOMMERCE — ESTADO Y CONFIGURACIÓN (actualizado 16/04/2026)

### Problema Redsys resuelto
- Error 0104: anti-fraude de Sabadell bloqueó operaciones por >3 intentos desde misma IP
- Causa raíz: múltiples pruebas de pago la noche del 14/04/2026
- Solución: whitelist de IPs en Sabadell (pendiente envío IP de Cristina Lautre)
- IP Jaime (Digi, dinámica): 79.116.239.140 — pendiente pedir IP fija al 1200
- Cloudflare: Browser Integrity Check OFF, Bot Fight Mode OFF, Always Use HTTPS ON
- Terminal TPV Virtual: 6304473868 (Sabadell Comestibles)
- FUC: 354272759
- Plugin: Pasarela Unificada de Redsys 1.2.1 (pendiente actualizar a 2.0 o migrar a José Conti Lite)

### Migración de productos (16/04/2026)
Se ejecutó migrar_productos.py sobre 6 eventos activos (IDs: 3350, 3347, 3278, 3276, 3274, 3272):
- virtual: True (todos)
- tax_class: "IVA 21" (servicios recreativos, antes estaban en Estándar=10%)
- low_stock_amount: 3
- HTML limpiado de nombres (<br><small> eliminados en 4 productos)
- short_description generada para productos que no la tenían
- 4 eventos pasados cerrados (status→private) con cerrar_eventos_pasados.py

### Configuración de impuestos verificada
- Tarifa estándar: 10% (productos alimentarios) — NO TOCAR
- IVA 21: clase separada para experiencias/eventos
- IVA 10: para productos alimentarios
- IVA 4: superreducido
- Cheque regalo (Regalismo mágico ID:2810): Estado impuesto = "Ninguno" (bonos polivalentes tributan al canje)

### Scripts WooCommerce (ventas_semana/)
| Script | Versión | Función |
|--------|---------|---------|
| alta_evento.py | v2 (16/04/2026) | Alta interactiva de eventos. 8 pasos, virtual+IVA21+SEO+imagen+categoría obligatoria |
| alta_evento_v1_backup.py | v1 backup | Backup de la versión anterior |
| migrar_productos.py | v1 (16/04/2026) | Corrección masiva de productos existentes. Soporta --dry-run, --auto, --ids |
| cerrar_eventos_pasados.py | v1 (16/04/2026) | Archiva eventos con fecha pasada (status→private). Soporta --ejecutar, --dias-gracia |
| imagenes_eventos.json | plantilla | Catálogo de imágenes por tipo de taller. Pendiente rellenar con IDs de Medios de WP |
| asistentes_taller.py | v1 | Envía lista de asistentes por email el día del taller |
| script_barea.py | v4.7 | Ventas Loyverse + WooCommerce (ejecución automática lunes) |

### Convención de nombres v2 para eventos
- Formato: "{Nombre del taller} — {DD de MES YYYY}"
- Ejemplo: "Cata de vinos naturales — 18 de abril 2026"
- Máximo 80 caracteres
- Sin MAYÚSCULAS completas, sin "CERRADO-" como prefijo
- SKU automático: evento-YYYYMMDD
- Slug: slugify sin acentos

### Decisión YITH Event Tickets
- Licencia caducada, NUNCA se usó (todos los productos son "Producto simple")
- Decisión: DESINSTALAR tras verificar que no hay productos tipo ticket-event
- Alternativa: Producto simple + Virtual cubre el 100% del caso de uso

### Emails WooCommerce
- WP Mail SMTP: funciona con PHP mail de Webempresa
- Remitente: hola@comestiblesbarea.com
- Email al cliente: "Gracias por tu reserva en Comestibles Barea" (fondo Soft Sage)
- Email a la tienda: "[Tasca Barea] Nuevo pedido #XXXX" (fondo Dorado) → tascabarea@gmail.com

### Pendientes WooCommerce
- [ ] Enviar IPs a Sabadell para whitelist
- [ ] Pedir IP fija a Digi
- [ ] Subir fotos a Medios y rellenar imagenes_eventos.json
- [ ] Arreglar wp-cron (cron real en Webempresa)
- [ ] Probar alta_evento.py v2 con evento de prueba
- [ ] Cambiar categoría "Bodega" → "catas" en producto 3347
- [ ] Limpiar HTML de producto "Prueba correos" (ID:3364)
- [ ] Activar Bizum (verificar con Sabadell primero)
- [ ] Actualizar plugin Redsys (hacer en día de baja venta: lunes/martes)
- [ ] Crear subdominio IPN sin Cloudflare para evitar bloqueos LaLiga
- [ ] Crear child theme de Hello Elementor
- [ ] Resolver WP Rocket (renovar o migrar a LiteSpeed Cache)
- [ ] Desinstalar YITH Event Tickets (tras verificar todo)

### Documentos de referencia
- PLAN_MEJORAS_WOOCOMMERCE_BAREA_v1.md
- ANALISIS_WOOCOMMERCE_ALTA_EVENTO_v2.md
- PROMPT_CLAUDE_CODE_ALTA_EVENTO_v2.md
- RESUMEN_SESION_14ABR_WOOCOMMERCE.md
- AUDITORIA_WOOCOMMERCE_BAREA.md

---

## CHANGELOG

### v4.5 (20/04/2026) — FIX DASHBOARD DTYPE + ALINEACIÓN PANDAS

**Fix dashboard dtype pandas 2.x/3.x (commit e388536):**
- Error en VPS: `could not convert string to float: '60,00 €40,00 €...'` al generar dashboards.
- Causa raíz: pandas 3.x reporta columnas de strings como dtype `str` (no `object`), saltando el bloque de cleanup en `ventas_semana/generar_dashboard.py` (`_calcular_woo` ~L466-473 y `_calcular_woo_devengo` ~L613-619). Resultado: `.sum()` concatenaba strings en vez de sumar.
- Fix: reemplazar `df["total"].dtype == object` por `pd.api.types.is_numeric_dtype(...)` con lógica invertida (rama fácil = numérico directo; rama costosa = no-numérico → cleanup + `pd.to_numeric(errors="coerce")`).
- Cleanup ampliado: `.replace("\u00a0", "")` (non-breaking space) + `.replace(".", "")` (separador miles es-ES), todos con `regex=False`.

**Alineación de pandas VPS (cierra ⚠️-3 de AUDITORIA_VPS_20260418):**
- VPS bajado de pandas 3.0.2 → 2.3.0 para igualar PC (`requirements.txt` pinneado).
- Regla nueva en `tasks/lessons.md` § "Pandas y tipos de datos": mantener `requirements.txt` pinneado y obligar al VPS a respetarlo con `pip install -r requirements.txt` tras cualquier upgrade.

**Corrección de rutas en doc:**
- SPEC v4.4 listaba `ventas/script_barea.py`; la ruta real es `ventas_semana/script_barea.py`. Corregido en §2 (árbol), §3.1 (tabla outputs) y §5 (módulo VENTAS).

**Backlog de pendientes detectados el 20/04 (ver §14 — no se abordan en este commit):**
- Google Drive sync HTTP 403 "insufficient authentication scopes" (PC y VPS) — scope `drive.readonly` no basta para listar carpetas.
- Ruta Windows hardcoded `C:\...\datos\Articulos 26.xlsx` que falla en VPS → migrar a pathlib + `GESTION_FACTURAS_DIR`.
- `datos/Ventas Barea Historico.xlsx` ausente en VPS → decidir vía (repo / Drive / scp manual).
- Deploy key del VPS sin write access en GitHub → `git push origin gh-pages` desde VPS falla.

**TODO refactor (backlog v4.6):**
- `cargar_historico_wc.py:89` escribe la columna total como strings `"60,00 €"`. El fix dtype actual tolera ese formato, pero la solución de raíz es escribir floats nativos al Excel. Cuando se aborde, mantener el lector compatible con el formato antiguo para históricos persistidos.

**Grep de bugs gemelos:** 0 hits adicionales de `dtype == object` en el repo.

### 19/04/2026 — Bloque 2 VPS
- Código sincronizado PC→VPS (git pull)
- Dependencias verificadas (117 extractores, 0 errores)
- pago_alto_landon.py corregido
- PYTHONPATH/PARSEO_DIR permanente (.bashrc + runner.py + systemd)
- API keys ventas copiadas (.env + python-dotenv)
- Streamlit migrado a servicio systemd (auto-restart tras reboot)
- Cron gmail.py restaurado (viernes 03:00)
- Documentado crontab y servicios systemd en SPEC

### v5.14 (16/04/2026) — SESIÓN WOOCOMMERCE
- Diagnóstico y resolución error Redsys 0104 (anti-fraude IP)
- Migración 6 eventos: virtual=True, tax_class="IVA 21", HTML limpiado
- 4 eventos pasados archivados (cerrar_eventos_pasados.py)
- alta_evento.py v2 creado (8 pasos, SEO, imagen, categoría obligatoria)
- migrar_productos.py creado (corrección masiva con --dry-run/--auto/--ids)
- Cheque regalo: IVA cambiado a "No sujeto a impuestos"
- Cloudflare: Always Use HTTPS activado, Browser Integrity Check OFF confirmado
- 7 emails de disculpa redactados para clientes afectados por caída del sistema

### v5.13 (14/04/2026) — VALIDACIONES NEGOCIO + MULTI-PDF + VENTANA GRACIA

**gmail.py v1.18.2 — Validaciones de negocio:**
- Total sospechoso: alerta si < 0,50€ o > 50.000€ (TOTAL_MIN_SOSPECHOSO, TOTAL_MAX_SOSPECHOSO)
- Detección abonos: alerta si total negativo (POSIBLE ABONO, no bloquea)
- Fecha antigua: alerta si factura > 2 años (FECHA_MAX_ANTIGUEDAD_DIAS = 730)
- 23 tests unitarios en test_validaciones_negocio.py

**gmail.py v1.18.1 — Fix multi-PDF:**
- Procesamiento de TODOS los PDFs adjuntos en un email (antes solo el primero)
- Cada PDF adicional crea su propio ResultadoProcesamiento con email_id__pdfN
- Registro inmediato en JSON por cada PDF extra
- 7 tests unitarios en test_multi_pdf.py

**gmail.py v1.18 — Ventana de gracia trimestral:**
- determinar_destino_factura() con 4 destinos: NORMAL, GRACIA, PENDIENTE_UBICACION, ATRASADA
- Días 1-11 del primer mes del trimestre → GRACIA (carpeta trimestre anterior sin ATRASADA)
- Días 12-20 → PENDIENTE_UBICACION (cola JSON en modo automático, pregunta en terminal en modo manual)
- Día 21+ → ATRASADA (comportamiento existente)
- Cola facturas_pendientes.json + carpeta datos/pendientes/ para PDFs temporales
- Contadores gracia/pendientes en gmail_resumen.json
- LocalDropboxClient: parámetro destino controla carpeta (GRACIA → trimestre factura)
- 29 tests unitarios en test_ventana_gracia.py

### v5.12 (13/04/2026) — VENTANA DE GRACIA TRIMESTRAL

**gmail.py v1.18 — Ventana de gracia:**
- `determinar_destino_factura()`: 4 destinos (NORMAL, GRACIA, PENDIENTE_UBICACION, ATRASADA)
- Días 1-11 del 1er mes del trimestre: GRACIA → carpeta trimestre anterior sin prefijo ATRASADA
- Días 12-20: PENDIENTE_UBICACION → cola JSON (automático) o pregunta terminal (manual)
- Día 21+ o mes 2/3: ATRASADA (comportamiento original)
- Solo aplica al trimestre inmediatamente anterior

**Cola de pendientes:**
- `datos/facturas_pendientes.json` + PDFs temporales en `datos/pendientes/`
- Anti-duplicación por `archivo_renombrado`
- Resolución: Streamlit (Log Gmail) o terminal manual

**Integración Dropbox:**
- `LocalDropboxClient.subir_archivo()` y `DropboxAPIClient.subir_archivo()`: nuevo parámetro `destino`
- GRACIA → carpeta del trimestre de la factura (no ejecución)
- `generar_nombre_archivo()`: parámetro `destino` controla prefijo ATRASADA

**Streamlit (Log Gmail):**
- Sección "Facturas pendientes de ubicación" con botones por factura
- KPIs: ventana gracia + pendientes ubicación
- `gmail_resumen.json`: nuevos campos `facturas_gracia`, `facturas_pendientes`

**Tests:** `tests/unit/test_ventana_gracia.py` — 27 tests (NORMAL, GRACIA, PENDIENTE, ATRASADA, cambio de año)

### v5.11 (13/04/2026) — RUTAS OS-AWARE + SYS.PATH VENTAS

**Rutas multiplataforma (Windows/Linux):**
- `core/config.py`: fallbacks por `platform.system()` — Windows → `C:\_ARCHIVOS\...`, Linux → `/opt/...`
- `gmail/gmail.py`: Config interno con detección automática para BASE_PATH, DROPBOX_BASE, EXTRACTORES_PATH
- `gmail/gmail_config.py`: PROYECTO_BASE y DROPBOX_BASE ahora leen env var + fallback por OS
- Corrige FileNotFoundError de MAESTRO_PATH al ejecutar gmail.py en VPS

**sys.path fix para nucleo/ en ventas_semana/:**
- `script_barea.py`: añadido sys.path insert antes de `from nucleo` (corrige ModuleNotFoundError desde bat)
- `pdf_generator.py`, `email_sender.py`, `netlify_publisher.py`: mismo fix por robustez
- `generar_dashboard.py` ya lo tenía

### v5.10 (12/04/2026) — MIGRACIÓN GMAIL AL VPS + EXTRACTORES NUEVOS

**gmail.py v1.17 — Revisión completa + Dropbox API:**
- FIX: Errores de extractores dedicados ahora logean a WARNING (antes DEBUG invisible)
- FIX: Validación REF anti-basura reforzada (min 3 chars, requiere dígito en genérico)
- FIX: `factura.total` ya no se sobreescribe a 0.00 cuando falta (queda None → celda vacía)
- Constante `VERSION` centralizada (elimina hardcoded en `ejecutar()`)

**gmail.py v1.16 — Dropbox API:**
- Selector automático Local/API según entorno (Windows → carpeta local, Linux → API REST)
- Nuevos archivos: gmail/dropbox_api.py, gmail/dropbox_selector.py
- Refresh token Dropbox configurado (permanente, no caduca)
- DROPBOX_API_BASE: /File inviati/TASCA BAREA S.L.L/CONTABILIDAD
- Config: DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET en datos_sensibles.py

**VPS operativo para gmail.py:**
- gmail.py --produccion ejecutado con éxito desde VPS Contabo
- Facturas subidas a Dropbox vía API REST (verificado)
- Cron Windows (Gmail_Facturas_Semanal) deshabilitado — VPS es ahora el entorno principal
- Reactivar PC: `schtasks /change /tn "Gmail_Facturas_Semanal" /enable`

**Extractores nuevos:**
- alpenderez.py: Embutidos Alpénderez (OCR, CHACINAS, portes proporcionales)
- contabo.py: Contabo GmbH (pdfplumber, GASTOS VARIOS, Reverse Charge 0% IVA)
- Ambos dados de alta en MAESTRO_PROVEEDORES

**Fix extractores:**
- sabores_paterna.py: UNDS hecho opcional en regex (antes 0 líneas, ahora extrae correctamente)
- pago_alto_landon.py: cantidad + precio_ud + consolidación SIN CARGO + precio_real

**Ejecutar Scripts (Streamlit):**
- Modo dual: subprocess directo en Windows, detección Linux para VPS
- 4 tarjetas: Gmail, Ventas, Cuadre, Mov Banco con log tiempo real

### v5.9 (11/04/2026) — EXTRACTORES: CAMPOS + CATEGORÍA CENTRALIZADA

**CANTIDAD/PRECIO_UD:** 7 extractores ya tenían los campos capturados (emjamesa, odoo, organia_oleum, jesus_figueroa, horno_santo_cristo, dist_levantina, pago_alto_landon).

**precio_real (campo nuevo):**
- Coste efectivo con IVA por unidad cuando hay producto gratis (SIN CARGO / promociones)
- Fórmula: `base × (1 + iva/100) / cantidad_total`
- Implementado en: pago_alto_landon, borboton

**CATEGORÍA centralizada (Opción C — híbrido):**
- Extractor propone con `categoria_fija` → main.py completa con DiccionarioProveedoresCategoria
- 15 extractores: añadido `'categoria': self.categoria_fija` al dict de salida
- Correcciones: pilar_rodriguez→DESPENSA
- Nuevos categoria_fija: carlos_navas/la_lleidiria/quesos_felix→QUESOS, isifar→DULCES, porvaz→CONSERVAS MAR
- 7 multi-producto delegados a diccionario: arganza, ceres, montbrione, virgen_de_la_sierra, serrin_no_chan, francisco_guerra, molienda_verde
- main.py ya tenía lookup automático en diccionario para líneas sin categoría (línea 1500)

**Fallbacks en main.py (ya existían):**
- TOTAL: extractor → `extraer_total()` genérico de nucleo/parser.py
- FECHA: extractor → `extraer_fecha()` genérico
- REF: extractor → `extraer_referencia()` genérico
- Cuadre: `validar_cuadre_con_retencion()` con tolerancia 0.02€ + detección IRPF

### v5.8 (10/04/2026) — PÁGINA EJECUTAR SCRIPTS REESCRITA
- **ejecutar.py reescrita:** 4 tarjetas principales (Gmail, Ventas, Cuadre, Mov Banco) con último resultado, file upload, log en tiempo real
- **Scripts secundarios:** Gmail test, Dashboard, Dashboard+Email, Tickets DIA en expander
- **runner.py:** añadido `mov_banco` (scripts/mov_banco.py --consolidado)
- **Último resultado:** lee gmail_resumen.json, fecha Excel ventas, último CUADRE_*.xlsx, fecha consolidado mov banco
- Total: 9 scripts registrados en runner

### v5.7 (10/04/2026) — DESPLIEGUE CONTROL-BAREA + CLOUDFLARE TUNNEL
- **Control Barea desplegado** en VPS Contabo: Docker (API + PostgreSQL + Caddy) en `/opt/control-barea`
- **Cloudflare Tunnel** instalado en VPS: `gestion.tascabarea.com → localhost:8501` via tunnel barea-api
- **DNS migrado:** registro `gestion` de A record → CNAME tunnel (proxied)
- **Streamlit asegurado:** bind `127.0.0.1` (no accesible por IP directa), puerto 8501 cerrado en firewall
- **controlhorario.tascabarea.com** activo con HTTPS (Caddy + Let's Encrypt)
- **Firewall:** solo 22, 80, 443 abiertos. Puertos internos (8080, 8501, 5432) bloqueados
- **Backup cron:** diario 3:00 AM para PostgreSQL control-barea
- **Sección 18 SPEC:** infraestructura cloud completa documentada

### v5.6 (09/04/2026) — FILTRO MESES CERRADOS + BUGS DASHBOARDS
- **Filtro meses cerrados triple barrera:** Python (generar_dashboard.py) + JS (closedMonths en templates HTML) + Streamlit (meses_completos en ventas.py)
- **Fix template Comestibles:** placeholders `{{D_DATA}}` etc. restaurados (estaban hardcodeados, generar_html no actualizaba datos)
- **Fix días semana Tasca:** `exportar_json_streamlit` usaba DIAS de Comestibles para Tasca. Nuevo `DIAS_TASCA` calculado con datos correctos. Martes: 11€→6.272€
- **Fix delta interanual:** usaba `meses_act` (incluía mes parcial) → ahora usa `meses_completos`. Q1 2025: 34.007€→25.576€
- **`calcular_DIAS`** parametrizado con `year_list` (antes hardcoded `YEAR_LIST`)
- **`.gitignore`** ampliado: datos/backups/, datos/dia_tickets/, datos/snapshots/, outputs/*.log|html|png, cuadre/banco/clasificaciones_historicas.json

### v5.5 (08/04/2026) — WOOCOMMERCE DEVENGO + DESPLIEGUE DOCUMENTADO
- WooCommerce integrado en Ventas Netas con criterio de devengo (fecha de celebración)
- Donut categorías incluye EXPERIENCIAS de WooCommerce
- Canal físico/online usa datos reclasificados por celebración
- Template Comestibles: eliminado gráfico Nº Tickets, donut promovido 220×220px
- Documentación flujo despliegue: `docs/FLUJO_DESPLIEGUE_DASHBOARDS.md`
- Despliegue producción via Streamlit Cloud, Cloudflare Tunnel solo desarrollo

### v5.4 (28/03/2026) — GOOGLE DRIVE SYNC + AUTH CENTRALIZADO
- Página Documentos en Streamlit (lista archivos Drive por subcarpeta)
- Google Drive sync verificado (nucleo/sync_drive.py)
- Seguridad importlib (sanitización path traversal en gmail.py)
- Auth OAuth2 centralizado (gmail/auth_manager.py)

### v5.3 (27/03/2026) — GITHUB PAGES + DIA TICKETS + BACKUP CIFRADO
- Migración Netlify a GitHub Pages
- Dia Tickets funcional (200 tickets)
- Backup cifrado (AES-256, 14 archivos)
- Auditoría seguridad + `.claude/rules/`

### v5.3 (26/03/2026) — SEGURIDAD + TESTS + LOGGING
- 10 vulnerabilidades corregidas (path traversal, CORS, RBAC, uploads, passwords)
- 136 tests unitarios + CI GitHub Actions
- Logging centralizado (RotatingFileHandler)
- 6 except pass corregidos, file locking JSON, detección Excel abierto
- Código muerto eliminado (539 líneas), cache singleton MAESTRO, API watchdog

### v5.2 (26/03/2026) — DISEÑO CORPORATIVO + EDITOR PROVEEDORES
- Diseño corporativo Streamlit (Syne + DM Sans, sidebar oscuro, login branded)
- Editor MAESTRO_PROVEEDORES (búsqueda, filtros, edición inline, CRUD API)
- Fix Plotly 6.x (margin duplicado)
- Formato EUR español obligatorio (fmt_eur)
- Skill /frontend-design

### v5.0 (25/03/2026) — STREAMLIT MULTI-USUARIO
- Login 4 roles, st.navigation() filtra por rol
- Alta Evento, Calendario Eventos, Ventas (Plotly)
- Repo PUBLIC para Streamlit Community Cloud

### v4.1 (01/03/2026) — PDF RESUMEN REDISEÑADO
- matplotlib + reportlab profesional (KPIs, gráficos, tablas categorías)
- PDF completo (3 págs) + PDF solo Comestibles

### v4.0 (01/03/2026) — DASHBOARD TASCA + PDF + EMAIL
- Dashboard Tasca (Chart.js, 4 años)
- Comestibles reducido a 2025-2026
- Email segmentado (FULL + COMES_ONLY)
- GitHub Pages multi-file

### v3.0 (28/02/2026) — DASHBOARD COMESTIBLES + AUTOMATIZACIÓN
- Dashboard Comestibles (Chart.js, rotación, rentabilidad)
- Email socios via Gmail API
- GitHub Pages + automatización Windows
- 6 mejoras robustez (gitignore, requirements, save_to_excel, timeout, alertas, rutas relativas)

### v2.9 (28/02/2026) — SISTEMA PROFORMA + 6 EXTRACTORES
- Detección automática proformas
- MRM, MOLIENDA VERDE, ECOFICUS, LA LLEIDIRIA corregidos

### v2.8 (27/02/2026) — GMAIL v1.8 + CUADRE v1.5b
- Gmail: column shift fix, TOTAL float, IBAN limpio, CUENTA nueva, anti-duplicado CIF+REF
- Cuadre: SERVICIO DE TPV (+12 mov), 16 aliases nuevos, 195 proveedores

### v2.7 (23/02/2026) — CUADRE v1.5
- buscar_factura_candidata() extraída, buscar_mejor_alias() optimizado (O(1))

### v2.6 (20/02/2026) — GMAIL v1.7
- 6 parches: fix ATRASADAS, column shift migration, FECHA_PROCESO, REF_INVALIDAS, duplicados NOMBRE+TOTAL, notificador fix
- Nuevo extractor: la_llildiria.py
- Primera ejecución producción (27 emails, 15 exitosos)
- Claude Code instalado

### v2.5 (14/02/2026) — DOCUMENTACIÓN EXTRACTORES
- Sección 5.6 completa (arquitectura, clase base, estadísticas, guía)
- Nuevo Excel: Facturas XTxx Provisional.xlsx

### v2.4 (13/02/2026) — GMAIL v1.6
- Anti-duplicados (JSON atómico), auto-reconexión, sanitización, 4 extractores corregidos, anti-suspensión

### v2.3 (06/02/2026) — GMAIL v1.5
- Mover TODOS emails a PROCESADAS
- Token OAuth investigado
- BERNAL, DE LUIS, TERRITORIO CAMPERO, YOIGO corregidos

### v2.2 (03/02/2026) — PARSEO 91→99 EXTRACTORES
- 8 extractores nuevos/corregidos
- Fórmula distribución portes IVA diferente documentada

### v2.1-v2.0 (30/01-02/02/2026) — GMAIL v1.4 + VENTAS
- Gmail v1.4: 91 extractores integrados, LocalDropboxClient, SEPA, ATRASADAS, automatización
- PARSEO originado como ParsearFacturas (dic 2025), tasa éxito 23% → 85%

### v1.0-v1.1 (27-28/01/2026) — VERSIÓN INICIAL
- Versión inicial del esquema

---

*Documento maestro unificado — generado 29/03/2026*
*Consolida: SPEC_GESTION_FACTURAS_v3.md + ESQUEMA_PROYECTO_DEFINITIVO_v5.4.md + PROPUESTA_MIGRACION_CLOUD_v1.md*

# lessons.md — Errores y patrones aprendidos
<!-- Actualizar tras cada corrección del usuario -->
<!-- Nunca borrar entradas existentes — solo añadir -->
<!-- Formato nueva entrada: YYYY-MM-DD | módulo | descripción | regla -->

---

## REGLAS CRÍTICAS (errores documentados del proyecto)

### Excel y openpyxl
- **[CRÍTICO] Excel abierto al escribir** → fallo silencioso o corrupción de archivo
  → REGLA: Avisar SIEMPRE al usuario antes de cualquier escritura Excel. Sin excepción.
- **Sobreescritura sin leer primero** → pérdida de datos existentes
  → REGLA: save_to_excel() SIEMPRE lee hoja existente antes de escribir. Dedup por unique_col.
- **Backup omitido** → sin posibilidad de recuperación si algo falla
  → REGLA: Backup automático en datos/backups/ antes de la primera escritura de cada sesión

### Scripts batch (.bat)
- **ERRORLEVEL dentro de bloques if ()** → no se actualiza en Windows
  → REGLA: Usar goto + labels para manejo de errores. Nunca if ERRORLEVEL anidado.
- **PYTHONPATH no configurado en gmail_auto.bat** → `ModuleNotFoundError: nucleo` tras reorganización de imports
  → REGLA: Si un script usa módulos del proyecto (nucleo/, config/), el bat debe hacer `set "PYTHONPATH=%PROJECT_ROOT%"` antes de ejecutar Python. Verificar .bat tras cualquier cambio de imports.

### Gmail API
- **Token OAuth2 caducado** → error silencioso o crash en gmail.py
  → REGLA: Si gmail.py falla con error de autenticación → ejecutar gmail/renovar_token_business.py
- **MIME type con barra invertida** → text\html en vez de text/html
  → REGLA: Al parsear payloads Gmail API, verificar que el MIME type usa barra normal.
- **Cambio de scope OAuth no se aplica con solo editar SCOPES** → la librería usa los scopes persistidos dentro de `token.json`, no los del código. Síntoma: 403 "insufficient authentication scopes" aunque el código declare el scope nuevo.
  → REGLA: Al cambiar scope, borrar/renombrar `token.json` (`mv token.json token.json.bak.YYYYMMDD`), ejecutar `python gmail/renovar_token_business.py` (navegador OAuth), copiar el nuevo `token.json` al VPS con `scp`.
- **Serialización de credenciales filtra scopes → se pierden al refresh** → Pasar `scopes=[...]` a `Credentials.from_authorized_user_file(token, scopes=X)` hace que, al refrescar y volcar con `creds.to_json()`, se persista SOLO el subconjunto `X`, destruyendo los scopes realmente autorizados. Caso real (21/04/2026): el scope `drive` desapareció de `token.json` entre el 18/04 y el 20/04 porque cada run de gmail.py pasaba solo `[gmail.readonly, gmail.modify]` y reescribía el token.
  → REGLA: En `gmail/auth_manager.get_credentials()` cargar sin parámetro `scopes`; dejar que el token dicte qué está autorizado. Los callers (`get_gmail_service`, `get_drive_service`) tampoco deben pasar scopes.

### Formato de datos
- **Coma decimal en datos 2024** → "3,51" en vez de "3.51"
  → REGLA: Al leer Excel histórico 2024, convertir comas a puntos antes de operar.
  → REGLA: Datos 2025+ usan punto. No aplicar conversión si el archivo es de 2025+.
- **Formato moneda en Excel/email** → SIEMPRE usar formato europeo: X,xx € (coma decimal, símbolo al final)
  → REGLA: Al escribir importes en Excel o HTML, usar `f"{v:.2f}".replace(".", ",") + " €"`
  → REGLA: Fechas en columnas Excel de ventas: formato DD-MM-YY (no YYYY-MM-DD)

### Extractores PDF
- **Extractor nuevo sin manejo de excepciones** → factura sin procesar si falla
  → REGLA: Todo extractor debe devolver datos parciales ante fallo, nunca lanzar excepción.
- **OCR como método primario** → solo para PDFs imagen pura confirmados
  → REGLA: Usar OCR primario solo en extractores confirmados: JIMELUZ, CASA DEL DUQUE, LA LLILDIRIA.
  → Para el resto: pdfplumber o pypdf con fallback_ocr=True.
- **`extraer_numero_factura` eliminado en Parseo v5.18** → gmail.py debe usar `extraer_referencia`
  → REGLA: Al crear extractores nuevos, solo implementar `extraer_referencia` (nunca `extraer_numero_factura`).

### Portes y envío en facturas
- **Portes como línea separada** → error de IVA y descuadre en totales
  → REGLA: Portes/envío SIEMPRE proporcionales entre productos.
  → FÓRMULA: (coste_envío × (1 + IVA_envío/100)) / (1 + IVA_productos/100)

### Python imports — `ModuleNotFoundError` vs `ImportError`
- **`from package import submodule` con submódulo ausente NO lanza `ModuleNotFoundError`** → lanza `ImportError: cannot import name 'X' from 'Y'`. Solo `import X.Y` lanza `ModuleNotFoundError`. El segundo hereda del primero, **NO al revés**. `except ModuleNotFoundError` deja escapar el `from..import` caso.
  → REGLA: en código que tolera módulos opcionales (loaders, plugins, fallbacks), SIEMPRE `except ImportError`, nunca `except ModuleNotFoundError` aislado. Caso real (24/04/2026): `config/loader.py:_from_legacy()` capturaba solo `ModuleNotFoundError`; Streamlit Cloud lanzaba `ImportError` al hacer `from config import datos_sensibles`. Fix: cambiar a `except ImportError` (commit `5530c10`).

### Streamlit Cloud — deploy y requirements
- **`requirements.txt` canónico en Cloud es el JUNTO AL main file**, no el de la raíz → Streamlit Cloud resuelve `requirements.txt` adyacente a `streamlit_app/app.py`. Libs añadidas SOLO al de la raíz NO llegan a Cloud.
  → REGLA: al añadir libs que Streamlit use, editar `streamlit_app/requirements.txt` (o ambos si se quiere mantener paridad con dev local/VPS). Ver SPEC §13.10 para deuda de consolidación.
- **Warning "More than one requirements file detected" en logs de Cloud NO es inofensivo** → indica que Cloud está eligiendo uno distinto al esperado. Leer el log con cuidado.
- **Logging visible en UI ahorra iteraciones de debug** → patrón `try/except ImportError` con `st.error(...)` + `st.expander("Traceback")` + `st.code(traceback.format_exc())`. Caso real: el 4º bug de la cadena `/documentos` v2 se resolvió en 1 minuto gracias a este logging (el traceback literal lo envió el usuario).
  → REGLA: páginas Streamlit con imports de dependencias externas (Drive, APIs, etc.) deben envolver con este patrón al menos en la primera release.
- **Cachés bytecode `.pyc` agresivos en Cloud** → a veces un redeploy normal no los limpia. Si un fix no aplica tras push, probar commit vacío o reboot manual. Validar visualmente antes de asumir que funciona.

### Python path en apps multipágina Streamlit
- **`sys.path` centralizado en main file** → cada página hacía su propio `sys.path.insert(0, ROOT)`, frágil ante páginas nuevas. Centralizar en `streamlit_app/app.py` garantiza que cualquier `pages/<new>.py` hereda el path correcto.
  → REGLA: si las páginas importan módulos de la raíz del repo (nucleo, config, gmail, etc.), poner el `sys.path.insert(0, ROOT)` en el main file una sola vez.

### Config sensible — cascada de fuentes
- **Tres entornos, tres fuentes: Cloud/VPS/PC**. Usar `config/loader.py` con cascada `st.secrets → env var → datos_sensibles.py → default`. Importar directamente `from config.datos_sensibles import X` está deprecated (rompe bootstrap en Cloud).
  → REGLA: claves sensibles nuevas (CIFs, API keys, tokens) se leen via `config.loader.get("CLAVE", default)`. Config devs locales via `datos_sensibles.py` (gitignored). Cloud via `st.secrets`. VPS via env vars.

### Sincronización de documentación
- **Versiones desincronizadas entre archivos**
  → REGLA: Al modificar un módulo, actualizar versión en 2 sitios: header del código + tabla en CLAUDE.md.
  → Actualizar ESQUEMA al cerrar sesión si hubo cambios significativos.

### Filas zombi en PAGOS_Gmail
- **Concepto: "fila zombi"** = entrada en `PAGOS_Gmail_<periodo>.xlsx` que quedó con TOTAL vacío y/o "ALERTA ROJA" en OBS porque la versión de gmail.py que la insertó tenía bugs hoy corregidos. Los extractores actuales sí parsean correctamente esos PDFs. Las filas no se reescriben automáticamente — quedan petrificadas hasta que algo las reprocese. Detectado en `PAGOS_Gmail_2T26.xlsx` (28/04/2026, 6 filas tras versiones pre-v1.14 de gmail.py).
  → REGLA: tras cualquier upgrade significativo de gmail.py o de extractores, considerar pase de `scripts/resucitar_zombis.py` sobre los Excel del trimestre activo. El script es seguro (dry-run + backup + interactivo).
  → REGLA: NO sobreescribir PROVEEDOR/CIF/IBAN si el Excel ya tiene valor del MAESTRO — la fuente canónica es MAESTRO, no el extractor (atributo `nombre`/`cif`/`iban` del extractor puede ser una versión corta, p.ej. `'CERES'` vs `'CERES CERVEZA SL'`). Limitar la sobreescritura a TOTAL/REF/FECHA/FORMA_PAGO/CUENTA. Las discrepancias en columnas protegidas se logean WARN no bloqueante (pueden indicar datos del proveedor desactualizados o factura mal asociada).

### Bug nombrado de archivo en facturas multi-albarán
- **gmail.py guarda el PDF con la fecha del PRIMER ALBARÁN, no la fecha de factura** → en facturas que agrupan varios albaranes (típico ForPlan/MIGUEZ CAL), el nombre de archivo refleja la fecha del primer albarán y desincroniza con la fecha real de factura. Caso real (28/04/2026): factura 31/12/25 archivada como `ATRASADA 4T25 1205 MIGUEZ CAL SL TF.pdf` (12/05 = primer albarán), no como `1231`. Después alguien renombra el PDF en disco al nombre correcto (1231) pero la columna ARCHIVO del Excel sigue con 1205 → buscar el PDF por nombre exacto falla.
  → REGLA: Al investigar incidencias en proveedores con facturas multi-albarán, comparar `ARCHIVO` del Excel con el nombre real del PDF en disco. Si difieren en la fecha, sospechar bug de nombrado en gmail.py.
  → REGLA: La FECHA_FACTURA extraída del PDF también puede ser la del primer albarán. El extractor de MIGUEZ tiene este bug (28/04/2026, anotado en backlog). Verificar manualmente facturas multi-albarán hasta arreglar el extractor.

### Bug FORMA_PAGO en flujo gmail.py
- **gmail.py prefiere MAESTRO sobre PDF para FORMA_PAGO cuando el extractor no la extrae** → si el extractor no expone `extraer_forma_pago()` o equivalente, el flujo pone en el Excel lo que diga MAESTRO_PROVEEDORES, ignorando lo que esté en el PDF. Caso real: DEBORA GARCIA TOLEDANO factura 14/04/26 — PDF dice "Efectivo", MAESTRO tiene `TJ` → escribió `TJ` en Excel.
  → REGLA: Cuando un proveedor cambie ocasionalmente de forma de pago, esto causará un dato silenciosamente erróneo. Mientras el bug existe, revisar manualmente FORMA_PAGO de proveedores que paguen en efectivo o con métodos no fijos.
  → SOLUCIÓN PENDIENTE: o (a) que el extractor extraiga FORMA_PAGO del PDF; o (b) que el flujo prefiera SIEMPRE el PDF cuando esté presente.

### Patrón dual A/B de extractores
- **Dos firmas conviviendo**: la mayoría de extractores definen solo hooks individuales (`extraer_lineas/total/fecha/referencia`) que reciben TEXTO. Solo unos pocos (CERES y similares) definen `extraer(pdf_path)` que devuelve dict con todo. gmail.py:2376-2453 maneja ambos: si la instancia tiene método `extraer`, lo invoca; si no, abre el PDF con pdfplumber+OCR y llama a los hooks.
  → REGLA: Cualquier herramienta que necesite invocar extractores fuera de gmail.py (p.ej. `scripts/resucitar_zombis.py`) debe replicar este patrón dual para mantener paridad. La extracción de texto SÍ está expuesta como utilidad reutilizable: `nucleo.pdf.extraer_texto_pdf(ruta, metodo='pdfplumber', fallback=True)`. La selección de patrón A vs B sigue inline en gmail.py — duplicar con comentario apuntando a la línea origen.

### Identificadores persistentes vs únicos en `extraer_referencia`
- **Trampa**: Un campo en la factura puede llamarse `Invoice number` o `Customer ID` o `Reference` y ser **persistente del cliente/billing**, no único por factura. Si un extractor lo captura como REF, el anti-dup CIF+REF (gmail.py:2247-2255) descartará silenciosamente todas las facturas siguientes del mismo proveedor. Caso real (29/04/2026): `Parseo/extractores/anthropic.py:75-80` capturaba `Invoice number EXB4HCQN` (persistente) en lugar del `Receipt #2880-2984-9190` único → factura Anthropic 20/04 descartada como duplicada, situación que se repetiría cada mes.
  → REGLA: Al crear/revisar un extractor, comprobar con AL MENOS DOS facturas distintas del mismo proveedor que `extraer_referencia()` devuelva valores DIFERENTES. Si devuelve el mismo string para ambas, el patrón captura un identificador persistente — corregir.
  → REGLA: Para proveedores con CIF vacío (extranjeros tipo ANTHROPIC), el riesgo es mayor porque `factura_existe` cae al fallback `nombre|REF`, y el `nombre` también es constante → la unicidad depende ENTERAMENTE del REF. Doble cuidado.
  → DETECCIÓN: revisar periódicamente `datos/emails_procesados.json` por proveedores con N entradas en `emails` pero pocas/una entrada en `facturas` (clave repetida). Es señal de REF colisionando.

### Anclar regex de fechas al contexto correcto
- **Cuando un PDF tiene múltiples fechas en distintas secciones** (cabecera de factura + tabla de albaranes/líneas/vencimientos), el regex de extracción debe anclarse al contexto de la fecha de cabecera, no capturar la primera que encuentre. Caso de referencia: facturas MIGUEZ CAL multi-albarán contienen `31/12/25 A 4724 ...` en cabecera y `ALBARÁN A-3184 FECHA 05/12/2025` en tabla — un regex genérico capturaría la del primer albarán como fecha de factura.
  → REGLA: patterns útiles para anclar — precedido de `Factura`, `Fecha factura`, `F.Emisión`; o restringido a las primeras N líneas; o anclado a un patrón único de la cabecera (ej. `^DD/MM/YY\s+A\s+\d+` para identificar la línea inmediatamente debajo de "FECHA FACTURA CLIENTE N.I.F TELÉFONO PÁG.").
  → DETECCIÓN tardía (red de seguridad observacional, gmail.py:_check_fecha_vs_email): si `factura.fecha < internalDate − 7 días` en facturas recientes, el log emite WARNING con la sospecha de multi-albarán. NO bloquea; sólo invita a revisar el nombre del archivo manualmente.

### Bug irreproducible — no tocar
- **Si un bug histórico documentado no es reproducible con el código actual** (los tests pasan verde y no hay diferencia git ni md5 vs producción), NO modificar el código preventivamente. Documentar el caso histórico, añadir red de seguridad observacional (logs, alertas), y esperar a que el bug reaparezca para diagnosticarlo con datos. Modificar regex "por si acaso" cuando los tests pasan solo introduce riesgo nuevo sin eliminar el viejo.
  → CASO DE REFERENCIA: MIGUEZ multi-albarán abril 2026 — fila Excel archivada con fecha del primer albarán (`05/12`) en lugar de cabecera (`31/12`). Detectado al resucitar zombis el 28/04. Investigación 29-30/04 confirmó: extractor pasa smoke test verde sobre 4 PDFs reales (incluido el problemático), md5 PC == VPS desde marzo. Hipótesis no verificable: `.pyc` cached o pdfplumber distinto en la corrida del 18/04. ACCIÓN TOMADA: check defensivo en gmail.py (`_check_fecha_vs_email`), NO modificar extractor.
  → REGLA HEURÍSTICA: si gastas más tiempo "robusteciendo" un código que pasa los tests que diagnosticando el bug, estás haciendo cargo culture engineering. Para. Documenta. Espera datos.

### Bytes NUL en pdfplumber
- **pdfplumber a veces inserta `\x00` (byte NUL, ord=0) como separador en el texto extraído**. Caso real (29/04/2026): texto de `Invoice number EXB4HCQN 0006` en PDFs Anthropic — el "espacio" entre `EXB4HCQN` y `0006` resultó ser `\x00`, no un espacio real. Un regex con `\s*` falla porque `\s` cubre `[\t\n\r\f\v ]` pero NO el byte NUL.
  → REGLA: para campos críticos extraídos del PDF con pdfplumber, los regex deben usar `[\s\x00]*` cuando se permitan separadores. Alternativa: pre-limpiar el texto con `texto.replace('\x00', ' ')` antes de aplicar regex.
  → DETECCIÓN: si un regex que parece correcto cae al fallback inesperadamente, inspeccionar bytes con `for i, c in enumerate(texto[idx:idx+30]): print(i, repr(c), ord(c))` para ver el separador real.
  → ÁMBITO: cualquier extractor que reciba texto de pdfplumber. Casos especialmente sospechosos: PDFs generados por servicios USA (Anthropic, etc.) donde la tipografía y el embedding de texto pueden diferir del estándar europeo.

### Rescate manual de facturas duplicadas zombis
- **Cuando una factura se descarta como duplicado CIF+REF por bug del extractor**, el flujo correcto NO es reprocesar vía gmail.py (eso re-etiquetaría email + intentaría duplicar todo). El flujo correcto es:
  1. Parchear el extractor.
  2. Smoke test contra PDFs históricos del proveedor para confirmar que extrae REFs únicas.
  3. Re-parsear el PDF original con el extractor parcheado.
  4. Resucitar manualmente: subir PDF a Dropbox + añadir 1 fila a cada Excel canónico (PAGOS Drive, Provisional Drive, Provisional Dropbox).
  5. Limpiar el control DB del VPS (`emails_procesados.json`):
     - Borrar la clave zombi de `facturas`.
     - Insertar la clave nueva única.
     - Reemplazar la entrada de `emails[email_id]` (de `motivo: "Duplicado..."` al formato canónico de 5 campos: `message_id, fecha_proceso, proveedor, archivo, dropbox`).
     - NO tocar `ultima_ejecucion`.
  6. Deploy del extractor parcheado al VPS (scp + verificar md5 match).
  → REGLA: NO re-etiquetar el email Gmail con label `FACTURAS` para que el cron lo reprocese — eso intentaría duplicar el PDF en Dropbox (saltaría por hash dup pero contaminaría logs) y crearía una segunda fila Excel con la nueva REF (real) MIENTRAS la fila original errónea seguiría sin escribirse. El email permanece en `FACTURAS_PROCESADAS`.
  → Caso real (29/04/2026): factura Anthropic 20/04 (REF correcta `EXB4HCQN-0007`, total 90€) se rescató con script one-shot `scripts/_rescate_anthropic_20260420.py`. Backups del control DB pre/post conservados en `outputs/backups/` como evidencia.

### Diagnóstico de facturas "perdidas" — alias coloquial vs canónico
- **Cuando el usuario dice "la factura de X no se procesó"**, antes de buscar bug confirmar que X es exactamente el `nombre` del MAESTRO o uno de sus `alias`. Caso real (29/04): el usuario enumeró "Pili Blanco" y "Welldone" como no procesadas — ambas SÍ estaban procesadas, pero bajo el nombre canónico `BLANCO GUTIERREZ PILAR` (alias incluye `PILAR BLANCO`) y `DEL RIO LAMEYER RODOLFO` (alias incluye `WELLDONE`). El log y `gmail_resumen.json` listan SIEMPRE el nombre canónico del MAESTRO.
  → REGLA: para diagnosticar "no procesada", la cadena de verificación es:
    1. Email existe en Gmail (consulta API por `from:` o `subject:` libre).
    2. Label actual: `FACTURAS` (pendiente) vs `FACTURAS_PROCESADAS` (Label_5 — procesado).
    3. Email_id en `emails_procesados.json:emails` (con `proveedor` y `motivo`).
    4. Si `proveedor` aparece, es el nombre **canónico** del MAESTRO — buscar por ese nombre en log/Excel, no por el alias coloquial.
  → REGLA: el sistema procesa EL CONTENIDO de un email, no su fecha. Un email del 21/04 puede contener una factura del 13/11/2025 — el `archivo` reflejará la fecha real de la factura, no la del email.

### Pandas y tipos de datos
- **`df["col"].dtype == object` es frágil entre pandas 2.x y 3.x** → pandas 3.x reporta columnas de strings como dtype `str`, no `object`, rompiendo ramas condicionales que dependen de esa igualdad.
  → REGLA: Usar `pd.api.types.is_numeric_dtype(df["col"])` o `pd.api.types.is_object_dtype(...)` en lugar de comparar `.dtype == object`. Invertir la condición: rama fácil (es numérico) → usar directo; rama costosa (cualquier no-numérico, incluido string) → limpiar + `pd.to_numeric(errors="coerce")`.
  → REGLA: En limpiezas sobre strings de moneda española, eliminar también `\u00a0` (non-breaking space) y pasar `regex=False` a `.str.replace()` por claridad y velocidad.
- **VPS con versiones de paquetes divergentes de `requirements.txt`** → fallos reproducibles solo en producción (caso WC dashboard 20/04/2026: pandas 3.0.2 en VPS, 2.3.0 en PC).
  → REGLA: Mantener `requirements.txt` pinneado y exigir al VPS respetar los pins; instalar SIEMPRE con `pip install -r requirements.txt` tras cualquier upgrade.
  → REGLA: Tras detectar drift, alinear con `pip install "paquete==X.Y.Z"` y confirmar `pip show paquete` idéntico en ambos entornos.

### TODO pendientes (para SPEC v4.5)
- **Refactor `cargar_historico_wc.py`** → la línea 89 (`total_eur = f"{float(...):.2f}".replace(".", ",") + " €"`) escribe strings en el Excel. Esto fuerza que el dashboard tenga que limpiar "€" y coma en cada lectura. Decisión pendiente: escribir floats nativos y formatear solo al mostrar.

---

## REGISTRO DE CORRECCIONES
<!-- Claude Code añade aquí cada vez que el usuario corrija un comportamiento -->

| Fecha | Módulo | Error cometido | Regla añadida |
|-------|--------|----------------|---------------|
| 2026-03-13 | General | — | Archivo creado con errores documentados del proyecto |
| 2026-04-21 | ventas_semana/generar_dashboard | `if df["total"].dtype == object` saltaba el cleanup en VPS (pandas 3.x, dtype `str`) → `sum()` concatenaba strings y `float()` petaba | Usar `pd.api.types.is_numeric_dtype`; pinnear pandas 2.3.0 en VPS; añadidas reglas "Pandas y tipos de datos" |
| 2026-04-21 | gmail/auth_manager | `get_credentials(scopes=[...])` filtraba el objeto Credentials; al refrescar, `creds.to_json()` volcaba el subconjunto y sobrescribía token.json perdiendo el scope `drive` | No pasar `scopes` a `from_authorized_user_file()`; el token dicta los scopes autorizados. Regla nueva en sección "Gmail API" |
| 2026-04-24 | config/loader | `except ModuleNotFoundError` capturaba bien `import config.datos_sensibles` pero dejaba escapar `from config import datos_sensibles` (distinto `ImportError`) → /documentos caía en Streamlit Cloud | Usar `except ImportError` (cubre ambos casos porque `ModuleNotFoundError` hereda de `ImportError`). Regla nueva "Python imports" |
| 2026-04-24 | streamlit_app | Libs añadidas a `requirements.txt` raíz no llegaban a Cloud (Cloud usa el adyacente al main file) → imports fallaban en /documentos aunque localmente OK | Editar `streamlit_app/requirements.txt` al añadir libs para Cloud. Regla nueva "Streamlit Cloud — deploy y requirements". Deuda técnica documentada SPEC §13.10 |
| 2026-04-24 | streamlit_app | Iteraciones ciegas de debug en Cloud tras cada push — sin traceback visible costaba 1 round trip por bug | Patrón logging visible en UI (try/except + st.error + expander con traceback.format_exc). Adoptado en documentos.py, extensible |
| 2026-04-28 | scripts/resucitar_zombis | 1ª pasada del script sobreescribía PROVEEDOR (`CERES CERVEZA SL`→`CERES`) e IBAN (formato distinto) tomando del extractor en lugar del MAESTRO → habría roto la canonicalización del MAESTRO en filas resucitadas | Lista `COLUMNAS_PROTEGIDAS_MAESTRO=(PROVEEDOR,CIF,IBAN)`: si el Excel ya tiene valor, no sobreescribir y logear WARN. Regla nueva en sección "Filas zombi" |
| 2026-04-28 | scripts/resucitar_zombis | 1ª pasada marcaba FECHA_FACTURA como cambio aunque solo difería el formato (DD/MM/YY vs DD/MM/YYYY) | Normalizar siempre FECHA_FACTURA a DD/MM/YY (estándar `.claude/rules/excel.md`); comparar fechas por valor, no por string |
| 2026-04-28 | gmail/gmail.py | Bug nombrado multi-albarán descubierto: PDF de MIGUEZ CAL (factura 31/12/25) archivado en Excel como `1205` (1ª fecha de albarán) | Regla nueva en lessons "Bug nombrado de archivo en facturas multi-albarán" + entrada en backlog para revisar lógica de nombrado |
| 2026-03-13 | Parseo | ESQUEMA buscado en carpeta equivocada | ESQUEMA está en gestion-facturas/docs/, no en Parseo/ |
| 2026-03-13 | Gmail | REF "86" de BERNAL rechazada por gmail.py | gmail.py exigía len>=3, extractor genérico len>=2. Alineado a >=2 |
| 2026-03-13 | La Llildiria | Total 93.94 en vez de 172.75 | PyPDF no captura tabla totales en PDFs imagen. Añadido cálculo desde subtotales + cambio a OCR primario |
| 2026-03-27 | Gmail/bat | gmail_auto.bat falló con ModuleNotFoundError: nucleo | Añadir `set "PYTHONPATH=%PROJECT_ROOT%"` en bat. Verificar bat tras cambios de imports |
| 2026-03-30 | Ventas/bat | barea_auto.bat falló con mismo error que gmail_auto.bat | Verificar TODOS los .bat del proyecto tras cambios de imports, no solo el afectado |
| 2026-04-09 | Dashboard | Template Comestibles tenía datos JSON hardcodeados, sin placeholders | Verificar que templates HTML tengan placeholders `{{D_DATA}}` etc. Si no existen, generar_html no actualiza datos |
| 2026-04-09 | Dashboard | exportar_json_streamlit usaba DIAS de Comestibles para JSON de Tasca | Cada tienda debe tener su propio cálculo de DIAS. `calcular_DIAS` parametrizado con year_list |
| 2026-04-09 | Streamlit | Delta interanual incluía mes parcial → inflaba cifra año anterior | Usar `meses_completos` (no `meses_act`) para comparativas interanuales |
| 2026-03-30 | Ventas | `_to_float` no definido en email semanal | Tras refactorizar imports a nucleo.utils, verificar que TODAS las funciones referenciadas se importan |
| 2026-03-30 | Alerta | alerta_fallo.py pedía scope gmail.send no presente en token | Usar scopes del token existente (gmail.modify cubre envío). No inventar scopes nuevos |
| 2026-03-31 | WooCommerce | Evento creado como `simple` no aparecía en calendario web | Crear siempre como `type: "ticket-event"`, con categorías (Comestibles Barea + tipo) y tag Producto_destacado |
| 2026-03-31 | WooCommerce | Evento sin meta_data no aparecía en calendario web | Siempre incluir `_start_date_picker`, `_end_date_picker` en meta_data. Sin ellos el plugin de eventos no posiciona el evento |
| 2026-03-31 | WooCommerce | CERRADO con catalog_visibility hidden no aparecía en web | Los CERRADOS deben ser `visibility: visible` (como los manuales). stock=0 impide la compra |

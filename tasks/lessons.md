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

### Sincronización de documentación
- **Versiones desincronizadas entre archivos**
  → REGLA: Al modificar un módulo, actualizar versión en 2 sitios: header del código + tabla en CLAUDE.md.
  → Actualizar ESQUEMA al cerrar sesión si hubo cambios significativos.

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

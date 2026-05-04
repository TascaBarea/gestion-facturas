# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Próxima sesión
**Objetivo:** resolver listado Drive en `/documentos` Cloud + favicon Comestibles + deuda requirements.

### Pendientes priorizados

- [ ] **ALTO — `/documentos` en Cloud no lista archivos reales** (porque `gmail/token.json` está `.gitignored`). Decidir entre:
  - **Opción A (recomendada)**: botones "Abrir en Drive" por sección con URL directo a la carpeta correspondiente. Cero credenciales en Cloud. `/documentos` queda como vista de estructura + navegación rápida. Implementación: refactor `streamlit_app/pages/documentos.py` para mostrar botones en lugar de listados, usando URLs de Drive (añadir mapping folder_id → URL).
  - **Opción B**: pegar `token.json` como secret en Streamlit Cloud dashboard. Más complejo (token OAuth expira, requiere rotación manual, mayor superficie de seguridad).

- [ ] **MEDIO — favicon Comestibles Barea en Streamlit**.
  - Asset: `Logo_BAREA_COMESTIBLES_RESOLUCION_WEB.png` (óvalo La Rumán, ~1507×1980) en `G:\Mi unidad\Barea - Datos Compartidos\Articulos\`.
  - La imagen tal cual NO funciona como favicon 16×16 (queda borrón amarillo). Necesita versión recortada ~512×512 priorizando cara.
  - Configurar en `st.set_page_config(page_icon=...)` en `streamlit_app/app.py`.

- [ ] **BAJO — deuda técnica `requirements.txt` duplicados**. Documentado en `tasks/nota_requirements.md` y SPEC §13.10. Evaluar:
  - Opción A: consolidar en `requirements.txt` raíz único, configurar Streamlit Cloud para leerlo.
  - Opción B: `streamlit_app/requirements.txt` contiene solo `-r ../requirements.txt`.
  - Opción C: mantener duplicación + test CI que detecte divergencia.

### Activación cron viernes 03:00 en VPS (decisión operativa)
- [ ] Si 2-3 ejecuciones gmail.py consecutivas OK en VPS → activar cron.

### Otros pendientes arrastrados
- [ ] Añadir sync Drive también a `scripts/mov_banco.py` (paralelo a `actualizar_movimientos.py`) — omitido por scope.
- [ ] Borrar `generar_refresh_token_dropbox.py` (gitignored, ya cumplió su función Fase X.2).
- [ ] Revisar REVISAR reales del run 24/04: La Mar de Tazones, Solicitud factura imagen.

---

## Sesión 29/04/2026
**Objetivo:** Diagnóstico de las 6 facturas que se creían no procesadas en el Bloque E del 23-24/04.

### Completado
- [x] **Diagnóstico 6 facturas Bloque E** — reporte `outputs/diagnostico_6_facturas_20260429.md`. Resultado: 5/6 ya procesadas correctamente (la premisa era inexacta — varias se procesaron bajo nombre canónico distinto del alias coloquial usado al enumerarlas). 1 bug real detectado.
- [x] Verificación cruzada: log VPS Bloque E + control DB `emails_procesados.json` + queries Gmail API + MAESTRO.
- [x] Verificación de cola pendiente para cron 01/05: 25 emails con label `FACTURAS` desde 22/04 → procesarán normal.

### Bug confirmado (NO aplicado — propuesta documentada)
- **`Parseo/extractores/anthropic.py:75-80`**: `extraer_referencia` captura el campo "Invoice number" que es **persistente del cliente** (`EXB4HCQN`) en lugar del Receipt # único de cada factura. Consecuencia: cada factura mensual de Anthropic choca con anti-dup CIF+REF (`ANTHROPIC|EXB4HCQN`) y se descarta silenciosamente. Confirmado para la factura del 20/04 (90€, REVISAR como duplicado) y previsible para todas las futuras.
- Fix propuesto: usar regex `Receipt\s*#?\s*(\d{4}-\d{4}-\d{4})` como primer patrón, con fallback al Invoice number actual.
- Tras el fix: re-etiquetar email 20/04 (`id=19dabd1a29b08e7a`) como `FACTURAS` para que el siguiente cron lo reprocese, o ejecución manual puntual.

### Casos cerrados como YA_PROCESADO
- Emjamesa 16/04 → procesado 18/04 (motivo: hash duplicado de cadena `Re: Re: Re:`).
- Pili Blanco 21/04 → procesado en Bloque E como `BLANCO GUTIERREZ PILAR` (alias en MAESTRO).
- Welldone 20/04 → procesado en Bloque E como `DEL RIO LAMEYER RODOLFO` (alias `WELLDONE` en MAESTRO).
- Miguez Cal 16/04 → procesado 18/04, fila zombi F5 ya resucitada en sesión 28/04.
- Martin Arbenza 26/03 → procesado 27/03 como `MARTIN ABENZA`; reenvíos del 22/04 saltados como hash dup ✓.

### Backlog generado por esta sesión (CERRADO 29/04 tarde)
- [x] **MEDIO — Arreglar `Parseo/extractores/anthropic.py`** ✅ commit Parseo `33e9add` — regex `r'Invoice\s+number\s+([A-Z][A-Z0-9]*?)[\s\x00]*(\d{3,5})\b'` que devuelve `EXB4HCQN-NNNN` único. Smoke test verde sobre 3 PDFs reales. Deploy VPS confirmado md5-match.
- [x] **MEDIO — Reprocesar factura Anthropic 20/04** ✅ rescate manual ejecutado (sin re-etiquetar el email — el script `_rescate_anthropic_20260420.py` descargó el PDF vía Gmail API, parseó con extractor parcheado, subió a Dropbox y añadió 1 fila a cada uno de los 3 Excels). Control DB VPS limpiado (clave zombi `ANTHROPIC|EXB4HCQN` → `ANTHROPIC|EXB4HCQN-0007`).
- [x] **BAJO — Limpieza outputs auxiliares** ✅ script y PDF temp borrados; backups del control DB (pre/post) conservados como evidencia de auditoría en `outputs/backups/`.

---

## Sesión 04/05/2026 — INTERRUMPIDA por cobertura
**Objetivo:** Resolver 5 pendientes post-ejecución gmail.py 04/05 11:41 (token Drive scope, jaleo extractor, rescate Jaleo zombi, CIF B85501989, alta Aquí Santoña).

### Completado
- [x] **Diagnóstico log 04/05**: 41 emails, 36 OK, 4 revisar, 0 errores. 3 problemas accionables identificados (Drive 403, 2 Jaleo sin total, Aquí Santoña REVISAR). Check defensivo MIGUEZ (`_check_fecha_vs_email`) disparó 2 veces sobre atrasadas reales (no falsos positivos) — funciona como red de seguridad observacional.
- [x] **Causa raíz Drive 403 confirmada**: bug del 21/04 reapareció. `gmail/gmail.py:706` filtra con `CONFIG.GMAIL_SCOPES = [gmail.readonly, gmail.modify]` (sin drive); línea 718 sobrescribe el token tras refresh, perdiendo el scope `drive`. Token actual verificado: scopes = `[gmail.readonly, gmail.modify]`, `drive` ausente.
- [x] **Plan dual decidido** (registrado para próxima sesión): regenerar token con `renovar_token_business.py` + parchear `GMAIL_SCOPES` en `gmail.py:191-194` añadiendo `drive`. Alternativa "limpia" (refactor `gmail.py:conectar()` para delegar en `auth_manager.get_gmail_service()`) queda como ítem de backlog futuro.
- [x] **Backup token conservado**: `gmail/token.json.bak.20260504` (md5 `e42e90a3...`, idéntico al token activo).

### Interrumpido
- [!] **OAuth flow abortado** sin completar (cobertura). Sesión revertida a estado idéntico al inicio: parche reverido en `gmail.py`, token restaurado del backup, working tree sin cambios commiteables (solo dirty pre-existente). El cron del viernes seguirá funcionando como hoy: procesa los emails, falla solo el sync Drive final con [DRIVE FALLO] 403 conocido.

### Pendientes para próxima sesión (orden recomendado, atómico)
- [ ] **🔴 1. Re-auth Drive + parche `GMAIL_SCOPES` + deploy VPS**:
  1. `python gmail/renovar_token_business.py` → autorizar 4 scopes en navegador (Gmail readonly, Gmail modify, Business manage, Drive).
  2. Verificar `token.json.scopes` contiene los 4.
  3. Aplicar parche en `gmail/gmail.py:191-194` añadiendo `'https://www.googleapis.com/auth/drive'` a `GMAIL_SCOPES`.
  4. Test: listar carpeta Drive vía API.
  5. scp token + scp gmail.py al VPS, verificar md5 match.
  6. Commit gestion-facturas + push.
- [x] **🟡 2. Crear `Parseo/extractores/jaleo.py`** ✅ commit Parseo `16f6c18`. Smoke test verde 2/2 PDFs (PDF1 N260761 598,50€ formato moderno + PDF2 #1807 523,50€ formato presupuesto). Deploy VPS md5-match `f9a8889b`. Reporte `outputs/fix_jaleo_20260504.md`.
- [x] **🟡 3. Resucitar 2 filas Jaleo zombi** ✅ aplicado solo en Provisional Dropbox (filas 53 + 64) — Drive Excels descartados del scope porque están desfasados 5 días (44 filas) — requieren re-sync masivo aparte. Total recuperado: 1.122,00 €.
- [ ] **🟢 4. Investigar CIF `B85501989`** detectado para "COMESTIBLES BAREA" en factura del 30/04. La tienda real es B87760575 (Tasca Barea SLL). Determinar si es error OCR o un proveedor nuevo legítimo. Archivo: `2T26 0430 COMESTIBLES BAREA.pdf` en Dropbox.
- [ ] **🟢 5. Alta MAESTRO + extractor para "Aquí Santoña"** (`comercial@aquisantona.com`). Factura quedó como `REVISAR 2T26 0504 (comercial@aquisantona.com).pdf` sin proveedor ni total.

### Pendientes derivados (sesión 04/05 tarde)
- [ ] **🔴 NUEVO — Drive Excels desfasados 5 días (44 filas)** en `G:\PAGOS_Gmail_2T26.xlsx` y `G:\Facturas 2T26 Provisional.xlsx`. Probable consecuencia del bug Drive 403: gmail.py lleva varias ejecuciones sin escribir en Drive. Cuando se complete el OAuth Drive (pendiente 1), plantear re-sync masivo desde Dropbox o re-ejecución selectiva.

### Pendiente cron viernes
- [ ] **NOTA**: el cron del viernes 08/05 seguirá fallando el sync Drive hasta que el OAuth se complete. No bloquea el procesamiento de emails (lo demás funciona). Las facturas JALEO entrantes ya usarán el nuevo extractor.

---

## Sesión 04/05/2026 — TARDE
**Objetivo:** Cerrar pendiente 2 (extractor JALEO) y pendiente 3 (rescate zombis) tras el corte por cobertura del OAuth.

### Completado
- [x] **Crear `Parseo/extractores/jaleo.py`** — 117 líneas. 2 formatos manejados: "moderno" (PDF1 27/04 cabecera one-line `Factura N260761 ... Total 598,50€`) y "presupuesto" (PDF2 23/03 atrasada con bloques separados `#1807` + `TOTAL : 523,50 €`). `extraer_lineas` queda como TODO. `extraer_forma_pago` no implementado (MAESTRO ya define TJ). Decorador con 3 aliases, registrado bajo `ACEITES DE ESPECIALIDAD JALEO / ACEITES JALEO / JALEO`. Commit Parseo `16f6c18`.
- [x] **Smoke test verde 2/2** sobre PDFs reales. Total/fecha/REF correctos en ambos.
- [x] **Deploy VPS md5-match** `f9a8889bcde5951641437345a6e2cbba`. `__pycache__` limpiados local + VPS.
- [x] **Rescate 2 zombis Provisional Dropbox** — script `_rescate_jaleo_20260504.py` (one-shot, borrado al cierre). Dry-run + apply OK. Filas 53 (`N260761`, 598,50€) y 64 (`#1807`, 523,50€). Total recuperado **1.122,00 €**. Backup: `Facturas 2T26 Provisional_backup_20260504_2253.xlsx`.
- [x] **Hallazgo crítico documentado**: Drive Excels (G:\) llevan 5 días sin actualizarse — 44 filas de desfase respecto a Dropbox. Decisión usuario: solo Dropbox; Drive re-sync queda como pendiente nuevo.
- [x] **Reporte completo** `outputs/fix_jaleo_20260504.md`.

---

## Sesión 30/04/2026
**Objetivo:** Push de los 4 commits 28-29/04 a GitHub + fix bugs MIGUEZ multi-albarán y DEBORA forma_pago.

### Completado
- [x] **Push GitHub gestion-facturas**: 4 commits 28-29/04 (`6c608ce`, `23bdc33`, `59a62e9`, `296deb8`) + commit cierre 30/04. VPS sincronizado por fast-forward (HEAD = `bd038f7`, ya alineado con origin/main).
- [x] **Bug DEBORA forma_pago**: añadido `extraer_forma_pago` en `Parseo/extractores/debora_garcia.py` con regex `Método de pago` + diccionario de códigos canónicos (EF/TF/TJ/RC/BZ/PP). Smoke test verde sobre 3 PDFs reales (los 3 dicen "Efectivo" → devuelve `EF`). Commit Parseo `961f5c7`. Deploy VPS md5-match.
- [x] **Check defensivo en gmail.py para multi-albarán**: nuevo método `_check_fecha_vs_email` que loga WARNING si `factura.fecha < internal_date − 7d`. Red de seguridad observacional (NO bloquea). `_obtener_detalle_email` ahora expone `internal_date` (datetime UTC).
- [x] **MIGUEZ multi-albarán** investigado y descartado: extractor pasa los 4 smoke tests verdes (incluye el caso ATRASADA 4T25 1231 que originó el zombi); md5 PC == VPS desde commit inicial Parseo (Marzo). Bug histórico no reproducible. Decisión: NO modificar el extractor; el check defensivo en gmail.py basta como red de seguridad.

### Backlog cerrado de la sesión 28/04
- [x] **ALTO — Bug nombrado multi-albarán en gmail.py**: cerrado con check defensivo (no era reproducible en el extractor MIGUEZ actual).
- [x] **MEDIO — Bug FORMA_PAGO MAESTRO vs PDF**: cerrado con `extraer_forma_pago` en debora_garcia.py.
- [x] **MEDIO — Soporte IRPF**: descartado tras decisión Jaime — la fila zombi F9 ya tiene la nota IRPF en OBS, y eso es suficiente. NO se añade columna al Excel.

---

## Sesión 28/04/2026
**Objetivo:** Resucitar filas zombi en `PAGOS_Gmail_2T26.xlsx` (6 confirmadas, secuelas de gmail.py pre-v1.14).

### Completado
- [x] **Resucitar 6 filas zombi `PAGOS_Gmail_2T26`** — script `scripts/resucitar_zombis.py` v1.0 + ejecución `--apply` interactiva.
  - F3 SABORES PATERNA: TOTAL=199.73 €, REF=001525.
  - F4 WEBEMPRESA: TOTAL=19.35 €.
  - F5 MIGUEZ CAL (manual): FECHA=31/12/25, REF=A 4724, TOTAL=216.24 € (override por bug multi-albarán).
  - F8 CERES (14/04): TOTAL=714.21 €, REF=2624798.
  - F9 DEBORA GARCIA (manual): FORMA_PAGO=EF, OBS con nota IRPF -0.73 €.
  - F11 CERES (10/04): TOTAL=198.71 €, REF=2624536.
  - Backup: `PAGOS_Gmail_2T26_backup_20260428_1536.xlsx`.
- [x] Corrección manual de `ARCHIVO` en F5 antes del apply (1205→1231) para destapar el bug de nombrado multi-albarán.

### Backlog generado por esta sesión

- [ ] **ALTO — Bug nombrado de archivo en facturas multi-albarán**: gmail.py nombra el PDF con la fecha del primer albarán en vez de la fecha de la factura. Detectado en MIGUEZ CAL SL (28/04/2026, factura 31/12/25 archivada como `1205`). Probable que afecte a cualquier proveedor con facturas que agrupen varios albaranes (ForPlan/MIGUEZ es el caso paradigmático, pero puede haber otros). Revisar lógica de nombrado en `gmail/gmail.py` además del extractor de MIGUEZ.
- [ ] **MEDIO — Crear extractores faltantes**: FIVE GALAXIES COMMERCE LTD (Loyverse, mensual recurrente) y DUE SERVICIOS INTEGRALES LABORALES SL (PRL). Ambas marcadas zombi en este Excel pero out-of-scope de la sesión por falta de extractor.
- [ ] **MEDIO — Bug FORMA_PAGO en flujo gmail.py**: para proveedores cuyo extractor no extrae FORMA_PAGO, el flujo aplica el valor de MAESTRO ignorando lo que diga el PDF. Caso real: DEBORA GARCIA (PDF=EF, MAESTRO=TJ → escribió TJ). Soluciones: (a) que el extractor extraiga FORMA_PAGO del PDF; (b) preferir SIEMPRE el PDF cuando esté presente.
- [ ] **MEDIO — Soporte de IRPF**: el Excel actual no tiene columna IRPF. Algunas facturas (DEBORA GARCIA y otros autónomos) tienen retención que Kinema necesita para el modelo 111. Decidir si añadir columna `IRPF` o seguir anotándolo en OBS.
- [ ] **BAJO — Borrar copia obsoleta `outputs/PAGOS_Gmail_2T26.xlsx`** (3-abr) — la canónica vive en Drive desde la reforma R.1 (23/04). Tener dos copias divergentes confunde el flujo.

---

## Sesión 24/04/2026
**Objetivo:** Bloque E (gmail VPS) + verificación DIA/ECOMS + `/documentos` v2 en Streamlit.

### Completado
- [x] Bloque E: primer disparo real `gmail.py --produccion` en VPS. 12 emails, 6 exitosos, 4 REVISAR, 0 errores. `[DROPBOX OK]` + `[DRIVE OK]` verificados.
- [x] Verificación DIA/ECOMS end-to-end. Formato 3 (factura canje) OK: fecha 20/04, ref FF202600000014, total 4,68 €, 3 líneas cuadre OK.
- [x] SPEC v4.5 → v4.6 (Bloque E + verificación DIA, commit `bc970a7`).
- [x] `/documentos` v2 en Streamlit Cloud: 6 secciones declarativas (Ventas, Compras, Movimientos Banco, Artículos, Maestro, Cuadres), pestañas Año en curso/Histórico donde aplica. Commit `572f155`.
- [x] Fix cadena de 4 bugs post-deploy `/documentos`:
  - `d803bf0` — Google API libs en `streamlit_app/requirements.txt`.
  - `c820b65` — deps transitivas (`pdfplumber`, `rapidfuzz`), `sys.path` defensivo en `app.py`, logging visible con `traceback.format_exc()`.
  - `410858f` — `config/loader.py` con cascada `secrets → env → legacy → default`; `config/settings.py` migrado.
  - `5530c10` — loader captura `ImportError`, no solo `ModuleNotFoundError`.
- [x] Tests nuevos: `test_config_loader.py` (6 casos, simulación Cloud con `monkeypatch(__import__)`), `test_documentos_config.py` (6 casos AST-based). Suite: 158 passed.
- [x] SPEC v4.6 → v4.7 con `/documentos` v2 + `config/loader` + §13.9 + §13.10 deuda requirements.
- [x] Autopsia: `tasks/cierre_sesion_24abr_documentos.md`.

### Reforma destinos cloud — estado final
- [x] R.1 gmail v1.21 — MAESTRO solo-lectura (`ec83c8f`).
- [x] R.2 gmail v1.22 — destinos cloud definitivos (`f72daf9`).
- [x] R.3 cuadre.py sync Drive (`20105ac`).
- [x] R.4 rutas PC → G:\ (`73d6d8e`).
- [x] R.5 migración física Drive.
- [x] R.6 push + pull VPS + smoke tests.
- [x] Fix token VPS (scope `drive`).
- [x] Bloque E ejecutado 24/04.

### Backlog 20/04/2026 (SPEC v4.5 §14)
- [x] 20A — Google Drive sync scope `drive` (cerrado 21/04).
- [ ] 20B — Ruta Windows hardcoded `C:\...\datos\Articulos 26.xlsx` (ahora `Articulos_2026.xlsx` en PC tras C2). Migrar VPS `.env` a `pathlib.Path` con `GESTION_FACTURAS_DIR`.
- [ ] 20C — `datos/Ventas Barea Historico.xlsx` ausente en VPS. Ahora está en Drive (`Ventas/Histórico/`, id `1JbaTVqa_Ojl87wALmLjTzdZtoY1FzDZ_`) — evaluar lectura desde Drive en VPS vs copia scp.
- [ ] 20D — Deploy key VPS sin write access en GitHub → regenerar o condicionar push a PC.
- [ ] v4.6 refactor — `ventas_semana/cargar_historico_wc.py:89` escribe total como string `"60,00 €"`. Pasar a floats nativos manteniendo lectura compatible.

### Pendientes seguridad
- [ ] Cambiar contraseñas Streamlit (las 4 son "2017") → decisión del usuario

### Pendientes Dia Tickets
- [ ] Integración Drive para subir tickets
- [ ] Login automático (JWT ~30 min, Playwright bloqueado por anti-bot)

### Pendiente Streamlit Cloud
- [ ] Verificar que el usuario cambió NETLIFY_DATA_URL a GitHub Pages en secrets

### Mejoras técnicas
- [ ] CUADRE: conectar con COMPRAS para ESTADO_PAGO automático
- [ ] CUADRE bugs: VINOS DE ARGANZA, SPOTIFY, Comunidad vecinos
- [ ] Documentar instalación OCR

### Alta evento — posibles mejoras futuras
- [ ] Calendario HTML visual (fechas coloreadas) — descartado por ahora, riesgo alto
- [ ] Cruce WC ↔ Loyverse para plazas pagadas online vs tienda (fuzzy matching)
- [ ] Email automático al organizador con enlace privado (requiere Gmail API)

---

## Sesión anterior (28-31/03/2026)
**Objetivo:** Drive + seguridad + alta evento completa + mov_banco

### Completado (28/03)
- [x] Verificar Google Drive sync + página "Documentos" en Streamlit
- [x] Seguridad: sanitizar importlib en gmail.py (path traversal)
- [x] Auth OAuth2 centralizado: gmail/auth_manager.py (5 scripts actualizados)
- [x] WooCommerce retry con backoff exponencial (3 intentos, 2/4/8s)
- [x] ESQUEMA actualizado a v5.4

### Completado (30/03)
- [x] mov_banco.py: fix encoding UTF-8, ejecutado con archivos Sabadell reales
- [x] Fix barea_auto.bat: PYTHONPATH + _to_float import + alerta_fallo scope
- [x] Ejecución manual ventas semanales (03:00 falló por PYTHONPATH)

### Completado (31/03)
- [x] Alta evento: selector cascada tipo→subtipo + detección conflictos fecha
- [x] Alta evento: soporte CERRADO (plazas pagadas/pendientes + enlace WhatsApp)
- [x] Alta evento: modo test ([TEST] privado + limpieza desde Streamlit)
- [x] Alta evento: lista fechas ocupadas antes del calendario
- [x] Alta evento: fix tipo ticket-event + categorías + tag Producto_destacado
- [x] Alta evento: fix meta_data _start_date_picker/_end_date_picker (calendario web)
- [x] Calendario Streamlit: columna Tipo (CERRADO/Abierto) + enlace privado
- [x] historico_eventos.py: Excel con 39 eventos desde WC (11 columnas)
- [x] Fix producto 3350 (CATA ESPECIAL 14/05/26): tipo + categorías + meta_data

---

## Sesión 27/03/2026
**Objetivo:** Contraseñas Streamlit + config Claude + Dia tickets + migración Netlify + auditoría

### Completado
- [x] Streamlit Cloud: contraseñas configuradas (plaintext, "2017")
- [x] `.claude/rules/` (api, extractores, excel) + `docs/api.md`
- [x] CLAUDE.md v4.2 (eliminar duplicados, punteros a rules/ y docs/)
- [x] Dia Tickets: script funcional, 200 tickets descargados con líneas productos
- [x] Dia Tickets: anti-duplicación (registro JSON + doble check)
- [x] Dia Tickets: registrado en runner API (dia_tickets, dia_tickets_stats)
- [x] Fix gmail_auto.bat: añadir PYTHONPATH para resolver nucleo/
- [x] Gmail ejecutado manualmente (11 procesados, 7 exitosos)
- [x] Migración Netlify → GitHub Pages completada y verificada
- [x] Fix .gitignore (cubrir datos/backups/, dia_tickets/, dia_session.json)
- [x] Fix SSL en data_client.py (verificación habilitada por defecto)
- [x] Backup cifrado: scripts/backup_cifrado.py (AES-256, 14 archivos, 162 KB)
- [x] Primer backup creado con contraseña Cascorro&Abades
- [x] Auditoría seguridad completa (1 crítico, 1 alto corregido, 10 medio, 4 bajo)
- [x] Plan migración archivos a Google Drive (Estrategia B aprobada)

### Notas
- El JWT de Dia.es expira en ~30 min, Playwright bloqueado por anti-bot → login manual necesario
- Contraseña backup cifrado: Cascorro&Abades (misma que Dia — usuario la eligió pese a recomendación)
- GitHub Pages URL: https://tascabarea.github.io/gestion-facturas
- El usuario debe cambiar NETLIFY_DATA_URL en Streamlit Cloud secrets

---

## Historial

| Fecha | Objetivo | Estado | Notas |
|-------|----------|--------|-------|
| 2026-03-12 | Auditoría Parseo v5.18 + limpieza | ✅ | 70 _convertir_europeo consolidados, dead code, VERSION unificada |
| 2026-03-13 | Análisis Gmail + docs + extractores | ✅ | CLAUDE.md v3.0, tasks/ creados, 2 skills |
| 2026-03-27 | Config + Dia + Netlify→GH Pages + seguridad | ✅ | Ver detalle arriba |
| 2026-04-23 | Reforma destinos cloud R.1-R.6 + fix token VPS | ✅ | SPEC v4.6 |
| 2026-04-24 | Bloque E + DIA/ECOMS + `/documentos` v2 + config/loader | ✅ | SPEC v4.7, 5 commits, autopsia en tasks/cierre_sesion_24abr_documentos.md |
| 2026-04-28 | Resucitar 6 filas zombi PAGOS_Gmail_2T26 | ✅ | `scripts/resucitar_zombis.py` v1.0; backup `PAGOS_Gmail_2T26_backup_20260428_1536.xlsx`; 4 items backlog (multi-albarán, FORMA_PAGO, IRPF, extractores FIVE GALAXIES + DUE) |
| 2026-04-29 | Diagnóstico 6 facturas no procesadas Bloque E | ✅ | Reporte `outputs/diagnostico_6_facturas_20260429.md`; 5/6 ya procesadas (premisa inexacta — alias coloquiales vs canónicos); 1 bug real (`anthropic.py` REF persistente → anti-dup colisiona) con parche propuesto sin aplicar |
| 2026-04-29 (tarde) | Fix anthropic.py + rescate factura 20/04 + limpieza control DB + deploy VPS | ✅ | Commits Parseo `33e9add` + gestion-facturas `59a62e9` (diagnóstico previo) + cierre. Rescate `EXB4HCQN-0007`, 4 escrituras OK. Control DB md5 PC==VPS post-scp `b415efe8`. Deploy VPS `/opt/Parseo/extractores/anthropic.py` md5-match. Reporte `outputs/fix_anthropic_20260429.md` |
| 2026-04-30 | Push GitHub + fix DEBORA forma_pago + check defensivo gmail.py multi-albarán | ✅ | Push 5 commits gestion-facturas + sync VPS. Commit Parseo `961f5c7` (DEBORA). Commit gestion-facturas `<hash>` (gmail.py + cierre). MIGUEZ extractor INTACTO (irreproducible, 4 smoke tests verdes). Reporte `outputs/fix_bugs_gmail_20260430.md` |
| 2026-05-04 | Diagnóstico post-ejecución 04/05 + intento fix Drive scope | ⏸ INTERRUMPIDA | Diagnóstico completo (causa Drive 403 confirmada = bug 21/04 reapareció). OAuth flow abortado por cobertura. Sesión revertida a estado pre-sesión sin commits. 5 pendientes documentados para próxima sesión. |

# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Sesión 14/05/2026 — Cluster B item 3/3 JIMELUZ (PR Parseo #19, en curso)

**Objetivo:** cerrar cluster B con fix de JIMELUZ. Cifra histórica 15/21 obsoleta (extractor v3 16/03/2026 ya resolvió el bulk). Sobre corpus 2T24 (9 samples) quedan 2/9 descuadres reales + 1/9 caso ortogonal de escalera OCR.

### Completado (14/05/2026)
- [x] **Issue Parseo #18**: análisis empírico + plan de fix.
- [x] **PR Parseo #19**: `fix(jimeluz): derivar tramos faltantes y bonificaciones del cuadro fiscal por delta con TOTAL_FACTURA` (commit `7e9c01a`). Branch `fix/jimeluz-derivar-tramos-faltantes` desde `fa1a4ed`.
  - Regex flexible en `_extraer_cuadro_fiscal` (`\s*` tolera typo OCR "0, 86").
  - Helper `_aplicar_cuadre_derivado`: si `subtotal_cf != TOTAL`, añade línea sintética `BONIFICACION (DERIVADA)` (caso 2131, diff=-11,20€) o `TRAMO IVA 0% (DERIVADO)` (caso 2195, diff=+6,76€). Tolerancia 0,02€ respetada.
  - Anotación `CUADRE_DERIVADO: ...` en OBSERVACIONES de pestaña Facturas (`salidas/excel.py`).
  - Logger.warning `[JIMELUZ_CUADRE_DERIVADO]` grep-friendly.
  - VERSION Parseo 5.24 → 5.25.
- [x] **Tests**: 10/10 JIMELUZ passed. Suite Parseo completa: 78 passed + 1 skipped, 0 regresiones.
- [x] **Dry-run validado**: 8/9 cuadran al céntimo + 2200 sigue SIN_TOTAL (asserción negativa cumplida).
- [x] **Reescalado TBD SPEC v4.17**: cifra histórica obsoleta, marcado "en curso, ver PR Parseo #19".

### Pendiente (STOP pre-merge)
- [~] CI Parseo verde tests.yml.
- [~] Aprobación explícita del usuario antes de `gh pr merge`.

### Backlog generado por esta sesión (side observations, TBDs propios)
- [ ] **`jimeluz.py:46` CIF hardcoded vacío**: patrón correcto es leer `proveedor.cif` de MAESTRO_PROVEEDORES al inicio del extractor. Hardcoded solo como fallback si MAESTRO no disponible. CIF confirmado en log dry-run: `B87760676`. Prio BAJA (cosmético, sin impacto fiscal hoy).
- [ ] **REF extraída solo 1/9 muestras JIMELUZ** (2155 OK). El extractor v3 no implementa `extraer_referencia` específico. Investigar regex de REF en `jimeluz.py`. Prio BAJA.
- [ ] **Ausencia JIMELUZ en 1T26 Dropbox** (0 facturas en 30 dry-runs entre 09/05 y 14/05). Posibles causas: cadencia irregular del proveedor o miss de `gmail.py` (alias del remitente cambió, asunto sin keyword). Verificar Gmail búsqueda `from:jimeluz OR subject:jimeluz` últimos 90d. Prio BAJA.
- [ ] **Caso 2200 (SIN_TOTAL)**: OCR severamente degradado (259 chars vs ~640 buenos). Síntoma de la escalera OCR nivel 2 pendiente (PSM alternativos `--psm 4`/`--psm 11` + preprocesado deskew/threshold). Fuera de cluster B JIMELUZ. TBD propio, prio MEDIA.

### Mantenimiento (sesión propia, no JIMELUZ)
- [ ] Revisar 12 ruidos working tree gestion-facturas → decidir `.gitignore` vs commit (sesión propia, no JIMELUZ).

---

## Sesión 14-15/05/2026 — Auditoría overnight wrapper `_linea_sintetica_desde_total` (SPEC v4.17)

**Objetivo:** ejecutar la auditoría TBD prioridad media-alta v4.15/v4.16 del wrapper que sintetiza líneas desde TOTAL en `Parseo/extractores/generico.py`. Sesión autoaccept overnight, sin supervisión humana hasta despertar.

### Completado
- [x] **Script auditor** `Parseo/_audit_linea_sintetica.py` (gitignored): detecta activaciones en hoja `Lineas` de los 3 Excel del 13/05 vía marcador `[GENERICO_SINTETICO]`. Cruza filename → MAESTRO (599 aliases @registrar + 568 keys MAESTRO expandidos por `,/;` ) con fuzzy `rapidfuzz.WRatio` cutoff 85. Clasifica en LEGÍTIMA-A/B, SOSPECHOSA-1/2, INDETERMINADA según árbol de reglas estricto. Tiempo total <1s.
- [x] **Reporte** `outputs/auditoria_linea_sintetica_20260514.md` (gitignored): 26 activaciones totales (4T25 + 1T26 + 2T26), 16 LEGÍTIMA-A, 5 SOSPECHOSA-1, 5 SOSPECHOSA-2. 10× menos que la estimación informal "~37/40 líneas log → cientos/trimestre" de SPEC v4.15 (estaba contando doble: primario + fallback OCR de la misma factura).
- [x] **Triage humano por filtro de importancia operacional** (Jaime, post-overnight): de 10 SOSPECHOSAs mecánicas → 2 falsos positivos del fuzzy 85, 6 proveedores irrelevantes archivados, 2 accionables reales (Café Dromedario alta MAESTRO + AMAZON evaluar extractor dedicado). Tasa de yield real: 2/26 = 7,7%.
- [x] **Nueva lección operativa 4ª** formalizada: filtro de importancia operacional como 2º filtro post-validación cuantitativa. Documentado en SPEC v4.17 + `tasks/lessons.md`.
- [x] **SPEC bump v4.16 → v4.17** (este cierre). CLAUDE.md tabla actualizada.

### Backlog generado por esta sesión
- [ ] **Alta MAESTRO Café Dromedario** (refuerzo): proveedor ya estaba en backlog. Esta auditoría confirma 2 facturas reales (`AR 1T26 0220` + `REVISAR 2T26 0506`). Acción: Jaime crea entrada con CIF + IBAN + alias `cafedromedario.com` desde el filename.
- [ ] **Evaluar extractor dedicado AMAZON BUSINESS EU SARL** (prio **MEDIA-BAJA**): 9 facturas en 3 trimestres = ~3/trimestre, ~60€/factura, 560,92€ total. Volumen recurrente que justifica extractor para ahorrar warning permanente del wrapper sintético. No fiscal urgente. Sesión propia cuando convenga.

### Hallazgos NO accionables (archivados, sin TBD)
GRUPO KUAI (363€), DISTRIBUCION LEVANTINA (259€), PANADERIA JR (272€), DROPBOX (19€), PIERRE COMUNICACION (18€), AIMANE HAMMOUCH (1.875€ pero 2 fact aisladas), MASSAXUXES SCP, FIVE GALAXIES. Razón: no recurrentes ni operacionalmente relevantes para Tasca/Comestibles. Reabrir solo si reaparecen con frecuencia creciente en auditorías futuras.

---

## Sesión 14/05/2026 — Auditoría canónica #7 + fix LA CUCHARA (PR #17)

**Objetivo:** ejecutar la auditoría barrida canónica #7 v4.14 sobre todos los extractores de Parseo + cerrar el hallazgo accionable (1 ALTA detectada).

### Completado
- [x] **Script auditor** `Parseo/_audit_skip_patterns.py` (gitignored): cross-match de listas de "ignorar" (incluyendo `skip_patterns`, `ignorar`, `IGNORAR`, `IGNORAR_DESC`) contra `DiccionarioProveedoresCategoria.xlsx` filtrado por proveedor. Identificación de proveedor vía decorador `@registrar('NOMBRE', ...)`. ~15 min de ejecución.
- [x] **Reporte** `outputs/auditoria_skip_patterns_20260513.md` (gitignored): 116 extractores auditados, 1 colisión ALTA (LA CUCHARA / VALE / 4 productos VALENTINA), 5 extractores con nomenclatura no estándar sin casos, 0 colisiones MEDIA/BAJA con impacto.
- [x] **Tasa empírica 1/116 = 0,86%**: confirma cuantitativamente que la canónica #7 NO es problema sistemático en producción. Refuerza lección 2 v4.15.
- [x] **PR Parseo #17 mergeado** (merge SHA `868dcf7`). Commit único `47a9e8e` con fix LA CUCHARA: `ignorar_exacto = {'TOTAL','VALE'}` separado de `ignorar_substring = ['IVA 10']` + 4 tests sintéticos en `tests/extractores/test_la_cuchara.py` + VERSION 5.23 → 5.24. CI verde 45s. Suite Parseo 68 passed + 1 skipped.
- [x] **Nueva decisión canónica #8** documentada en SPEC v4.16: exact-match por defecto en filtros de cabecera, substring solo cuando el contexto fuerza unicidad.
- [x] **SPEC bump v4.15 → v4.16** (este cierre). CLAUDE.md tabla actualizada.

### Backlog generado por esta sesión
- [ ] **Regex de captura LA CUCHARA `[A-Z0-9\s%]` sin puntos** (prio **MEDIA**): bug condicional al comportamiento del OCR. Si tesseract conserva puntos (`E.AMARILLA`), el regex rechaza la descripción. Si el OCR los borra (`E AMARILLA`), no hay problema. Sin PDF real con punto conservado, no podemos validar impacto. Próxima ejecución de Parseo sobre LA CUCHARA puede dar la primera señal — sospechar este caso si aparecen líneas truncadas o base=0. Sesión propia.
- [ ] **Estandarización nominal `ignorar:` → `skip_patterns:`** en 4 extractores adicionales (`ceres`, `ecoms`, `la_alacena`, `la_lleidiria`): prio **BAJA**, sin casos reales. Conveniencia para que futuras auditorías canónica #7 sean robustas con un solo nombre de variable.

---

## Sesión 14/05/2026 — Auditoría merge primario↔fallback OCR (PR #16)

**Objetivo:** investigar mecanismo real del 1215 (errata v4.14) + añadir observabilidad permanente del merge primario↔fallback OCR en `Parseo/main.py`.

### Completado
- [x] **Investigación del mecanismo real**: el merge en `main.py:1582-1669` (`_merge_resultados` + `_necesita_fallback` + `_calcular_descuadre`), NO el `_linea_sintetica_desde_total` de `generico.py` (errata v4.14 confirmada). Caso 1215 atribuido al merge OCR; típico typo OCR `TICKEIT` + skip_pattern `\bTICKET\b` no anclado.
- [x] **Errata v4.14 documentada** en SPEC sin bump (commit gestion-facturas `11a32ed`).
- [x] **PR #16 mergeado en `TascaBarea/Parseo` main** (merge commit `8a3538a`, `--merge` preserva commit). 1 commit principal `2b67231`: refactor `_necesita_fallback`→`Optional[str]` C1-C4 + WARNING `[MERGE_FALLBACK]` en `_merge_resultados` + 5 tests caplog + VERSION 5.22→5.23.
- [x] **Auditoría empírica 4T25+1T26+2T26 (627 facturas)**: 48 invocaciones del merge (7,7%), **1 sola activación real** (LEVANTINA 1T26 1061, C3+M1, LEGÍTIMA por construcción), 47 mantienen primario, 0 sospechosas. **Hipótesis original ("merge enmascara bugs sistemáticamente") invalidada empíricamente**.
- [x] **Validación sub-B contra `517cf1f`** (pre-cluster-BM): 1215 reaparece con perfil C3+**M2** swing **−3,86€** (fallback descuadró peor, ganó por cantidad de líneas). Confirma que M2 es heurística cuantitativa débil y blinda el WARNING contra patrones históricos.
- [x] **Hallazgo secundario M3 código muerto**: bajo `_calcular_descuadre` actual (devuelve `inf` cuando líneas vacío), M1 siempre dispara antes que M3. Documentado en test dedicado. TBD para sesión futura.
- [x] **CI Parseo verde** (PR #16, 32s). Suite **64 passed + 1 skipped**, 0 regresiones.
- [x] **SPEC bump v4.14 → v4.15** (este cierre). CLAUDE.md tabla actualizada.

### Backlog generado por esta sesión
- [x] **Auditoría wrapper `_linea_sintetica_desde_total` en `Parseo/extractores/generico.py`** → ejecutada 14-15/05/2026 overnight (SPEC v4.17). 26 activaciones reales, 10× menos que la estimación informal. Tasa de yield 2/26=7,7%. Conteo de "~37/40 líneas" era doble-contado primario+fallback OCR.
- [ ] **Invocaciones inocuas del fallback OCR**: 47/627 facturas (7,5%) entran al merge y mantienen primario. Coste computacional (un OCR completo) sin impacto en datos. Posible refactor: evitar invocación cuando `_necesita_fallback` dispara por C4 sin descuadre real. Baja prioridad.
- [ ] **Refactor M3 en `_merge_resultados`**: decisión abierta — eliminar M3 (código muerto actual) o reparar `_calcular_descuadre` para que devuelva valor finito (p.ej. el TOTAL) y M3 sea alcanzable.

---

## Sesión 13/05/2026 — Cluster B item 2/3 BM SUPERMERCADOS (PR #15)

**Objetivo:** segundo item del cluster B (tras DIA done en v4.13). Refactor de `Parseo/extractores/bm.py` para 2 bugs coordinados que causaban descuadres en tickets con descuentos retail y productos con TOTAL en marca.

### Completado
- [x] **PR #15 mergeado en `TascaBarea/Parseo` main** (merge commit `e3b5dae`, --merge preserva 3 commits atómicos). Branch `fix/bm-cluster-oferta-y-total` eliminado. Bug A `cfec5a3` + Bug B `5b7c576` + VERSION bump `cc4714b`.
- [x] **Issue #14 abierto y cerrado**. Auto-cerrado por la cadena LITERAL `"Closes #14"` presente en commit `cc4714b` aunque iba entre paréntesis explicando que se omitía deliberadamente — GitHub parsea regex sin contexto (tercera manifestación de la lección v4.13 #1). Comentario aclaratorio posteado aparte con `gh issue comment 14 --body "..."` ([issuecomment-4444016856](https://github.com/TascaBarea/Parseo/issues/14#issuecomment-4444016856)).
- [x] **Fixtures reales** en `Parseo/tests/extractores/fixtures/bm/`: 7 PDFs de 1T26 (Dropbox/.../FACTURAS RECIBIDAS/1 TRIMESTRE 2026/). 7 tests parametrizados: **7/7 passed** al céntimo. Suite Parseo completa: **59 passed + 1 skipped**, 0 regresiones. CI verde 32s.
- [x] **Dry-run pre/post validado empíricamente** en baseline real:
  - 4T25 (309 fac): BM 1→0 descuadres, otros 20=20 (cero regresión), importe 79.681,55 € idéntico.
  - 1T26 (227 fac): BM 5→0 descuadres, otros 9=9 (cero regresión), importe 53.129,81 € idéntico.
- [x] **VERSION Parseo bump 5.21 → 5.22**.
- [x] **SPEC bump v4.13 → v4.14** (este cierre). CLAUDE.md tabla actualizada. Cluster B item 2/3 marcado cerrado.
- [x] **Reporte** `outputs/cluster_b_bm_20260513.md` referenciado desde SPEC.

### Cluster B — estado tras esta sesión
- [x] DIA — done (PR #13, v4.13).
- [x] BM SUPERMERCADOS — done (PR #15, v4.14).
- [ ] JIMELUZ — pendiente. 15/21 descuadres, usa OCR primario; validar si los patrones (saneamiento OCR de DIA, descuentos retail de BM) aplican.

### Backlog generado por esta sesión
- [ ] **Auditoría wrapper `fallback_sintetico` en `Parseo/main.py`**: nuevo TBD nacido del refuerzo de lección v4.13 #5 con datos cuantificados (fixture 1215: test aislado SUMA=0,84 con Δ=+6,05 vs dry-run Total=9,99 con Δ=−3,10 — mismo PDF, mismo código, signo opuesto). Casos legítimos vs casos donde enmascara bugs upstream. Posible refinamiento: cuando se active el wrapper, logar WARNING con magnitud de la corrección sintética. 1 sesión.
- [ ] **Auditoría barrida `skip_patterns` con `\b` no anclados**: en TODOS los extractores BM y similares (no solo bm.py). Aplicar decisión canónica #7 de v4.14: cada token corto de los `skip_patterns` se cruza contra el catálogo del proveedor buscando colisiones con descripciones legítimas. Tokens a revisar: `\bFACTURA\b`, `\bproducto\b`, `\bgénero\b`, `\bpresente\b`, `\boferta con\b`, etc. 1 sesión.
- [ ] **Re-procesar 4T25 para validación empírica de los clusters ECOMS + BM combinados**: opcional, NO fiscal. Confirmaría cuántos de los 23/31 (DIA) + 33 (BM SUPERMERCADOS) descuadres históricos se arreglan empíricamente.

---

## Sesión 13/05/2026 — Cluster ECOMS/DIA (PR #13)

**Objetivo:** segundo extractor del cluster B abierto en v4.11. Refactor de `Parseo/extractores/ecoms.py` para resolver 6 bugs coordinados que causan 74% descuadre DIA en histórico (23/31 facturas).

### Completado
- [x] **PR #13 mergeado en `TascaBarea/Parseo` main** (merge commit `517cf1f`). 6 bugs ECOMS atomizados en 6 commits (eba7d4d → 25d6d05) + chore VERSION (3da3d26) + fix CI tests OCR-skip (78a0c6c).
- [x] **Issue #12 cerrado** automáticamente vía `Closes #12`. Comentario aclaratorio posteado aparte con `gh issue comment` (segunda manifestación del patrón "no se puede comentar al cerrar si ya está cerrado").
- [x] **Fixtures reales** en `Parseo/tests/extractores/fixtures/dia/`: 4 PDFs (1 canje 2T26 + 3 OCR del 4T25 cubriendo IVA único y mixto). 18 tests parametrizados: 17 passed + 1 skipped intencional (local con tesseract). En CI: 5 passed + 13 skipped (tesseract/poppler no instalados).
- [x] **VERSION Parseo bump 5.20 → 5.21** (gracias a la unificación del Issue #5, 1 línea cambia y las 3 salidas coinciden).
- [x] **Diccionario externo `DiccionarioProveedoresCategoria.xlsx` actualizado**: fila 1347 añadida (`ECOMS / JABON ALMEND MI IMAQ / LIMPIEZA / IVA 21`). Backup local en `datos/backups/DiccionarioProveedoresCategoria_pre_jabon_almend_20260513_130223.xlsx`.
- [x] **SPEC bump v4.12 → v4.13** (este cierre). CLAUDE.md tabla actualizada. Cluster B item 1/3 marcado cerrado.

### Cluster B — estado tras esta sesión
- [x] DIA — done (PR #13).
- [ ] BM SUPERMERCADOS — pendiente. 33/77 descuadres, mayor volumen absoluto del cluster.
- [ ] JIMELUZ — pendiente. 15/21 descuadres, usa OCR primario; validar si el patrón body-first aplica con texto OCR pre-existente.

### Backlog generado por esta sesión
- [ ] **Auditoría barrida del bug "solo pág 0"**: 12 extractores de Parseo con `with pdfplumber.open(...)` propio podrían replicar el bug #1 de ECOMS. Lista exhaustiva: `alcampo`, `fabeiro`, `garda`, `ceres`, `arganza`, `casa_del_duque`, `celonis_make`, `embutidos_ferriol`, `fernando_moro`, `grupo_disber`, `angel_borja`, `abbati`. 1 sesión de barrido. Decisión por extractor sobre si reprocesar histórico — solo necesario para los que atiendan facturas multi-página.
- [ ] **Protocolo versionado `DiccionarioProveedoresCategoria.xlsx`**: snapshot diario al repo o detección de drift. Segunda manifestación del problema (sesión 12/05 y 13/05 lo tocaron desde código).
- [ ] **Re-procesar 4T25** para validación empírica del cluster ECOMS (opcional, no fiscal — solo auditoría interna). Confirmaría cuántos de los 23/31 descuadres DIA históricos se arreglan empíricamente.

---

## Próxima sesión (backlog OG mantenido)
**Objetivo OG:** resolver listado Drive en `/documentos` Cloud + favicon Comestibles + deuda requirements.

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
- [ ] **MAESTRO_PROVEEDORES** — completar CIF de **ISTA METERING SERVICES** (CUENTA `41096000`). Detectado en smoke 1T26 Parseo sesión 08/05 (factura 1025): el extractor `ista.py` identificó el proveedor correctamente pero CIF queda PENDIENTE porque MAESTRO no lo tiene poblado. No es bug del extractor — el recibo ISTA no muestra CIF en absoluto, hay que añadirlo manualmente desde fuente externa (web ISTA, CIRBE, BORME).
- [ ] **MAESTRO_PROVEEDORES — altas pendientes 1T26**: 7 proveedores detectados como CIF_PENDIENTE en smoke 1T26 sesión 08/05 (post-fix issue #8 Parseo). Necesitan alta completa (CUENTA, CIF, ALIAS, CLASE, ARCHIVO_EXTRACTOR si procede):
  - **ANTHROPIC** — [CIF pendiente, US, suscripción Claude API/web, 3 facturas en 1T26: 1070, 1104, 1168]
  - **ICATU SPIRITS** — [CIF pendiente, factura 1032]
  - **CLEMENT GEORGES** — [CIF pendiente, factura 1037]
  - **AIMANE HAMMOUCH** — [CIF pendiente, factura 1117]
  - **CAFÉ DROMEDARIO** — [CIF pendiente, factura 1179, recibida vía email administracion@cafedromedario.com]
  - **MAKRO** — [CIF pendiente, factura 1192 `0302 MAKRO EF.pdf`]
  - **ORGANIA OLEUM, S.L.** — [CIF pendiente, factura 1065. Pre-fix se mis-identificaba como QUESOS NAVAS por bug substring (issue #8 cerrado en commit Parseo `03dde16`)]

- [ ] **MAESTRO_PROVEEDORES — altas pendientes 2T26**: detectados como CIF_PENDIENTE / extractor genérico en diagnóstico 2T26 sesión 09/05/2026 (89 PDFs procesados con Parseo `415dc73` + flag `--dry-run`). Necesitan alta completa:
  - **FIVE GALAXIES COMMERCE LTD** — [CIF pendiente, factura `2T26 0418 FIVE GALAXIES COMMERCE LTD TJ.pdf`, fecha también pendiente]
  - **DUE SERVICIOS INTEGRALES LABORALES SL** — [CIF pendiente, factura `2T26 0420 DUE SERVICIOS INTEGRALES LABORALES SL TF.pdf`, sin total]
  - **kombucheria** — [REVISAR `2T26 0418 (katrin@kombucheria.com).pdf`, fecha pendiente]
  - **cetareatazones** — [REVISAR `2T26 0423 (info@cetareatazones.com).pdf`, fecha pendiente]
  - (TORRES IMPORT, ANTHROPIC y CAFÉ DROMEDARIO ya en lista 1T26 arriba; reaparecen en 2T26)

- [x] **Parseo — bug PANRUJE descuadre sistemático** (CERRADO 12/05/2026, commit Parseo `3053eda`). Refactor body-first: parsea IVA explícito por línea, agrupa por tasa, cross-check con footer. 6 tests nuevos + 4 PDFs fixtures reales (Patrón A IVA 4%/10%, Patrón C1 dos albaranes, Patrón C2 footer roto). Dry-run 2T26: 73 → 76 OK (+3 PANRUJE: 0408=178,63€, 0422=93,20€, 0507=93,20€). Decisión: fix quirúrgico en panruje.py (no helper compartido) — cluster B (supermercados) y C (retenciones IRPF) son patrones distintos, no del mismo bug. Documentado en SPEC v4.12.

---

## Sesión 09/05/2026 — gmail.py v1.26 lock-safe + Parseo --dry-run
**Objetivo:** parche crítico de data loss en gmail.py + flag dry-run real en Parseo (cierre de la deuda detectada en diagnóstico 2T26).

### Completado
- [x] **Auditoría preventiva del prompt v1.26**: detectadas 8 discrepancias entre el prompt y el código real ANTES de implementar (path `compras/gmail.py` → `gmail/gmail.py`, pre-flight v1.5 ya existía con bug, 29 emails históricos no 24, motivos JSON verificados, `--test` vs `--dry-run` inexistente, etc.). Reportado y confirmado con Jaime.
- [x] **gmail.py v1.25 → v1.26** (commit `6b9cdad`): pre-flight Excels (`r+b`, no `open('a')` prohibido), `ExcelBloqueadoError`, filtro pendientes ignora `error:` y `limpieza_pre_v1.13` (recovery retroactivo de 29 emails históricos), reordering del flujo por email (move etiqueta Gmail al PASO 6, no al PASO 2), eliminado check duplicado en `_crear_backups`. 15 tests nuevos en `tests/unit/test_gmail_lock_safe.py`. Suite 259 → 274 passed.
- [x] **Decisión canónica del reordering**: el `_mover_email_seguro` pasa de "red de seguridad inicial" a "confirmatorio final". La capa B (hash MD5) cubre el rol antiguo sin el bug de email huérfano. Ver `tasks/lessons.md`.
- [x] **CLAUDE.md sincronizada**: Gmail v1.25 → v1.26 (en commit anterior), SPEC v4.9 → v4.10 (en este cierre).
- [x] **SKILL.md gestion-facturas**: añadido TBD para rename `--test` → `--dry-run` en gmail.py (consistencia con la convención global).
- [x] **Diagnóstico Parseo 2T26 read-only** (sin commit): 89 PDFs, 73 cuadran (82%), importe 22.762,30€. Detectó violación de restricciones del prompt: el "modo aislado" (-o + --no-aprendizaje + --no-subcarpetas) NO era aislado — contaminó Drive y `Parseo/outputs/log_*.txt`. Hallazgos para tracking: PANRUJE descuadre sistemático, 5 SIN_LINEAS, 7 al genérico, 0 GGM GASTRO mismatches (patrón anterior no persiste en 2T26).
- [x] **Parseo `--dry-run` implementado** (commit Parseo `415dc73`, push origin/main verificado): plan en 3 fases (recon → propuesta → implementación) con checkpoints. Flag mutuamente excluyente con `-o` y `--aplicar-sugerencias` vía `parser.error()`, fuerza `--no-aprendizaje` (con aviso solo si no era explícito), Excel + log a `outputs/dry_runs/`, salta upload Drive. 8 tests nuevos. Suite Parseo 21 → 29 passed. Smoke test verificado sin leaks.

### Decisiones senior tomadas durante la sesión
- **Inversión del orden de `_mover_email_seguro`** en gmail.py: la propuesta inicial de "no marcar JSON + log + mover etiqueta a mano" del análisis de discrepancias era inaceptable como recovery. Jaime propuso reordering completo del flujo (move al final), aceptado y aplicado. Justificación: la capa B de duplicados ya cubre la función de "red de seguridad" sin el bug de email huérfano.
- **Verificación cruzada Dropbox en pre-flight**: aunque el data loss histórico fue por el Excel local, añadir también el chequeo de la copia Dropbox previene un fallo distinto pero igual de real (Drive Desktop bloqueando durante sobreescritura final). Coste despreciable (un `r+b` más).
- **Tests con subprocess** en `Parseo/tests/test_dry_run.py`: descartado mockeo de helpers internos. Subprocess + captura stdout/stderr es más robusto, refleja CLI real, no requiere refactor del orquestador. Fixture `scope="module"` ejecuta el run UNA vez para 5 tests (~3s vs ~30s).
- **NO usar `add_mutually_exclusive_group`** en argparse: forzaría también que `-o` y `--aplicar-sugerencias` sean mutuos entre sí (no lo son hoy). Usar `parser.error()` explícito por caso, exit 2 estándar argparse.

### Backlog generado por esta sesión
- 4 altas MAESTRO 2T26 (FIVE GALAXIES, DUE SERVICIOS, kombucheria, cetareatazones) — ver "Próxima sesión" arriba.
- Bug Parseo PANRUJE descuadre sistemático — ver "Próxima sesión" arriba.
- Inconsistencia versión Parseo: `--help` v5.15 vs `--version` v5.20 vs banner v5.15 (issue #5 conocido, separado).
- Investigar "Fallback sintético GENERICO" al import-time en Parseo (4 mensajes antes del banner; aparenta ser side-effect de templates auto-cargados).
- Rename `--test` → `--dry-run` en gmail.py (TBD añadido a skill `gestion-facturas`).

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
- [x] **🔴 1. Re-auth Drive + parche `GMAIL_SCOPES` + deploy VPS** ✅ resuelto en sesión 05/05/2026. Token regenerado con 4 scopes (`gmail.readonly`, `gmail.modify`, `business.manage`, `drive`), parche `gmail.py:191-194` aplicado, Drive API verificada (list Barea - Datos Compartidos OK), creds.to_json() preserva los 4 scopes. Deploy VPS md5-match `6c4af8156aacc6807af82e6218eed5fc`. Reporte: `outputs/fix_oauth_drive_20260505.md`.
- [x] **🟡 2. Crear `Parseo/extractores/jaleo.py`** ✅ commit Parseo `16f6c18`. Smoke test verde 2/2 PDFs (PDF1 N260761 598,50€ formato moderno + PDF2 #1807 523,50€ formato presupuesto). Deploy VPS md5-match `f9a8889b`. Reporte `outputs/fix_jaleo_20260504.md`.
- [x] **🟡 3. Resucitar 2 filas Jaleo zombi** ✅ aplicado solo en Provisional Dropbox (filas 53 + 64) — Drive Excels descartados del scope porque están desfasados 5 días (44 filas) — requieren re-sync masivo aparte. Total recuperado: 1.122,00 €.
- [x] **🟢 4. Investigar CIF `B85501989`** ✅ CERRADO 05/05/2026 noche. Es CIF de COMPROVINO SL (proveedor de vinos, nombre comercial BODEGABIERTA). Bug original: el PDF tenía datos del cliente (Comestibles Barea) prominentes y la heurística genérica los registró como proveedor. Resuelto creando extractor dedicado + alta MAESTRO con `cif='B85501989'` estático. Ver `outputs/fix_comprovino_20260505.md`.
- [ ] **🟢 5. Alta MAESTRO + extractor para "Aquí Santoña"** (`comercial@aquisantona.com`). Factura quedó como `REVISAR 2T26 0504 (comercial@aquisantona.com).pdf` sin proveedor ni total.
- [ ] **🟢 NUEVO 6. Alta MAESTRO + extractor "Torres Import S.A.U."** (`torresimport@torresimport.com`). Detectado en validación 05/05 23:54. Mismo patrón que Aquí Santoña: factura `REVISAR 2T26 0505 (torresimport@torresimport.com).pdf` sin proveedor identificado, sin total, ref `227152`, fecha no detectada.
- [ ] **🟡 NUEVO 7. Investigar `Parseo/extractores/pifema.py`** — extractor existe pero falla en producción (validación 05/05): fecha extraída `03/06/2026` (futura) y total no extraído (ALERTA ROJA). Email "AB26/171" con archivo `2T26 0603 PIFEMA SL TF.pdf`. Anti-dup descartó la factura por CIF+REF=PIFEMA|1284 ya en Excel, así que NO hay zombi nueva, pero el extractor está roto. Requiere inspección PDF + fix `extraer_fecha` y `extraer_total`.
- [x] **🟢 NUEVO 8. Race condition OCR temp file** ✅ CERRADO 06/05 (Bloque A QW2). Resuelto a nivel `gmail.py` (no en `francisco_guerra.py`): `NamedTemporaryFile` con cierre explícito + `Image.open()` en context manager + cleanup en `finally` con `try/except OSError`. Commit `9611fb3`.

### Pendientes derivados (sesión 04/05 tarde)
- [x] **🔴 Drive Excels desfasados 5 días** ✅ Provisional re-sincronizado desde Dropbox en sesión 05/05/2026 (21 → 65 filas). PAGOS_Gmail_2T26 sin equivalente en Dropbox; se actualizará automáticamente cuando el cron del viernes 08/05 corra con OAuth Drive funcional. Backup pre-resync: `Facturas 2T26 Provisional_backup_pre_resync_20260505_2023.xlsx`.

### Pendiente próxima ejecución manual
- [ ] **NOTA**: la próxima ejecución manual de `python gmail.py --produccion` desde PC será test end-to-end de los 5 fixes recientes (anthropic 33e9add, debora 961f5c7, miguez check c810d77, jaleo 16f6c18, OAuth Drive 0c10a86). PAGOS_Gmail Drive recibirá las facturas pendientes desde 29/04. Ver `docs/FLUJO_MANUAL_GMAIL.md`.

### Corrección de premisa
- [x] **El cron de gmail.py NO existe** — auditoría 05/05/2026 tarde reveló que en VPS solo había un header huérfano `# Gmail facturas - viernes 03:00` sin línea cron debajo. Las afirmaciones previas en sesiones 04/05 y 05/05 mañana ("cron viernes procesará...") eran incorrectas. Header reemplazado por comentario explicativo apuntando a `docs/FLUJO_MANUAL_GMAIL.md`. Backup pre-cambio: `/opt/gestion-facturas/backups/crontab_pre_20260505.txt` (en VPS).

---

## Sesión 06/05/2026 — BLOQUE B + FILTRADO NO-FACTURA (v1.25)
**Objetivo:** refactor heurística cliente/proveedor a 4 capas + detector PDFs no-factura.

### Completado
- [x] **Heurística `_nombre_aproximado` refactorizada a 4 capas**: Capa 4 sufijo societario (más fiable) + Capa 2 proximidad CIF + Capa 0 primera línea razonable + Capa 1 lista negra `CONFIG.NOMBRES_CLIENTE`. Helper `_es_nombre_proveedor_razonable` centraliza el criterio.
- [x] **Detector `_es_factura_valida`**: cuenta marcadores típicos (nº factura, fecha, importe, CIF). ≥2 = factura, <2 = no-factura. Integrado en `_procesar_pdf` con estrategia conservadora (marca REVISAR pero NO descarta).
- [x] **VERSION** 1.24 → 1.25 + bloque MEJORAS v1.25.
- [x] **Tests**: nuevo `test_bloque_b.py` (22 tests) + adaptados 2 de `test_nombre_aproximado.py` (cambian `_nombre_aproximado(None, ...)` por `proc._nombre_aproximado(...)`). Suite local 179 passed (antes 157).
- [x] **CI iteración**: primer push `91f648c` falló (FileNotFoundError MAESTRO — gitignored, no existe en runner). Fix `00eceff` con `__new__` en lugar de `__init__` (tests no necesitan cargar MAESTRO). CI verde.
- [x] **Sync VPS** (HEAD `00eceff`).
- [x] **Backlog cerrado**:
  - 🟡 Bloque B (heurística cliente/proveedor) → ✅ resuelto.
  - 🟢 Filtrado no-factura (caso Aquí Santoña) → ✅ resuelto.

### Decisiones senior tomadas durante la sesión
- Test "PROVEEDOR ARTESANAL" del plan inconsistente con `_KEYWORDS_NO_NOMBRE` (la palabra "proveedor" rechaza la candidata). Cambiado a "ARTESANIA LOCAL".
- Regresión 2 tests preservados de `test_nombre_aproximado.py`: plan ordenaba STOP. Adaptados a invocación con instancia (firma se mantiene; cambia solo cómo invocan).
- Fix CI iterativo (`__new__` en lugar de `__init__`): los métodos testeados no necesitan `self.maestro`, así que crear instancia sin disparar `__init__` evita la carga de MAESTRO gitignored.

---

## Sesión 06/05/2026 — FUENTE DE VERDAD MAESTRO (v1.24)
**Objetivo:** resolver bug silencioso lectura Drive vs escritura datos/.

### Completado
- [x] **Bug confirmado**: `datos/` 197 filas con COMPROVINO+JALEO; `G:\Maestro\` 196 filas (mtime 28/04) sin COMPROVINO. La próxima factura COMPROVINO/JALEO habría reproducido "Proveedor NUEVO" del 04/05.
- [x] **Decisión arquitectónica Opción B**: `datos/MAESTRO_PROVEEDORES.xlsx` (PC repo) es la fuente de verdad. Validada en chat con Jaime (un solo usuario activo, simplicidad > Drive multi-usuario).
- [x] **`gmail.py` simplificado**: ~80 LOC eliminadas. Removidos `_MAESTRO_PATH_WINDOWS`, `MaestroDriveError`, `load_maestro_from_drive` (~70 líneas), su llamada en `_conectar_servicios`, e import transitivo `from nucleo.sync_drive import descargar_archivo`. `resolver_maestro_path` simplificado: siempre `<base_path>/datos/MAESTRO_PROVEEDORES.xlsx`.
- [x] **VERSION** 1.23 → 1.24 + bloque MEJORAS v1.24 en header.
- [x] **Tests**: borrado `test_gmail_maestro_drive.py` (206 LOC, testaba API eliminada). Nuevo `test_maestro_path.py` (7 tests). Preservado `test_nombre_aproximado.py` (6 tests reubicados de heurística no afectada). Suite local: 157 passed, 0 failed (antes 144).
- [x] **Drive deprecado**: `G:\Maestro\MAESTRO_PROVEEDORES.xlsx` movido a `G:\_DEPRECATED_20260506\Maestro\` con README explicativo. `DiccionarioProveedoresCategoria.xlsx` NO afectado (no es MAESTRO).
- [x] **Commit `b4e0651` push origin main**. CI verde (run 25445425979, 46s). Sync VPS OK.
- [x] **Reporte completo** `outputs/fix_maestro_fuente_verdad_20260506.md` (incluye plan migración B→A si entran nuevos usuarios).

### Backlog cerrado
- 🔴 Bug silencioso MAESTRO lectura Drive vs escritura datos/ → ✅ resuelto.

---

## Sesión 06/05/2026 — BLOQUE A (auditoría gmail.py, 5 quick wins)
**Objetivo:** aplicar Bloque A de la auditoría completa generada en chat (`AUDITORIA_GMAIL_PY_20260506.md`).

### Completado
- [x] **5 quick wins aplicados en `gmail.py`** v1.22 → v1.23:
  - QW1: VERSION única — eliminados strings hardcoded `v1.14`/`v1.15` del HTML email + asunto + argparse. `Notificador` acepta `version` como param.
  - QW2: OCR race condition — `NamedTemporaryFile` con cierre explícito + `Image.open()` context manager + cleanup defensivo. Evita `WinError 32`.
  - QW3: Validación scopes token — `GmailClient.conectar()` aborta con `RuntimeError` si scopes incompletos. Defensa contra causa raíz bug OAuth Drive 28-30/04.
  - QW4: `LocalDropboxClient` lanza `FileNotFoundError` (no `Exception` genérica).
  - QW5: `ProveedorNuevoDetectado` `@dataclass` — sustituye lista de dicts ad-hoc.
- [x] **8 tests unitarios** en `tests/unit/test_gmail_quick_wins.py`. Suite local: 144 passed (antes 136), 0 fallos.
- [x] **Commit `9611fb3` push origin main**. Sync VPS OK (md5 difiere por CRLF/LF, 2784 líneas idénticas).
- [x] **Backlog "Race condition OCR `francisco_guerra.py`" cerrado** (resuelto a nivel `gmail.py`).
- [x] Reporte completo `outputs/bloque_A_gmail_qw_20260506.md`.

### Próximos bloques de la auditoría
- 🟡 **Bloque B**: bug latente cliente/proveedor (refactor identificación heurística).
- 🟡 **Bloque C**: Excel I/O (separar lectura/escritura, lock handling).
- 🟡 **Bloque D**: refactor modular (división de gmail.py en submódulos).

---

## Sesión 05/05/2026 — NOCHE-4 (validación end-to-end)
**Objetivo:** Lanzar `gmail.py --produccion` para validar los 6 fixes acumulados en producción.

### Completado
- [x] **gmail.py ejecutado** (tras 2 ajustes path/PYTHONPATH + 1 unlock zombi). 5 emails pendientes, 3 OK, 2 revisión, 0 errores. Log: `outputs/logs_gmail/2026-05-05_manual.log`.
- [x] **OAuth Drive fix VALIDADO** — `[DRIVE OK] Excels de compras sincronizados`. Sin `[DRIVE FALLO] 403`. PAGOS Drive recuperado de **21 → 69 filas** (+48 las 5 días desfasados desde 29/04).
- [x] **Miguez check defensivo VALIDADO** — MIGUEZ CAL procesada limpiamente sin disparar el check (ref `A 1537`, fecha 30/04, coherente con email).
- [x] **Provisional Drive y Dropbox sincronizados** (md5 idéntico tras la ejecución, +4 filas cada uno).
- [x] **Bugs en docs corregidos**: `docs/FLUJO_MANUAL_GMAIL.md` tenía 2 errores en el comando documentado (`gmail.py` no `gmail/gmail.py`, faltaba `PYTHONPATH=.`). Corregido + añadido `outputs/` al pre-check de lock files (lock zombi en `outputs/~$PAGOS_Gmail_2T26.xlsx` abortó el primer intento).
- [x] **3 problemas nuevos detectados** y registrados como backlog (PIFEMA fecha futura + total no extraído, TORRES IMPORT proveedor nuevo, FRANCISCO GUERRA race condition OCR).
- [x] **4 fixes pendientes de validación** (Anthropic, Debora, Jaleo, Comprovino) — esperan próxima factura del proveedor.
- [x] **Reporte completo** `outputs/validacion_20260505.md`.

---

## Sesión 05/05/2026 — NOCHE-3
**Objetivo:** Consolidar deps de test (4 ImportError + 22 async).

### Completado
- [x] **Auditoría pyproject.toml + workflow** — `pyproject.toml [dev]` solo tenía 4 deps (pytest, pytest-cov, pytest-asyncio, httpx). Workflow `tests.yml` instalaba 5 extras a mano (`openpyxl pdfplumber rapidfuzz pydantic httpx`). Las 4 deps que CI no satisfacía (google-auth, google-api-python-client, numpy, python-dotenv) NO estaban en ningún sitio — sí en .venv local del PC porque alguien las pip-install-ó a mano en su día.
- [x] **Consolidadas 9 deps en `pyproject.toml [dev]`** — añadidas google-api-python-client, google-auth, google-auth-oauthlib, numpy, openpyxl, pdfplumber, pydantic, python-dotenv, rapidfuzz. Reordenado alfabéticamente. `asyncio_mode=auto` ya estaba en `[tool.pytest.ini_options]`.
- [x] **Workflow simplificado** — eliminada la línea `pip install openpyxl pdfplumber rapidfuzz pydantic httpx`. Ahora una sola fuente de verdad: `pip install -e ".[dev]"`.
- [x] **Reinstalado local** — `pytest-asyncio 1.3.0`, `pytest-cov 7.1.0`, `coverage 7.13.5`. Las google/numpy/dotenv ya estaban.
- [x] **Suite local 136 passed, 0 failed** (antes: 114 + 22 async fail). 44 deselected (sin marker `unit`).
- [x] **3 iteraciones CI hasta verde**: `1de22b5` (consolidación inicial, 4→1 errors) → `df71401` (+pandas+fastapi, 0 errors collection pero 22 ERRORs runtime) → `ab94d04` (+python-multipart, **success** 179 passed/1 skipped). Backlog 🟡 4 ImportError CI + 🟡 22 async cerrados.

---

## Sesión 05/05/2026 — NOCHE-2
**Objetivo:** Extractor COMPROVINO + alta MAESTRO + cierre backlog CIF B85501989.

### Completado
- [x] **Diagnóstico bug 04/05** confirmado — PDF de COMPROVINO tiene datos del cliente (Comestibles Barea) prominentes y datos del proveedor (COMPROVINO/BODEGABIERTA) en jerarquía visual menor. Heurística genérica de gmail.py registró el cliente como proveedor con CIF B85501989 (que en realidad es del proveedor).
- [x] **Extractor `Parseo/extractores/comprovino.py`** creado (~110 líneas). Aliases: `COMPROVINO SL / COMPROVINO S.L. / COMPROVINO / BODEGABIERTA`. CIF estático `B85501989` (defensa anti-confusión). Smoke test verde 3/3 sobre 1 PDF (255,21€ / 30/04/2026 / A/261096). Commit Parseo `e6aabf7`.
- [x] **Alta MAESTRO_PROVEEDORES** fila 197 (CUENTA=None, lo rellena Kinema). 196 → 197 filas. Backup `MAESTRO_PROVEEDORES_backup_20260505_2320.xlsx`. Sigue patrón VINOS (CLASE=2, TIPO_CATEGORIA=HARDCODED, CATEGORIA_FIJA=VINOS) idéntico a Gredales/Pago Alto Landon.
- [x] **Deploy VPS** md5-match `5a0c7f995d1f8fee176d6f4be032f02b`. `__pycache__` limpiado local + VPS. MAESTRO sincroniza vía git pull (no gitignored).
- [x] **Lessons** — regla nueva sobre PDFs con jerarquía visual cliente/proveedor invertida.
- [x] **Backlog CIF B85501989 CERRADO**.

---

## Sesión 05/05/2026 — NOCHE
**Objetivo:** Arreglar tests CI rotos (TOTAL_MIN_SOSPECHOSO).

### Completado
- [x] **Diagnóstico completo del bug** — ambos tests (`test_validaciones_negocio.py` y `test_ventana_gracia.py`) cargan `gmail.py` vía `importlib.util.spec_from_file_location("gmail_module*", ...)` y esperan API eliminada: 3 constantes (`TOTAL_MIN_SOSPECHOSO`, `TOTAL_MAX_SOSPECHOSO`, `FECHA_MAX_ANTIGUEDAD_DIAS`) y 3 funciones (`trimestre_de_fecha`, `es_trimestre_inmediatamente_anterior`, `determinar_destino_factura`).
- [x] **Origen identificado** — merge `cec9306` (18/04/2026) "prioridad código PC" eliminó 481 líneas de `gmail.py`. La versión PC priorizada NO tenía las constantes de rango y reemplazó la API de ventana de gracia (4 estados → binaria via `obtener_trimestre` + `es_factura_atrasada`).
- [x] **Decisión Opción A** (recomendación senior) — borrar ambos tests obsoletos. Las features se descartaron conscientemente; restaurar constantes solo para que pasen los tests sería gimnasia.
- [x] **Borrados 2 tests** (304 líneas total) — commit `c0f1710`.
- [x] **Suite tests/unit/ verificada local** — antes: 2 errors during collection (suite no arrancaba). Después: 114 passed, 22 failed. Los 22 fallos son deuda async preexistente en `test_api_security.py` (falta plugin `pytest-asyncio`) — bug distinto, fuera de scope.

### Backlog generado (preexistente destapado al arreglar collection)
- [x] **🟡 4 ImportError en CI por dependencias faltantes en workflow** ✅ CERRADO 05/05 NOCHE-3. Consolidadas 9 deps en `pyproject.toml [dev]` (google-auth, google-auth-oauthlib, google-api-python-client, numpy, python-dotenv, openpyxl, pdfplumber, pydantic, rapidfuzz). Workflow simplificado: `pip install -e ".[dev]"` sin extras manuales. Commit `1de22b5`.
- [x] **🟡 22 tests async fallando en `test_api_security.py`** ✅ CERRADO 05/05 NOCHE-3. `pytest-asyncio` ya estaba en `[dev]` pero faltaba reinstalar. Suite local post-fix: **136 passed, 0 failed**. Reporte: `outputs/fix_ci_deps_20260505.md`.

---

## Sesión 05/05/2026 — TARDE
**Objetivo:** Desactivar cron gmail.py + documentar flujo manual.

### Completado
- [x] **Auditoría crontab VPS** — `crontab -l`, systemd timers, `/etc/cron.d/`, otros usuarios. Resultado: NO existe cron activo de `gmail.py`; solo había un header huérfano `# Gmail facturas - viernes 03:00`. La premisa "cron viernes procesará" registrada en sesiones 04/05 y 05/05 mañana era falsa.
- [x] **Header crontab reemplazado** por 3 líneas explicativas apuntando a `docs/FLUJO_MANUAL_GMAIL.md`. Línea backup diario `control-barea` intacta. cron daemon active.
- [x] **Backup crontab pre-cambio** en `/opt/gestion-facturas/backups/crontab_pre_20260505.txt`.
- [x] **Documentación del flujo manual** en `docs/FLUJO_MANUAL_GMAIL.md`: comando único, cuándo lanzar, pre-checks, lectura de log, renovación de token, reactivación cron si en el futuro se quisiera.
- [x] **Lessons.md** — regla nueva sobre cron silencioso vs ejecución manual con observación humana.

---

## Sesión 05/05/2026 — MAÑANA
**Objetivo:** OAuth Drive + parche `GMAIL_SCOPES` + re-sync Drive Excels desfasados.

### Completado
- [x] **Parche `gmail/gmail.py:191-194`** — añadido `'https://www.googleapis.com/auth/drive'` a `GMAIL_SCOPES`. Razón: `gmail.py:706` carga con `from_authorized_user_file(path, GMAIL_SCOPES)` y al hacer `creds.to_json()` filtra el token al subset; sin drive en la lista, cada refresh borraba el scope. Mismo patrón ya documentado en lessons.md (caso 21/04 + revisitado 04/05).
- [x] **Token regenerado vía `gmail/renovar_token_business.py`** con los 4 scopes: gmail.readonly, gmail.modify, business.manage, drive. Backup PRE-OAuth conservado (`token.json.bak.20260505`).
- [x] **Drive API verificada** — `svc.files().list(q='Barea - Datos Compartidos')` devuelve la carpeta canónica con ID `1nYsbBT2oxmXAIgOdF60gqDlnuKV8X-y-`. Sin 403.
- [x] **Robustez creds.to_json()** — tras load + serializar, los 4 scopes se preservan.
- [x] **Deploy VPS** — md5-match `6c4af8156aacc6807af82e6218eed5fc`. Backup remoto `token.json.bak_pre_oauth_20260505`.
- [x] **Re-sync Drive Provisional** — copiado desde Dropbox (8753 bytes / 65 filas), reemplazando versión Drive del 29/04 (6401 bytes / 21 filas). Backup `Facturas 2T26 Provisional_backup_pre_resync_20260505_2023.xlsx`. Δ filas Dropbox==Drive ✓, bytes ✓.
- [x] **PAGOS Drive deja en pendiente cron viernes** — sin equivalente en Dropbox como fuente.
- [x] **Reporte completo** `outputs/fix_oauth_drive_20260505.md`.

### Backlog generado
- [ ] **🟡 Refactor `gmail.py:conectar()`** delegando en `auth_manager.get_gmail_service()` para eliminar la duplicación de carga de credenciales. Este parche es la solución mínima; refactor pendiente.

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

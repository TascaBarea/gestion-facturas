# SPEC GESTION-FACTURAS v4.19

> Documento maestro unificado — actualizado 19/05/2026
> Consolida: SPEC v3.0 (28/03) + ESQUEMA DEFINITIVO v5.4 (28/03) + Propuesta Migración Cloud (29/03)
> Ruta local: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\`

---

## CHANGELOG v4.19 — 19/05/2026 (Cierre refactor Parseo/Streamlit + CI cross-repo estable)

Contexto del cierre:
- Commit de consolidación CI cross-repo: `b5985f4` (`ci: use PARSEO_RO_TOKEN for cross-repo checkout of Parseo`).
- Run CI verde: `26066541701` (workflow `Tests`, checkout cruzado + unit + cobertura en verde).
- Parseo en versión canónica: `5.26`.

PRs cerradas en este bloque:
- **PR-1**: contrato de esquema SPEC v4.x en Parseo (`tests/test_excel_schema_spec_v4.py`).
- **PR-2**: paridad CLI + Streamlit en export canónico (`COMPRAS_<trim>_parseo.xlsx`) y archivado de `main.py` legacy en gestion-facturas.
- **PR-3**: fuente única de `VERSION` en gestion-facturas leyendo Parseo canónico por `importlib.util` + CI con doble checkout.

6 fixes concretos aplicados:
1. Test de contrato de cabeceras exactas SPEC v4.x (hojas `Lineas` y `Facturas`) en Parseo.
2. Streamlit `pages/parseo.py` deja de construir DataFrame legacy y delega en `salidas.generar_excel` canónico de Parseo.
3. Naming alineado CLI + dashboard: salida canónica `COMPRAS_<trim>_parseo.xlsx`.
4. `gestion-facturas/main.py` legacy archivado (`main_LEGACY_ARCHIVADO.py`) y stub de protección con `sys.exit(1)`.
5. `gestion-facturas/config/settings.py` toma `VERSION` desde `Parseo/config/settings.py` (soporte `PARSEO_ROOT`).
6. Workflow `tests.yml` con checkout cruzado autenticado de Parseo vía `secrets.PARSEO_RO_TOKEN`.

TBDs cerrados por este refactor (pasan a CERRADO):
- **Paridad de formato Excel CLI vs Streamlit**: CERRADO (ambos caminos usan el exportador canónico de Parseo).
- **Fuente de verdad de VERSION entre repos**: CERRADO (`config/settings.py` en gestion-facturas ya no mantiene versión duplicada).
- **Blindaje por test de contrato de esquema**: CERRADO (falla en CI si se rompe la forma v4.x del Excel).

Notas de coherencia documental:
- Las referencias a columnas legacy (`TOTAL_CALCULADO`, `MATCH`, `CÓDIGO`, `LÍNEAS`, `ERRORES`) quedan solo como histórico en changelogs/tareas previas.
- La salida canónica vigente para Parseo es `COMPRAS_<trim>_parseo.xlsx`.

---

## CHANGELOG v4.18 — 15/05/2026 (Cierre cluster B íntegro + 5ª validación cuantitativa culminada)

### Cluster B cerrado íntegro

El cluster B (descuadres de extracción en proveedores con cuadro fiscal / OCR primario) queda cerrado en sus 3 items:

| Item | Proveedor | PR Parseo | Cerrado en | Mecanismo del fix |
|---|---|---|---|---|
| 1/3 | ECOMS / DIA | #13 | v4.13 | leer todas las páginas + orden saneamiento OCR antes de diccionario keywords |
| 2/3 | BM SUPERMERCADOS | #15 | v4.14 | distinguir `Oferta` (informativa, ya descontada) vs `Promoción`/`Vales` (descuento real) + `skip_patterns` anclados a inicio de línea |
| 3/3 | JIMELUZ | #19 | v4.18 (este bump) | regex flexible del cuadro fiscal + derivación de tramos/bonificaciones por delta con TOTAL_FACTURA |

JIMELUZ item 3/3 — detalle del cierre:
- Issue Parseo #18: análisis empírico sobre corpus 2T24 (9 samples).
- PR Parseo #19 mergeado (merge SHA `904ac71`, commit fix `7e9c01a`): `fix(jimeluz): derivar tramos faltantes y bonificaciones del cuadro fiscal por delta con TOTAL_FACTURA`.
  - Regex flexible en `_extraer_cuadro_fiscal` (tolera typo OCR sistemático tipo `"0, 86"` con `\s*`).
  - Helper `_aplicar_cuadre_derivado`: añade línea sintética marcada `(DERIVADO)` cuando `subtotal_cuadro_fiscal != TOTAL_FACTURA` (tolerancia 0,02€). Patrón unificado que resuelve 2 casos opuestos en signo — bonificación derivada (caso 2131, −11,20€) y tramo IVA 0% omitido por el ticket (caso 2195, +6,76€).
  - Anotación `CUADRE_DERIVADO` en OBSERVACIONES (`salidas/excel.py`) + `logger.warning("[JIMELUZ_CUADRE_DERIVADO]...")` grep-friendly.
  - VERSION Parseo 5.24 → 5.25.
- Tests: 10/10 JIMELUZ passed (fixtures OCR pre-capturados, sin dependencia de tesseract en CI). Suite Parseo completa 78 passed + 1 skipped, 0 regresiones. CI verde.
- Issue #18 cerrado manualmente post-merge.

### 5ª validación cuantitativa culminada — JIMELUZ: cifra histórica 15/21 → 2/9 real

La validación empírica de JIMELUZ culmina la serie de validaciones cuantitativas del eje "no convertir datos en trabajo automáticamente" (lecciones v4.15 #2, v4.16 #1, v4.17 #4):

| Validación | Cifra informal / histórica | Cifra real validada |
|---|---|---|
| BM SUPERMERCADOS (v4.14) | ~33 descuadres | 6 reales |
| Merge primario↔fallback OCR (v4.15) | "merge enmascara bugs sistemáticamente" | 1/627 = 0,16% activación, 0 sospechosas |
| skip_patterns canónica #7 (v4.16) | patrón potencialmente sistemático | 1/116 = 0,86% |
| wrapper `_linea_sintetica` (v4.17) | "~cientos por trimestre" | 26 activaciones, 2/26 = 7,7% yield |
| **JIMELUZ (v4.18)** | **"15/21 descuadres"** | **2/9 descuadres reales** + 1/9 ortogonal (2200 OCR) |

La cifra histórica "15/21" provenía de un conteo previo a la v3 del extractor (16/03/2026), que ya había resuelto el grueso. Sobre corpus 2T24 (9 samples) con el extractor v3 vigente: 2/9 descuadres reales por cuadro fiscal con tramos parciales/bonificaciones (resueltos en PR #19) + 1/9 caso ortogonal de escalera OCR (2200, `SIN_TOTAL`, fuera de cluster B). Patrón consistente con las 4 validaciones previas: **toda cifra informal de descuadres, al validarse, resulta sustancialmente menor que la estimación**.

### Errata v4.17 formalizada (commit `82ea1c7`)

Los 3 puntos de la errata 14/05/2026 (registrados sin bump en v4.17) quedan formalizados con su estado de cierre:

1. **Bug identificador filenames email-derivados** — Café Dromedario llega con filename derivado del email del remitente (`REVISAR_2T26_0506__administracion_cafedromedario_com_.pdf`), no nomenclatura canónica. **Estado: ABIERTO** → reformulado como issue Parseo #20 (ver TBDs nuevos).
2. **Punto ciego del auditor overnight (encadenamiento MAESTRO→alias)** — re-cruce ejecutado 14/05/2026 (`Parseo/_recheck_sosps2.py`). Resultado: 0 falsos negativos puros del encadenamiento, 4 CONFIRMADO_SIN_EXTRACTOR, 1 borderline descartado (PIERRE COMUNICACION, score 72). **Estado: CERRADO** (investigación concluida).
3. **Discrepancia CIF en `cafes_pozo.py`** (`A28136189` fantasma vs `ESA28917250` real del footer). **Estado: CERRADO** — fix en commit Parseo `312afe6`.

### Cierre quick-win Café Dromedario

Quick-win ejecutado 14/05/2026: fix del CIF fantasma de `cafes_pozo.py` (`A28136189` → `A28917250`, commit Parseo `312afe6`, pusheado + CI verde) + apertura de issue Parseo #20 para el bug del renombrado por sender + docs en gestion-facturas (commit `f8a2566`: `tasks/todo.md` + lección "CIFs hardcodeados pueden ser fantasma" en `tasks/lessons.md`).

### TBDs nuevos

- **gmail.py — mapeo sender `administracion@cafedromedario.com` → CAFES POZO SA** (issue Parseo #20, **ABIERTO**). gmail.py renombra el PDF con el email del remitente como token PROVEEDOR cuando no resuelve el proveedor del contenido. Causa raíz del punto 1 de la errata v4.17. Prioridad MEDIA (proveedor recurrente real). 3 opciones de fix planteadas en el issue, sin decisión.
- **Side observations JIMELUZ** (4, todas **VIVAS**, derivadas del trabajo de PR #19):
  - `jimeluz.py` CIF hardcoded vacío — debe leer `cif` de MAESTRO. Prioridad BAJA.
  - REF extraída solo en 1/9 muestras JIMELUZ — el extractor v3 no implementa `extraer_referencia` específico. Prioridad BAJA.
  - Ausencia de JIMELUZ en 1T26 Dropbox (0 facturas en dry-runs 09–14/05) — verificar Gmail 90d. Prioridad BAJA.
  - Caso 2200 `SIN_TOTAL` — OCR severamente degradado, síntoma de la escalera OCR nivel 2 pendiente (PSM alternativos + preprocesado). Fuera de cluster B. Prioridad MEDIA.

### TBDs heredados que siguen vivos

`Cluster B item 3/3: JIMELUZ` sale de la lista (cerrado en este bump). El resto de TBDs heredados de v4.17 siguen vigentes sin cambios (ver §CHANGELOG v4.17, sección "TBDs heredados"): invocaciones inocuas fallback OCR, refactor M3 `_merge_resultados`, regex LA CUCHARA, estandarización `ignorar:`→`skip_patterns:`, barrido pdfplumber multi-página, protocolo versionado Drive, dedup aliases MAESTRO, bug identificador proveedor, cluster C IRPF, issue #5 Parseo.

### Progreso TBD v4.19 — repo canónico para Diccionario (parcial)

Ejecutado 16/05/2026 (sesión separada de la reformulación del 15/05, commit 282194f):
- `Parseo/config/settings.py`: `DICCIONARIO_DEFAULT` resuelve a path relativo del repo gestion-facturas via pathlib (commit Parseo `a5d734c`).
- Post-commit hook en `gestion-facturas/.git/hooks/post-commit` copia el Diccionario a Drive tras cada commit que lo modifique. Template versionado en `docs/hooks-templates/post-commit.sample.sh`; instalación documentada en `docs/HOOKS.md`.

Cierra el item principal del TBD v4.19: el riesgo de drift repo↔Drive del Diccionario queda cubierto por sync automático. El desajuste puntual detectado el 14/05 (repo atrasado respecto a Drive) ya se había resuelto con el commit `dfd7dbd`; lo que esta ejecución aporta es la prevención de que recurra.

Items residuales del TBD v4.19 (vivos, no cerrados en esta ejecución):
- **MAESTRO sync sigue manual**: `MAESTRO_PROVEEDORES.xlsx` está gitignored (repo público + IBANs sensibles). El hook usa `git diff-tree` que solo ve ficheros versionados — incluir MAESTRO requeriría repo privado aparte o mecanismo que no dependa de git. Prioridad BAJA hasta que el drift se manifieste.
- **4 extractores con cascadas hardcoded**: `rufino.py`, `makro.py`, `jimeluz.py`, `legacy/bm.py` resuelven el Diccionario contra paths relativos propios, ignorando `DICCIONARIO_DEFAULT`. Funcionan porque sus cascadas ya apuntan al repo, pero la unificación que pedía el TBD original no se hizo en esta ejecución. Prioridad MEDIA.

Bump SPEC v4.18 → v4.19 NO se hace en esta sub-sección — decisión aparte cuando los residuales se cierren o se quiera publicar.

---

## CHANGELOG v4.17 — 15/05/2026 (Auditoría wrapper `_linea_sintetica` ejecutada — filtro de importancia operacional)

### Auditoría wrapper `_linea_sintetica_desde_total` ejecutada (TBD v4.15/v4.16 cerrado)

Sesión autoaccept overnight 14-15/05/2026. Reporte completo en `outputs/auditoria_linea_sintetica_20260514.md` (gitignored).

Resultado empírico:
- **26 activaciones totales en 4T25+1T26+2T26** (10× MENOS que la estimación de SPEC v4.15 "~37/40 líneas log → cientos por trimestre"). El conteo informal estaba contando doble: warning del primario + warning del fallback OCR de la misma factura.
- Distribución mecánica del auditor: 16 LEGÍTIMA-A, 5 SOSPECHOSA-1, 5 SOSPECHOSA-2.
- Tras triage humano (Jaime), de los 10 SOSPECHOSAs mecánicas:
  - 2 confirmados falsos positivos del fuzzy threshold 85 (DANI GUTIERREZ → BLANCO GUTIERREZ PILAR, SCM CERVEZA → ACEITES GARCIA)
  - 6 proveedores irrelevantes operacionalmente (GRUPO KUAI, LEVANTINA, PANADERIA JR, DROPBOX, PIERRE COMUNICACION, otros) — archivados sin TBD
  - 2 accionables reales: Café Dromedario (alta MAESTRO, ya en backlog) y Amazon Business EU (9 facturas/3 trimestres, candidato a extractor dedicado por volumen)

**Tasa de yield real: 2/26 = 7,7%** — la auditoría confirma que el wrapper NO es fuente sistemática de pérdida de datos. Mismo patrón que sesiones previas (cluster B BM 33→6 reales, merge bugs 1/627=0,16%, skip_patterns 1/116=0,86%).

### Calibración del auditor — threshold fuzzy 85 produce falsos positivos

El auditor usó fuzzy=85 para cross-match filename↔MAESTRO. Esto produjo 2 falsos positivos en 5 sospechosos (40%) por apellidos comunes o prefijos compartidos. El orquestador de Parseo es más estricto y rechazó correctamente esos casos. NO es bug del orquestador.

Decisión: NO ajustar threshold del auditor (el script es ad-hoc, no se va a reutilizar literalmente). Documentar como limitación conocida del barrido de auditoría: thresholds permisivos sobre-generan candidatos, requieren triage humano post-clasificación.

### Nueva lección operativa (4ª) — filtro de importancia operacional

Tras lecciones v4.15 #2 (valor de hipótesis invalidadas) y v4.16 #1 (validación cuantitativa de hipótesis de impacto), esta sesión añade la 4ª lección del eje "no convertir datos en trabajo automáticamente":

**Filtro de importancia operacional**. Cada hallazgo de una auditoría debe pasar dos filtros antes de generar TBD: (1) ¿es estadísticamente significativo? (validación cuantitativa); (2) ¿es operacionalmente relevante? (proveedor recurrente o importe material). Sin el segundo filtro, las auditorías de barrido inflan el backlog con casos que nunca volverán a aparecer. **Protocolo**: tras clasificar mecánicamente, el responsable del negocio (no Claude) marca cada cluster como ACCIONABLE / ARCHIVAR. Solo ACCIONABLE se eleva a TBD del SPEC.

Ilustración cuantitativa de esta sesión: clasificador mecánico produjo 10 sospechosos. Filtro de importancia humano dejó 2. Sin filtro, habría generado ~8 TBDs nuevos sobre proveedores irrelevantes.

### TBDs nuevos (filtrados por importancia operacional)

- **Café Dromedario — alta MAESTRO**: pendiente desde antes de esta auditoría. Esta sesión confirma que aparece (2 facturas) y refuerza la prioridad. Acción: Jaime crea entrada en MAESTRO con CIF + IBAN + alias.

- **Amazon Business EU SARL — evaluar extractor dedicado**: 9 facturas en 3 trimestres = volumen recurrente (~3/trimestre, ~60€/factura, 560€ total). Coste-beneficio: extractor evita fallback sintético para proveedor habitual. Prioridad MEDIA-BAJA (no fiscal urgente, pero ahorra warning recurrente). Sesión propia cuando convenga.

### Hallazgos NO accionables (archivados, sin TBD)

Filtro de importancia operacional aplicado por Jaime tras revisar el reporte:
- GRUPO KUAI (363€, 2 fact), DISTRIBUCION LEVANTINA ALIMENTOS (259€, 1 fact), PANADERIA JR (272€, 1 fact), DROPBOX (19€), PIERRE COMUNICACION (18€), AIMANE HAMMOUCH (2 fact aisladas), MASSAXUXES SCP (1 fact), FIVE GALAXIES (2 fact).
- Razón: no son proveedores recurrentes ni operacionalmente relevantes para Tasca/Comestibles. El wrapper sintético hace su trabajo correctamente para estos casos (LEGÍTIMA-A) o el orquestador rechaza con razón (falsos positivos del auditor).
- Si en futuras auditorías alguno de estos reaparece con frecuencia creciente, reabrir entonces.

### TBDs heredados que siguen vivos

- **Cluster B item 3/3: JIMELUZ** — en curso, ver PR Parseo #19. Cifra histórica "15/21 descuadres" obsoleta: validado 14/05/2026 sobre corpus 2T24 (9 samples) con extractor v3 (16/03/2026), 2/9 descuadres reales por cuadro fiscal con tramos parciales/bonificaciones + 1/9 caso ortogonal de escalera OCR (2200, fuera de cluster B, TBD propio).
- Invocaciones inocuas del fallback OCR (v4.15, 47/627, baja prio).
- Refactor M3 en `_merge_resultados` (v4.15, decisión abierta).
- Regex captura LA CUCHARA `[A-Z0-9\s%]` sin puntos (v4.16, MEDIA).
- Estandarización nominal `ignorar:` → `skip_patterns:` (v4.16, BAJA).
- Barrido pdfplumber multi-página en 12 extractores (v4.13).
- Protocolo versionado Drive Maestro/ (v4.13).
- Dedup aliases `MAESTRO_PROVEEDORES.xlsx` (v4.11).
- Bug identificador proveedor (~5% filename como nombre) (v4.11).
- Cluster C (retenciones IRPF autónomos) (v4.11).
- Issue #5 Parseo (cp1252) (v4.11).

### Errata 14/05/2026 (post-cierre v4.17)

Tras el cierre de v4.17 se detectaron 3 hallazgos derivados que corrigen y matizan la auditoría del wrapper `_linea_sintetica`:

1. **Café Dromedario NO necesitaba alta MAESTRO**. CAFES POZO SA ya está en MAESTRO (confirmado por Jaime) y `cafes_pozo.py` incluye `'CAFE DROMEDARIO'` y `'CAFÉ DROMEDARIO'` como aliases en su decorador `@registrar`. El caso debería haberse clasificado como SOSPECHOSA-1, no SOSPECHOSA-2. El problema real está en el identificador del orquestador, que no seleccionó `cafes_pozo.py` para el filename no canónico `REVISAR_2T26_0506__administracion_cafedromedario_com_.pdf` (formato email-derivado con prefijo REVISAR, no nomenclatura canónica `####_TRIM_MMDD_PROV_MODO`).

   TBD reformulado: investigar bug del identificador para filenames email-derivados o no canónicos. Sesión propia, prioridad MEDIA (proveedor recurrente real).

2. **Punto ciego del auditor overnight**. La lógica del clasificador fue filename → MAESTRO → alias_a_extractor en cadena. Si el match MAESTRO falla, nunca consulta directamente alias_a_extractor. Esto produce **falsos negativos**: proveedores con extractor existente pero filename no parseable se clasifican como SOSPECHOSA-2 (sin extractor) cuando deberían ser SOSPECHOSA-1.

   Re-cruzar ejecutado 14/05/2026 (`Parseo/_recheck_sosps2.py`, gitignored): de las 5 SOSPECHOSAs-2, **0 son falsos negativos puros del encadenamiento MAESTRO→alias** (ningún `prov_raw` extraído matchea `alias_a_extractor` con cutoff 85) y **4 son CONFIRMADO_SIN_EXTRACTOR** mecánicamente (PANADERIA JR, DROPBOX, y los 2 de Café Dromedario). 1 caso (PIERRE COMUNICACION) matchea borderline con `ecoms` a score 72 — falso positivo espurio del fuzzy, descartado.

   Matiz importante sobre Café Dromedario: las 2 facturas SÍ son falsos negativos en sentido amplio porque `cafes_pozo.py` registra `'CAFE DROMEDARIO'` como alias, pero el bug NO está en el encadenamiento MAESTRO→alias_a_extractor — está aguas arriba: `extraer_prov_de_filename` elimina el email entre paréntesis (`(administracion@cafedromedario.com)`) que es la única pista del proveedor, dejando un `prov_raw` inútil (`'2T26 0506'`, `'AR 1T26 0220'`). El TBD del punto 1 captura exactamente este caso — no es bug genérico del orquestador.

3. **Bug pre-existente en `cafes_pozo.py` — discrepancia de CIF**:
   - Extractor (docstring línea 5 + atributo línea ~19): `A28136189` ("del registro mercantil")
   - Footer del PDF emitido por Cafés Pozo SA: `ESA28917250`

   El CIF del footer es el oficial. El extractor propaga un CIF incorrecto al output de Parseo cuando procesa facturas Cafés Pozo / Dromedario. Bug independiente del problema actual.

   TBD nuevo: verificar CIF correcto contra entrada MAESTRO de CAFES POZO SA, fixear `cafes_pozo.py`. Sesión propia, prioridad BAJA (cosmético pero útil para integridad del output fiscal).

Estos 3 puntos NO requieren bump de versión — son matices y bugs adyacentes del trabajo cerrado en v4.17, formalizables en el próximo bump.

---

## CHANGELOG v4.16 — 14/05/2026 (Auditoría canónica #7 cerrada + fix LA CUCHARA VALE/TOTAL substring)

### Auditoría barrida skip_patterns — canónica #7 v4.14 ejecutada

Sesión semi-autoaccept (10-15 min real, no overnight largo) que barrió todos los extractores de Parseo cruzando listas de "ignorar" con `DiccionarioProveedoresCategoria.xlsx`. Reporte completo en `outputs/auditoria_skip_patterns_20260513.md` (gitignored, no se duplica aquí).

Resultado empírico:
- **116 extractores auditados** (cifra del reporte, NO ~80 como estimaba informalmente en sesiones previas).
- **1 sola colisión ALTA detectada**: `la_cuchara.py` con filtro `'VALE'` substring matcheando 4 productos del catálogo LA CUCHARA (`SSA VALENTINA E.AMARILLA/E.NEGRA 370ML`).
- 5 extractores adicionales con nomenclatura no estándar (variable `ignorar`/`IGNORAR`/`IGNORAR_DESC` en lugar de `skip_patterns`) sin casos reales: `ceres`, `ecoms`, `la_alacena`, `la_lleidiria`, `la_cuchara`.
- 0 colisiones MEDIA o BAJA con impacto detectable.

**Tasa de incidencia: 1/116 = 0,86%** — confirma cuantitativamente que el patrón de canónica #7 existe pero NO es sistemático en producción. Refuerza la lección 2 v4.15 sobre invalidar hipótesis con datos.

### Fix LA CUCHARA — VALE/TOTAL como match exacto (PR #17, repo separado)

| # | Cambio | Commit |
|---|---|---|
| 1 | `ignorar_exacto = {'TOTAL', 'VALE'}` separado de `ignorar_substring = ['IVA 10']` (set vs list tipa la intención) | `47a9e8e` |
| 1 | 4 tests sintéticos en `tests/extractores/test_la_cuchara.py` (regresión VALENTINA + 3 cases positivos: VALE exacto, TOTAL exacto, IVA 10 substring) | `47a9e8e` |
| 1 | VERSION Parseo 5.23 → 5.24 | `47a9e8e` |

Mergeado vía PR #17 (merge SHA `868dcf7`). CI verde 45s. Suite Parseo: **68 passed + 1 skipped**, 0 regresiones. LA CUCHARA es OCR primario; tests sobre texto post-OCR sintético, sin dependencia de tesseract en CI.

### Nueva decisión canónica #8 — exact-match por defecto en filtros de cabecera

El fix LA CUCHARA cristaliza un principio generalizable: **filtros de "ignorar" para cabeceras fiscales son exact-match por defecto, substring-match solo cuando el contexto fuerza inequívocamente.**

Razonamiento: las cabeceras fiscales (`TOTAL`, `VALE`, `BASE`, `IVA`, `CIF`, `NIF`) aparecen como palabras aisladas en líneas que NO son productos. Los nombres de productos legítimos pueden contener esas mismas palabras como substring (`VALENTINA` contiene `VALE`; `Colgate Total` contiene `TOTAL`). El default correcto es match exacto.

Substring solo se justifica cuando el contexto fuerza unicidad — ej. `IVA 10` nunca aparece como descripción de producto porque siempre va con el porcentaje pegado (`IVA 10%`).

**Aplicación inmediata**: cluster B item 3/3 JIMELUZ. Cuando se aborde, auditar todos sus filtros de "ignorar" contra este principio antes de tocar lógica de extracción.

### Hallazgo secundario — regex de captura `[A-Z0-9\s%]` sin puntos

Durante implementación del fix, al ajustar el fixture sintético para que el regex de captura del extractor lo acepte, se descubrió que `la_cuchara.py` usa `[A-Z0-9\s%]` para capturar la descripción del producto. Esto **NO permite puntos**. Pero los productos del catálogo tienen punto (`SSA VALENTINA E.AMARILLA 370ML`).

LA CUCHARA es OCR primario. Si el OCR de tesseract conserva el punto, el regex rechaza la descripción y la línea queda truncada o perdida. Si el OCR borra el punto (lo que hizo en los 2 samples inspeccionados durante la sesión), no hay problema. **El bug es condicional al comportamiento del OCR, no determinista**.

Sin PDFs reales donde el OCR conserve el punto, no podemos validar el impacto. TBD prioridad **MEDIA** (no nominal) — más interesante que un refactor cosmético pero no fiscal urgente.

### Lecciones operativas formalizadas (3)

1. **Validación cuantitativa de hipótesis de impacto**. La auditoría canónica #7 nació de una predicción razonable: si BM tenía el problema, otros extractores BM-like probablemente también. El dato empírico (1/116 = 0,86%) invalidó la predicción de impacto sistemático. Esto refuerza la lección 2 v4.15: hipótesis razonables pueden necesitar invalidación empírica, no solo extrapolación lógica. **Protocolo**: cuando una sesión cierra un cluster con N items afectados, antes de extrapolar a "muchos más casos" en otros extractores, auditar barriendo es la inversión correcta (esta sesión: ~15 min reales, cierra debate y produce el fix prioritario en el mismo flujo).

2. **Patrón "fix durante test reveals bug adyacente"**. Al construir el fixture sintético para `test_la_cuchara` se reveló el regex de captura `[A-Z0-9\s%]` sin puntos — bug adyacente no relacionado al fix original. Esto es valor inesperado del trabajo de tests: forzar sintetizar input válido revela suposiciones implícitas del extractor que no se manifestaban en el camino feliz. **Protocolo**: documentar como TBD cualquier hallazgo de este tipo, aunque sea ortogonal al fix en curso. NO ampliar el alcance del PR actual — bug adyacente va a sesión propia. El test debe pasar con input compatible con la implementación actual; el TBD captura la limitación descubierta.

3. **`set` vs `list` para filtros: tipar la intención**. El fix usó `ignorar_exacto = {'TOTAL', 'VALE'}` (set) y `ignorar_substring = ['IVA 10']` (list). El tipo de colección expresa la semántica de búsqueda: set para exact-match (O(1) y semántica clara), list para iteración con `in` substring (orden potencialmente relevante). Mejor que dos listas con comentarios explicando cuál es cuál. **Protocolo**: para filtros con semánticas mixtas, usar tipos de colección distintos como documentación auto-explicativa. Aplicar al cluster B item 3/3 JIMELUZ y a cualquier refactor futuro de extractores con filtros.

### TBDs nuevos

- **Regex de captura LA CUCHARA `[A-Z0-9\s%]` sin puntos** (prioridad **MEDIA**): bug condicional al comportamiento del OCR de tesseract. Requiere PDF real con punto conservado para validar el impacto. Sesión propia. La próxima ejecución de Parseo sobre una factura LA CUCHARA puede dar la primera señal — si el log muestra líneas truncadas o líneas con base=0, sospechar este caso.

- **Estandarización nominal `ignorar:` → `skip_patterns:`** en los 5 extractores afectados (`ceres`, `ecoms`, `la_alacena`, `la_lleidiria`, `la_cuchara` aunque este ya está fixeado): prioridad **BAJA**, sin casos reales detectados. Conveniencia para que futuras auditorías canónica #7 se puedan correr con el primer regex (la versión inicial del script auditor de esta sesión perdió 5 extractores por buscar solo `skip_patterns`). Se amplió para incluir nombres alternativos, pero estandarizar a un solo nombre es más robusto.

### TBDs heredados que siguen vivos

- **Cluster B item 3/3: JIMELUZ** (15/21 descuadres, OCR primario). Único item pendiente del cluster B. La decisión canónica #8 de esta sesión aplica directamente a sus filtros de "ignorar"; auditar antes de tocar lógica de extracción.
- Auditoría wrapper `_linea_sintetica_desde_total` en `generico.py` (v4.15, prioridad media-alta, ~37 activaciones visibles en 40 líneas de log).
- Invocaciones inocuas del fallback OCR (v4.15, 47/627, baja prio).
- Refactor M3 en `_merge_resultados` (v4.15, decisión abierta).
- Barrido pdfplumber multi-página en 12 extractores (v4.13).
- Protocolo versionado `DiccionarioProveedoresCategoria.xlsx` (v4.13).
- Dedup aliases en `MAESTRO_PROVEEDORES.xlsx` (v4.11).
- Bug identificador proveedor (~5% filename como nombre) (v4.11).
- Cluster C (retenciones IRPF autónomos) (v4.11).
- Issue #5 Parseo (cp1252) reabierto — sigue manifestándose (v4.11).

---

## CHANGELOG v4.15 — 14/05/2026 (Auditoría merge primario↔fallback OCR + resolución errata v4.14)

### Resolución errata v4.14

La errata de 13/05/2026 (registrada al final del bloque CHANGELOG v4.14, sin bump de versión) documentaba una atribución incorrecta del mecanismo que produjo el descuadre del fixture 1215 (test aislado SUMA=0,84 Δ=+6,05 vs `main.py` dry-run Total=9,99 Δ=−3,10, signos opuestos). Esta sesión audita el mecanismo real (`_merge_resultados` en `Parseo/main.py:1582-1669`) y añade observabilidad permanente vía WARNING `[MERGE_FALLBACK]`. Mergeado en PR #16 (merge SHA `8a3538a`) en repo Parseo.

### Auditoría empírica del merge primario↔fallback OCR (PR #16, repo separado)

| # | Cambio | Commit |
|---|---|---|
| 1 | Refactor `_necesita_fallback` a `Optional[str]` devolviendo etiqueta C1/C2/C3/C4 (o None) — truthy semantics conservadas | `2b67231` |
| 1 | Instrumentación `_merge_resultados` con WARNING permanente `[MERGE_FALLBACK]` (formato grep-friendly: archivo, extractor, criterio_entrada, criterio_merge, total, total_origen, swing, swing_ratio, desc_prim, desc_fall, n_prim, n_fall) | `2b67231` |
| 1 | 5 tests caplog en `tests/test_merge_resultados.py` (M1, M2 sin mejora cuadre, M3 dead code, no_warn primario OK, swing_ratio para ticket pequeño) | `2b67231` |
| 1 | VERSION 5.22 → 5.23 | `2b67231` |

Métricas empíricas (4T25 + 1T26 + 2T26, código post-cluster-BM, branch `fix/main-merge-resultados-observable`):

| Trimestre | n_facturas | n_invocaciones_merge | n_activaciones | C1 | C2 | C3 | C4 | M1 | M2 | M3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4T25 | 309 | 31 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1T26 | 227 | 9 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| 2T26 | 91 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **627** | **48** | **1** | **0** | **0** | **1** | **0** | **1** | **0** | **0** |

- **48 invocaciones del merge (7,7%)** — entran al fallback OCR pero solo **1 activación real** sustituye líneas.
- **1 caso (LEVANTINA 1T26 1061, generico.py)**: C3+M1, swing 156€ (60%), total origen primario → clasificada **LEGÍTIMA por construcción**.
- **47 merges donde se mantuvo el primario** (ruido informativo, coste computacional sin impacto en datos).
- **0 SOSPECHOSAS, 0 INDETERMINADAS, 0 BASURA_COHERENTE** detectadas.

Suite Parseo: **64 passed + 1 skipped**, 0 regresiones. CI verde (PR #16).

### Hallazgo principal — hipótesis original invalidada empíricamente

La sesión nació del TBD reformulado de la errata v4.14: *"el wrapper de merge enmascara bugs upstream sistemáticamente"*. El dato empírico es **0,16% de activación post-cluster-BM con un único caso clasificado como LEGÍTIMA**. La hipótesis queda **invalidada empíricamente** — el merge NO es fuente crónica de problemas en producción actual.

Esto es hallazgo positivo, no neutro: reduce el espacio de causas posibles para descuadres futuros y orienta el trabajo de extractores hacia las causas reales (skip_patterns con `\b` sin anclaje, decisión canónica #7 v4.14).

### Hallazgo M2 — el caso paradigmático 1215 fue elegido por cantidad, no calidad

Validación sub-B contra `517cf1f` (pre-cluster-BM) con `bm.py` y `settings.py` rolled back y la misma instrumentación de `main.py` (que no cambió entre 517cf1f y HEAD) reveló que el 1215 disparaba **C3+M2** con **swing NEGATIVO −3,86€** (descuadre primario 6,05€, descuadre fallback 9,91€, swing/total 56%). El fallback descuadró **PEOR** que el primario, pero ganó porque tenía 3 líneas vs 2 del primario.

Esto confirma cuantitativamente la observación del Paso A.1(b): **M2 es heurística cuantitativa débil** (mide cantidad de líneas, no calidad del cuadre). La causa raíz del descuadre del 1215 NO fue el merge — fue el typo OCR `TICKEIT` + skip_pattern `\bTICKET\b` sin anclaje (decisión canónica #7 v4.14, refuerzo de esta sesión). Pero el merge contribuyó al daño al elegir el resultado peor cuando tuvo que elegir.

### Hallazgo M3 — código muerto bajo implementación actual

`_calcular_descuadre` (`main.py:1565-1579`) devuelve `float('inf')` cuando `lineas` está vacía. Por tanto, si `primario.lineas == []`:
- `descuadre_primario = inf`
- `descuadre_fallback = finito` (si `fallback.lineas` no vacío)
- M1 (`desc_fall < desc_prim - 0.50`) → `finito < inf - 0.50 = True` → **M1 siempre dispara antes que M3**

M3 (`not primario.lineas AND fallback.lineas`) solo sería alcanzable si ambos descuadres fueran `inf`, escenario que no debería ocurrir en práctica si llegamos al merge. Documentado en `test_merge_M3_es_codigo_muerto_con_calcular_descuadre_actual`.

Decisión abierta (TBD): eliminar M3 (es código muerto) o reparar `_calcular_descuadre` para que devuelva valor finito (p.ej. el TOTAL como descuadre máximo cuando no hay líneas) y M3 sea alcanzable. Sesión futura.

### Lecciones operativas formalizadas (3)

1. **Distinguir observación verificada de hipótesis técnica en documentación maestra** (formalización de la lección candidata que motivó la errata v4.14). En SPEC, CHANGELOG y cualquier documento permanente, cada afirmación de mecanismo concreto debe ser empíricamente reproducible o etiquetarse explícitamente como hipótesis pendiente. La diferencia entre *"hay un wrapper en main.py"* (hipótesis no verificada que terminó siendo incorrecta) y *"el mecanismo real es `_merge_resultados` en `main.py:1582-1669`"* (observación verificada con `grep`+lectura) no es matiz menor — son reproducibilidades cualitativamente distintas. Protocolo: cuando atribuyas un comportamiento a una función concreta, citar archivo + rango de líneas y haber leído ese rango. Si no se ha verificado, escribir *"hipótesis pendiente de verificar"* explícitamente.

2. **Una investigación con hipótesis a invalidar también es valor**. Esta sesión no encontró bugs en el merge porque no los hay (en código post-cluster-BM: 0,16% activación, 0 sospechosas). Esto NO es *"sesión sin resultado"* — es resultado positivo: la hipótesis original (*"merge enmascara bugs sistemáticamente"*) queda invalidada empíricamente, lo que permite redirigir el esfuerzo de futuras sesiones a las causas reales (skip_patterns, decisión canónica #7). Protocolo: documentar hipótesis invalidadas con datos en CHANGELOG, no enterrarlas — orientan el trabajo futuro y previenen reabrir investigaciones ya cerradas.

3. **Patrón "sub-validación contra baseline pre-fix"**. Cuando una auditoría se ejecuta sobre código post-fix (típico cuando el bug que motivó la sesión ya está resuelto), validar la instrumentación contra el código pre-fix sobre los casos conocidos para confirmar que habría captado el patrón histórico. En esta sesión: 5-10 minutos de rollback selectivo de `bm.py` + `settings.py` a `517cf1f` (manteniendo `main.py` con instrumentación) + dry-run sobre 1T26 → el caso 1215 reapareció con perfil C3+M2 swing −3,86€, confirmando que el WARNING habría capturado el patrón. Sin esta sub-validación, el commit *"el código actual funciona bien"* sería declaración sin prueba. Con ella, queda blindado: el código actual funciona bien **Y** el código antiguo se caracterizaba correctamente por la instrumentación. Aplicable a cualquier sesión de observabilidad o refactor con casos históricos conocidos.

### TBDs nuevos / refinados

- **Auditoría wrapper `_linea_sintetica_desde_total` en `extractores/generico.py`**: el OTRO mecanismo, el que SÍ emite `logger.warning` hoy (línea 300) y que originalmente atribuí mal al 1215 (errata v4.14). Conteo informal en 4T25: ~37 activaciones visibles en primeras 40 líneas del log stderr → posiblemente cientos por trimestre. El sub-caso LEVANTINA 1T26 1061 sugiere que el genérico puede leer totales incorrectos via este wrapper (primario 7,08€ vs fallback 259,20€, ambos sintéticos). Prioridad media-alta dado el volumen. Sesión propia.

- **Invocaciones inocuas del fallback OCR**: 47/627 facturas (7,5%) entran al merge pero mantienen el primario. Coste computacional (un OCR completo) sin impacto en datos. Posible refactor: evitar invocación cuando `_necesita_fallback` dispara por C4 (categorización débil) sin descuadre real. Sesión propia, baja prioridad.

- **Refactor M3 en `_merge_resultados`**: decisión abierta — eliminar M3 (es código muerto bajo implementación actual) o reparar `_calcular_descuadre` para que devuelva valor finito y M3 sea alcanzable. Test dedicado documenta el estado actual.

### TBDs heredados que siguen vivos

- **Cluster B item 3/3: JIMELUZ** (15/21 descuadres, OCR primario). Único item pendiente del cluster B. Comparte diagnóstico con esta sesión: si JIMELUZ tiene tickets retail con líneas informativas espurias, el merge NO lo desambigua (OCR es primario, no fallback). Decisión canónica #7 aplica directamente.
- Auditoría barrida `skip_patterns` con `\b` no anclados (decisión canónica #7 v4.14, refuerzo de esta sesión).
- Barrido pdfplumber multi-página en 12 extractores (v4.13).
- Protocolo versionado `DiccionarioProveedoresCategoria.xlsx` (v4.13).
- Dedup aliases en `MAESTRO_PROVEEDORES.xlsx` (v4.11).
- Bug identificador proveedor (~5% filename como nombre) (v4.11).
- Cluster C (retenciones IRPF autónomos) (v4.11).
- Issue #5 Parseo (cp1252) reabierto — sigue manifestándose en cada dry-run (v4.11).

---

## CHANGELOG v4.14 — 13/05/2026 (Cluster BM SUPERMERCADOS — TBD #1 v4.13 segundo item cluster B)

Aplicación del segundo item del cluster B abierto en v4.11 y refinado en v4.13: refactor del extractor BM SUPERMERCADOS (`Parseo/extractores/bm.py`) para resolver dos bugs coordinados que causaban descuadres sistemáticos en tickets con descuentos retail y productos con la palabra TOTAL en el nombre. Mergeado vía PR #15 (merge commit `e3b5dae`) en repo Parseo.

Reporte completo de la sesión: `outputs/cluster_b_bm_20260513.md` (no se duplica aquí).

### Cluster BM SUPERMERCADOS — 2 bugs coordinados (PR #15, repo separado)

| # | Bug | Commit | Severidad |
|---|---|---|---|
| A | `Oferta -X.XX` capturada como descuento real cuando es informativa (el IMPORTE de la línea de producto YA está descontado) → doble resta | `cfec5a3` | ALTO |
| B | Skip pattern `\bTOTAL\b` cazaba productos con TOTAL en marca (Colgate Total, Listerine Total). Producto perdido upstream → descuento posterior absorbido en línea anterior incorrecta, enmascarando el bug | `5b7c576` | MEDIO |
| — | VERSION bump 5.21 → 5.22 | `cc4714b` | chore |

Fixtures reales en `Parseo/tests/extractores/fixtures/bm/`: 7 PDFs (2 controles puros + 4 Bug A puro + 1 Bug A + Bug B combinados, 1T26). Tests parametrizados: **7/7 passed** al céntimo. Suite Parseo completa: **59 passed + 1 skipped**, 0 regresiones. CI verde (32s).

Validación empírica vía dry-run pre/post en baseline real:

| Trimestre | Facturas | BM PRE | BM POST | Otros PRE | Otros POST | Importe total |
|---|---:|---:|---:|---:|---:|---:|
| 4T25 | 309 | 1 | **0** | 20 | 20 | 79.681,55 € idéntico |
| 1T26 | 227 | 5 | **0** | 9 | 9 | 53.129,81 € idéntico |

Cero descuadres BM residuales en el horizonte 4T25+1T26 → el cluster cierra los bugs en los PDFs reprocesables. Histórico 1T25/3T25 (Kinema cerrado) no se reprocesa — la auditoría v4.11 reportaba 33 BM SUPERMERCADOS pero solo 6 viven en PDFs reprocesables.

### Refinamiento de lección v4.13 #1 — "Closes #N" peligro (tercera manifestación)

Variante más sutil que las dos anteriores. El commit 3 del cluster (`cc4714b`) deliberadamente NO usaba `Closes #14` para preservar control manual del cierre del issue. Pero el commit body incluía la cadena LITERAL `"(Closes #14 deliberadamente OMITIDO ..."` explicando que se omitía. GitHub auto-cerró el issue al merge porque parsea con regex sin entender contexto sintáctico ni semántico — vio la cadena `Closes #14` literal y disparó el cierre, ignorando la nota explicativa.

**Protocolo refinado**: NUNCA escribir la cadena `Closes #N` / `Fixes #N` / `Resolves #N` en ningún commit message del PR — ni siquiera negada, comentada, entre paréntesis o explicando que se omite. Si hay que mencionar el comportamiento de auto-cierre como nota, hacerlo fuera del commit body (en el cuerpo del PR o en comentario tras merge). Usar siempre `Refs #N` / `Tracks #N` / `Related to #N` para referenciar sin disparar.

### Refuerzo de lección v4.13 #5 — test aislado ≠ producción (manifestación cuantificada)

Segunda manifestación del gap test aislado vs dry-run, esta vez con datos numéricos concretos. Para fixture 1215 (Colgate TOTAL + Oferta) sobre baseline main pre-fix:

- `extraer_lineas()` invocado directo (test aislado): **SUMA = 0,84 €**, Δ = **+6,05 €** (parseo infravalora)
- `main.py` dry-run (pipeline completo):           **Total Parseo = 9,99 €**, Δ = **−3,10 €** (parseo sobrevalora)

Mismo PDF, mismo código fuente, **dos números completamente distintos con SIGNO OPUESTO**. Tras aplicar el fix, ambos caminos convergen a TOTAL=6,89 €, Δ=0.

**Diagnóstico**: hay un wrapper de fallback en `main.py` (test_generico.py muestra `test_fallback_sintetico_cuando_no_hay_lineas_pero_si_total` y `test_fallback_sintetico_no_se_activa_si_hay_lineas_legitimas`) que sintetiza líneas cuando `extraer_lineas` devuelve algo anómalo. A veces el fallback sobre-corrige. El fix en la raíz del extractor desactiva el wrapper para esos casos — eso es buena señal, indica que el extractor ya es correcto.

**Protocolo**: comparación dry-run pre/post **NO opcional** para PRs de extractor; los tests aislados NO sustituyen — pueden dar números distintos en **magnitud y signo** para el mismo PDF. El número del test crudo es solo un eslabón; el número de producción es el del orquestador.

### Lecciones operativas nuevas — dominio retail

1. **Tickets retail mezclan descuentos informativos y aplicables**. En BM:
   - `Oferta -X.XX` = informativa (el IMPORTE de la línea de producto YA está descontado). Ignorar.
   - `Promoción ...` y `Vales ...` = descuentos reales (IMPORTE de la línea es PVP). Aplicar.
   El parser debe distinguir **por keyword distintiva**, no por signo del importe (ambas son negativas). Validado contra `TICKET SIN AHORROS` / `AHORRO` de los 7 fixtures de 1T26. Esperable que aplique también a JIMELUZ si tiene tickets de supermercado.

2. **`skip_patterns` con `\b` sin anclaje cazan nombres de producto legítimos**. `r'\bTOTAL\b'`, pensado para descartar `TOTAL COMPRA (iva incl.) X.XX`, también se comía cualquier producto cuyo nombre contenía "TOTAL" (Colgate Total, Listerine Total, P.Total). Cuando un producto se descarta así, el siguiente descuento en el post-procesado de `lineas_filtradas[-1]` aterriza en el producto anterior, **enmascarando el bug como si fuera de otra naturaleza**. Protocolo: anclar `skip_patterns` a inicio de línea (`^\s*TOKEN\b`) o a contexto específico (`\bTOTAL COMPRA\b`) cuando la palabra es genérica.

### Decisión canónica añadida hoy

7. **Auditoría barrida obligatoria de `skip_patterns` con `\b` genéricos**: cuando un extractor define `skip_patterns` con tokens cortos sin anclaje (`\bFACTURA\b`, `\bproducto\b`, `\bgénero\b`, `\bpresente\b`, etc.), es alta probabilidad que algún producto del catálogo del proveedor matchee silenciosamente y se pierda. Al revisar un extractor: cada token de los `skip_patterns` se cruza contra el `DiccionarioProveedoresCategoria.xlsx` del proveedor (búsqueda case-insensitive por substring) y se inspecciona cualquier matching. Aplica a todos los extractores con `skip_patterns`, no solo BM.

### TBDs nuevos / refinados

- **Cluster B item 3/3**: **JIMELUZ** (15/21 descuadres, OCR primario). Único item pendiente del cluster B. Esperable que comparta patrones con DIA (saneamiento OCR) pero también con BM (descuentos retail si el proveedor tiene tickets de supermercado). Orden recomendado: tras este, cluster B queda íntegramente cerrado.
- **Auditoría wrapper `fallback_sintetico` en `Parseo/main.py`**: nuevo TBD nacido del refuerzo de lección v4.13 #5. Casos legítimos (Patrón A con líneas vacías + TOTAL claro) vs casos donde enmascara bugs upstream (como fixture 1215). Posible refinamiento: cuando se active el wrapper, logar WARNING con magnitud de la corrección sintética para detectar enmascaramientos. 1 sesión.
- **Auditoría barrida de `skip_patterns` con `\b` no anclados** en TODOS los extractores BM y similares (no solo bm.py). Buscar tokens genéricos (TOTAL, FACTURA, producto, género, etc.) que puedan coincidir con descripciones legítimas del catálogo del proveedor. Aplica decisión canónica #7 arriba. 1 sesión.
- **Re-procesar 4T25 para validación empírica del cluster ECOMS + BM combinados**: opcional, NO fiscal. Confirmaría empíricamente cuántos de los 23/31 (DIA) + 33 (BM SUPERMERCADOS) descuadres históricos se arreglan con los clusters cerrados.

### TBDs heredados que siguen vivos

- **Cluster B item 3/3: JIMELUZ** (renumerado: 1→DIA done v4.13, 2→BM done v4.14, 3→JIMELUZ pendiente). Único pendiente del cluster B.
- Barrido pdfplumber multi-página en 12 extractores (heredado de v4.13).
- Protocolo versionado `DiccionarioProveedoresCategoria.xlsx` (heredado de v4.13, refuerzo de v4.12).
- Dedup de aliases en `MAESTRO_PROVEEDORES.xlsx` (v4.11).
- Bug del identificador de proveedor (~5% filename como nombre) (v4.11).
- Cluster C (retenciones IRPF autónomos) — análisis separado (v4.11).
- Issue #5 Parseo (cp1252) reabierto, pendiente fix real (v4.11).

### Errata 14/05/2026 (pre-cierre v4.15)

La atribución del mecanismo en la sección "Refuerzo de lección v4.13 #5" es incorrecta. Texto original menciona "wrapper `fallback_sintetico` en `main.py` (visible en tests/test_generico.py)" como causante del descuadre del fixture 1215 en baseline pre-fix.

El mecanismo real es **`_merge_resultados` en `Parseo/main.py:1632-1659`**, que cuando el descuadre del fallback OCR (mismo extractor, tesseract en lugar de pdfplumber) es menor que el del primario con margen ≥0,50€, reemplaza las líneas del primario por las del fallback. En el caso 1215, el fallback OCR introdujo una línea espuria (`TICKEIT SIN AHORROS` — typo OCR de "TICKET SIN AHORROS" no cazada por el skip_pattern `\bTICKET\b` por el typo), lo que dio SUMA=9,99 vs SUMA primario 0,84. El merge eligió el fallback al cuadrar mejor.

`_linea_sintetica_desde_total` en `extractores/generico.py:276` (que sí emite `logger.warning` hoy) es un mecanismo distinto que NO se ejecuta para extractores dedicados como BM. Los tests `test_fallback_sintetico_*` en `tests/test_generico.py` verifican ese otro mecanismo, no el del 1215.

La lección sigue válida en su fenómeno observado (gap test-aislado vs dry-run con magnitud y signo distintos). Lo que es incorrecto es la atribución a un mecanismo concreto sin verificación empírica.

TBD anterior "Auditoría wrapper `fallback_sintetico` en `main.py`" se reformula como "Auditoría merge primario↔fallback OCR en `_merge_resultados` de `main.py`" (sesión 14/05/2026 en curso).

Lección operativa candidata para v4.15: **en documentación maestra, distinguir observación verificada de hipótesis técnica**. Cada afirmación de mecanismo concreto debe ser empíricamente reproducible o etiquetarse explícitamente como hipótesis pendiente.

---

## CHANGELOG v4.13 — 13/05/2026 (Cluster ECOMS/DIA — TBD #1 v4.11 segundo extractor)

Aplicación del segundo extractor del cluster B abierto en v4.11: refactor del extractor ECOMS/DIA para resolver el 74% de descuadres históricos (23/31 facturas DIA descuadradas en el histórico). Mergeado vía PR #13 (merge commit `517cf1f`) en repo Parseo.

### Cluster ECOMS/DIA — 6 bugs coordinados (PR #13, repo separado)

| # | Bug | Commit | Severidad |
|---|---|---|---|
| 1 | `procesar()` solo leía `pdf.pages[0]` → TOTAL formato canje a veces None (cuando la ruta de `procesar()` se activaba; existe ruta secundaria en `main.py` que ya leía multi-página) | `eba7d4d` | CRÍTICO |
| 2 | Regex Formato 2 (OCR) intolerante a ruido tipográfico (`?`, `;`, `*`, etc.) | `f7d9fe9` | ALTO |
| 3 | Formato 2 no manejaba descripción separada del importe en líneas distintas | `f0a820a` | ALTO |
| 4 | Regex de descripción no aceptaba comas → `1,5 LT` se perdía | `f7d9fe9` (inline) | ALTO |
| 5 | Patrones de TOTAL demasiado estrictos para OCR roto | `41d5a4e` | CRÍTICO |
| 6 | Fallback cuadro fiscal demasiado estricto + sin cross-check | `25d6d05` | MEDIO |
| — | VERSION bump 5.20 → 5.21 | `3da3d26` | chore |
| — | Skip CI para tests OCR-dependientes (tesseract ausente en runner) | `78a0c6c` | fix tests |

Fixtures reales en `Parseo/tests/extractores/fixtures/dia/`: 4 PDFs (1 canje 2T26 + 3 OCR del 4T25 cubriendo IVA único 4%/10% y IVA mixto + sub-variantes del OCR). 18 tests parametrizados: **17 passed + 1 skipped intencional** (ref OCR-rota en 4204) en local con tesseract. Suite Parseo completa: **52 passed**, 0 regresiones. Dry-run 2T26 sin diferencia (DIA 2T26_0420 TOTAL=4,68€ idéntico antes/después).

### Refinamiento de la decisión canónica "body-first para IVA mixto"

La decisión canónica #4 (v4.11) — *agrupar por tasa desde body, footer solo como cross-check* — se extiende a **tickets OCR**, no solo a facturas PDF limpias. Para tickets DIA, donde el OCR destruye descripciones y rompe regex aunque el contenido sea recuperable, se introduce un patrón nuevo:

**`CORRECCIONES_OCR_DIA`** — diccionario interno de pares `(keywords_obligatorias, nombre_canónico)`. Cuando TODAS las keywords aparecen como substring en una línea (case-insensitive), la descripción se sustituye por el nombre limpio. El importe e IVA se extraen como siempre por las regex normales (tras saneamiento OCR genérico).

Reglas duras del diccionario:
- Las keywords deben ser substring distintivo (poco probable que matchee otra línea).
- El `nombre_canónico` debe coincidir **exacto** con la entrada del `DiccionarioProveedoresCategoria.xlsx` para que el lookup downstream funcione.
- NO inventar entradas: solo tras confirmación manual del usuario sobre identidad del producto + verificación de presencia en el diccionario externo con categoría correcta.
- Orden de aplicación: saneamiento OCR PRIMERO, correcciones después (las keywords son substring y sobreviven al saneamiento; el saneamiento sí desbloquea matches al normalizar separadores).

Entradas iniciales aplicadas:
- `JABON ALMEND MI IMAQ` (keywords `ALMCND + IMAQ`) — fila añadida hoy al diccionario externo en Drive (fila 1347), categoría LIMPIEZA, IVA 21.
- `AGUA BEZOYA 1.5 LT` (keywords `BEZOY + 7182`) — ya existía con formato `1.5 LT` (PUNTO, no coma), categoría GASTOS NO PERTENECIENTES A TASCA BAREA, IVA 10.

### Lecciones operativas formalizadas (5)

1. **`closes #N` peligro reconfirmado** (segunda manifestación tras Issue #5 Parseo). Esta vez el auto-cierre fue correcto, pero el patrón "no se puede postear comentario al cerrar si ya está cerrado" se reprodujo. Protocolo: tras merge con `Closes #N` automático, postear comentario aclaratorio aparte con `gh issue comment N --body "..."` como paso separado.
2. **Orden saneamiento → correcciones (contraintuitivo)**: cuando se combina diccionario de keywords con saneamiento regex, aplicar saneamiento PRIMERO. Las keywords son substring y sobreviven al saneamiento; el saneamiento sí desbloquea matches al normalizar separadores (`0 7182` → `0,7182` hace que la keyword `7182` sea encontrable dentro del decimal). El reflejo contrario (correcciones primero por "preservar texto original") es incorrecto.
3. **Drift CI vs local por dependencias de runtime**: tesseract/poppler disponibles en local pero no en runner de CI causó 12 tests rojos. Política: cualquier test que dependa de runtime externo (OCR, fuentes del sistema, sockets, GPU, binarios opcionales) DEBE llevar `pytest.mark.skipif` condicional. No asumir paridad de entornos entre dev y CI.
4. **Drift Drive↔repo (segunda ocurrencia, refuerzo)**: `DiccionarioProveedoresCategoria.xlsx` modificado dos sesiones consecutivas desde código sin control de versiones. Hay backups locales datados, pero el Drive no es git. Item de backlog: protocolo de versionado del diccionario (snapshot diario al repo `gestion-facturas/datos/backups/`).
5. **Tests unitarios verdes no prueban impacto en producción** (formulación generalizada): el commit 1 del cluster describía un bug que los tests parametrizados aislados validaban, pero el dry-run pre/post NO mostraba diferencia (DIA 2T26_0420 TOTAL=4,68€ idéntico antes/después). Existe ruta secundaria en `main.py` que ya cubría el caso en producción. El fix sigue siendo correcto, pero el alcance real es menor del descrito. **Protocolo**: SIEMPRE comparar dry-run pre/post como prueba de impacto real, no solo tests aislados, antes de afirmar magnitud del bug en commit messages o reports.

### Decisión canónica #6 — Diccionario externo + repositorio interno desacoplados

Cuando un extractor necesita un mapeo de keywords→nombre_canónico (caso `CORRECCIONES_OCR_DIA`), ese mapeo vive en el **código** del extractor (visible en code review). La asignación de **categoría** vive en el **`DiccionarioProveedoresCategoria.xlsx`** (visible en negocio). Ambos deben mantenerse sincronizados manualmente: el nombre canónico del código debe matchear EXACTO el del diccionario externo, o el lookup downstream falla silenciosamente.

### TBDs nuevos / refinados

- **Cluster B parcialmente cerrado**: DIA done (PR #13). Pendientes BM SUPERMERCADOS (33/77 descuadres, mayor volumen absoluto) y JIMELUZ (15/21 descuadres, usa OCR primario). Orden recomendado: BM primero por volumen, JIMELUZ último por complejidad OCR (validar si el patrón body-first aplica con texto OCR pre-existente).
- **Auditoría barrida del bug "solo pág 0"**: 12 extractores de Parseo abren PDF con `with pdfplumber.open(...)` propio y podrían replicar el bug #1 de ECOMS: `alcampo`, `fabeiro`, `garda`, `ceres`, `arganza`, `casa_del_duque`, `celonis_make`, `embutidos_ferriol`, `fernando_moro`, `grupo_disber`, `angel_borja`, `abbati`. 1 sesión de barrido. Decisión por extractor sobre si reprocesar histórico — solo necesario para los que atiendan facturas multi-página.
- **Protocolo versionado `DiccionarioProveedoresCategoria.xlsx`**: snapshot diario al repo o detección de drift. Segunda manifestación del problema (sesión 13/05/2026 fila 1347 añadida).
- **Re-procesar 4T25 para validación empírica del cluster ECOMS**: opcional, NO fiscal (Kinema ya cerró), solo auditoría interna. Confirmaría cuántos de los 23/31 descuadres DIA históricos se arreglan empíricamente.

### TBDs heredados que siguen vivos

- Dedup de aliases en `MAESTRO_PROVEEDORES.xlsx` (v4.11).
- Bug del identificador de proveedor (~5% filename como nombre) (v4.11).
- Cluster C (retenciones IRPF autónomos) — análisis separado (v4.11).
- Issue #5 Parseo (cp1252) reabierto, pendiente fix real (no la versión) (v4.11).

---

## CHANGELOG v4.12 — 12/05/2026 (Parseo PANRUJE fix — IVA mixto body-first)

Aplicación del primero de los TBD abiertos en v4.11: refactor del extractor PANRUJE para resolver el descuadre sistemático en 2T26.

### Parseo `extractores/panruje.py` refactor (commit `3053eda`, repo separado)

**Bug resuelto.** Descuadre 68,64€ en FT A26 58 (22/04/2026): la fila del IVA 4% se omite en el cuadro fiscal del PDF cuando la plantilla 2T26 introdujo columnas R.Equ. (sub-variante C2). El extractor v5.20 leía el footer como fuente única → al perderse la fila 4%, el TOTAL extraído cuadraba solo con el 21% (24,56€ + portes), perdiendo los 68,64€ de las rosquillas.

**Refactor aplicado** (5 cambios coordinados):
1. Nueva `RE_LINEA_BODY_CON_IVA` captura IVA explícito por línea desde el body.
2. `_extraer_lineas_body()` parsea body sin depender del footer.
3. `extraer_lineas()` agrupa por IVA y devuelve una línea por tasa (consumido por el orquestador downstream que consolida a 1 línea por factura — política "una línea por coste, no por IVA").
4. `extraer_total()` calcula desde body como fuente de verdad (footer solo cross-check con `TOLERANCIA_CUADRE=0.05€`).
5. `_extraer_total_pdf()` refactorizado: máximo de candidatos (cubre Patrón A footer 5-números, Patrón B/C TOTAL aislado, Patrón C2 roto).

Fallback a `_extraer_lineas_legacy()` preserva 100% el comportamiento Patrón A (3T25-4T25, IVA único 4% o 10%).

Tests `tests/extractores/test_panruje.py` (nuevo, 6 tests parametrizados + 2 adicionales) con 4 fixtures reales:
- FT 15 (30/01/2025, Patrón A IVA 10%): 48,16€ ✓
- FT 206 (29/12/2025, Patrón A IVA 4%): 92,85€ ✓
- FT A26 49 (08/04/2026, Patrón C1, 2 albaranes): 178,63€ ✓
- FT A26 58 (22/04/2026, Patrón C2 footer roto): 93,20€ ✓ — bug original resuelto

Suite Parseo: **29 → 35 passed**, 0 regresiones. CI verde.

Validación dry-run 2T26 (90 PDFs): **73 → 76 OK (+3)**. Las 3 PANRUJE 2T26 ahora cuadran:
- FT-A26-49 (0408): 178,63€
- FT-A26-58 (0422): 93,20€ — antes descuadraba 68,64€
- FT-A26-69 (0507): 93,20€ — factura nueva (no estaba en diagnóstico 11/05)

### Decisión canónica añadida hoy

5. **Una línea por factura en COMPRAS, no por tasa de IVA**: el orquestador downstream consolida las N líneas que devuelve el extractor (una por IVA) en una sola fila en la hoja `Lineas` con TOTAL real + IVA del producto principal + BASE = TOTAL/(1+IVA/100). Razón: el Excel COMPRAS se usa para **conocer el coste**, no para llevar el registro de IVA detallado (esa labor recae en Kinema/Modelo 303 por otro lado). Trade-off conocido: la BASE escrita asume IVA único (89,62€ en FT-A26-58 vs 86,30€ suma real) — algebraicamente coherente con la fila (BASE × IVA = TOTAL) aunque no refleja la mezcla real. Aceptable porque la BASE de COMPRAS no alimenta declaraciones fiscales.

### TBD cerrados

1. **Scope del refactor IVA mixto** (v4.11 TBD #1): cerrado con **fix quirúrgico en `panruje.py`** (no helper compartido ni refactor en `ExtractorBase`). Decisión basada en evidencia empírica del Excel `auditoria_iva_mixto_20260511_1813.xlsx`: la mayoría de los 22 proveedores en NIVEL ALTO son tickets de supermercado (cluster B, patrón distinto a PANRUJE — multi-IVA real, no error de extractor) o autónomos con retenciones IRPF (cluster C — sin relación con IVA mixto). Solo PANRUJE encajaba en el patrón "extractor mal calibrado para IVA mixto". El refactor de `ExtractorBase` queda como deuda para cuando aparezca el segundo proveedor con el mismo patrón.

### TBD que siguen vivos (heredados de v4.11)

2. Dedup de aliases en MAESTRO_PROVEEDORES.
3. Bug del identificador de proveedor (~5% filename como nombre).
4. Cluster B (tickets supermercado) y Cluster C (retenciones IRPF) — análisis separado.
5. Issue #5 Parseo (cp1252) reabierto, pendiente.

---

## CHANGELOG v4.11 — 11/05/2026 (Parseo VERSION única + auditoría IVA mixto)

Sesión doble: unificación de la fuente única para `VERSION` en el repo Parseo y nueva herramienta de auditoría sobre proveedores candidatos al refactor de IVA mixto, motivado por el descuadre PANRUJE 2T26.

### Parseo — VERSION única (commit `5d9a2e0`, repo separado)

Tres salidas inconsistentes en `Parseo/main.py` se unificaron contra `config/settings.py:VERSION` (valor actual `"5.20"`):
- `--version` (ya usaba la constante).
- `description` de argparse (línea 1733: hardcoded `"v5.15"` → `f"v{VERSION}"`).
- Banners de ejecución (líneas 1835, 1878).

Las tres salidas ahora coinciden en v5.20. Tests Parseo verde (29 passed).

**Regla canónica (aplicable a todos los bumps futuros en Parseo)**: la fuente de versión vive en `config/settings.py` (constante `VERSION`). Cualquier referencia en código de aplicación se hace por f-string sobre la constante. Prohibido literalizar el número en `main.py`, banners o argparse. Bumpear la versión es modificar **una sola línea**.

**Lección operativa secundaria**: el keyword `closes #N` en el commit message cierra automáticamente al hacer push. Si el número del issue no corresponde con el cambio real, queda daño no trivial (el issue #5 trataba del bug cp1252, no de versión). Reabierto manualmente con `gh issue reopen` + comentario aclaratorio. Verificar siempre `gh issue view N` antes de usar el keyword.

### Auditoría IVA mixto — herramienta nueva (commit `df92dc6`)

Nuevo script read-only `scripts/auditoria_iva_mixto.py` + 19 tests sintéticos. Analiza `outputs/Facturas_<trim>.xlsx` (con hoja `Lineas`) de los últimos 4 trimestres + dry-run de 2T26 generado con Parseo `--dry-run --no-subcarpetas`. Agrupa por proveedor y reporta:

- `HAS_FACTURA_IVA_MIXTO` (intra-factura, >1 IVA en la misma factura).
- `HAS_IVAS_DISTINTOS_ENTRE_FACTURAS` (inter-factura, distinto IVA entre facturas del mismo proveedor — síntoma típico PANRUJE 2T26).
- `N_FACTURAS_CON_DESCUADRE` (columna `CUADRE` ≠ `OK` / `SIN_LINEAS`).
- `TIENE_PORTES` por keyword en `ARTICULO` (señal complementaria, no condición; rara en histórico por la regla del repo de prorratear portes en líneas de producto).
- `ID_DUDOSA` (heurística regex que marca "proveedores" cuyo nombre es realmente un trozo de filename con fallo de identificación).

Criterio `NIVEL_SOSPECHA` (de mayor a menor): `ALTO` (iva_mixto + descuadres) → `MEDIO-ALTO` → `MEDIO` → `BAJO` → `SIN`. Orden secundario: `ID_DUDOSA` asc (legítimos primero) → `N_FACTURAS` desc.

Ejecución sobre 6 archivos (4 históricos + 1T26 sandbox + 2T26 dry-run): **419 proveedores totales, 22 ALTO + 1 MEDIO-ALTO + 40 MEDIO + 0 BAJO + 356 SIN**. PANRUJE SL: NIVEL ALTO (10 facturas, 5 descuadres, IVAs [4.0, 21.0], keyword PORTES detectada). Excel `outputs/auditoria_iva_mixto_20260511_1813.xlsx` (gitignored). Regenerable trimestralmente.

### Decisiones canónicas consolidadas hoy

1. **VERSION única para Parseo** (regla canónica detallada arriba). Fix aplicado en commit `5d9a2e0`; el `closes #5` del mensaje cerró erróneamente el issue de cp1252, que queda reabierto pendiente.
2. **Política IVA en COMPRAS**: respetar el IVA tal como factura el proveedor. No recalcular, no prorratear, no "corregir". El dato que llega a Kinema/Modelo 303 debe coincidir con la factura original. La regla previa "distribute proportionally" del SPEC se circunscribe a **categorización de coste** (asignar el porte a la categoría del producto transportado), NO al recálculo de tasas de IVA.
3. **Patrón "descubrir antes de refactorizar"**: cuando un bug afecta potencialmente a múltiples extractores, el ataque empieza por un script read-only de auditoría sobre los `COMPRAS_<trim>_parseo.xlsx` existentes para mapear el alcance real. Solo después se decide entre fix quirúrgico, helper compartido o refactor en `ExtractorBase`.
4. **Lectura de IVA mixto en facturas**: cuando el extractor encuentra líneas con valores distintos en la columna `IVA %`, debe agrupar por tasa desde el body y reconstruir totales por grupo. NO confiar en el footer del PDF como fuente única — hay plantillas (caso PANRUJE FT A26 58 22/04/2026) que renderizan footer parcial. Usar el footer solo como cross-check.

### TBD / Decisiones abiertas

1. **Scope del refactor IVA mixto**: tres opciones — fix quirúrgico solo en `panruje.py`, helper compartido en `nucleo/iva_mixto.py`, o método en `ExtractorBase`. Decisión pendiente del análisis cualitativo del Excel `outputs/auditoria_iva_mixto_20260511_1813.xlsx`. Categoría A objetivo: ~10-12 proveedores únicos post-dedup (PANRUJE SL, JIMELUZ, DISTRIBUCIONES LAVAPIES, FABEIRO, SERRIN NO CHAN, CURRIMAR, APOZA, PAGO DE LAS OLMAS, COOPERATIVA MONTBRIO, GRUPO DISBER, GARDA IMPORT).
2. **Dedup de aliases en MAESTRO_PROVEEDORES**: la auditoría revela duplicación sistemática (PANRUJE/PANRUJE SL, CERES/CERES CERVEZA SL, BM/BM SUPERMERCADOS/2 BM, SERRIN NO CHAN/CHAO/SL, FABEIRO/FABEIRO SL/02218 FABEIRO, ZUCCA en 3 variantes, MARITA en 3, GADITAUN en 3, ORTEGA en 3, JAIME FERNANDEZ en 2, LIDL en 2, MERCADONA en 2). Item de backlog pendiente de priorizar.
3. **Bug del identificador de proveedor**: ~5% de facturas históricas (~20/419) tienen "proveedor" = trozo de filename, indicando fallo del extractor de identificación. La heurística regex `id_dudosa()` del script de auditoría detecta el patrón. Item de backlog pendiente de priorizar.
4. **Patrones distintos al IVA-mixto-proveedor que la auditoría reveló**: tickets multi-IVA de supermercado (Cat B: BM, DIA, LIDL, MERCADONA, MAKRO, ALCAMPO), autónomos con retención IRPF (Cat C), servicios con suplidos/tasas (Cat D: SOM ENERGIA, ODOO, KINEMA). Cada uno merece su propio análisis y fix; no se confunden con el patrón PANRUJE.
5. **Issue #5 (cp1252) reabierto, pendiente**: el commit `5d9a2e0` lo cerró erróneamente por uso incorrecto de `closes #5` en el mensaje. Issue reabierto manualmente con `gh issue reopen`. Pendiente: o bien crear issue separado para el fix de VERSION ya aplicado (y vincularlo al commit), o cerrar #5 cuando se resuelva su contenido real (cp1252).

---

## CHANGELOG v4.10 — 09/05/2026 (gmail.py v1.26 lock-safe + Parseo --dry-run)

Sesión doble: parche crítico de data loss en `gmail/gmail.py` y nuevo flag `--dry-run` en repo `Parseo/` (módulo hermano). HEAD Parseo `415dc73` ya pusheado.

### gmail.py v1.25 → v1.26 (commit `6b9cdad`) — lock-safe Excel handling

**Bug resuelto (data loss histórico).** Entre 20/03 y 10/04/2026 el script registró **29 emails** en `datos/emails_procesados.json` con motivo `error: [Errno 13] Permission denied: PAGOS_Gmail_*.xlsx`. El filtro `email_procesado()` v1.25 trataba esas entradas como procesadas, así que esos emails NUNCA volvieron a procesarse — los Excels quedaron incompletos para Kinema sin que se notara.

**Cinco cambios coordinados:**

| # | Cambio | Mecanismo |
|---|---|---|
| 1 | Pre-flight check de Excels al arrancar | Nuevo `pre_flight_check_excels()` con `_excel_disponible()` usando `open(path, 'r+b')` (NO `open('a')` prohibido por `.claude/rules/excel.md`). Verifica PAGOS_Gmail local + Facturas Provisional local + Facturas Provisional Dropbox. Si bloqueado → `SystemExit(1)` antes de tocar nada. |
| 2 | Filtro de pendientes ignora errores transitorios | `email_procesado()` reescrito: motivos `error: ...` y `limpieza_pre_v1.13` ya NO cuentan como procesado. **Recovery retroactivo automático** de los 29 emails históricos en la próxima ejecución. |
| 3 | `ExcelBloqueadoError(RuntimeError)` para fallos mid-flight | Si `PermissionError` salta a mitad de procesar un email, NO se marca como procesado y NO se mueve la etiqueta Gmail. Excepción capturada en bucle principal → log + `SystemExit(1)`. |
| 4 | **Reordering del flujo por email** (decisión canónica) | `_mover_email_seguro` (cambio etiqueta FACTURAS → FACTURAS_PROCESADAS) pasa de PASO 2 (red de seguridad inicial) a PASO 6 (confirmatorio final). Elimina el bug de email huérfano cuando Excel falla mid-flight. La capa B de duplicados (hash MD5) cubre la función de "red de seguridad" sin colateral. |
| 5 | Eliminado check duplicado en `_crear_backups` | El antiguo `open('a')` (prohibido por `excel.md`) sobrevivía como redundancia. Ahora el chequeo vive solo en `pre_flight_check_excels`. |

Tests: **`tests/unit/test_gmail_lock_safe.py`** (15 nuevos: 5 pre-flight, 6 filtro pendientes, 3 mid-flight + reordering, 1 sanity version). Suite total **259 → 274 passed**, 0 fallos.

Mejora apuntada en TBD de skill `gestion-facturas`: rename `--test` → `--dry-run` en `gmail.py` para alinear con la convención de modos especiales.

### Parseo `main.py` v5.20 + flag `--dry-run` (commit `415dc73`, repo separado)

Cierra deuda detectada en sesión 09/05 21:15: el "modo aislado" anterior (`-o C:\temp\... + --no-aprendizaje + --no-subcarpetas`) **NO era aislado** — un dry-run contaminó Drive (`Compras/Año en curso/test_2T26_diagnostico.xlsx`) y `Parseo/outputs/log_*.txt`.

`--dry-run`:
- Fuerza output a `outputs/dry_runs/<ts>_<input>.xlsx` (gitignored vía `outputs/`).
- Salta upload a Drive (envuelve el bloque `sync_archivos` con `if not args.dry_run:`).
- Salta `outputs/log_<ts>.txt`; redirige el log a `outputs/dry_runs/<ts>_<input>.log`.
- Implica `--no-aprendizaje` (con aviso explícito en stderr solo si el usuario no lo pasó ya). Esto protege también contra `procesar_correcciones()` que modifica el Diccionario Excel y `actualizar_historial()` que escribe `learning_history.json` fuera del repo Parseo.
- Mutuamente excluyente con `-o/--output` y `--aplicar-sugerencias` vía `parser.error()` (no `add_mutually_exclusive_group`).
- Mensajes `[DRY-RUN]` a stderr (inicio, forzado de `--no-aprendizaje` cuando aplica, final).

Tests: **`Parseo/tests/test_dry_run.py`** (8 nuevos). Suite Parseo **21 → 29 passed**, 0 fallos.

### Diagnóstico Parseo 2T26 — read-only (sin commit)

89 PDFs procesados, 73 cuadran (82%), importe 22.762,30€. Hallazgos para tracking:
- **Descuadre sistemático PANRUJE** (2 de 2 facturas: 12,60€ + 68,64€) — bug de extractor.
- 5 SIN_LINEAS (SABORES DE PATERNA, ACEITES JALEO, MOLLETES ARTESANOS, COMPROVINO, INDUSTRIAS CARNICAS MRM).
- 7 facturas al extractor genérico (4 candidatos a dedicado: TORRES IMPORT, FIVE GALAXIES, DUE SERVICIOS, ANTHROPIC).
- 0 GGM GASTRO mismatches (patrón anterior no persiste en 2T26).
- 0 proformas, 0 abonos.
- Capas B/C duplicados aún sin implementar en Parseo (TBD prioridad 1).

---

## CHANGELOG v4.9 — 05–06/05/2026 (auditoría gmail.py: Bloque A + MAESTRO unificado + Bloque B)

Tres sesiones de auditoría/refactor consecutivas sobre `gmail/gmail.py`. Versión interna **v1.22 → v1.25**. Suite local **157 → 179 tests** (passed, 0 failed). CI verde tras 3 iteraciones (push 91f648c → fix `__new__` → 00eceff). HEAD VPS = `a3f1134`.

### v1.23 — Bloque A: 5 quick wins (commit `eee4cda` rango)

Hardening sin cambios funcionales. Cinco correcciones puntuales identificadas en auditoría de calidad:

| QW | Problema | Fix |
|---|---|---|
| 1 | `Notificador` con `version` hardcoded | `Notificador(version=VERSION)` (DRY con constante de cabecera) |
| 2 | `francisco_guerra.py` — race condition WinError 32 en OCR | `NamedTemporaryFile.close()` antes de `Image.open()` + cleanup `try/except OSError` |
| 3 | `conectar()` sin validación de scopes | `Credentials.from_authorized_user_file(scopes=GMAIL_SCOPES)` + `'drive' in creds.scopes` con `RuntimeError` si falta |
| 4 | Carga MAESTRO sin `FileNotFoundError` claro | `raise FileNotFoundError(f"MAESTRO no encontrado: {path}")` antes del open |
| 5 | Email "Proveedores nuevos" sin estructura tipada | `@dataclass ProveedorNuevoDetectado(cif, nombre, iban, factura, importe, fecha)` |

Tests: **`tests/unit/test_gmail_quick_wins.py`** (8 tests).

### v1.24 — MAESTRO fuente verdad unificada (commit `b4e0651` rango)

**Bug silencioso resuelto.** v1.21–v1.23 leían MAESTRO de `G:\Mi unidad\...\Maestro\` (Drive Desktop, Windows) o `/opt/...` (Linux), pero `api/maestro.py` (única vía de escritura) escribía siempre en `<base>/datos/MAESTRO_PROVEEDORES.xlsx`. Resultado: PC y VPS leían un archivo distinto al que se modificaba desde Streamlit. Detectado al investigar por qué un alta vía Streamlit no aparecía en el siguiente run de gmail.py.

**Fix:** unificar a `<base>/datos/MAESTRO_PROVEEDORES.xlsx` en todas las plataformas.

- `resolver_maestro_path(es_windows, base)` simplificado a una sola rama; conserva soporte env `MAESTRO_OVERRIDE` para tests.
- Eliminados ~80 LOC: `_MAESTRO_PATH_WINDOWS`, `MaestroDriveError`, `load_maestro_from_drive`, helper de descarga vía Drive API.
- Drive ya no es fuente primaria del MAESTRO en runtime — el archivo canónico vive en el repo (gitignored). Drive sigue siendo el sync para Excels de salida (Compras/Año en curso/, etc.).
- Tests: `tests/unit/test_maestro_path.py` (7 casos: Windows/Linux equivalencia, override, ausencia de helpers eliminados).

### v1.25 — Bloque B: refactor heurística + filtrado no-factura (commits `91f648c` + `00eceff`)

Dos bugs en producción descubiertos al analizar PDFs reales (COMPROVINO 04/05, Aquí Santoña 04/05):

| Bug | Caso real | Fix |
|---|---|---|
| Heurística captura nombre del cliente | COMPROVINO 04/05 → `_nombre_aproximado` devolvía `"COMESTIBLES BAREA"` (cliente, no proveedor) | Refactor a 4 capas + lista negra `CONFIG.NOMBRES_CLIENTE` |
| Heurística captura etiquetas plantilla | Torres Import → devolvía `"FORMA DE PAGO"` | Lista `_KEYWORDS_NO_NOMBRE` filtra |
| Procesa catálogos como facturas | Aquí Santoña 04/05 → catálogo 21 págs → entrada basura en Excel | Detector `_es_factura_valida` (≥2 marcadores: nº factura, fecha, importe, CIF/NIF) |

**Heurística `_nombre_aproximado` — refactor 1 capa → 4 capas:**

| Capa | Estrategia | Ejemplo capturado |
|---|---|---|
| 4 | Sufijo societario (`S.A.U./S.L.U./S.L.L./S.A./S.L./S.COOP`) | `TORRES IMPORT S.A.U.`, `COMPROVINO SL` |
| 2 | Proximidad al CIF (1–3 líneas antes) | nombre cerca del `B12345678` |
| 0 | Primera línea razonable | `ARTESANIA LOCAL` |
| 1 | **Lista negra `NOMBRES_CLIENTE`** (filtro transversal a 4/2/0) | rechaza `TASCA BAREA S.L.`, `COMESTIBLES BAREA` |

Fallbacks: `nombre_remitente` → local-part email → `"DESCONOCIDO"`.

**Detector `_es_factura_valida(texto) -> (bool, list[str])`:** cuenta 4 marcadores (nº factura, fecha `dd/mm/yyyy`, importe `TOTAL/BASE/IVA`, CIF/NIF español). Umbral ≥2 → factura. Si <2 → marca `requiere_revision="Posible no-factura"` pero **no descarta el procesamiento** (estrategia conservadora).

**Helpers nuevos:** `_es_nombre_proveedor_razonable(s)` (longitud + letras + sin keywords + sin nombre cliente). **Constantes nuevas:** `CONFIG.NOMBRES_CLIENTE`, `_SUFIJOS_SOCIETARIOS`, `_KEYWORDS_NO_NOMBRE`.

Tests:
- **`tests/unit/test_bloque_b.py`** (NUEVO, 22 tests): 2 CONFIG + 8 razonable + 7 heurística (4 capas + 3 fallback + regresión) + 5 detector.
- **`tests/unit/test_nombre_aproximado.py`** (preservado, 6 tests): 2 tests adaptados a invocación con instancia (`proc = GmailProcessor.__new__(GmailProcessor)`) porque v1.25 usa `self` para acceder a helpers — los otros 4 siguen invocando con `None` porque caen al fallback sin tocar `self`.

**Validación cruzada con textos reales (extraídos de PDFs reales analizados durante la sesión):**

| PDF | v1.24 | v1.25 |
|---|---|---|
| Torres Import | `"FORMA DE PAGO"` ❌ | `"TORRES IMPORT S.A.U."` ✅ (Capa 4) |
| COMPROVINO | `"COMESTIBLES BAREA"` ❌ | `"COMPROVINO SL"` ✅ (Capa 4) |
| Aquí Santoña catálogo | (cualquier línea catálogo) ❌ | n/a — `_es_factura_valida` 0/4 → REVISAR ✅ |

### Iteración CI v1.25 — bug `__init__` pesado en CI

Push 91f648c falló en CI con `FileNotFoundError: /opt/gestion-facturas/datos/MAESTRO_PROVEEDORES.xlsx` (MAESTRO está gitignored, no existe en runner). Local pasaba porque sí lo tenía. **Fix `00eceff`:** los tests instancian `GmailProcessor.__new__(GmailProcessor)` en lugar de `GmailProcessor(modo_test=True)` — los métodos testeados (`_es_nombre_proveedor_razonable`, `_nombre_aproximado`, `_es_factura_valida`) NO acceden a `self.maestro`, así que `__new__` basta y evita cargar Excel inexistente.

### Reglas nuevas en `tasks/lessons.md`

- **MAESTRO única fuente verdad** — `<base>/datos/MAESTRO_PROVEEDORES.xlsx` en todas las plataformas. Lectura y escritura por la misma ruta. Drive solo para Excels de salida.
- **Validar heurísticas en frío** — antes de aplicar refactor de heurística, extraer texto de 2-3 PDFs reales del caso problema y validar manualmente layer-by-layer; ahorra iteraciones de CI.
- **Tests con `__init__` pesado en CI** — si `__init__` carga ficheros gitignored (MAESTRO, credenciales, etc.), instanciar con `Cls.__new__(Cls)` en tests unitarios cuando los métodos bajo test no acceden a esos atributos.

### Documentación de la sesión

- `outputs/bloque_a_quick_wins_20260506.md` — informe Bloque A.
- `outputs/maestro_unificado_20260506.md` — informe MAESTRO fuente verdad.
- `outputs/bloque_b_no_factura_20260506.md` — informe Bloque B + filtrado.

### Backlog cerrado en estas sesiones

- 🔴 OAuth Drive scope filtering bug (validado en producción 24/04 + hardening v1.23)
- 🔴 Drive Excels desfasados (sync re-ejecutado tras fix scope)
- 🟡 Tests TOTAL_MIN_SOSPECHOSO obsoletos (eliminados, eran del v1.18.2 pre-refactor)
- 🟢 CIF B85501989 → COMPROVINO (alta MAESTRO + extractor `comprovino.py`)
- 🟡 4 ImportError CI + 22 async failures (consolidación deps en `pyproject [dev]`)
- 🟡 Bloque A — 5 quick wins
- 🔴 Bug silencioso MAESTRO paths divergentes
- 🟢 Race condition OCR `francisco_guerra.py`
- 🟢 Filtrado no-factura (Aquí Santoña catálogo)

### Backlog vivo (no abordado en estas sesiones)

- 🟡 `Parseo/extractores/pifema.py` — fecha futura + total no extraído.
- 🟢 Alta MAESTRO + extractor "Aquí Santoña" / "Torres Import" formal (v1.25 mejora detección, alta sigue pendiente).
- 🟡 Refactor `gmail.py:conectar()` — deuda OAuth.
- 🟡 Bloques C / D auditoría (Excel I/O, refactor modular).
- `/documentos` Cloud Opción A (URLs directos a Drive).

---

## CHANGELOG v4.8 — 28-29/04/2026 (resucitar_zombis.py + bugs descubiertos)

**Nuevo script `scripts/resucitar_zombis.py` v1.0** (commit `6c608ce`). Herramienta interactiva para reprocesar "filas zombi" en `PAGOS_Gmail_<periodo>.xlsx`: entradas con TOTAL vacío y/o "ALERTA ROJA" en OBS que quedaron petrificadas porque la versión de gmail.py que las insertó tenía bugs hoy corregidos. Los extractores actuales sí parsean correctamente esos PDFs, pero las filas no se reescriben automáticamente.

**Diseño** (paridad real con flujo de producción):

- **Resolución de extractor**: `MAESTRO_PROVEEDORES.archivo_extractor` como fuente primaria (idéntico a `gmail.py:2170`); fallback a dict manual `MAPEO_EXTRACTORES_FALLBACK` si el MAESTRO no tiene el campo poblado.
- **Patrón dual A/B**: replica inline la lógica de `gmail.py:2376-2453` con comentario apuntando al origen. Patrón A (clase con `extraer(pdf_path)` que devuelve dict — caso CERES). Patrón B (clase solo con `extraer_lineas/total/fecha/referencia` que reciben TEXTO — caso mayoritario, requiere `nucleo.pdf.extraer_texto_pdf` con fallback OCR).
- **Búsqueda de PDFs**: si el archivo empieza por `ATRASADA`, prioriza la carpeta `<trimestre del Excel>/ATRASADAS` (deducido del propio nombre del Excel: `PAGOS_Gmail_2T26.xlsx` → 2T2026). Las atrasadas se contabilizan en el trimestre actual, no en el de su fecha original.
- **Protección MAESTRO**: `COLUMNAS_PROTEGIDAS_MAESTRO = (PROVEEDOR, CIF, IBAN)`. Si el Excel ya tiene valor, NO se sobreescribe — la fuente canónica de identidad del proveedor es el MAESTRO, no el atributo `nombre`/`cif`/`iban` del extractor (que puede ser una versión corta, p.ej. `'CERES'` vs `'CERES CERVEZA SL'`). Las discrepancias se logean WARN no bloqueante: pueden indicar incidencia (datos del proveedor desactualizados, factura mal asociada).
- **Equivalencia de fechas**: FECHA_FACTURA siempre se normaliza a `DD/MM/YY` (estándar `.claude/rules/excel.md`). Si el actual y el propuesto representan el mismo día (independiente del formato `DD/MM/YY` vs `DD/MM/YYYY`), no se cuenta como cambio.
- **Modo seguro por defecto**: `--apply` requiere flag explícito; sin él, dry-run. Backup obligatorio antes de escribir (`PAGOS_Gmail_<periodo>_backup_YYYYMMDD_HHMM.xlsx`). Detección de PermissionError → mensaje "Excel ABIERTO" + exit code 2 sin escritura parcial.

**Sesión inaugural — 6 filas zombi resucitadas en `PAGOS_Gmail_2T26.xlsx`**:

| Fila | Proveedor | Acción | Resultado |
|------|-----------|--------|-----------|
| F3 | SABORES PATERNA | auto | TOTAL=199,73 €, REF=001525 |
| F4 | WEBEMPRESA | auto | TOTAL=19,35 € |
| F5 | MIGUEZ CAL | manual override | FECHA=31/12/25, REF=A 4724, TOTAL=216,24 € (nota multi-albarán) |
| F8 | CERES (14/04) | auto | TOTAL=714,21 €, REF=2624798 |
| F9 | DEBORA GARCIA | manual override | FORMA_PAGO=EF (PDF dice efectivo, MAESTRO tenía TJ) + nota IRPF -0,73 € |
| F11 | CERES (10/04) | auto | TOTAL=198,71 €, REF=2624536 |

Out-of-scope (sin extractor, marcadas `fallidas` por el script y apuntadas en backlog): F6 FIVE GALAXIES COMMERCE LTD, F10 DUE SERVICIOS INTEGRALES LABORALES SL.

**Bugs descubiertos durante la sesión** (todos en backlog `tasks/todo.md` sesión 28/04 — no se atacan en este commit):

1. **ALTO — Bug nombrado de archivo en facturas multi-albarán** (`gmail/gmail.py`). gmail.py nombra el PDF con la fecha del PRIMER albarán en vez de la fecha de la factura. Detectado en MIGUEZ CAL: factura 31/12/25 archivada como `ATRASADA 4T25 1205 MIGUEZ CAL SL TF.pdf` (12/05 = primer albarán); el PDF físico fue renombrado manualmente a `1231` correcto pero la columna `ARCHIVO` del Excel mantenía `1205` → fallaba el lookup por nombre exacto. Probable que afecte a cualquier proveedor con facturas multi-albarán.
2. **MEDIO — Bug FORMA_PAGO en flujo gmail.py**. Para proveedores cuyo extractor no expone `extraer_forma_pago()`, el flujo aplica el valor de MAESTRO ignorando lo que diga el PDF. Caso DEBORA GARCIA: PDF=Efectivo, MAESTRO=TJ → escribió TJ. Soluciones posibles: (a) que el extractor extraiga FORMA_PAGO; (b) preferir SIEMPRE el PDF cuando esté presente.
3. **MEDIO — Bug fecha en extractor MIGUEZ CAL** (`Parseo/extractores/miguez_cal.py`). En facturas multi-albarán lee la fecha del primer albarán como `FECHA_FACTURA`. Debería usar la fecha del header de factura.
4. **MEDIO — Soporte de IRPF**. El Excel actual no tiene columna IRPF. Algunas facturas (DEBORA GARCIA y otros autónomos) tienen retención que Kinema necesita para el modelo 111. Decidir si añadir columna `IRPF` o seguir anotándolo en OBS.
5. **MEDIO — Crear extractores faltantes**: FIVE GALAXIES COMMERCE LTD (Loyverse, mensual recurrente) y DUE SERVICIOS INTEGRALES LABORALES SL (PRL).
6. **BAJO — Limpieza post-R.1**: existe copia obsoleta `outputs/PAGOS_Gmail_2T26.xlsx` (3-abr) que la reforma R.1 dejó atrás. La canónica vive en Drive desde 23/04. Antes de borrar: grep en repo de referencias.

**Reglas nuevas en `tasks/lessons.md`**:

- **Filas zombi en PAGOS_Gmail** — concepto + workflow de resucitación + protección MAESTRO.
- **Bug nombrado multi-albarán** — fecha del primer albarán vs factura.
- **Bug FORMA_PAGO** — gmail.py prefiere MAESTRO sobre PDF.
- **Patrón dual A/B de extractores** — paridad obligada con `gmail.py:2376-2453` para herramientas externas que invoquen extractores.

**Workflow recomendado tras upgrade significativo de gmail.py o extractores**: pase de `python scripts/resucitar_zombis.py` (dry-run) sobre los Excel del trimestre activo. Si reporta zombis con extractor disponible y datos limpios → `--apply`. El script es seguro por diseño: dry-run + backup + interactivo + protección MAESTRO.

---

## CHANGELOG v4.7 — 24/04/2026 (/documentos v2 + config/loader cascade)

**Página `/documentos` v2** (commits `572f155`, `d803bf0`, `c820b65`). Ampliada de 2 a **6 secciones** alineadas con la estructura Drive post-R.5 — lista cerrada, sin scan dinámico:

| Sección | Ruta Drive | Subcarpetas |
|---------|------------|-------------|
| 📊 Ventas | `Ventas/` | Año en curso · Histórico |
| 🧾 Compras | `Compras/` | Año en curso · Histórico |
| 🏦 Movimientos Banco | `Movimientos Banco/` | Año en curso · Histórico |
| 📦 Artículos | `Articulos/` | (plana) |
| 📚 Maestro | `Maestro/` | (plana) |
| ⚖️ Cuadres | `Cuadres/` | (plana) |

Config declarativa `CARPETAS_DOCUMENTOS` en `streamlit_app/pages/documentos.py`. Subcarpetas renderizadas con `st.tabs([...])`. Listado plano (sin mostrar sub-folders dentro de `listar_carpeta`).

**Arquitectura de configuración sensible — `config/loader.py`** (commits `410858f`, `5530c10`). Nueva capa unificada con cascada de resolución:

```
st.secrets  →  env var  →  config/datos_sensibles.py  →  default
  (Cloud)       (VPS)           (PC dev — gitignored)
```

- `config/settings.py:CIF_PROPIO` ahora se resuelve vía `loader.get("CIF_PROPIO", "")` (antes: `from config.datos_sensibles import CIF_PROPIO` sin try/except → `ModuleNotFoundError` al bootstrap en Cloud).
- Política: secrets sensibles vía `st.secrets` en Cloud, variables de entorno en VPS, `config/datos_sensibles.py` en PC (gitignored). El loader cae al siguiente nivel cuando el actual devuelve `None`.
- **Captura `ImportError` (NO solo `ModuleNotFoundError`)**: `from config import datos_sensibles` lanza `ImportError: cannot import name 'datos_sensibles' from 'config'` cuando el paquete `config/` existe pero el submódulo no — y ese `ImportError` **no** es subclase capturable por `except ModuleNotFoundError`. El loader usa `except ImportError` para cubrir ambos casos.
- Tests: `tests/unit/test_config_loader.py` — 6 casos incluyendo simulación Cloud con `monkeypatch(__import__)` para ambos tipos de error.

**Deuda técnica — `streamlit_app/requirements.txt` canónico en Cloud** (commits `d803bf0`, `c820b65`). Streamlit Cloud usa el `requirements.txt` **junto al main file** (`streamlit_app/app.py`), no el de la raíz. Libs añadidas para desbloquear `/documentos`:
- Google API: `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`.
- Deps transitivas arrastradas por `nucleo/__init__.py → .maestro`: `pdfplumber`, `rapidfuzz`.
- Mantener **AMBOS** requirements sincronizados al añadir libs nuevas. Deuda documentada en `tasks/nota_requirements.md` — próxima sesión decide consolidación.

**Infra Streamlit — mejoras defensivas** (commit `c820b65`):
- `sys.path.insert(0, ROOT)` centralizado en `streamlit_app/app.py` (defensa en profundidad: las páginas ya lo hacían pero quedaba frágil ante páginas nuevas).
- Patrón de logging visible en UI: `try/except ImportError` con `st.error(...)` + expander `st.code(traceback.format_exc())`. Ver `streamlit_app/pages/documentos.py`. Extensible a otras páginas — gracias a esto el 4º bug salió en 1 minuto con el traceback literal.

**Limitación conocida — listado Drive en Cloud**. `gmail/token.json` está `.gitignored` → Streamlit Cloud no puede autenticar contra Drive → `/documentos` muestra la **estructura** de 6 secciones pero el listado real de archivos falla. Decisión pendiente próxima sesión (Opción A "Abrir en Drive" con URLs directos vs Opción B token como secret en Cloud).

---

## CHANGELOG v4.6 — 22–23/04/2026 (reforma destinos cloud)

**Fase X.3** — Dropbox API en VPS.
- App Dropbox `gestion-facturas-barea` creada (Scoped, Full Dropbox). Refresh token OAuth2 generado via `generar_refresh_token_dropbox.py` (one-shot, gitignored).
- Credenciales (`DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`) desplegadas a `/opt/gestion-facturas/config/datos_sensibles.py` en VPS via scp append.
- Fix bug `gmail/dropbox_selector.py`: `from dropbox_api` → `from gmail.dropbox_api` (commit `0646ee9`). En PC no se notaba (rama API no se ejecutaba); en VPS sí.
- Smoke test OK: `DropboxAPIClient` autentica `tascabarea@gmail.com`, `files_list_folder("/File inviati/TASCA BAREA S.L.L/CONTABILIDAD", limit=1)` devuelve `BANCOS`.

**R.1 — gmail.py v1.21** (commit `ec83c8f`). MAESTRO **solo-lectura**.
- Se elimina el sync MAESTRO→Drive del final del run (v1.19).
- Fuente diferenciada por plataforma via nuevo `resolver_maestro_path(es_windows, base)`:
  - Windows → `G:\Mi unidad\Barea - Datos Compartidos\Maestro\MAESTRO_PROVEEDORES.xlsx` (Drive Desktop).
  - Linux → `/opt/gestion-facturas/datos/MAESTRO_PROVEEDORES.xlsx` (caché de Drive API).
  - Env `MAESTRO_OVERRIDE` para tests/desarrollo.
- Nuevo helper `load_maestro_from_drive()` + `MaestroDriveError`:
  - Descarga OK → usa ruta.
  - Descarga falla + caché existe → warning + usa caché.
  - Descarga falla + sin caché → aborta el run.
- **Política proveedor nuevo** (CIF detectado en PDF pero no en MAESTRO):
  - Procesa con **nombre aproximado** (heurística primera línea PDF → fallback remitente → fallback email-user) sin prefijo REVISAR.
  - Stub `Proveedor(nombre=nombre_aprox, cif=cif_pdf)` para que `generar_nombre_archivo` y Excels lo traten como conocido.
  - Se registra en `proveedores_nuevos_detectados` y aparece en el email resumen en la sección "⚠️ Proveedores nuevos detectados (revisar MAESTRO)" con CIF / nombre / IBAN / nº factura / importe / fecha.
  - El fichero `PROVEEDORES_NUEVOS_YYYYMMDD.txt` se elimina (reemplazado por sección email).
  - Caso "PDF no parseable / sin CIF legible" sigue siendo REVISAR como antes.
- Nuevo `nucleo.sync_drive.descargar_archivo(nombre, carpeta, destino)` con `MediaIoBaseDownload`.
- Tests: `tests/unit/test_gmail_maestro_drive.py` (12 casos — resolver path, 6 caminos de load, heurística nombre aproximado).

**R.2 — gmail.py v1.22** (commit `f72daf9`). Destinos cloud definitivos.
- **PDFs de facturas**: solo Dropbox (destino primario permanente). Se elimina la rama Drive de `_procesar_pdf` + el helper `subir_pdf_a_drive_compras` + `tests/unit/test_gmail_drive_helper.py`.
- **Facturas {trim} Provisional.xlsx**: doble escritura Dropbox + Drive.
  - Dropbox: `FACTURAS {año}/FACTURAS RECIBIDAS/X TRIMESTRE {año}/` (Kinema revisa este Excel antes de validar el trimestre).
  - Drive: `Compras/Año en curso/` (consulta del usuario).
- **PAGOS_Gmail_{trim}.xlsx**: solo Drive en `Compras/Año en curso/`.
- Nuevo método `subir_archivo_a_ruta(bytes, ruta_relativa)` en `LocalDropboxClient` y `DropboxAPIClient` (`WriteMode.overwrite`, semántica "última versión gana" apropiada para Excels).
- **Guardia inicial**: si en producción `self.dropbox is None`, `ejecutar()` aborta con `RuntimeError`. Fase X.3 garantiza que VPS tiene `DropboxAPIClient`.
- Fallos Dropbox/Drive best-effort (no abortan el run), excepto la guardia inicial. Logs `[DROPBOX OK/FALLO]` `[DRIVE OK/FALLO]`.

**R.3 — cuadre.py** (commit `20105ac`). Sync a Drive.
- Tras save exitoso del `Cuadre_DDMMYY-DDMMYY.xlsx`, best-effort upload a `Cuadres/` (raíz de Drive).
- Bootstrap `sys.path` (3 niveles arriba) para import de `nucleo.sync_drive`. Log dual: `print` + `log()`.

**R.4 — rutas PC → Drive Desktop** (commit `73d6d8e`). Las rutas hardcoded del PC apuntan a `G:\Mi unidad\Barea - Datos Compartidos\`:
- `scripts/actualizar_movimientos.py`: auto-detect regex ahora escanea `G:\...\Movimientos Banco\Año en curso\` (no cwd); fallback hardcoded a ruta completa en G:.
- `cuadre/banco/cuadre.py`: `MAESTRO_PATH = Path(r"G:\...\Maestro\MAESTRO_PROVEEDORES.xlsx")`.
- `ventas_semana/script_barea.py`: `PATH_HISTORICO = os.getenv("PATH_VENTAS_HISTORICO", <fallback __file__>)`.
- `ventas_semana/.env` (gitignored, no commit): `PATH_VENTAS`, `PATH_ARTICULOS`, `PATH_VENTAS_HISTORICO` a G:.
- `Parseo/config/settings.py` (repo local-only sin remote): `DICCIONARIO_DEFAULT` y `MAESTRO_DEFAULT` a G:.
- VPS no tocado — `CONFIG.MAESTRO_PATH` resuelve dinámicamente por plataforma.

**R.5 — migración física Drive** (EJECUTADA 23/04). Resultado:
- 3 archivos movidos de `Datos/` con patrón rename→move→trash (IDs preservados). Los 3 duplicados viejos quedan en papelera Drive como `*.OLD_20260423` (30 días recuperable).
- `Datos/` + subcarpetas `Compras/Año en curso/{T1..T4,T_pendiente}/` trasheadas.
- `Cuadres/` creada (id `1iaW1BmqT1JALvVDCb0byCw8aR1u0gkoy`).
- Snapshot final verificado — estructura coincide con la esperada.

**R.6 — push + pull VPS + smoke test** (EJECUTADO 23/04). 5 commits pusheados a GitHub, pull VPS fast-forward, py_compile + imports + VERSION 1.22 + `MaestroProveedores` (195 proveedores, CIF propio filtrado) todo verde. Cron VPS sigue inactivo (decisión del usuario).

**Fix B — token VPS scope Drive** (EJECUTADO 23/04). Durante smoke R.6 se detectó que el token VPS sólo tenía scopes Gmail (`gmail.readonly`, `gmail.modify`) — faltaba `drive`. `load_maestro_from_drive` caía silenciosamente al fallback caché (403 `insufficientPermissions`). Fix: scp del `token.json` del PC al VPS. PC tiene 4 scopes (gmail.readonly, gmail.modify, business.manage, drive) y mismo `client_id` (`955658996230-8tr632h8aju0mt2loi8vo03vl7iqtba2.apps.googleusercontent.com`). Post-fix: descarga real MAESTRO desde Drive verificada (size 28 657, md5 `1f56005c59896e62c72d23ef68a98673`, cero warnings de fallback). 3 backups del token VPS conservados en `gmail/token.json.bak*` (red de seguridad 30 días).

**Bloque E** (pendiente): ejecución real `python3 gmail/gmail.py --produccion` en VPS el viernes 24/04 con disparo manual. Observables: `[DROPBOX OK]` por PDF, `[DRIVE OK]` para Excels finales en `Compras/Año en curso/`, doble escritura Facturas Provisional (Dropbox + Drive), email resumen con sección "Proveedores nuevos detectados" si aplica, MAESTRO sin modificar.

### 24/04/2026 — Bloque E ejecutado + verificación DIA/ECOMS

**Bloque E (primer disparo real post-migración cloud):** 12 emails procesados, 6 exitosos, 4 REVISAR, 0 errores. Log: `outputs/logs_gmail/2026-04-24_primera_vps.log`. Tags `[DROPBOX OK]` por PDF y `[DRIVE OK]` para Excels finales (PAGOS_Gmail + Facturas Provisional) en `Compras/Año en curso/`. Token VPS con scope `drive` operativo, MAESTRO solo-lectura confirmado, dedupe funcionando (hash + CIF+REF).

**Casos REVISAR (4):** Solicitud factura (imagen), La Mar de Tazones (no identificado), DIA/ECOMS (extractor Formato 3 aún no desplegado en VPS en ese momento), duplicado La Mar de Tazones.

**Verificación DIA/ECOMS end-to-end:** `ecoms.py` ya cubría CIF B72738602 con Formato 3 (factura de canje). Test con PDF real: fecha 20/04/2026 ✓, ref FF202600000014 ✓, total 4,68 € ✓ (cuadre 4,38 base + 0,30 IVA), 3 líneas con códigos/cantidades/IVA mixto 4%+10% correctos. Próxima ejecución semanal procesará DIA directamente.

**Pendientes:** activación cron viernes 03:00, revisión REVISAR reales (La Mar de Tazones, Solicitud factura imagen), `git pull` VPS antes de próxima ejecución gmail.py (VPS alineado hoy tras pull manual).

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

### 6.1 GMAIL (v1.25) — ✅ 99%

**Script:** `gmail/gmail.py` (~2.500 líneas, Google API)
**Módulos:** auth.py, descargar.py, identificar.py, renombrar.py, guardar.py, generar_sepa.py, dropbox_api.py, dropbox_selector.py
**Automatización:** VPS Contabo, disparo **manual** los viernes (cron aún NO activado — decisión del usuario hasta tener 1–2 viernes empíricamente exitosos).

**Destinos cloud (v1.22):**
- PDFs de facturas → **solo Dropbox** (`FACTURAS {año}/FACTURAS RECIBIDAS/X TRIMESTRE {año}/`).
- `Facturas {trim} Provisional.xlsx` → Dropbox + Drive/`Compras/Año en curso/` (doble escritura; Kinema revisa Dropbox).
- `PAGOS_Gmail_{trim}.xlsx` → solo Drive/`Compras/Año en curso/`.
- MAESTRO → **solo-lectura, fuente verdad unificada** (v1.24): `<base>/datos/MAESTRO_PROVEEDORES.xlsx` en todas las plataformas. gmail.py nunca modifica MAESTRO (solo `api/maestro.py` es writer, vía Streamlit). Drive solo sync de Excels de salida.

**Heurística proveedor + filtrado no-factura (v1.25):**
- `_nombre_aproximado` 4 capas: sufijo societario → proximidad CIF → primera línea razonable, con lista negra `CONFIG.NOMBRES_CLIENTE` transversal y `_KEYWORDS_NO_NOMBRE`.
- `_es_factura_valida(texto)` cuenta marcadores (nº factura / fecha / importe / CIF). <2 → marca REVISAR `"Posible no-factura"` sin descartar procesamiento.

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

### 6.2 PARSEO (v5.26) — ✅ 85%

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

**URL producción:** `tascabarea.streamlit.app` (CNAME `gestion.tascabarea.com`).
**Main file:** `streamlit_app/app.py`. **Requirements canónico en Cloud:** `streamlit_app/requirements.txt` (NO el de la raíz — ver §13.9 deuda técnica).
**Login:** 4 roles (admin, socio, comes, eventos). Usuarios: Jaime (admin), Roberto (socio), Elena (comes), Benjamin (eventos).
**Páginas:** Alta Evento, Calendario Eventos, Ventas (Plotly), Maestro Editor (admin), Cuadre (placeholder), Log Gmail (placeholder), Monitor (placeholder), Ejecutar Scripts (placeholder), Documentos (Drive, v2 con 6 secciones — ver abajo).
**Página `/documentos` v2** (24/04/2026): lista declarativa `CARPETAS_DOCUMENTOS` con 6 entradas — Ventas, Compras, Movimientos Banco, Artículos, Maestro, Cuadres. Las 3 primeras con pestañas Año en curso/Histórico (`st.tabs`), las 3 últimas planas. Limitación actual: token Drive ausente en Cloud → muestra estructura pero no lista archivos (pendiente decisión Opción A URLs directos vs Opción B token-secret).
**Diseño:** Tipografía Syne + DM Sans, sidebar oscuro, identidad Tasca Barea (#8B0000, #FFF8F0)
**Filtro meses cerrados:** Triple barrera para excluir meses incompletos de comparativas:
1. `generar_dashboard.py` filtra DataFrames al generar datos (default `solo_meses_cerrados=True`)
2. Templates HTML (`closedMonths()` en JS) filtran al renderizar gráficos
3. `pages/ventas.py` filtra `meses_completos` al renderizar + delta interanual usa solo meses cerrados
Afecta: evolución €, tickets/mes, ticket medio/mes, categorías, márgenes, WooCommerce, delta YoY. No afecta: KPIs totales, gráficos diarios, tab Productos.

### 9.3 Google Drive Sync

Carpeta raíz: **`Barea - Datos Compartidos`** (id `1nYsbBT2oxmXAIgOdF60gqDlnuKV8X-y-`). Ruta PC via Drive Desktop: `G:\Mi unidad\Barea - Datos Compartidos\`.

Estructura (tras R.5 — pendiente completar):
```
Barea - Datos Compartidos/
├── Articulos/             Articulos_2026.xlsx
├── Compras/
│   ├── Año en curso/      PAGOS_Gmail_XTxx.xlsx, Facturas XTxx Provisional.xlsx
│   └── Histórico/         Compras Historico.xlsx
├── Cuadres/               Cuadre_DDMMYY-DDMMYY.xlsx (tras R.5.5)
├── Maestro/               MAESTRO_PROVEEDORES.xlsx, DiccionarioProveedoresCategoria.xlsx
├── Movimientos Banco/
│   ├── Año en curso/      Movimientos_Cuenta_26.xlsx
│   └── Histórico/
└── Ventas/
    ├── Año en curso/      Ventas Barea 2026.xlsx + dashboards HTML
    └── Histórico/         Ventas Barea Historico.xlsx
```

`nucleo/sync_drive.py` (API pública): `sync_archivos(paths, carpeta)`, `descargar_archivo(nombre, carpeta, destino)`, `listar_carpeta(carpeta)`. Auth via token OAuth2 con scope `drive` (no `drive.file`) compartido con gmail.py. Clientes Dropbox en VPS: `DropboxAPIClient` con refresh token (Fase X.3).

Scripts que sincronizan a Drive:
- `ventas_semana/script_barea.py` → `["Ventas", "Año en curso"]` (Excel ventas + dashboards).
- `scripts/actualizar_movimientos.py` → `["Movimientos Banco", "Año en curso"]`.
- `Parseo/main.py` → `["Compras", "Año en curso"]` (`COMPRAS_XTxx_parseo.xlsx`).
- `gmail/gmail.py` → `["Compras", "Año en curso"]` (ambos Excels) + Dropbox para Facturas Provisional + PDFs.
- `cuadre/banco/cuadre.py` → `["Cuadres"]` (best-effort).

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
| Gmail (gmail.py) | Viernes (manual) | SSH al VPS, ejecución manual (cron **NO activado** hasta 1-2 viernes empíricamente OK) | Evaluar cron tras luna de miel |
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

### 13.9 Config sensible — cascada unificada (`config/loader.py`)

**Tres entornos, tres fuentes**:

| Entorno | Fuente primaria | Archivo/objeto |
|---------|-----------------|----------------|
| Streamlit Cloud | `st.secrets` | Dashboard Cloud `secrets.toml` |
| VPS Contabo | variables de entorno | systemd env / `.env` |
| PC dev | archivo legacy | `config/datos_sensibles.py` (gitignored) |

`config/loader.get(key, default=None)` recorre la cascada `secrets → env → legacy → default` y devuelve el primer valor no nulo. Importar directamente `from config.datos_sensibles import X` está **deprecated** porque revienta el bootstrap en Cloud: el paquete `config/` existe pero el submódulo no, y Python lanza `ImportError: cannot import name 'datos_sensibles' from 'config'` — **que no es subclase capturable por `except ModuleNotFoundError`**. `config/settings.py` ya migrado al patrón `loader.get`.

Tests: `tests/unit/test_config_loader.py` (6 casos, incluye simulación Cloud con `monkeypatch(__import__)` para ambos tipos de error).

### 13.10 Deuda técnica — duplicación `requirements.txt`

Hay dos requirements en el repo:

| Archivo | Uso | Canónico para |
|---------|-----|---------------|
| `requirements.txt` (raíz) | dev local + VPS | pip install -r en PC/VPS |
| `streamlit_app/requirements.txt` | Streamlit Cloud | deploy en tascabarea.streamlit.app |

Cloud usa el que está junto al main file (`streamlit_app/app.py`). **Mantener ambos sincronizados al añadir libs**. Warning "More than one requirements file detected" en logs de Cloud NO es inofensivo — confirma que Cloud elige uno distinto al de la raíz. Tres alternativas para la próxima sesión (ver `tasks/nota_requirements.md`):

- **A**: consolidar en `requirements.txt` raíz único + configurar Cloud para leerlo.
- **B**: `streamlit_app/requirements.txt` con solo `-r ../requirements.txt`.
- **C**: mantener duplicación + test CI que detecte divergencia.

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
| 20A | ~~Google Drive sync HTTP 403~~ | — | ✅ **Cerrado 21/04/2026** (commit `bd3d3d7`). Scope `drive.file` → `drive` en `renovar_token_business.py`; bug de `auth_manager.get_credentials()` arreglado (pasar `scopes=` filtraba y, al refresh, serializaba un subconjunto — así se perdió el scope drive entre 18/04 y 20/04). Token regenerado y propagado al VPS. Verificado: `listar_carpeta()` devuelve la raíz "Barea - Datos Compartidos" en PC y VPS |
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

---

**21/04/2026 — cierre pendiente 20A (Drive 403) (commit `bd3d3d7`):**
- `gmail/renovar_token_business.py`: scope `drive.file` → `drive` (full). `drive.file` solo ve archivos/carpetas creados por la app → `_buscar_carpeta("Barea - Datos Compartidos")` devolvía None y `_crear_carpeta()` habría duplicado carpetas.
- `gmail/auth_manager.py`: eliminado parámetro `scopes` en `get_credentials()`, `get_gmail_service()`, `get_drive_service()`. Pasar `scopes` a `Credentials.from_authorized_user_file()` filtraba el objeto; al refrescar, `creds.to_json()` serializaba solo ese subconjunto y sobrescribía `token.json` perdiendo scopes autorizados (así desapareció `drive` entre 18/04 y 20/04).
- Token regenerado con 4 scopes (`gmail.readonly`, `gmail.modify`, `business.manage`, `drive`) y propagado al VPS. `listar_carpeta()` y página Documentos Streamlit OK en ambos entornos.

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

### v4.7 (24/04/2026) — /DOCUMENTOS v2 + CONFIG/LOADER CASCADE
- `/documentos` v2: 6 secciones (Ventas, Compras, Movimientos Banco, Artículos, Maestro, Cuadres) con pestañas Año en curso/Histórico donde aplica. Config declarativa `CARPETAS_DOCUMENTOS`.
- `config/loader.py`: cascada `st.secrets → env → datos_sensibles.py → default`. Captura `ImportError` (no solo `ModuleNotFoundError`) para cubrir `from X import Y` vs `import X.Y`.
- `config/settings.py`: migrado a `loader.get` (antes rompía bootstrap Cloud).
- Infra Streamlit: `sys.path.insert(0, ROOT)` en `app.py`; patrón logging visible con `traceback.format_exc()` en UI.
- Requirements: deuda `streamlit_app/requirements.txt` vs raíz documentada en §13.10.
- Tests: +7 (`test_config_loader.py` 6 casos, `test_documentos_config.py` 6 casos) → 158 pasan.

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

---
name: gestion-facturas
description: "Decisiones de diseño, contexto operativo y reglas no documentadas en el SPEC para el sistema de procesamiento de facturas de TASCA BAREA SLL (proyecto gestion-facturas). Usa esta skill SIEMPRE que el usuario mencione TASCA BAREA, COMESTIBLES BAREA, parseo, parsear facturas, COMPRAS, MAESTRO_PROVEEDORES, gestoría Kinema, extractores, cuadre fiscal, IVA, portes, abonos, proformas, modo de pago (RC/TF/TJ/EF), o cualquier trabajo sobre el codebase de gestion-facturas. Esta skill COMPLEMENTA docs/SPEC_GESTION_FACTURAS_v4.md (la fuente canónica de versiones, conteos, arquitectura y formatos). Aporta lo que el SPEC no recoge: contexto operativo del usuario, decisiones tomadas en planificación, política cruzada de identificación nombre+CIF, política de duplicados con cuarentena, escalera de extracción de 4 niveles, modos especiales de ejecución, y el log de decisiones cerradas y abiertas. Léela ANTES de escribir o modificar código y antes de proponer arquitectura nueva."
---

# Skill maestra del sistema `gestion-facturas`

Esta skill **no duplica el SPEC**. El SPEC (`docs/SPEC_GESTION_FACTURAS_v4.md`) es la fuente canónica para versiones, conteos, arquitectura, paths, nomenclatura y formatos de Excel. Lee el SPEC para esos datos. Esta skill captura lo que el SPEC no recoge: las decisiones de diseño tomadas en conversaciones de planificación, el contexto operativo del usuario y las reglas que aún no están implementadas.

Estado de referencia (19/05/2026): Parseo canónico en `v5.26`.

## Cómo usar esta skill junto con el SPEC

| Para esto | Consulta |
|---|---|
| Versiones, conteos, paths, nomenclatura, formato exacto de COMPRAS, listado de extractores | SPEC v4.x |
| Por qué tomamos las decisiones que ves implementadas, qué falta, qué está abierto | esta skill |

Si esta skill y el SPEC se contradicen en un dato fáctico, **gana el SPEC**. Si esta skill aporta una regla de diseño que el SPEC no recoge (como la política de cuarentena de duplicados), aplícala. Si tienes dudas sobre qué prevalece, pregunta al usuario antes de proceder.

## Contexto operativo del sistema

Estas son las condiciones reales bajo las que opera el sistema. Afectan el diseño y se deben respetar al proponer cambios. No están en el SPEC.

- **Único usuario activo**: Jaime, desde su PC Windows. No hay multiusuario hoy. Por eso no hace falta locks de concurrencia ni modo headless obligatorio.
- **Frecuencia de ejecución**: 1-2 veces al mes sobre la misma carpeta de un trimestre. No es ejecución continua. Por eso los duplicados son una rareza, no un riesgo cotidiano.
- **Recovery cuando hay error**: Jaime edita el Excel COMPRAS a mano y se lo reenvía a Kinema. El sistema no necesita auto-reparación sofisticada; sí necesita **backups automáticos** porque los Excels se editan in-situ.
- **Kinema nunca corrige facturas**: una vez Kinema procesa una factura, no la modifica. Esto significa que dos versiones de la misma factura con TOTALES distintos solo pueden venir de variaciones de extracción, no de correcciones reales.
- **Política de duplicados**: conservadora. El usuario prefiere revisar 2-3 cuarentenas al mes a que se cuele un duplicado al COMPRAS final.

Si alguna de estas condiciones cambia (Streamlit producción, multiusuario, comercialización SaaS, integración con otra gestoría), revisita el diseño.

## Identificación de proveedor (flujo cruzado nombre + CIF)

El SPEC describe la identificación secuencial actual (alias MAESTRO → fuzzy ≥85%). El diseño acordado va más allá: cruza SIEMPRE el nombre del filename con el CIF detectado en el PDF, y aplica esta tabla de decisión:

| Caso | Nombre identifica | CIF en PDF | Acción |
|---|---|---|---|
| 1 | Sí | Sí, mismo proveedor | Confirmado, sin warning |
| 2 | Sí | Sí, OTRO proveedor | Usa el del CIF (más fiable). Log warning `DISCREPANCIA_NOMBRE_CIF` |
| 3 | Sí | No se detecta CIF | Usa nombre. Marca `CIF_NO_VERIFICADO` en OBS |
| 4 | No | Sí | Usa CIF. Sugiere aprender alias del nombre al sistema de aprendizaje |
| 5 | No | No | `DESCONOCIDO` → al extractor genérico, añadir a cola de revisión |

**Coste técnico**: una llamada extra a `extraer_cif()` siempre, no solo cuando falla la identificación por nombre. Es barato si se reutiliza el texto ya extraído por el extractor primario para la primera página del PDF.

**No bajes el umbral del fuzzy del 85%** sin discutirlo. Ese umbral es decisión cerrada.

## Match parcial seguro en categorización

El SPEC documenta que la categorización usa exacto → parcial → fuzzy. La regla específica del paso parcial NO está en el SPEC y es importante:

**El match parcial (substring) exige al menos 5 caracteres en la palabra del diccionario Y coincidencia en frontera de palabra**.

Razón: bug histórico — `SAL` del diccionario matcheaba erróneamente `SALMOREJO`, `SALSA`, `SALPICÓN`. Sin frontera de palabra, los substrings cortos secuestran categorías incorrectas de forma silenciosa.

Implementación: usar `\b` en regex o partir el artículo en palabras y comparar en lugar de hacer `in`.

## Detección de duplicados (capa B + capa C)

El SPEC no documenta detección de duplicados. Es diseño nuevo.

**Capa B (hash MD5)**: antes de procesar, calcula `md5(file_bytes)`. Si el hash ya está en el histórico (`gestion-facturas/datos/historico_procesados.parquet`), el archivo es duplicado seguro. Acción: skip silencioso + log evento `duplicate_detected` + escribir fila en `outputs/Duplicados.xlsx` con [archivo_actual, archivo_original, hash, fecha_proceso_original, excel_destino_original].

**Capa C (firma semántica)**: tras la extracción, compone la firma `{PROVEEDOR_NORMALIZADO}|{REF}|{FECHA}`. Si esa firma coincide con un registro del histórico Y el hash difiere, es un caso ambiguo (típicamente Kinema renumeró el archivo o se reprocesó con extractor distinto).

**Política para capa C: SIEMPRE cuarentena, sin umbrales de TOTAL.** Escribir ambas versiones en `outputs/Revisar.xlsx` con [archivo_actual, archivo_historico, total_actual, total_historico, fecha_proceso_historico, motivo: `firma_coincidente_hash_distinto`]. NO escribir en COMPRAS hasta confirmación manual.

**Por qué cuarentena ciega, sin lógica de umbral**: Kinema no corrige facturas, por lo que cuando capa C se activa solo hay dos causas reales — reproceso con extractor distinto (variación esperable) o coincidencia genuina (rarísima si la REF se extrajo). La diferencia entre los dos no se puede deducir automáticamente sin riesgo. El volumen esperado es muy bajo (1-2 casos al mes) y el coste de revisión manual es despreciable.

**No incluyas TOTAL_FACTURA en la firma semántica.** El TOTAL puede variar entre versiones del extractor por mejoras de OCR; eso no significa que sea otra factura. La REF es la señal estable.

**Cuándo se actualiza el histórico**: solo en ejecuciones reales (no en `--dry-run`) y solo si la factura se escribió correctamente en COMPRAS. Las facturas en cuarentena (Revisar.xlsx) NO entran al histórico hasta que se resuelvan.

## Escalera de extracción (4 niveles)

El SPEC documenta el fallback nivel 1 → 2 actual. La escalera completa propuesta es:

**Nivel 1 — Extractor primario**: el método declarado en el extractor (`pdfplumber` por defecto, `pypdf`, `tesseract` para OCR primario, `hibrido` para casos como CASA DEL DUQUE). Esto ya existe.

**Nivel 2 — OCR ampliado**: tesseract con `--psm 6` por defecto, intentar también `--psm 4` (single column) y `--psm 11` (sparse) si el primero no saca líneas. Antes del OCR aplicar preprocesado de imagen: detección de orientación (`pytesseract.image_to_osd`), deskew, threshold adaptativo, contraste con PIL/OpenCV. Hoy existe parcialmente; el preprocesado y los PSM alternativos son la mejora.

**Nivel 3 — Vision LLM**: convertir el PDF a imagen, llamar a la API de Anthropic con la imagen y un prompt que pida JSON estructurado `{fecha, ref, total, lineas: [...]}`. Solo se invoca cuando 1+2 fallan. **TBD: presupuesto mensual exacto y modelo a usar (Haiku 4.5 vs Sonnet 4.6).**

**Nivel 4 — Cola manual**: marcar la factura `MANUAL_REQUIRED`, escribir fila mínima en COMPRAS con lo que se pudo extraer del filename, y volcar el archivo en `outputs/Revisar.xlsx` para que el usuario la complete a mano.

Cada nivel utilizado debe anotarse en la columna `EXTRACTOR` (o equivalente) de la pestaña Facturas para auditoría: `pdfplumber`, `tesseract`, `tesseract→psm4`, `vision_llm`, `manual`.

**Criterios para subir de nivel** (cualquiera dispara): 0 líneas extraídas, sin total, descuadre >1€, todas las líneas sin categoría válida.

## Modos especiales de ejecución (no implementados aún)

**`--dry-run`**: ejecuta todo el procesado pero NO escribe COMPRAS, NO sincroniza con Drive, NO actualiza el histórico de procesados, NO ejecuta el sistema de aprendizaje. Solo imprime el resumen de validación previa. Esencial para testear cambios sin contaminar `outputs/`.

**`--incremental`** (opcional, no default): usando el histórico de capa B, solo procesa archivos cuyo hash MD5 no esté ya registrado. Para Jaime con su frecuencia de 1-2 ejecuciones/mes esto es nice-to-have, no esencial. La capa B ya cubre el caso típico.

**Modo headless** (deferido): hoy no es prioridad porque solo Jaime ejecuta y solo desde su PC con tkinter disponible. Reactivar como requisito cuando entre Streamlit en producción o se incorpore otro usuario. La detección debe ser explícita: `try: import tkinter` al arrancar, no en mitad del flujo.

## Tipos especiales de factura

**Proforma**: detectar con `re.search(r'\bPROFORMA\b', texto)`. La función `ExtractorBase.es_proforma()` ya existe pero no se llama desde el orquestador. Activarla. Si es proforma, NO escribir en COMPRAS principal; escribir en `outputs/Proformas.xlsx` aparte. Marcar `factura.es_proforma = True`.

**Abono / Nota de crédito**: importes totales negativos. Procesar como factura normal pero marcar `factura.es_abono = True`. En las pestañas Lineas y Facturas los importes serán negativos. Anotar `ABONO` en la columna OBSERVACIONES.

## Backups automáticos

Cada vez que se va a sobrescribir un Excel COMPRAS, copiar el actual a `outputs/backups/COMPRAS_<trim>_<sufijo>_pre_{YYYYMMDD_HHMM}.xlsx` antes de escribir. Esto cubre el caso "el aprendizaje aplicó algo mal y quiero rollback rápido", que es el flujo de recovery natural del usuario (edita Excel a mano).

## Logging estructurado JSONL

Eventos a loguear, en formato JSON Lines (un objeto por línea) en `outputs/log_{YYYYMMDD_HHMM}.jsonl`:

- `file_started`, `file_completed`
- `extractor_chosen` (con razón: nombre, CIF, fallback genérico)
- `cif_discrepancy_detected`
- `fallback_triggered` (con nivel destino)
- `duplicate_detected` (capa B o C)
- `descuadre_detected`
- `proforma_detected`, `abono_detected`
- `manual_required`
- `vision_llm_invoked` (con coste estimado)

Esto permite construir luego un dashboard simple en Streamlit consultando con `jq` o pandas.

## Mejoras candidatas al formato COMPRAS

El formato canónico de `COMPRAS_<trim>_parseo.xlsx` (15 cols Lineas + 9 cols Facturas) está en SPEC §6.2. Estas son adiciones propuestas a evaluar antes de implementar:

- **En Lineas**: `OBS_LINEA` (marcas tipo `MATCH_FUZZY_85%`, `CIF_NO_VERIFICADO`, `PORTES_PRORRATEADOS`).
- **En Facturas**: `CIF` (de MAESTRO o detectado en PDF), `ES_PROFORMA` (bool, hoy se marca solo en OBSERVACIONES como texto), `ES_ABONO` (bool, para importes negativos).

No implementarlas sin discutirlo primero con el usuario. Si se acuerdan, deben añadirse al final, no insertarse en medio (preserva compatibilidad de scripts que leen por índice).

## Política de modo de pago: TR deprecado

El SPEC §4.1 lista los modos válidos como RC/TF/TJ/EF. Importante adicional: existió un código `TR` (transferencia recurrente) que se ha **unificado en `TF`**. Cualquier referencia a `TR` en código viejo, comentarios, aliases o filenames debe migrarse a `TF` cuando se toque ese punto. No introducir `TR` en código nuevo.

## Skills relacionadas (forward references)

Cuando estén creadas, complementan a esta:

- `extractor-creator` — patrón para crear/modificar extractores individuales. (Existe ya una skill `extractor` en el repo; antes de crear `extractor-creator` hay que revisar si la existente cubre el caso o conviene fundir/sustituir.)
- `tickets-fotografiados` — preprocesado de imagen, decisión de PSM, validación post-OCR. A crear cuando el nivel 2 de la escalera esté refactorizado.
- `cuadre-fiscal` — reglas duras de cuadre, retenciones IRPF, prorrateo IVA mixto, detección de abonos. (Existe ya una skill `cuadre`; revisar antes de crear nada nuevo.)

## Decisiones cerradas

Log de decisiones tomadas en conversaciones de planificación. No revertirlas sin discutirlo con el usuario.

- Identificación de proveedor cruza nombre + CIF (no uno u otro).
- Match parcial en categorización exige ≥5 chars y frontera de palabra.
- Fuzzy threshold para nombre de proveedor: 85%.
- Capas de duplicados: B (hash, auto-skip silencioso) + C (semántica, **siempre cuarentena, sin umbrales de TOTAL**).
- Capa C → siempre escritura en `Revisar.xlsx`, NO en COMPRAS, hasta confirmación manual.
- Firma semántica: `PROVEEDOR + REF + FECHA`, sin TOTAL.
- Códigos de modo de pago: cuatro válidos (`RC`, `TF`, `TJ`, `EF`). El antiguo `TR` se unifica en `TF`. No introducir TR en código nuevo.
- Mejoras candidatas al formato COMPRAS son TBD, no implementar sin acuerdo previo.
- Modo headless deferido hasta multiusuario o Streamlit producción.
- Backups automáticos obligatorios antes de sobrescribir cualquier COMPRAS.
- Sistema de logging migrar a JSONL estructurado (hoy es .txt plano).
- Refactor Parseo/Streamlit 19/05/2026 cerrado: Streamlit y CLI exportan el mismo formato canónico (`COMPRAS_<trim>_parseo.xlsx`) usando el exportador de Parseo.
- Fuente de verdad de `VERSION` unificada: gestion-facturas lee `Parseo/config/settings.py` (sin duplicar número de versión local).
- CI cross-repo cerrado con checkout autenticado de Parseo mediante `PARSEO_RO_TOKEN`.

## Decisiones abiertas (TBD)

Cuando se cierren, mover a la sección anterior y eliminar de aquí.

- Presupuesto mensual exacto para el nivel 3 (Vision LLM) y modelo concreto (Haiku 4.5 vs Sonnet 4.6).
- Lista completa y porcentajes exactos de retenciones IRPF por proveedor.
- Umbrales de la validación previa a salida que disparan confirmación obligatoria.
- Si la skill `extractor-creator` se crea ahora o tras refactor del `ExtractorBase`. Antes de crearla, revisar la skill `extractor` ya existente en el repo.
- Si las skills existentes (`cuadre`, `revisar`, `plan`, `nuevo-proveedor`, `debug-extractor`, `extractor`) requieren consolidación con esta o entre ellas para evitar instrucciones contradictorias.
- Renombrar `--test` de `gmail/gmail.py` a `--dry-run` (o añadir alias) para alinear con la convención global descrita arriba ("Modos especiales de ejecución"). Hoy `gmail/gmail.py` ya implementa la semántica `--dry-run` bajo el flag `--test` (no escribe Excels, no registra JSON, no envía notificación). Cambio cosmético, scope mínimo. Detectado el 2026-05-09 durante el parche v1.26 lock-safe.

## Cómo encajan estas convenciones con el código actual

Lo que ya respeta el código (ver SPEC §6.2): nomenclatura de archivos, MAESTRO como fuente de verdad, prorrateo de portes, fuzzy 85% en nombre de proveedor, sistema de fallback pdfplumber→tesseract, formato COMPRAS canónico SPEC v4.x documentado.

Lo que falta y hay que añadir, en orden sugerido de prioridad:

1. Detección de duplicados capa B + C con cuarentena.
2. Identificación cruzada nombre+CIF (hoy es secuencial: nombre primero, CIF como fallback).
3. Match parcial seguro (≥5 chars + frontera de palabra) en `categorizar_linea`.
4. Modo `--dry-run`.
5. Backups automáticos antes de sobrescribir COMPRAS.
6. Logging JSONL.
7. Escalera de extracción nivel 2 ampliado (PSM alternativos + preprocesado).
8. Mejoras candidatas al formato COMPRAS (si se acuerdan).
9. Escalera nivel 3 (Vision LLM) — depende de cerrar el TBD de presupuesto.
10. Escalera nivel 4 (cola manual `Revisar.xlsx` con resolución desde Streamlit).

Cuando trabajes en una sección concreta, mira primero qué dice el SPEC sobre el estado actual del código, qué dice esta skill sobre el diseño objetivo, y discute con el usuario antes de empezar a programar. No fabriques implementación de las TBD sin pedir input.

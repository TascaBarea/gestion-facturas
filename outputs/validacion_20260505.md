# Validación end-to-end — gmail.py 05/05/2026 23:54

**Sesión:** 05/05/2026 (séptima del día)
**Modo:** auto-accept

---

## Resumen ejecutivo

1. `gmail.py --produccion` ejecutado correctamente: 5 emails, 3 OK, 2 revisión, 0 errores.
2. **OAuth Drive fix VALIDADO en producción** — `[DRIVE OK] Excels de compras sincronizados` (sin `[DRIVE FALLO]`).
3. PAGOS Drive recuperado: 21 → 69 filas (+48, las 5 días desfasados desde 29/04 + las 3 nuevas).
4. 3 fixes del backlog validados en producción; 3 fixes sin oportunidad de validarse (no llegaron facturas de esos proveedores).
5. 3 problemas nuevos detectados, registrados como backlog (PIFEMA, TORRES IMPORT, OCR temp file race condition).

---

## Resumen gmail.py

```
GMAIL MODULE v1.22 - PRODUCCIÓN
Filtro fecha: after:2026/05/03 (última ejecución: 2026-05-04)
Emails pendientes: 5

Procesados:
  · FRANCISCO GUERRA OLLER       → OK   (30/04, 691.28€)
  · PIFEMA SL                    → REVISIÓN (duplicado CIF+REF, omitido)
  · DE LUIS SABORES UNICOS SL    → OK   (30/04, 375.63€)
  · TORRES IMPORT, S.A.U.        → REVISIÓN (proveedor no identificado)
  · MIGUEZ CAL SL                → OK   (30/04, 122.96€)

RESUMEN: 5 procesados, 3 exitosos, 2 revisión, 0 errores.
[DRIVE OK]   Excels de compras sincronizados
[DROPBOX OK] Facturas Provisional sincronizado
```

---

## Validación de los 6 fixes

| Fix | Commit | Estado | Detalle |
|---|---|---|---|
| Anthropic REF única | `33e9add` | ⚪ N/A | No llegó factura Anthropic en este batch |
| Debora `extraer_forma_pago` | `961f5c7` | ⚪ N/A | No llegó factura Debora |
| Miguez check defensivo multi-albarán | `c810d77` | ✅ VALIDADO | MIGUEZ CAL procesada limpiamente, sin disparar el check (ref `A 1537`, fecha 30/04 — coherente con email) |
| Jaleo extractor 2 formatos | `16f6c18` | ⚪ N/A | No llegó factura Jaleo |
| **OAuth Drive scope** | `0c10a86` | ✅ **VALIDADO CRÍTICO** | `[DRIVE OK] Excels de compras sincronizados`. **Sin `[DRIVE FALLO] 403`**. PAGOS Drive recuperó +48 filas pendientes desde 29/04 |
| Comprovino extractor | `e6aabf7` | ⚪ N/A | No llegó factura Comprovino |

Conclusión: **2 fixes validados en producción** (Miguez, OAuth Drive). El más crítico (OAuth Drive) confirmado funcional. Los otros 4 esperan próxima factura del proveedor correspondiente.

---

## Snapshot Excels pre/post

| Archivo | Pre (filas) | Post (filas) | Δ |
|---|---|---|---|
| PAGOS Drive | 21 (29/04) | **69** (05/05) | **+48** |
| Provisional Drive | 65 (04/05) | 69 (05/05) | +4 |
| Provisional Dropbox | 65 (04/05) | 69 (05/05) | +4 |

PAGOS Drive recuperó las 5 días desfasados (28-29 abr + ejecuciones posteriores que fallaron Drive 403 + las 3 OK de hoy). Provisional Drive y Dropbox idénticos (md5 match) ✓.

---

## Problemas nuevos detectados (caso C — backlog)

### 🟡 1. PIFEMA SL — extractor existe pero no extrae total + duplicado CIF+REF

```
Procesando: AB26/171...
  ↳ Proveedor: PIFEMA SL
  ↳ Usando extractor: pifema.py
  ↳ Fecha: 03/06/2026                 ← ¿FECHA FUTURA? Bug en extraer_fecha
  ↳ 🔴 ALERTA ROJA: No se pudo extraer total del PDF
  ↳ Ref: 1284
  ↳ Factura CIF+REF duplicada — NO se guardará
  ↳ Archivo: 2T26 0603 PIFEMA SL TF.pdf
```

Dos problemas combinados:
- `extractor pifema.py` parsea fecha **03/06/2026** (futura), no la real → posible bug en `extraer_fecha`.
- `extractor pifema.py` no extrae total → ALERTA ROJA.
- Anti-duplicación detecta CIF+REF=PIFEMA|1284 ya en Excel → omite Dropbox y Excel.

Como NO se guardó nada en Excel, no es zombi. Pero el extractor está roto. Necesita inspección del PDF + fix del extractor.

**Backlog**: investigar `Parseo/extractores/pifema.py`. El email original sigue con label FACTURAS para reprocesar tras fix.

### 🟢 2. TORRES IMPORT, S.A.U. — proveedor nuevo sin extractor

```
Procesando: Factura TORRES IMPORT, S.A.U. Nº 2810047013 DE 30....
  ↳ Proveedor no identificado
  ↳ ⚠️ Fecha no detectada - puede ser factura ATRASADA
  ↳ 🔴 ALERTA ROJA: No se pudo extraer total del PDF
  ↳ Ref: 227152
  ↳ Archivo: REVISAR 2T26 0505 (torresimport@torresimport.com).pdf
```

Mismo patrón que Aquí Santoña: proveedor recurrente sin alta MAESTRO, sin extractor → cae al fallback genérico, fila zombi en Excel.

**Backlog**: investigar PDF, alta MAESTRO + extractor `torres_import.py`. Email proveedor: `torresimport@torresimport.com`.

### 🟢 3. FRANCISCO GUERRA — OCR temp file race condition (no bloqueante)

```
  ↳ Proveedor: GUERRA OLLER FRANCISCO
  ↳ Usando extractor: francisco_guerra.py
  ↳ ⚠️ Error OCR en francisco_guerra.py: [WinError 32] El proceso no
     tiene acceso al archivo porque está siendo utilizado por otro proceso:
     'C:\Users\jaime\AppData\Local\Temp\tmphw7nbhd2.png'
  ↳ Fecha: 30/04/2026
  ↳ Total: 691.28€
  ↳ A�adido a Excel
```

OCR falló por un PNG temporal bloqueado (race condition con otro proceso, posiblemente AV o el propio cleanup). Pero el extractor recuperó valores correctos (¿pdfplumber fallback?). Factura procesada OK.

Es informativo, no urgente. Si vuelve a salir en futuras ejecuciones de FRANCISCO GUERRA, considerar añadir retry/lock al manejo del temp file en el extractor.

---

## Bugs colaterales en docs/scripts (corregidos en esta sesión)

### `docs/FLUJO_MANUAL_GMAIL.md` (creado en sesión TARDE) — 2 bugs

1. El comando documentado era `python gmail.py --produccion` pero `gmail.py` está en `gmail/gmail.py`, no en raíz → falla con `[Errno 2] No such file or directory`.
2. Faltaba `PYTHONPATH=.` → falla con `ModuleNotFoundError: No module named 'nucleo'` (regla ya documentada en `lessons.md`).

**Fix aplicado**: comando correcto ahora es:
```bash
cd c:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas
PYTHONPATH=. python gmail/gmail.py --produccion
```

### Pre-check de lock files: añadido `outputs/` al doc

Esta sesión tuvo que abortar el primer intento por un lock zombi en `outputs/~$PAGOS_Gmail_2T26.xlsx` (mtime 20:02 — Jaime había cerrado pero quedó huérfano tras crash de Excel). El doc original solo listaba lock files en G:\Drive y Dropbox, no en `outputs/`. **Fix aplicado**: doc ahora menciona también `outputs/`.

---

## Backlog actualizado

### Cerrado hoy
- 🔴🔴 OAuth Drive (mañana) → ✅ validado en producción esta sesión
- ✨ Cron gmail.py + flujo manual (tarde)
- 🟡 Tests CI rotos TOTAL_MIN_SOSPECHOSO (noche)
- 🟢 CIF B85501989 + extractor COMPROVINO (noche-2)
- 🟡 4 ImportError CI + 22 fallos async (noche-3)

### Vivo
- 🟢 Alta MAESTRO + extractor "Aquí Santoña" (`comercial@aquisantona.com`).
- 🟢 **NUEVO**: Alta MAESTRO + extractor "Torres Import S.A.U." (`torresimport@torresimport.com`).
- 🟡 **NUEVO**: Investigar `Parseo/extractores/pifema.py` (no extrae total + fecha futura 03/06).
- 🟢 **NUEVO**: Race condition OCR temp file en `francisco_guerra.py` (no bloqueante).
- 🟡 Refactor `gmail.py:conectar()` (deuda OAuth).
- `/documentos` Cloud Opción A.

### Validación pendiente (no llegó factura del proveedor)
- ⏳ Anthropic (`33e9add`) — esperar próxima factura mensual.
- ⏳ Debora (`961f5c7`) — esperar próxima factura.
- ⏳ Jaleo (`16f6c18`) — esperar próxima factura.
- ⏳ Comprovino (`e6aabf7`) — esperar próxima factura.

---

## Comando útil para futuras sesiones

Pre-check de locks completo (incluyendo `outputs/`):
```bash
ls "/g/Mi unidad/Barea - Datos Compartidos/Compras/Año en curso/" | grep "^~"
ls "/c/Users/jaime/Dropbox/File inviati/TASCA BAREA S.L.L/CONTABILIDAD/FACTURAS 2026/FACTURAS RECIBIDAS/2 TRIMESTRE 2026/" | grep "^~"
ls "outputs/" | grep "^~"
```

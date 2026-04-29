# Diagnóstico — 6 facturas no procesadas en Bloque E (23-24/04/2026)

**Fecha del diagnóstico**: 29/04/2026
**Ejecutor**: gmail.py v1.22 — primer disparo `--produccion` en VPS (23/04 15:51:52, log `2026-04-24_primera_vps.log`).
**Filtro temporal aplicado**: `after:2026/04/17` (cursor `ultima_ejecucion = 2026-04-18` − 1 día).
**Resultado oficial del Bloque E**: 12 emails procesados, 6 exitosos, 4 REVISAR, 0 errores.

---

## TL;DR

**5 de las 6 facturas estaban procesadas correctamente.** Solo 1 caso real de bug: ANTHROPIC. La premisa "no aparecieron en exitosos ni REVISAR" es inexacta — varias se procesaron bajo el nombre canónico del MAESTRO (no el alias coloquial usado al enumerarlas).

| # | Caso usuario | Veredicto | Detalle |
|---|---|---|---|
| 1 | Emjamesa 16/04 | A) YA_PROCESADO (2026-04-18) | Procesado en run anterior al Bloque E. Motivo: `duplicado` (hash PDF). |
| 2 | Pili Blanco 21/04 | A) YA_PROCESADO (Bloque E) | Procesada como **`BLANCO GUTIERREZ PILAR`** (alias en MAESTRO incluye `PILAR BLANCO`); contenía factura ATRASADA 4T25 (13/11/2025). |
| 3 | Welldone 20/04 | A) YA_PROCESADO (Bloque E) | Procesada como **`DEL RIO LAMEYER RODOLFO`** (alias incluye `WELLDONE`, `WELLDONE LACTICOS`). Contenía factura ATRASADA 1T26 (10/03/2026). Extractor: `welldone.py`. |
| 4 | Anthropic 20/04 | **E) EXTRACTOR_FALLO** | El extractor extrae como REF un identificador persistente (`EXB4HCQN`) en lugar del receipt # único de cada factura → siempre choca con el anti-dup CIF+REF. **Bug real** que afectará todos los meses futuros mientras no se arregle. |
| 5 | Miguez Cal abril | A) YA_PROCESADO (2026-04-18) | Es la fila zombi F5 detectada y resucitada en la sesión 28/04 (factura 31/12/25 archivada como `1205`). Causa raíz documentada: bug nombrado multi-albarán. |
| 6 | Martin Arbenza 26/03 | A) YA_PROCESADO (2026-03-27) | Procesada como `MARTIN ABENZA`; archivo `1T26 0302 MARTIN ABENZA TF.pdf` (la factura adjunta era del 02/03, no del 26/03). Los reenvíos del 22/04 saltados como `PDF duplicado (hash), saltando` ✓ comportamiento correcto. |

**Acción única requerida**: arreglar `Parseo/extractores/anthropic.py` (extractor en repo hermano, no en este). Sin fix, cada factura mensual de Anthropic será silenciosamente descartada por anti-dup CIF+REF.

---

## Contexto técnico

### Lógica del filtro y anti-dup en gmail.py

- **Filtro temporal** (`gmail/gmail.py:1834-1844`): `after_date = ultima_ejecucion - 1 día`. Solo trae emails con `internalDate ≥ after_date`.
- **Filtro de label** (`gmail/gmail.py:782-826`): `labelIds: [FACTURAS]`. Solo emails todavía etiquetados como `FACTURAS` (no los movidos a `FACTURAS_PROCESADAS`).
- **Movimiento de label** (`gmail/gmail.py:890-923`): tras procesar (éxito, REVISAR, o duplicado), el email pasa a `FACTURAS_PROCESADAS` y pierde `FACTURAS` + `UNREAD`. Comportamiento idéntico para los 3 outcomes.
- **Anti-dup hash** (`gmail/gmail.py:487-488`): `hash_existe(hash_pdf)`. Salta el email sin extraer si el hash del PDF coincide con uno previo.
- **Anti-dup CIF+REF** (`gmail/gmail.py:490-498, 2247-2255`): `clave = f"{cif|nombre}|{ref}"` — si CIF está vacío usa `nombre`. Si la clave ya existe: marca `requiere_revision = True`, motivo `"Duplicado (CIF+REF) — descartado"`, NO escribe Dropbox/Excel pero SÍ mueve email y lo registra.

### Mapa de labels Gmail

```
FACTURAS              = Label_2100432740716010866   (origen)
FACTURAS_PROCESADAS   = Label_5                     (destino)
```

---

## Tabla diagnóstica completa

### Caso 1 — Emjamesa (esperada 2026-04-16)

| Campo | Valor |
|---|---|
| Email Gmail | `id=19d967a0e074b74a`, subject `EMJAMESA FACTURA PENDIENTE DE COBRO Re: ...`, fecha 2026-04-16 13:19 UTC |
| Labels actuales | `IMPORTANT, CATEGORY_PERSONAL, Label_5` (= `FACTURAS_PROCESADAS`) |
| Adjunto (metadata) | `False` ← see note |
| Control DB | ✅ presente: `fecha_proceso = 2026-04-18T00:25:52, motivo = "duplicado"` |
| MAESTRO | ✅ `EMJAMESA SL`, CIF `B37352077`, archivo_extractor `emjamesa.py` |
| En log Bloque E (23/04) | ❌ no aparece (porque ya estaba procesado el 18/04) |
| Veredicto | **A) YA_PROCESADO** — comportamiento correcto |

**Notas**:
- El email del 16/04 fue procesado el 18/04 (entre el 18/04 y el 23/04 hubo una ejecución manual; la `gmail_resumen.json` local muestra `fecha_ejecucion: 2026-04-18T23:16:08`).
- Motivo `duplicado` apunta al hash del PDF: Emjamesa envía cadenas de respuesta (`Re: Re: Re:`) re-adjuntando el mismo PDF; al hash-deduplicar, los reenvíos saltan.
- `attach=False` en metadata API es solo porque la cabecera básica no expone los parts; el PDF sí está y fue extraído (de ahí que el hash quedara registrado).

---

### Caso 2 — Pili Blanco (esperada 2026-04-21)

| Campo | Valor |
|---|---|
| Email Gmail | `id=19daf3f72dc311ae`, from `Pili Blanco <blanco.pili@gmail.com>`, subject `facturas`, fecha 2026-04-21 08:54 UTC |
| Labels actuales | `CATEGORY_PERSONAL, Label_5` (procesado) |
| Control DB | ✅ presente: `proveedor=BLANCO GUTIERREZ PILAR`, `archivo=ATRASADA 4T25 1113 BLANCO GUTIERREZ PILAR TF.pdf`, fecha 2026-04-23 15:53:03 |
| MAESTRO | ✅ `BLANCO GUTIERREZ PILAR` con alias `[PRAIZAL, PILAR BLANCO, QUESOS PRAIZAL]`. CIF `09768240W`. archivo_extractor `praizal.py`. |
| En log Bloque E | ✅ línea 49-56: `Procesando: facturas... → Proveedor: BLANCO GUTIERREZ PILAR → praizal.py → 13/11/2025 → 235.16€ → Ref: 6652025 → ATRASADA 4T25 1113 ...` |
| Veredicto | **A) YA_PROCESADO** correctamente |

**Notas**:
- El email de Pili del 21/04 contenía facturas atrasadas (factura del 13/11/2025), no una factura nueva de abril.
- El alias del usuario "Pili Blanco" no es exacto; el MAESTRO usa `PILAR BLANCO` y `PRAIZAL` (su empresa).

---

### Caso 3 — Welldone (esperada 2026-04-20)

| Campo | Valor |
|---|---|
| Email Gmail | `id=19daad94d4aca550`, from `wellDone Lácticos <wellDone_quesos@yahoo.com>`, subject `Factura pendiente`, fecha 2026-04-20 12:24 UTC |
| Labels actuales | `IMPORTANT, CATEGORY_PERSONAL, Label_5` |
| Control DB | ✅ presente: `proveedor=DEL RIO LAMEYER RODOLFO`, `archivo=ATRASADA 1T26 0310 DEL RIO LAMEYER RODOLFO TF, TJ.pdf`, fecha 2026-04-23 15:53:06 |
| MAESTRO | ✅ `DEL RIO LAMEYER RODOLFO` con alias `[WELLDONE, WELLDONE LACTICOS, WELLDONE LÁTICOS, RODOLFO DEL RIO, ...]`. archivo_extractor `welldone.py` |
| En log Bloque E | ✅ línea 65-72: `Procesando: Factura pendiente... → DEL RIO LAMEYER RODOLFO → welldone.py → 10/03/2026 → 202.58€ → Ref: 000093 → ATRASADA 1T26 0310 ...` |
| Veredicto | **A) YA_PROCESADO** correctamente |

**Notas**:
- El email del 20/04 contenía una factura del 10/03/2026 (atrasada 1T26).
- Welldone es el nombre comercial; el titular del MAESTRO es la persona física DEL RIO LAMEYER RODOLFO.

---

### Caso 4 — Anthropic (esperada 2026-04-20) ⚠️ BUG REAL

| Campo | Valor |
|---|---|
| Email Gmail | `id=19dabd1a29b08e7a`, from `Anthropic, PBC <invoice+statements@mail.anthropic.com>`, subject `Your receipt from Anthropic, PBC #2880-2984-9190`, fecha 2026-04-20 16:55 UTC |
| Labels actuales | `CATEGORY_PERSONAL, Label_5, INBOX` (procesado pero conserva INBOX por config Anthropic) |
| Control DB (emails) | ✅ presente: `fecha_proceso = 2026-04-23T15:53:04, motivo = "Duplicado (CIF+REF) — descartado"` |
| Control DB (facturas) | clave `ANTHROPIC|EXB4HCQN` ya existía → registrado por la primera factura procesada (email Mar 21, archivo `1T26 0320 ANTHROPIC TJ.pdf`) |
| MAESTRO | ✅ `ANTHROPIC`, CIF=`""` (empresa USA, sin CIF), archivo_extractor `anthropic.py` |
| En log Bloque E | ✅ línea 57-64: `Procesando: Your receipt from Anthropic, PBC #2880-2984-9190... → ANTHROPIC → anthropic.py → 20/04/2026 → 90.00€ → Ref: EXB4HCQN → Factura CIF+REF duplicada — NO se guardará` |
| Veredicto | **E) EXTRACTOR_FALLO** |

**Causa raíz** (`Parseo/extractores/anthropic.py:75-80`):
```python
def extraer_referencia(self, texto: str) -> Optional[str]:
    """Extrae número de factura."""
    m = re.search(r'Invoice\s+number\s+([\w\-]+)', texto)
    if m:
        return m.group(1)
    return None
```

El campo "Invoice number" en los receipts de Anthropic es un identificador **persistente del cliente/billing account** (`EXB4HCQN`), no el número único de factura. El número único está en la cabecera/asunto: `Receipt #2880-2984-9190` (o similar `#XXXX-XXXX-XXXX`).

**Impacto operacional**:
- El control DB tiene 4 facturas Anthropic registradas (Feb 02, Feb 27 → archivo `1T26 0220`, Mar 06 → `ATRASADA 4T25 1220`, Mar 21 → `1T26 0320`). La 5ª (Mar 21) registró la clave `ANTHROPIC|EXB4HCQN`. Las anteriores se procesaron **antes de que el `factura_existe` cargara con CIF vacío + nombre fallback** (introducido en v1.8) → no se chocaron.
- Desde Mar 21 en adelante TODA factura nueva de Anthropic chocará con `ANTHROPIC|EXB4HCQN` y será descartada como duplicado.
- El email se mueve a `FACTURAS_PROCESADAS` igual → no quedará en backlog. Pero el PDF NO se sube a Dropbox y NO se añade al Excel.

---

### Caso 5 — Miguez Cal (esperada 2026-04-XX)

| Campo | Valor |
|---|---|
| Email Gmail | `id=19d9583601baa332`, from `Miguez Cal S.L. <miguezcal@gmail.com>`, subject `FACTURA FOR-PLAN (MIGUEZ CAL S.L)`, fecha 2026-04-16 08:58 UTC |
| Labels actuales | `IMPORTANT, CATEGORY_PERSONAL, Label_5` |
| Control DB | ✅ presente: `proveedor=MIGUEZ CAL SL`, `archivo=ATRASADA 4T25 1205 MIGUEZ CAL SL TF.pdf`, fecha 2026-04-18T00:25:56 |
| MAESTRO | ✅ `MIGUEZ CAL SL`, CIF `B79868006`, archivo_extractor `miguez_cal.py` |
| En log Bloque E | ❌ no aparece (procesado el 18/04) |
| Veredicto | **A) YA_PROCESADO** — ya conocido (fila zombi F5 resucitada en sesión 28/04) |

**Notas**:
- Esta es **la misma factura** que se resucitó manualmente el 28/04 en `PAGOS_Gmail_2T26.xlsx` (fila F5). El bug nombrado multi-albarán ya está documentado como ítem ALTO en backlog.

---

### Caso 6 — Martin Arbenza (esperada 2026-03-26)

| Campo | Valor |
|---|---|
| Email Gmail original | `id=19d29773bc8b9ff1`, from `MARTIN ABENZA <conservaselmodesto@gmail.com>`, subject `FACTURA PENDIENTE DE PAGO`, fecha 2026-03-26 09:26 UTC |
| Labels actuales | `IMPORTANT, CATEGORY_PERSONAL, Label_5` |
| Control DB | ✅ presente: `proveedor=MARTIN ABENZA`, `archivo=1T26 0302 MARTIN ABENZA TF.pdf`, fecha 2026-03-27T10:23:14 |
| Reenvíos 22/04 | `id=19db6a03bea185ae` y `id=19db69fc890cc1be` (`Fwd: FACTURA PENDIENTE DE PAGO`) — control DB: `motivo = "duplicado"` (saltados por hash) |
| MAESTRO | ✅ `MARTIN ABENZA`, CIF `74305431K` |
| En log Bloque E | ✅ líneas 21-25: dos `Procesando: Fwd: FACTURA PENDIENTE DE PAGO... → PDF duplicado (hash), saltando` |
| Veredicto | **A) YA_PROCESADO** — correctamente |

**Notas**:
- Email original procesado el 27/03 con factura del 02/03 (no del 26/03 como pensaba el usuario). Igual que Welldone, el email es de fecha distinta a la factura adjunta.
- Los dos reenvíos del 22/04 fueron correctamente identificados como duplicados de hash y saltados — comportamiento esperado.

---

## Hallazgos adicionales (no se diagnostican en profundidad)

Durante el barrido se detectaron **25 emails con label `FACTURAS` pendientes** desde el 22/04 (que cogerá el cron del viernes 01/05 con `after:2026/04/22`). Listado destacable:

- Varios `Re: ...` enviados desde `tascabarea@gmail.com` el 24-25/04 (Emjamesa, Miguez For-Plan, Solicitud de factura) → posiblemente reenvíos propios; el flujo los detectará como tal (línea 1993).
- 2 facturas CERES recientes (27/04, refs 2626806/2626808) → extractor estándar.
- 1 factura ODOO ERP SP SL del 26/04 → ya tiene extractor.
- 1 factura Som Energia, 1 LIDL, 1 Trucco, 1 PORVAZ, 1 Quesos Cati, 1 Quesos Carlos Navas, 1 Bernal, 1 Pepe Jolabrador, 1 Aquí Santoña, 1 Molletes Antequera, 1 Bendito Jaleo, 1 Vinos de Arganza, 1 La Lleldiría, 1 Cooperativa Kinema, 1 La Pep Jo (Pepe Jolabrador) — se procesarán según existencia de extractor en MAESTRO.

**No se profundiza en estos** (out of scope de esta sesión). El cron del 01/05 los gestionará.

---

## Propuestas de fix por categoría

### Categoría A — YA_PROCESADO (5 casos): comportamiento correcto

Cerrar. Los 5 casos están como deben estar. La premisa "no procesadas" del usuario era inexacta (las facturas se procesaron bajo el nombre canónico del MAESTRO, distinto del alias coloquial usado al enumerarlas).

### Categoría E — EXTRACTOR_FALLO (1 caso): Anthropic

**Bug**: `Parseo/extractores/anthropic.py:75-80` extrae `Invoice number` (persistente) en lugar del receipt # único.

**Fix propuesto** (NO aplicado — instrucciones de la sesión):

Cambiar `extraer_referencia` para usar el `Receipt #XXXX-XXXX-XXXX` que aparece tanto en el subject del email como en el PDF. Patrón:
```python
def extraer_referencia(self, texto: str) -> Optional[str]:
    """Extrae número de factura único (Receipt #).

    Anthropic usa dos identificadores:
    - 'Invoice number EXB4HCQN' → persistente del cliente/billing
    - 'Receipt #XXXX-XXXX-XXXX' → único por factura ← este queremos
    """
    m = re.search(r'Receipt\s*#?\s*(\d{4}-\d{4}-\d{4})', texto)
    if m:
        return m.group(1)
    # Fallback al Invoice number persistente (mantiene comportamiento previo)
    m = re.search(r'Invoice\s+number\s+([\w\-]+)', texto)
    if m:
        return m.group(1)
    return None
```

**Validación necesaria**: extraer texto de un PDF Anthropic real y verificar que `Receipt #XXXX-XXXX-XXXX` aparece. El subject lo tiene (`#2880-2984-9190`); el PDF body suele contenerlo también.

**Migración del control DB**: tras el fix, las 4 entradas existentes en `emails` con proveedor=ANTHROPIC seguirán ahí. La clave `ANTHROPIC|EXB4HCQN` en `facturas` también seguirá. NUEVAS facturas tendrán `ANTHROPIC|2880-2984-9190` etc → no chocarán. La factura del 20/04 que ya fue saltada como duplicada **no se reprocesará automáticamente** (está movida a `FACTURAS_PROCESADAS`); habría que resucitarla manualmente o reetiquetarla como `FACTURAS`.

**Backlog asociado**:
- Reprocesar factura Anthropic 20/04 tras el fix (recuperar PDF + subir a Dropbox + añadir a Excel). Mover la fila correspondiente del Excel — **en este caso NO existe fila zombi porque el flujo no la creó al ser duplicado descartado**, así que hay que crear la fila desde cero con el extractor arreglado.
- Re-etiquetar el email del 20/04 con label `FACTURAS` (en Gmail: añadir Label `FACTURAS` y quitar `FACTURAS_PROCESADAS`) para que el siguiente cron lo reprocese.
- O bien: ejecución manual de un mini-script puntual.

### Categoría D — PROVEEDOR_NO_MAESTRO (0 casos): N/A

Los 6 proveedores ya están en MAESTRO con sus alias correctos. No se requiere edición.

### Categorías B/C/F/G/H: 0 casos

Ningún caso cae en estas categorías.

---

## Acciones aplicadas en esta sesión

**Ninguna escritura.** Per instrucciones:
- Sin alta MAESTRO (no procede — todos los proveedores existen).
- Sin parche en código (Anthropic queda como propuesta).
- Sin ejecutar gmail.py.

## Archivos auxiliares (limpiar al cierre)

- `outputs/bloque_e.log` — copia local del log VPS (útil para futuras revisiones; mantener o mover a `outputs/logs_gmail/2026-04-24_primera_vps.log` para consistencia).
- `outputs/emails_procesados_vps.json` — snapshot del control DB del VPS al 29/04 (pesado, 256 KB; **borrar**).
- `scripts/_diag_6_facturas.py` — script one-shot de diagnóstico (**borrar**).

## Próximas acciones sugeridas (no aplicadas)

1. **Arreglar `Parseo/extractores/anthropic.py:75-80`** según parche propuesto. Repo `Parseo/`, no este. Sesión separada o follow-up directo.
2. **Reprocesar factura Anthropic 20/04** una vez el extractor esté arreglado (re-etiquetar email + mini-script).
3. **Validar el fix con un PDF real** antes de desplegar a VPS.
4. **Cron del viernes 01/05**: monitorizar que los 25 emails pendientes se procesan limpiamente. Antes del cron NO es necesaria intervención.

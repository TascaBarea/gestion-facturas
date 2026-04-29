# Fix extractor Anthropic + rescate factura 20/04 — 29/04/2026

## a) Resumen ejecutivo

- Bug detectado el 29/04 (sesión diagnóstico): `Parseo/extractores/anthropic.py` capturaba como REF el ID persistente del cliente (`EXB4HCQN`) en vez del Invoice number completo único (`EXB4HCQN 0006`), causando colisión en anti-dup CIF+REF de gmail.py para todas las facturas mensuales tras la primera.
- Parche aplicado: nuevo regex que captura ID + sufijo numérico, devolviendo `EXB4HCQN-0006`. Soporta espacio o byte NUL (`\x00`) como separador (pdfplumber inserta NUL a veces).
- Rescate manual de la factura del 20/04 que se descartó como duplicado: PDF a Dropbox + 1 fila en cada uno de los 3 Excels canónicos (PAGOS Drive, Provisional Drive, Provisional Dropbox).
- Control DB del VPS limpiado: clave zombi `ANTHROPIC|EXB4HCQN` reemplazada por `ANTHROPIC|EXB4HCQN-0007`. Email entry actualizado al formato canónico.
- Deploy del extractor parcheado al VPS (`/opt/Parseo/extractores/anthropic.py`). md5 PC == md5 VPS.

## b) Parche aplicado en `Parseo/extractores/anthropic.py`

```diff
@@ -73,7 +73,19 @@ class ExtractorAnthropic(ExtractorBase):
         return None

     def extraer_referencia(self, texto: str) -> Optional[str]:
-        """Extrae número de factura."""
+        """Extrae número de factura único.
+
+        Formato Anthropic: 'Invoice number EXB4HCQN 0006' donde
+          - EXB4HCQN es el ID persistente del cliente/billing
+          - 0006 es el contador único por factura (incremental mensual)
+        Devuelve 'EXB4HCQN-0006' para legibilidad y garantizar unicidad anti-dup.
+        """
+        # Principal: ID persistente + sufijo numérico (separador puede ser
+        # espacio, NUL byte \x00 que pdfplumber inserta a veces, o nada).
+        m = re.search(r'Invoice\s+number\s+([A-Z][A-Z0-9]*?)[\s\x00]*(\d{3,5})\b', texto)
+        if m:
+            return f"{m.group(1)}-{m.group(2)}"
+        # Fallback: captura completa (PDFs antiguos o formato inesperado)
         m = re.search(r'Invoice\s+number\s+([\w\-]+)', texto)
         if m:
             return m.group(1)
```

## c) Smoke test contra 3 PDFs Anthropic reales

Inspección del texto extraído por pdfplumber confirmó que el separador entre `EXB4HCQN` y el sufijo numérico es a veces un byte NUL (`\x00`, ord=0), no un espacio. Una primera versión del regex con solo `\s*` falló silenciosamente y caía al fallback; la corrección final usa `[\s\x00]*`.

```
enero    | 1070 1T26 0202 ANTHROPIC TJ.pdf
         REF=EXB4HCQN-0004  FECHA=20/01/2026  TOTAL=90.0
febrero  | 1104 1T26 0220 ANTHROPIC TJ.pdf
         REF=EXB4HCQN-0005  FECHA=20/02/2026  TOTAL=90.0
marzo    | 1168 1T26 0320 ANTHROPIC TJ.pdf
         REF=EXB4HCQN-0006  FECHA=20/03/2026  TOTAL=90.0
```

Patrón secuencial confirmado: cada factura mensual incrementa el sufijo en 1.

## d) Rescate factura 20/04/2026

### d.1) Dry-run

Salida resumida:
```
PDF: 31256 bytes, sha256=008c523ae20a04ac...
From:    "Anthropic, PBC" <invoice+statements@mail.anthropic.com>
Subject: Your receipt from Anthropic, PBC #2880-2984-9190

REF:   EXB4HCQN-0007
FECHA: 20/04/2026
TOTAL: 90.0 €
LÍNEAS: 1
  - {'codigo': '', 'articulo': 'SUSCRIPCION CLAUDE MAX', 'cantidad': 1, 'precio_ud': 90.0, 'iva': 0, 'base': 90.0, 'categoria': 'GASTOS VARIOS'}

[DRY-RUN] subiría PDF (31256 B) a: <DROPBOX>/...2 TRIMESTRE 2026/2T26 0420 ANTHROPIC TJ.pdf
[DRY-RUN] añadiría fila a PAGOS: G:\...\Compras\Año en curso\PAGOS_Gmail_2T26.xlsx
[DRY-RUN] añadiría fila a Provisional Drive: ...
[DRY-RUN] añadiría fila a Provisional Dropbox: ...
```

### d.2) `--apply`

Las 4 escrituras se completaron sin errores:

| Destino | Operación | Verificación |
|---|---|---|
| Dropbox PDF | escribir 31.256 B | sha256 `008c523ae20a04ac…` ✅ idéntico al dry-run |
| PAGOS Drive · FACTURAS | +1 fila | 19 → 20; última fila REF=`EXB4HCQN-0007`, total 90, fecha `20/04/26` |
| PAGOS Drive · SEPA | sin cambios | 14 → 14 (forma_pago=TJ, no entra a SEPA) |
| Provisional Drive | +1 fila | 19 → 20; ref `="EXB4HCQN-0007"`, total 90 |
| Provisional Dropbox | +1 fila | 19 → 20; idem |

## e) Control DB

### Diff

```diff
 emails["19dabd1a29b08e7a"]:
-  fecha_proceso: 2026-04-23T15:53:04.346037
-  motivo: "Duplicado (CIF+REF) — descartado"
+  message_id: <0101019dabd19f6f-...amazonses.com>
+  fecha_proceso: 2026-04-29T23:02:59.622163
+  proveedor: ANTHROPIC
+  archivo: 2T26 0420 ANTHROPIC TJ.pdf
+  dropbox: /File inviati/.../2 TRIMESTRE 2026/2T26 0420 ANTHROPIC TJ.pdf

 facturas:
-  "ANTHROPIC|EXB4HCQN":      { email_id: 19d0c2b1043b43f7, archivo: 1T26 0320 ANTHROPIC TJ.pdf }
+  "ANTHROPIC|EXB4HCQN-0007": { email_id: 19dabd1a29b08e7a, archivo: 2T26 0420 ANTHROPIC TJ.pdf }
```

### md5

| Estado | md5 |
|---|---|
| VPS pre-fix (= local backup pre) | `4b55007b655604848324799f5d5a7fa6` |
| Local post (calculado en PC) | `b415efe8c4c529864d0d8a2296cae9da` |
| VPS post-scp | `b415efe8c4c529864d0d8a2296cae9da` ✅ |

### Invariantes preservados

- `len(facturas) = 152` (sin cambio)
- `len(emails) = 863` (sin cambio)
- `ultima_ejecucion = 2026-04-23T15:51:54.968359` (sin tocar)

Backups locales conservados:
- `outputs/backups/emails_procesados_pre_anthropic_fix_20260429.json`
- `outputs/backups/emails_procesados_post_anthropic_fix_20260429.json`

## f) Deploy VPS de `anthropic.py`

- Localización en VPS: `/opt/Parseo/extractores/anthropic.py` (canónico; existe también `/opt/Parseo/extractores/legacy/anthropic.py` que se ignora).
- Backup remoto antes de sustituir: `/opt/Parseo/extractores/anthropic.py.bak_20260429` (md5 `c8712dde7dc06709e49d694cc1658911`).
- Tras `scp`: md5 PC `5a13f4b86fffaa717d4a0052bbac0161` == md5 VPS ✅.
- `grep -n 'x00'` en VPS confirma el regex parcheado presente:
  ```
  84:        # espacio, NUL byte \x00 que pdfplumber inserta a veces, o nada).
  85:        m = re.search(r'Invoice\s+number\s+([A-Z][A-Z0-9]*?)[\s\x00]*(\d{3,5})\b', texto)
  ```

## g) Commits realizados (sin push)

| Repo | Hash | Mensaje |
|---|---|---|
| gestion-facturas | `59a62e9` | docs: cierre sesión 29/04 — diagnóstico 6 facturas Bloque E |
| Parseo | `33e9add` | fix(anthropic): usar Invoice number completo como REF única |
| gestion-facturas | (commit final cierre tras este reporte) | docs: cierre fix Anthropic — rescate 20/04 + control DB |

`outputs/diagnostico_6_facturas_20260429.md`, `outputs/logs_gmail/2026-04-24_primera_vps.log`, y `outputs/backups/emails_procesados_*.json` se commitean con `git add -f` porque `outputs/` está en `.gitignore` con reglas globales (`outputs/*.md`, `outputs/backups/`, `outputs/logs_gmail/`). Los 4 archivos son evidencia de auditoría de esta sesión y se conservan en el repo intencionalmente.

**No se hizo push en ninguno de los dos repos** (gestion-facturas ni Parseo).

## h) Próxima factura Anthropic esperada

- Mayo 2026, REF esperada `EXB4HCQN-0008`.
- El cron del viernes 01/05 procesará el email cuando llegue (Anthropic emite alrededor del día 20 de cada mes); para mayo aún no hay email a procesar.
- Tras el fix:
  - El extractor devolverá `EXB4HCQN-0008` correctamente.
  - El anti-dup CIF+REF NO chocará (clave única).
  - Flujo normal: PDF a Dropbox + filas a Excels.
- La factura saliente (mayo 2026) reproducirá el comportamiento esperado en producción y validará el fix end-to-end.

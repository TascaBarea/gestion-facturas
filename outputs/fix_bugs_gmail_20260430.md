# Fix bugs gmail.py — sesión 30/04/2026

## a) Resumen

- Push GitHub de los 4 commits 28-29/04 + sync VPS limpio.
- Bug DEBORA forma_pago: parche en `Parseo/extractores/debora_garcia.py` (nuevo `extraer_forma_pago`). Smoke test verde sobre 3 PDFs reales. Deploy VPS md5-match.
- Bug MIGUEZ multi-albarán: irreproducible con código actual. Decisión: extractor INTACTO; check defensivo en `gmail.py` (`_check_fecha_vs_email`) como red de seguridad observacional para futuros casos.

## b) BUG DEBORA — forma_pago

### Diff `Parseo/extractores/debora_garcia.py` (commit `961f5c7`)

```diff
+    # Mapeo keyword (en el PDF) → código canónico del MAESTRO
+    _FORMA_PAGO_MAP = {
+        'EFECTIVO':       'EF',
+        'CASH':           'EF',
+        'TRANSFERENCIA':  'TF',
+        'TRANSFER':       'TF',
+        'TARJETA':        'TJ',
+        'CARD':           'TJ',
+        'DOMICILIACION':  'RC',
+        'DOMICILIACIÓN':  'RC',
+        'DIRECT':         'RC',
+        'BIZUM':          'BZ',
+        'PAYPAL':         'PP',
+    }
+
+    def extraer_forma_pago(self, texto: str) -> Optional[str]:
+        """Extrae la forma de pago del PDF.
+
+        Las facturas DEBORA tienen una línea explícita
+        'Método de pago Efectivo' (o equivalente). Si no hay match,
+        devuelve None para que gmail.py mantenga el fallback al MAESTRO.
+        """
+        m = re.search(r'M[ée]todo\s+de\s+pago\s+(\w+)', texto, re.IGNORECASE)
+        if m:
+            keyword = m.group(1).upper()
+            return self._FORMA_PAGO_MAP.get(keyword)
+        return None
```

### Smoke test (3 PDFs reales)

```
Archivo                                                 | FECHA       | TOTAL  | REF        | FP | OK
------------------------------------------------------------------------------------------------------
1024 1T26 0116 DEBORA GARCIA TOLEDANO TF OJO RETENCI    | 16/01/2026  |   43.5 | F2026-53   | EF | ✅
1098 1T26 0216 DEBORA GARCIA TOLEDANO TF.pdf            | 16/02/2026  |   87.0 | F2026-185  | EF | ✅
2T26 0414 DEBORA GARCIA TOLEDANO TF.pdf                 | 14/04/2026  |   87.0 | F2026-458  | EF | ✅
```

Los métodos previos (`extraer_total`, `extraer_fecha`, `extraer_referencia`) siguen funcionando — el patch solo añade un método nuevo.

## c) BUG MIGUEZ — investigación e intacto

### Smoke test del extractor actual contra 4 PDFs reales

| Archivo | Fecha esperada | Fecha extraída | OK |
|---|---|---|---|
| `1T26 0130 MIGUEZ CAL SL TF.pdf` | 30/01/2026 | 30/01/2026 | ✅ |
| `1T26 0227 MIGUEZ CAL SL TF.pdf` | 27/02/2026 | 27/02/2026 | ✅ |
| `1T26 0331 MIGUEZ CAL SL TF.pdf` | 31/03/2026 | 31/03/2026 | ✅ |
| `ATRASADA 4T25 1231 MIGUEZ CAL SL TF.pdf` | 31/12/2025 | 31/12/2025 | ✅ |

Todos verde, incluido el caso `ATRASADA 4T25 1231` que originó el zombi F5 con fecha errónea `05/12` (primer albarán). El regex actual (`r'^(\d{2})/(\d{2})/(\d{2})\s+A\s+\d+'` con `re.MULTILINE`) está anclado al patrón único de la cabecera (`31/12/25 A 4724`) y NO matchea las líneas de albaranes (`ALBARÁN A-3184 FECHA 05/12/2025`).

### md5

| Ubicación | md5 | Mtime |
|---|---|---|
| PC `Parseo/extractores/miguez_cal.py` | `3a2d6215e2d4ef5c7af095b7167d0b85` | (commit inicial Marzo 2026) |
| VPS `/opt/Parseo/extractores/miguez_cal.py` | `3a2d6215e2d4ef5c7af095b7167d0b85` | `2026-04-18 12:26` |

PC y VPS idénticos. El extractor no ha cambiado desde el commit inicial Parseo.

### Hipótesis del bug original (irreproducible)

- `.pyc` cached con versión vieja se ejecutó en la corrida del 18/04.
- Versión de pdfplumber distinta extrajo el texto en orden diferente.
- Algún test/dry-run intermedio modificó momentáneamente el extractor.

Ninguna verificable post-hoc.

### Decisión: NO modificar el extractor

Tocar el regex "por si acaso" cuando los smoke tests pasan introduce riesgo nuevo sin eliminar el viejo. Documentado como caso de referencia en `tasks/lessons.md` → "Bug irreproducible — no tocar".

## d) Check defensivo en gmail.py

### Diff `gmail/gmail.py`

```diff
@@ -837,13 +837,25 @@ class GmailClient:
             headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
-
+            # internalDate: timestamp en ms epoch UTC (recepción real Gmail).
+            # Lo exponemos como datetime para checks defensivos posteriores
+            # (p.ej. comparar con la fecha extraída del PDF).
+            internal_date_dt = None
+            try:
+                ms = int(msg.get('internalDate', 0))
+                if ms > 0:
+                    internal_date_dt = datetime.fromtimestamp(ms / 1000)
+            except (ValueError, TypeError):
+                pass
             return {
                 'id': email_id,
                 ...
+                'internal_date': internal_date_dt,
                 'payload': msg['payload']
             }
```

```diff
@@ -2034,6 +2046,13 @@ class GmailProcessor:
+            # v1.23: check defensivo multi-albarán.
+            # Si la fecha extraída del PDF queda > 7 días antes del internalDate
+            # del email, sospechar bug de extractor multi-albarán (caso MIGUEZ:
+            # extrae fecha del primer albarán en vez de la cabecera de factura).
+            # Solo logea WARNING — NO bloquea ni altera el flujo.
+            self._check_fecha_vs_email(resultado, email_data)
+
             self.resultados.append(resultado)
```

```diff
+    def _check_fecha_vs_email(self, resultado, email_data):
+        """Red de seguridad observacional contra bugs de extractor multi-albarán.
+        ...
+        """
+        if not resultado.factura or not resultado.factura.fecha:
+            return
+        internal_date = email_data.get('internal_date')
+        if not internal_date:
+            return
+        try:
+            delta_dias = (internal_date.date() - resultado.factura.fecha.date()).days
+        except (AttributeError, TypeError):
+            return
+        if delta_dias > 7:
+            self.logger.warning(
+                f"  ↳ ⚠️ Fecha factura {resultado.factura.fecha:%d/%m/%Y} > "
+                f"7 días antes de email ({internal_date:%d/%m/%Y}, "
+                f"delta={delta_dias}d): posible multi-albarán o factura "
+                f"atrasada. Verificar nombre archivo."
+            )
```

### Comportamiento

- NO bloquea: solo loguea WARNING.
- NO falsos positivos para facturas legítimamente atrasadas (que el usuario reenvía con días/semanas de retraso): el WARNING es informativo y útil precisamente para identificar atrasadas que conviene revisar manualmente.
- Robusto a campos faltantes (early return si no hay `factura.fecha` o no hay `internal_date`).

## e) Deploy VPS

### `Parseo/extractores/debora_garcia.py`

| Estado | md5 |
|---|---|
| Backup remoto previo (`anthropic.py.bak_20260430`) | `5625fb99aea2255271b2601b87bace1a` |
| HEAD post-commit (PC) | `cac2eecf6d328995a272851c296e322a` |
| VPS post-scp | `cac2eecf6d328995a272851c296e322a` ✅ |

`grep` en VPS confirma `extraer_forma_pago` presente (línea 135) y `_FORMA_PAGO_MAP` (línea 121).

### `Parseo/extractores/miguez_cal.py` — NO se despliega (no hubo cambio)

### `gestion-facturas/gmail/gmail.py`

Se desplegará al VPS automáticamente vía `git pull` tras el commit final + push (paso 6.5).

## f) Push GitHub

### Push inicial (paso 1)

```
fde66f8..296deb8  main -> main      (4 commits previos)
```

VPS `git pull --ff-only`: fast-forward limpio.

### Push final (paso 6.5)

(Pendiente al cierre de este reporte; el commit del cierre y el push se hacen tras este `outputs/fix_bugs_gmail_20260430.md`.)

## g) Commits de esta sesión

| Repo | Hash | Mensaje |
|---|---|---|
| Parseo | `961f5c7` | fix(debora): añadir extraer_forma_pago al extractor |
| gestion-facturas | (commit final tras este reporte) | feat(gmail) + docs: check defensivo multi-albarán + cierre 30/04 |

`Parseo/` no tiene remote → el commit `961f5c7` solo existe localmente. `gestion-facturas/` se push-ea al final.

## h) Siguiente factura DEBORA y MIGUEZ — test end-to-end

- **DEBORA mayo 2026** (esperada hacia el 14/05): el cron del viernes la procesará. El extractor devolverá `EF` desde el PDF, gmail.py escribirá `EF` en el Excel en lugar de `TF` del MAESTRO. Validación end-to-end del fix.
- **MIGUEZ mayo 2026** (esperada hacia 30 del mes, ej. 30/05): el extractor devolverá la fecha de cabecera correcta. Si por algún motivo el bug irreproducible reaparece, el check defensivo en gmail.py lo logará como WARNING ofreciendo el primer dato verificable.

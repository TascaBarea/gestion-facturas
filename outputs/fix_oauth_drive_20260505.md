# Fix OAuth Drive scope + re-sync Drive Excels

**Sesión:** 05/05/2026
**Modo:** auto-accept
**Continuación de:** sesión 04/05 mañana (interrumpida por cobertura) y sesión 04/05 tarde (Jaleo + hallazgo Drive desfasado).

---

## Resumen ejecutivo

1. **Bug Drive 403 resuelto**: regenerado `gmail/token.json` con 4 scopes (incluido `drive` full) + parche `gmail.py:191-194` añadiendo `drive` a `GMAIL_SCOPES` para que el siguiente refresh no borre el scope.
2. **Drive API verificada**: list `Barea - Datos Compartidos` OK; `creds.to_json()` preserva los 4 scopes tras load.
3. **Deploy VPS**: token con 4 scopes en VPS, md5-match con PC.
4. **Re-sync Drive Provisional**: 21 → 65 filas (+44 recuperadas) desde Dropbox.
5. **PAGOS Drive sin re-sync** (no hay fuente en Dropbox) — se actualizará vía cron viernes 08/05.

---

## A · OAuth re-auth: scopes pre/post

**Token PRE (bug confirmado, 2 scopes):**
```
['https://www.googleapis.com/auth/gmail.readonly',
 'https://www.googleapis.com/auth/gmail.modify']
```

**Token POST (4 scopes):**
```
['https://www.googleapis.com/auth/gmail.readonly',
 'https://www.googleapis.com/auth/gmail.modify',
 'https://www.googleapis.com/auth/business.manage',
 'https://www.googleapis.com/auth/drive']
expiry: 2026-05-05T18:58:59Z
refresh_token presente: True
```

Backups conservados:
- `gmail/token.json.bak.20260421` (token PRE-bug 21/04, sin drive)
- `gmail/token.json.bak.20260504` (token PRE-sesión 04/05)
- `gmail/token.json.bak.20260505` (token PRE-OAuth 05/05)
- VPS: `gmail/token.json.bak_pre_oauth_20260505` (md5 `d902c79e63c092ead0bd86be4f747a8b`)

---

## B · Parche `gmail/gmail.py:191-194`

**Diff:**
```python
     GMAIL_SCOPES: List[str] = field(default_factory=lambda: [
         'https://www.googleapis.com/auth/gmail.readonly',
-        'https://www.googleapis.com/auth/gmail.modify'
+        'https://www.googleapis.com/auth/gmail.modify',
+        'https://www.googleapis.com/auth/drive',
     ])
```

**Por qué este parche es necesario** aunque `auth_manager.py` ya esté correcto: `gmail/gmail.py:706` carga credenciales con `Credentials.from_authorized_user_file(self.token_path, CONFIG.GMAIL_SCOPES)`. La librería filtra los scopes del token al subset pasado. En `:718` el `creds.to_json()` reescribe el token con ese subset → cualquier scope no listado se pierde.

Con `CONFIG.GMAIL_SCOPES` ahora incluyendo `drive`, los 3 scopes que `gmail.py` necesita (gmail.readonly, gmail.modify, drive) se preservan tras refresh. `business.manage` no se usa en `gmail.py`, así que su pérdida no afecta — y de todos modos el parche del 21/04 en `auth_manager.py` (que carga sin scopes) preserva todos los scopes desde otros call sites.

---

## C · Test Drive API post-fix

```
=== Drive API ===
files: [{'owners': [{'emailAddress': 'tascabarea@gmail.com'}],
        'id': '1nYsbBT2oxmXAIgOdF60gqDlnuKV8X-y-',
        'name': 'Barea - Datos Compartidos'}]
```

Carpeta canónica encontrada vía `svc.files().list(...)`. **Sin error 403**.

---

## D · Test robustez refresh

```
=== Robustez creds.to_json() ===
post-load scopes: ['gmail.readonly', 'gmail.modify',
                   'business.manage', 'drive']
len scopes: 4
```

`get_credentials()` (de `gmail/auth_manager.py`, sin parámetro `scopes`) carga el token y `to_json()` devuelve los 4 scopes intactos. Si el patrón se replica en `gmail.py:706-718` con `GMAIL_SCOPES` ahora con 3 scopes, el refresh preservará gmail.readonly + gmail.modify + drive.

---

## E · Deploy VPS

| | md5 |
|---|---|
| PC `gmail/token.json` | `6c4af8156aacc6807af82e6218eed5fc` |
| VPS `/opt/gestion-facturas/gmail/token.json` | `6c4af8156aacc6807af82e6218eed5fc` |

Verificación scopes en VPS: lista de 4 scopes confirmada con `python3 json.load`.

`gmail.py` se sincroniza vía `git pull` tras el commit (no scp manual).

---

## F · Re-sync Drive Excels

### Estado pre-resync

| Excel | mtime | bytes | filas |
|---|---|---|---|
| Dropbox Provisional (fuente) | 2026-05-04 22:53 | 8753 | **65** |
| Drive Provisional (destino) | 2026-04-29 20:17 | 6401 | 21 |
| Drive PAGOS_Gmail_2T26 | 2026-04-29 20:17 | 10688 | 21 |

Δ = +44 filas faltantes en Drive Provisional respecto a Dropbox.

### Acción

- **Provisional Drive**: backup `Facturas 2T26 Provisional_backup_pre_resync_20260505_2023.xlsx` + `cp Dropbox → Drive` (sobrescritura).
- **PAGOS Drive**: NO se re-sync. Equivalente en Dropbox no existe. Se actualizará automáticamente cuando el cron del viernes 08/05 procese facturas nuevas (con la API Drive ya operativa).

### Estado post-resync

| Excel | filas | bytes |
|---|---|---|
| Dropbox Provisional | 65 | 8753 |
| Drive Provisional | **65** | 8753 |

✅ filas Dropbox == Drive
✅ bytes Dropbox == Drive

---

## G · Commits

| Repo | Hash | Asunto |
|---|---|---|
| gestion-facturas | (este commit) | `fix(gmail) + docs: OAuth Drive scope + re-sync Excels — sesión 05/05` |

Parseo no se toca en esta sesión.

---

## Próximos pasos

### Cron viernes 08/05 03:00 — test end-to-end

El cron procesará:
- Emails con label FACTURAS desde 04/05 (pendientes acumulados).
- Si Anthropic, Debora o Miguez tienen factura mensual ese día, será también test end-to-end de los 3 fixes anteriores (commits `33e9add`, `961f5c7`, `c810d77`).
- Drive sync vía API: ahora **funcional**. Ya no debería aparecer `[DRIVE FALLO] 403` en el log.
- PAGOS Drive se actualizará por primera vez en 5 días (con todas las facturas pendientes desde 29/04).

### Backlog actualizado (pendientes)

1. **🟡 Refactor `gmail.py:conectar()`** delegando en `auth_manager.get_gmail_service()` para eliminar la duplicación. Este parche es la solución mínima; el refactor es deuda técnica pendiente.
2. **🟢 Investigar CIF B85501989** detectado para "COMESTIBLES BAREA" (pendiente sesión 04/05 D).
3. **🟢 Alta MAESTRO + extractor "Aquí Santoña"** (pendiente sesión 04/05 E).
4. **Tests rotos GitHub Actions** (si los hay — verificar tras este push).
5. **`/documentos` en Cloud — Opción A** (botones "Abrir en Drive" — pendiente arrastrado).

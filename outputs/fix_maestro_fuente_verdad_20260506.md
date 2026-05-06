# Fix MAESTRO fuente de verdad — v1.23 → v1.24

**Sesión:** 06/05/2026 (segunda del día tras Bloque A)
**Modo:** auto-accept

---

## Resumen ejecutivo

Bug silencioso: gmail.py leía MAESTRO desde `G:\...\Maestro\` (Drive Desktop) pero los scripts de alta escribían en `datos/`. Las altas COMPROVINO (05/05) y JALEO se perdieron silenciosamente. Fix: unificar todo en `datos/` y eliminar ~80 LOC de código Drive (lecturas, fallbacks, excepciones específicas). 7 tests añadidos + 6 preservados. Suite local 157 passed, CI verde.

---

## Causa raíz

| | gmail.py v1.21+ leía | Scripts alta escribían |
|---|---|---|
| Ruta resuelta | `G:\Mi unidad\Barea - Datos Compartidos\Maestro\MAESTRO_PROVEEDORES.xlsx` | `c:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\datos\MAESTRO_PROVEEDORES.xlsx` |
| md5 antes del fix | `G:\Maestro\` 196 filas, mtime 28/04, **SIN COMPROVINO** | `datos/` 197 filas, mtime 05/05, **CON COMPROVINO+JALEO** |

Lecturas y escrituras a archivos distintos → altas perdidas para gmail.py.

Verificación pre-fix:
```
datos/ (PC + VPS): md5 6d40e5779cd627b249f696a3491db0bf, 197 filas
G:\Maestro\:        28671 bytes, 196 filas (sin COMPROVINO)
```

La próxima factura COMPROVINO o JALEO habría producido `Proveedor NUEVO` en log, reproduciendo el bug original del 04/05.

---

## Decisión arquitectónica (chat 06/05)

**Opción B**: `datos/MAESTRO_PROVEEDORES.xlsx` (PC repo) es la fuente de verdad. Razones:

- Solo 1 usuario activo (Jaime desde PC). Los pros de Drive (compartir con Roberto/Cristina/gestoría) no aplican hoy.
- Pros de `datos/`: simplicidad, sin dependencia Drive Desktop, tests sencillos, scripts de alta ya alineados.
- Migración futura B→A trivial (1 commit): código exacto de `load_maestro_from_drive` queda en git history (`pre-b4e0651`).

---

## Cambios en `gmail/gmail.py`

```diff
-# Raíz Drive Desktop en PC (G: por defecto de Google Drive)
-_MAESTRO_PATH_WINDOWS = r"G:\Mi unidad\Barea - Datos Compartidos\Maestro\MAESTRO_PROVEEDORES.xlsx"
-
-
-def resolver_maestro_path(es_windows: bool, base_path: str) -> str:
-    """Resuelve ... según plataforma."""
-    if es_windows:
-        return _MAESTRO_PATH_WINDOWS
-    return os.path.join(base_path, "datos", "MAESTRO_PROVEEDORES.xlsx")
+def resolver_maestro_path(es_windows: bool, base_path: str) -> str:
+    """v1.24: siempre <base_path>/datos/MAESTRO_PROVEEDORES.xlsx."""
+    override = os.environ.get("MAESTRO_OVERRIDE")
+    if override:
+        return override
+    return os.path.join(base_path, "datos", "MAESTRO_PROVEEDORES.xlsx")
```

Eliminados:
- `_MAESTRO_PATH_WINDOWS` (constante)
- `class MaestroDriveError(RuntimeError)` (excepción)
- `def load_maestro_from_drive(...)` (~70 líneas, fallbacks Linux + check Drive Desktop)
- Llamada `load_maestro_from_drive(CONFIG.MAESTRO_PATH, logger=...)` en `_conectar_servicios`
- Import transitivo `from nucleo.sync_drive import descargar_archivo`

**Total: ~80 LOC eliminadas en gmail.py.**

---

## Tests

### Borrado: `tests/unit/test_gmail_maestro_drive.py` (206 líneas, 16 tests)

Razón: 10 tests testaban API eliminada (`MaestroDriveError`, `load_maestro_from_drive`, ruta Drive en `resolver_maestro_path`); 6 tests testaban heurística `_nombre_aproximado` que sí sigue siendo válida.

### Nuevo: `tests/unit/test_maestro_path.py` (7 tests)

```
✓ test_resolver_maestro_path_windows_apunta_a_datos
✓ test_resolver_maestro_path_linux_apunta_a_datos
✓ test_resolver_maestro_path_windows_y_linux_dan_misma_ruta
✓ test_maestro_override_env_var_funciona
✓ test_maestro_drive_error_no_existe
✓ test_load_maestro_from_drive_no_existe
✓ test_maestro_path_windows_no_existe
```

### Preservado en archivo nuevo: `tests/unit/test_nombre_aproximado.py` (6 tests)

Tests de `GmailProcessor._nombre_aproximado` (heurística para extraer nombre de proveedor desde PDF/remitente/email). Funcionalidad NO afectada por v1.24, simplemente reubicados:

```
✓ test_nombre_aproximado_primera_linea_pdf
✓ test_nombre_aproximado_salta_lineas_no_utiles
✓ test_nombre_aproximado_fallback_remitente
✓ test_nombre_aproximado_fallback_email_user
✓ test_nombre_aproximado_con_display_name
✓ test_nombre_aproximado_desconocido
```

---

## Resultado tests

| | Antes (Bloque A) | Después (v1.24) |
|---|---|---|
| Suite local `-m unit` | 144 passed | **157 passed** |
| Failed | 0 | 0 |
| Run CI `25445425979` | — | ✅ success (46s) |

---

## Estado md5 datos/MAESTRO_PROVEEDORES.xlsx

| | md5 |
|---|---|
| PC `datos/` | `6d40e5779cd627b249f696a3491db0bf` |
| VPS `/opt/gestion-facturas/datos/` | `6d40e5779cd627b249f696a3491db0bf` |

Sincronizado tras NOCHE-2 (05/05) — sin cambios necesarios en esta sesión.

---

## Drive `Maestro/` deprecado

```
G:\Mi unidad\Barea - Datos Compartidos\Maestro\
  ├── DiccionarioProveedoresCategoria.xlsx  (NO afectado, sigue ahí)
  ├── desktop.ini
  └── (MAESTRO_PROVEEDORES.xlsx eliminado de aquí)

G:\Mi unidad\Barea - Datos Compartidos\_DEPRECATED_20260506\Maestro\
  ├── MAESTRO_PROVEEDORES.xlsx  (ÚLTIMO snapshot 28/04, deprecado)
  ├── README.txt                (explicación + plan migración B→A)
  └── desktop.ini
```

`DiccionarioProveedoresCategoria.xlsx` se dejó en su sitio porque NO es MAESTRO y no participa del bug.

**Acción para Jaime**: si quieres, verifica en https://drive.google.com (web) que la carpeta `_DEPRECATED_20260506/Maestro/` está creada con MAESTRO_PROVEEDORES.xlsx + README dentro.

---

## Plan de migración futura B→A (si entran nuevos usuarios)

1. Copiar `datos/MAESTRO_PROVEEDORES.xlsx` (estado actual) a `G:\Maestro\`.
2. `git revert b4e0651` → restaura `load_maestro_from_drive`, `_MAESTRO_PATH_WINDOWS`, `MaestroDriveError` y la llamada en `_conectar_servicios`.
3. Adaptar scripts de alta (alta_proveedor.py, _alta_*.py) para escribir en G:\ además de datos/.
4. Plan: 1 commit aislado, código exacto en git history.

---

## Commit

| Hash | Asunto |
|---|---|
| `b4e0651` | `fix(gmail): unificar fuente de verdad MAESTRO en datos/ (v1.23 → v1.24)` |

VPS HEAD = `b4e0651` ✓.

---

## Backlog

### Cerrado hoy
- 🔴 Bug silencioso lectura MAESTRO Drive vs escritura datos/.

### Vivo (sin cambios)
- 🟡 `Parseo/extractores/pifema.py` (fecha futura + total no extraído).
- 🟢 Alta MAESTRO + extractor "Aquí Santoña" / "Torres Import".
- 🟡 Refactor `gmail.py:conectar()` (deuda OAuth — más amplio que QW3).
- `/documentos` Cloud Opción A.
- 🟡 Bloque B / C / D auditoría (cliente/proveedor, Excel I/O, refactor modular).

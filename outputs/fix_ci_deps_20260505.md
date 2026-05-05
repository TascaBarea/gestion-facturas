# Fix CI — consolidación deps de test

**Sesión:** 05/05/2026 (quinto cierre del día)
**Modo:** auto-accept

---

## Resumen ejecutivo

1. **26 problemas de CI cerrados de golpe**: 4 ImportError + 22 fallos async, todos por deps no consolidadas.
2. Pyproject.toml `[dev]` ahora incluye TODAS las deps de test (13 paquetes). Workflow simplificado a `pip install -e ".[dev]"` sin extras manuales.
3. **Suite local: 136 passed, 0 failed** (antes 114 + 22 fail).

---

## Estado pre-fix

### `pyproject.toml [project.optional-dependencies] dev` (antes — 4 deps)

```toml
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]
```

### `.github/workflows/tests.yml` (antes)

```yaml
run: |
  pip install --upgrade pip
  pip install -e ".[dev]"
  pip install openpyxl pdfplumber rapidfuzz pydantic httpx
```

### CI status

- 4 ImportError: `google`, `googleapiclient`, `numpy`, `dotenv` ausentes en pyproject Y en workflow.
- 22 fallos async: `pytest-asyncio` estaba en `[dev]` pero el venv local no lo tenía instalado (último `pip install -e ".[dev]"` previo a su adición).

---

## Cambios

### Diff `pyproject.toml`

```diff
 [project.optional-dependencies]
 dev = [
+    "google-api-python-client>=2.0",
+    "google-auth>=2.0",
+    "google-auth-oauthlib>=1.0",
+    "httpx>=0.27",
+    "numpy>=1.26",
+    "openpyxl>=3.1",
+    "pdfplumber>=0.11",
+    "pydantic>=2.0",
     "pytest>=8.0",
-    "pytest-cov>=5.0",
     "pytest-asyncio>=0.24",
-    "httpx>=0.27",
+    "pytest-cov>=5.0",
+    "python-dotenv>=1.0",
+    "rapidfuzz>=3.0",
 ]
```

`[tool.pytest.ini_options]` ya tenía `asyncio_mode = "auto"` desde antes (sin cambios).

### Diff `.github/workflows/tests.yml`

```diff
       - name: Instalar dependencias
         run: |
           pip install --upgrade pip
           pip install -e ".[dev]"
-          pip install openpyxl pdfplumber rapidfuzz pydantic httpx
```

---

## Validación local

`.venv/Scripts/python -m pip install -e ".[dev]"` instaló:
- pytest-asyncio 1.3.0
- pytest-cov 7.1.0
- coverage 7.13.5
- (las google/numpy/dotenv ya estaban instaladas a mano de antes)

`.venv/Scripts/python -m pytest tests/unit/ -v --tb=short -m unit` →

| | Antes | Después |
|---|---|---|
| Passed | 114 | **136** |
| Failed | 22 | **0** |
| Deselected (no `unit`) | 44 | 44 |

Sin warnings sobre `Unknown config option: asyncio_mode`. Sin "async def functions are not natively supported".

---

## Beneficio operativo

Una sola fuente de verdad para deps de test. Cualquier test nuevo que requiera una dep extra → se añade en `pyproject.toml [dev]` y CI la recoge automáticamente. Antes había que recordar tocar dos archivos (pyproject + workflow), y se olvidaba.

---

## Iteraciones CI hasta verde

CI requirió 3 push para llegar a verde. Cada push reveló deps transitivas adicionales que el .venv local sí tenía (instaladas a mano antaño) pero CI no:

| Push | Resultado | Causa |
|---|---|---|
| `1de22b5` | 4 errors → 1 error | Faltaba `pandas` (test_nucleo.py) |
| `df71401` (+pandas+fastapi) | collection OK, 22 ERRORs runtime | Faltaba `python-multipart` (FastAPI form data) |
| `ab94d04` (+python-multipart) | **🎉 SUCCESS** — 179 passed, 1 skipped | — |

## Commits

| Hash | Asunto |
|---|---|
| `1de22b5` | `fix(ci): consolidar deps de test en pyproject [dev]` |
| `df71401` | `fix(ci): añadir pandas + fastapi a [dev] (deps transitivas test)` |
| `ab94d04` | `fix(ci): añadir python-multipart a [dev] (FastAPI form data)` |

---

## Backlog actualizado

### Cerrado hoy (5 sesiones del 05/05)

- 🔴 OAuth Drive scope (mañana)
- 🔴 Drive Excels desfasados (mañana)
- ✨ Cron gmail.py + flujo manual (tarde)
- 🟡 Tests CI rotos TOTAL_MIN_SOSPECHOSO (noche)
- 🟢 CIF B85501989 + extractor COMPROVINO (noche-2)
- 🟡 4 ImportError CI + 22 fallos async (esta sesión, noche-3)

### Vivo

- 🟢 Alta MAESTRO + extractor "Aquí Santoña" (`comercial@aquisantona.com`).
- 🟡 Refactor `gmail.py:conectar()` (deuda OAuth).
- `/documentos` Cloud Opción A.

---

## Estado CI final

URL: https://github.com/TascaBarea/gestion-facturas/actions/runs/25403946824

Resultado: **success** ✅ · 51s de duración · **179 passed, 1 skipped** en el paso de cobertura.

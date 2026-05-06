# Bloque B + Filtrado no-factura — gmail.py v1.25

**Sesión:** 06/05/2026 (tercera del día tras Bloque A y v1.24 MAESTRO)
**Modo:** auto-accept

---

## Resumen ejecutivo

Refactor de `_nombre_aproximado` a 4 capas + nuevo detector `_es_factura_valida`. Corrige 2 bugs descubiertos al analizar PDFs reales: heurística capturaba CLIENTE/etiquetas como proveedor; gmail.py procesaba catálogos como facturas. 22 tests añadidos + 2 adaptados. Suite local 179 passed, CI verde.

---

## Bugs cubiertos

| # | Bug | Caso real |
|---|---|---|
| 1 | `_nombre_aproximado` capturaba nombre cliente | COMPROVINO 04/05: capturó "COMESTIBLES BAREA" |
| 1bis | Capturaba etiquetas plantilla | Torres Import: capturaría "FORMA DE PAGO" |
| 2 | Procesaba PDFs no-factura como facturas | Aquí Santoña 04/05: catálogo 21 pág. → entrada basura en Excel |

---

## Validación cruzada (textos reales)

| PDF | _nombre_aproximado v1.24 | _nombre_aproximado v1.25 | _es_factura_valida v1.25 |
|---|---|---|---|
| Torres Import | "FORMA DE PAGO" ❌ | **"TORRES IMPORT S.A.U."** ✅ (Capa 4) | 4/4 marcadores ✅ |
| COMPROVINO | "COMESTIBLES BAREA" ❌ | **"COMPROVINO SL"** ✅ (Capa 4) | 4/4 marcadores ✅ |
| Aquí Santoña | (cualquier línea catálogo) | (n/a — no es factura) | **0/4 marcadores** ✅ → REVISAR |

---

## Cambios en `gmail/gmail.py`

### `CONFIG.NOMBRES_CLIENTE` (nueva)

Lista negra de nombres del cliente (`TASCA BAREA`, `COMESTIBLES BAREA`, etc.).

### `_es_nombre_proveedor_razonable` (helper nuevo)

Centraliza criterio: longitud + letras + sin keywords + sin nombre cliente.

### `_nombre_aproximado` (refactor a 4 capas)

| Capa | Estrategia |
|---|---|
| 4 | Sufijo societario (S.A.U./S.L.U./S.L.L./S.A./S.L./S.COOP) |
| 2 | Proximidad al CIF detectado por regex (1-3 líneas antes) |
| 0 | Primera línea razonable (Capa 0 antigua + lista negra) |
| 1 | Lista negra `NOMBRES_CLIENTE` (filtro transversal a 4/2/0) |

Fallbacks: nombre_remitente → local-part email → "DESCONOCIDO".

### `_es_factura_valida` (detector nuevo)

Cuenta 4 marcadores:
1. Nº factura (regex `factura/invoice` + alfanumérico)
2. Fecha (`dd/mm/yyyy`, `dd-mm-yyyy`, `dd.mm.yyyy`)
3. Importe (`TOTAL/BASE IMPONIBLE/IVA` + número)
4. CIF/NIF español

Umbral ≥2 → factura. <2 → marca `requiere_revision` con motivo "Posible no-factura". **No descarta el procesamiento** — estrategia conservadora.

### Integración en `_procesar_pdf`

Detector se invoca tras identificar el proveedor pero antes de la lógica `if not proveedor:`. Si no es factura, marca REVISAR con motivo claro y loggea WARNING.

---

## Tests

### Nuevo: `tests/unit/test_bloque_b.py` (22 tests)

```
CONFIG.NOMBRES_CLIENTE:                                    2 tests ✓
_es_nombre_proveedor_razonable:                            8 tests ✓
_nombre_aproximado (4 capas + 3 fallback + 1 regresión):   7 tests ✓
_es_factura_valida (5 escenarios):                         5 tests ✓
```

### Adaptado: `tests/unit/test_nombre_aproximado.py` (6 tests preservados)

2 tests que invocaban como método estático (`GmailProcessor._nombre_aproximado(None, ...)`) cambian a invocación con instancia (`proc._nombre_aproximado(...)`) porque v1.25 usa `self` para acceder a helpers (`_es_nombre_proveedor_razonable`) y constantes (`_SUFIJOS_SOCIETARIOS`). La firma se mantiene (3 params); cambia solo cómo los tests la invocan.

Los otros 4 tests siguen invocando con `None` porque pasan `texto_pdf=""` y caen al fallback sin tocar `self`.

### Resultado

| | Antes (v1.24) | Después (v1.25) |
|---|---|---|
| Suite local `-m unit` | 157 passed | **179 passed** |
| Failed | 0 | 0 |
| CI | — | (esperando run tras push 91f648c) |

---

## Decisiones senior tomadas durante la sesión

1. **Test `test_nombre_aproximado_capa0_fallback_primera_linea`**: el plan usaba "PROVEEDOR ARTESANAL" como nombre de prueba, pero la palabra "proveedor" está en `_KEYWORDS_NO_NOMBRE` (rechaza etiquetas tipo "Datos del proveedor:"). Inconsistencia interna del plan. Cambié el texto a "ARTESANIA LOCAL" para que sea consistente con la lista negra.
2. **Regresión 2 tests `test_nombre_aproximado.py`**: el plan ordenaba STOP. Tras consultar al usuario, opción A (adaptar tests a usar instancia) — solución mínima que preserva cobertura sin tocar la API. Documentado en commit.

---

## Sync VPS

VPS HEAD = `00eceff`. Verificación grep: 8 matches de `NOMBRES_CLIENTE|_es_factura_valida` en gmail.py. Sync OK.

---

## Commits

| Hash | Asunto |
|---|---|
| `91f648c` | `feat(gmail): bloque B + filtrado no-factura — heurística proveedor v1.24 → v1.25` |
| `00eceff` | `fix(tests): usar __new__ en lugar de __init__ para evitar cargar MAESTRO` |

**Iteración CI**:
- Push `91f648c` → failure: tests fallaron en CI por `FileNotFoundError: /opt/gestion-facturas/datos/MAESTRO_PROVEEDORES.xlsx` (MAESTRO está gitignored, no existe en runner). Local pasaba porque sí lo tenía.
- Fix push `00eceff` → success ✅: usar `GmailProcessor.__new__(GmailProcessor)` en `_make_processor()` para crear instancia sin invocar `__init__`. Los métodos testeados no acceden a `self.maestro`, así que `__new__` basta.

---

## Backlog actualizado

### Cerrado
- 🟡 Bloque B (auditoría) — heurística cliente/proveedor.
- 🟢 Filtrado no-factura (caso Aquí Santoña 04/05).

### Vivo
- 🟡 `Parseo/extractores/pifema.py` (fecha futura + total no extraído).
- 🟢 Alta MAESTRO + extractor "Aquí Santoña" / "Torres Import" (la heurística v1.25 mejora la detección, pero el alta MAESTRO formal sigue pendiente).
- 🟡 Refactor `gmail.py:conectar()` (deuda OAuth).
- 🟡 Bloques C / D auditoría (Excel I/O, refactor modular).
- `/documentos` Cloud Opción A.

---

## Validación pendiente

Próxima ejecución manual de `gmail.py --produccion` validará:
- Si llega factura COMPROVINO → debe procesarse limpiamente (alta MAESTRO ya existe + heurística mejorada).
- Si llega factura Torres Import → "TORRES IMPORT S.A.U." capturado (en lugar de "FORMA DE PAGO").
- Si llega catálogo / brochure → marcado REVISAR con motivo "Posible no-factura".

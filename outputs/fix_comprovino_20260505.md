# Fix COMPROVINO — extractor + alta MAESTRO + cierre backlog B85501989

**Sesión:** 05/05/2026 (cuarto cierre del día)
**Modo:** auto-accept

---

## Resumen ejecutivo

1. **Cierra dual backlog**: 🟢 "Investigar CIF B85501989" → es CIF de **COMPROVINO SL** (proveedor de vinos), el log del 04/05 leyó mal la cabecera del PDF y registró erróneamente "COMESTIBLES BAREA" como proveedor.
2. **Extractor nuevo** `Parseo/extractores/comprovino.py` (commit Parseo `e6aabf7`). Smoke test verde 3/3 sobre 1 PDF.
3. **Alta MAESTRO** fila 197 (CUENTA vacía, la rellena Kinema). 196 → 197 filas. Backup creado.
4. **Deploy VPS** md5-match `5a0c7f995d1f8fee176d6f4be032f02b`.
5. La próxima factura COMPROVINO se procesará limpiamente (alias COMPROVINO/BODEGABIERTA en MAESTRO + extractor con `cif='B85501989'` estático).

---

## Contexto del bug original

Log del 04/05/2026 línea 119:
```
Proveedor NUEVO (no en MAESTRO): COMESTIBLES BAREA (CIF B85501989)
```

**Causa raíz**: el PDF de COMPROVINO (`2T26 0430 COMPROVINO TF.pdf`) tiene la cabecera "FACTURA" estructurada con los datos del **CLIENTE** en posición visualmente prominente:

```
FACTURA
COMESTIBLES BAREA          ← cliente (prominente)
665381585
Elena de Miguel
TASCA BAREA S.L.
COMPROVINO SL              ← proveedor (a la izquierda, jerarquía menor)
BODEGABIERTA Rodas 2,
C/ ESPIRITU SANTO, 36. LOCAL 2
28005 MADRID                ← dir cliente
28004 MADRID                ← dir proveedor
...
C.I.F. B85501989 B87760575  ← proveedor primero, cliente segundo
```

La heurística genérica de gmail.py extrajo "COMESTIBLES BAREA" como proveedor y `B85501989` (que es del proveedor) como su CIF. Confusión cliente/proveedor.

---

## Estructura PDF observada

| Campo | Valor | Pattern crítico |
|---|---|---|
| TOTAL | 255,21 € | `TOTAL FACTURA\s+([\d.,]+)\s*€` (multilínea — el € está en línea siguiente) |
| Fecha factura | 30/04/2026 | `A/\d+\s+(\d{2})/(\d{2})/(\d{4})` (anclado a REF para no capturar fecha albarán) |
| REF | A/261096 | `\b(A/\d{4,8})\b` (no captura `Nº Albarán 260646`) |
| CIFs | `B85501989 B87760575` | NO se parsea — `cif` estático en clase |
| Subtotal | 210,92 € | (no usado) |
| Descuento P.Pago | 7% (15,88€) | (no usado) |
| IVA | 21% (44,29€) | (no usado) |
| Forma pago | TRANSFERENCIA DIA15 | (codificado TF en MAESTRO) |

---

## Extractor

`Parseo/extractores/comprovino.py` (~110 líneas).
- Decorador: `@registrar('COMPROVINO SL', 'COMPROVINO S.L.', 'COMPROVINO', 'BODEGABIERTA')`
- Clase: `ExtractorComprovino(ExtractorBase)`
- Atributos:
  - `nombre = 'COMPROVINO SL'`
  - `cif = 'B85501989'` ← **estático para evitar bug cliente/proveedor**
  - `iban = 'ES34 0049 6129 0020 1603 4741'`
  - `metodo_pdf = 'pdfplumber'`
  - `categoria_fija = 'VINOS'`
- Métodos: `extraer_total / extraer_fecha / extraer_referencia` (los 3 verificados).
- `extraer_lineas`: TODO `→ []` (descuento global proporcional 7%, mismo patrón que jaleo.py).
- `extraer_forma_pago`: NO implementado (MAESTRO define TF).

---

## Smoke test

```
=== Registro extractores ===
  COMPROVINO SL          -> ExtractorComprovino
  COMPROVINO S.L.        -> ExtractorComprovino
  COMPROVINO             -> ExtractorComprovino
  BODEGABIERTA           -> ExtractorComprovino

[OK] CIF estático = B85501989 (no captura cliente B87760575)

=== Smoke test ===
  [OK]   total: got=255.21  exp=255.21
  [OK]   fecha: got='30/04/2026'  exp='30/04/2026'
  [OK]   ref: got='A/261096'  exp='A/261096'
  [info] lineas: 0 (TODO esperado: 0)
RESULTADO: VERDE
```

Test anti-confusión cliente/proveedor (defensivo): `assert extractor.cif == "B85501989"` y `assert extractor.cif != "B87760575"`. Pasa.

---

## Alta MAESTRO

Posición: fila 197 (al final). MAESTRO 196 → 197 filas.

```
CUENTA            = None                  (rellena Kinema)
PROVEEDOR         = COMPROVINO SL
CLASE             = 2                     (proveedor regular, igual JALEO/Gredales)
ALIAS             = COMPROVINO, COMPROVINO S.L., BODEGABIERTA
CIF               = B85501989
IBAN              = ES34 0049 6129 0020 1603 4741
FORMA_PAGO        = TF                    (TRANSFERENCIA DIA15)
EMAIL             = info@bodegabierta.es
TIENE_EXTRACTOR   = SI
ARCHIVO_EXTRACTOR = comprovino.py
TIPO_CATEGORIA    = HARDCODED
CATEGORIA_FIJA    = VINOS
METODO_PDF        = pdfplumber
ACTIVO            = SI
NOTAS             = Alta 05/05/2026. Cierra backlog CIF B85501989 detectado
                    erroneamente como COMESTIBLES BAREA en log 04/05.
```

Backup: `datos/MAESTRO_PROVEEDORES_backup_20260505_2320.xlsx`.

---

## Deploy VPS

| | md5 |
|---|---|
| PC `Parseo/extractores/comprovino.py` | `5a0c7f995d1f8fee176d6f4be032f02b` |
| VPS `/opt/Parseo/extractores/comprovino.py` | `5a0c7f995d1f8fee176d6f4be032f02b` |

`__pycache__` limpiados local + VPS.

**MAESTRO_PROVEEDORES.xlsx**: gitignored → sync por scp manual al VPS:

| | md5 |
|---|---|
| PC `datos/MAESTRO_PROVEEDORES.xlsx` | `6d40e5779cd627b249f696a3491db0bf` |
| VPS `/opt/gestion-facturas/datos/MAESTRO_PROVEEDORES.xlsx` | `6d40e5779cd627b249f696a3491db0bf` |

Hallazgo colateral: el MAESTRO del VPS llevaba **desfasado desde 23/04** (mtime 23 abr). Como gmail.py ya no se ejecuta en VPS (decisión 05/05 TARDE), no había impacto en producción. Backup pre-resync en VPS: `datos/backups/MAESTRO_PROVEEDORES_pre_resync_20260505.xlsx`.

---

## Validación pendiente

La próxima factura COMPROVINO que llegue será test natural end-to-end. La ejecución manual de `python gmail.py --produccion` (cuando el usuario lo decida) debería:
1. Detectar el email entrante.
2. Identificar proveedor → `COMPROVINO SL` vía MAESTRO (alias matchea con BODEGABIERTA si el remitente lo usa).
3. Cargar `comprovino.py`.
4. Rellenar TOTAL/FECHA/REF correctamente.
5. **NO** crear fila zombi ni "Proveedor NUEVO" en log.

---

## Backlog cerrado tras esta sesión

- 🟢 `[CERRADO]` Investigar CIF `B85501989` para "COMESTIBLES BAREA" → es COMPROVINO SL.

## Backlog vivo (sin cambios)

- 🟢 Alta MAESTRO + extractor para "Aquí Santoña" (`comercial@aquisantona.com`).
- 🟡 Refactor `gmail.py:conectar()` (deuda OAuth).
- 🟡 4 ImportError CI por deps faltantes en workflow.
- 🟡 22 fallos async en `test_api_security.py` (falta `pytest-asyncio`).
- `/documentos` Cloud Opción A.

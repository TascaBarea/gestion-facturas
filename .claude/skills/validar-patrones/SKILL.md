---
name: validar-patrones
description: Valida que los patrones regex del extractor generico de gmail.py funcionan correctamente contra textos de prueba.
disable-model-invocation: true
argument-hint: "[completo]"
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Validar Patrones Regex de gmail.py

Extrae y testea los patrones regex del extractor generico (clase ExtractorPDF en gmail/gmail.py).
Detecta roturas silenciosas como dobles backslash en raw strings.

## 1. Crear script de test temporal

Crea el archivo `gmail/_test_patrones_skill.py` con el siguiente contenido:

```python
"""Test automatico de patrones regex del ExtractorPDF"""
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open(r'c:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\gmail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extraer patrones ejecutando asignaciones
code_lines = []
capturing = False
for line in lines:
    stripped = line.strip()
    if any(stripped.startswith(x) for x in ['PATRONES_FECHA', 'PATRONES_TOTAL', 'PATRONES_REF', 'PATRON_IBAN']):
        capturing = True
    if capturing:
        code_lines.append(line)
        if stripped.endswith(']') or (stripped.startswith('PATRON_IBAN') and stripped.endswith("'")):
            capturing = False

ns = {}
dedented = [line.lstrip() for line in code_lines]
exec('\n'.join(dedented), ns)

PATRONES_FECHA = ns['PATRONES_FECHA']
PATRONES_TOTAL = ns['PATRONES_TOTAL']
PATRONES_REF = ns['PATRONES_REF']
PATRON_IBAN = ns['PATRON_IBAN']

ok = fail = 0

def test(nombre, pats, texto):
    global ok, fail
    plist = pats if isinstance(pats, list) else [pats]
    for p in plist:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            print(f'  OK  {nombre}: {m.group()!r}')
            ok += 1
            return
    print(f'  FAIL {nombre}: sin match en {texto!r}')
    fail += 1

# Verificar dobles backslash (bug conocido)
for i, p in enumerate(PATRONES_FECHA + PATRONES_TOTAL + PATRONES_REF + [PATRON_IBAN]):
    if '\\\\' in p:
        print(f'  BUG  Patron {i}: contiene doble backslash → regex roto')
        fail += 1

print('=== PATRONES_FECHA ===')
test('Fecha dd/mm/yyyy', PATRONES_FECHA, 'fecha: 15/03/2026')
test('Fecha dd-mm-yy', PATRONES_FECHA, 'fecha: 15-03-26')
test('Fecha texto', PATRONES_FECHA, '3 de marzo de 2026')
test('Fecha yyyy-mm-dd', PATRONES_FECHA, '2026-03-15')

print('\n=== PATRONES_TOTAL ===')
test('Total con puntos', PATRONES_TOTAL, 'importe total....... 56,78')
test('Total factura', PATRONES_TOTAL, 'Total factura: 123,45')
test('Total simple', PATRONES_TOTAL, 'total: 99,99')
test('Total con miles', PATRONES_TOTAL, 'total: 1.234,56')
test('Importe total', PATRONES_TOTAL, 'importe total: 45,00')

print('\n=== PATRONES_REF ===')
test('Ref factura', PATRONES_REF, 'factura: FA2026/001')
test('Ref numero', PATRONES_REF, 'ref: 20260315')

print('\n=== PATRON_IBAN ===')
test('IBAN ES', [PATRON_IBAN], 'IBAN: ES12 3456 7890 12 3456789012')

print(f'\n{"="*40}')
print(f'Resultado: {ok} OK, {fail} FAIL')
if fail:
    sys.exit(1)
```

## 2. Ejecutar el test

```bash
cd c:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas && python gmail/_test_patrones_skill.py
```

## 3. Limpiar

Borrar el script temporal:
```bash
rm gmail/_test_patrones_skill.py
```

## 4. Si $ARGUMENTS contiene "completo"

Ademas de los patrones, verificar tambien:
- Que `nucleo/maestro.py` importa correctamente: `python -c "from nucleo.maestro import Proveedor, MaestroProveedores, normalizar_nombre_proveedor; print('nucleo OK')"`
- Que `gmail/gmail.py` compila: `python -c "import py_compile; py_compile.compile('gmail/gmail.py', doraise=True); print('gmail.py OK')"`
- Que no hay imports inline huerfanos: `grep -n "^\s*import \(io\|time\|tempfile\|traceback\|importlib\)" gmail/gmail.py`

## 5. Presentar resumen

```
VALIDACION PATRONES - gmail.py
================================
FECHA:  X/4 OK
TOTAL:  X/5 OK
REF:    X/2 OK
IBAN:   X/1 OK
BUGS:   X dobles backslash detectados

Resultado: XX OK, XX FAIL
```

Idioma: espanol. Sin emojis.

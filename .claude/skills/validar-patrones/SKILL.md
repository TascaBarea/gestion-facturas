---
name: validar-patrones
description: Valida que las funciones de extraccion de nucleo/parser.py funcionan correctamente contra textos de prueba.
disable-model-invocation: true
argument-hint: "[completo]"
---

# Validar Extractor Generico (nucleo/parser + ExtractorPDF)

Testea las funciones de extraccion centralizadas en nucleo/parser.py que usa
el ExtractorPDF de gmail.py. Detecta regresiones en patrones regex.

## 1. Crear script de test temporal

Crea el archivo `gmail/_test_patrones_skill.py` con el siguiente contenido:

```python
"""Test automatico de extraccion: nucleo/parser.py + ExtractorPDF"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'c:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas')
sys.path.insert(0, '.')

from nucleo.parser import extraer_fecha, extraer_total, extraer_referencia, extraer_iban

ok = fail = 0

def test(nombre, funcion, texto, esperado_tipo='any'):
    global ok, fail
    resultado = funcion(texto)
    if resultado is not None:
        print(f'  OK  {nombre}: {resultado!r}')
        ok += 1
    else:
        print(f'  FAIL {nombre}: sin resultado en {texto!r}')
        fail += 1

print('=== FECHA ===')
test('Fecha dd/mm/yyyy', extraer_fecha, 'Fecha factura: 15/03/2026')
test('Fecha dd-mm-yy', extraer_fecha, 'Fecha: 15-03-26')
test('Fecha texto', extraer_fecha, '3 de marzo de 2026')
test('Fecha con label', extraer_fecha, 'F. factura: 01/02/2026')

print('\n=== TOTAL ===')
test('Total factura', extraer_total, 'Total factura: 123,45')
test('Total importe', extraer_total, 'TOTAL IMPORTE: 56,78')
test('Total a pagar', extraer_total, 'TOTAL A PAGAR 99.99€')
test('Total con miles', extraer_total, 'Total Factura: 1.234,56')
test('Total euros', extraer_total, '123,45 Euros')

print('\n=== REFERENCIA ===')
test('Ref factura', extraer_referencia, 'Factura: FA2026/001')
test('Ref numero', extraer_referencia, 'Ref: 20260315')

print('\n=== IBAN ===')
test('IBAN ES', extraer_iban, 'IBAN: ES12 3456 7890 1234 5678 9012')

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
- Que ExtractorPDF usa nucleo/parser: `grep -n "from nucleo.parser import" gmail/gmail.py`

## 5. Presentar resumen

```
VALIDACION EXTRACTOR GENERICO
================================
FECHA:  X/4 OK
TOTAL:  X/5 OK
REF:    X/2 OK
IBAN:   X/1 OK

Resultado: XX OK, XX FAIL
```

Idioma: espanol. Sin emojis.

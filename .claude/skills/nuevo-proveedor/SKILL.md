---
name: nuevo-proveedor
description: Registra un proveedor nuevo completo: alta en MAESTRO, alias, extractor PDF y test. Checklist de 8 pasos.
disable-model-invocation: true
argument-hint: "<nombre_proveedor>  ej: ANGEL BORJA, PRODUCTOS DEL SUR"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Alta de Proveedor Nuevo

Checklist completo para dar de alta un proveedor nuevo en el sistema.

## Requisito previo

El usuario debe indicar el nombre del proveedor y proporcionar (o localizar) una factura PDF de ejemplo.
Si falta alguno de estos datos, pedirlos antes de continuar.

## Paso 1: Verificar que no existe ya

```bash
python -c "
import pandas as pd
df = pd.read_excel('datos/MAESTRO_PROVEEDORES.xlsx')
print(df[df['PROVEEDOR'].str.contains('$1', case=False, na=False)][['PROVEEDOR','CIF','TIENE_EXTRACTOR']].to_string())
"
```

Si ya existe, informar al usuario y no continuar.

## Paso 2: Extraer texto del PDF para identificar datos

```bash
python -c "
import pdfplumber
with pdfplumber.open(r'RUTA_PDF') as pdf:
    for i, p in enumerate(pdf.pages):
        print(f'--- PAG {i+1} ---')
        print(p.extract_text())
"
```

Del texto, extraer:
- **Nombre oficial** del proveedor (como aparece en la cabecera)
- **CIF** (formato B12345678)
- **IBAN** si aparece (para pagos por transferencia)
- **Tipo de IVA**: 4% (lácteos, pan), 10% (alimentación general), 21% (servicios, alcohol)
- **Si es PDF texto o imagen** (si el texto salió vacío → imagen → necesita OCR)

## Paso 3: Alta en MAESTRO_PROVEEDORES

**Confirmar con el usuario que el Excel está cerrado antes de escribir.**

```bash
python -c "
import pandas as pd, openpyxl
df = pd.read_excel('datos/MAESTRO_PROVEEDORES.xlsx')
nueva_fila = {
    'PROVEEDOR': 'NOMBRE OFICIAL',
    'CIF': 'B12345678',
    'IBAN': 'ES00 0000 0000 0000 0000 0000',
    'TIENE_EXTRACTOR': True,
    'CATEGORIA': 'CATEGORIA_CORRECTA',
    'ACTIVO': True
}
df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
df.to_excel('datos/MAESTRO_PROVEEDORES.xlsx', index=False)
print('Alta completada')
"
```

## Paso 4: Añadir alias al maestro

Los alias permiten el matching fuzzy en cuadre.py y gmail.py. Añadir variaciones comunes del nombre:
- Nombre corto (sin S.L., S.A., S.L.U.)
- Nombre como aparece en el banco (puede ser diferente)
- CIF como alias (para pagos por transferencia donde el banco pone el CIF)

Abrir `datos/MAESTRO_PROVEEDORES.xlsx` hoja `ALIASES` y añadir las filas correspondientes.

## Paso 5: Crear el extractor

Invocar `/extractor` con el PDF del proveedor:
```
/extractor NOMBRE_PROVEEDOR RUTA_PDF
```

O seguir manualmente:
- Copiar `C:/_ARCHIVOS/TRABAJO/Facturas/Parseo/extractores/_plantilla.py`
- Renombrar a `nombre_proveedor.py` (snake_case, sin tildes)
- Implementar `extraer_lineas()` y métodos necesarios según formato del PDF

## Paso 6: Limpiar caché (OBLIGATORIO)

```cmd
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\__pycache__"
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\nucleo\__pycache__"
rmdir /s /q "C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\__pycache__"
```

## Paso 7: Probar con PDF real

```bash
python -c "
import sys; sys.path.insert(0, r'C:/_ARCHIVOS/TRABAJO/Facturas/Parseo')
from extractores import obtener_extractor
ext = obtener_extractor('NOMBRE_PROVEEDOR')
import pdfplumber
with pdfplumber.open(r'RUTA_PDF') as pdf:
    texto = chr(10).join(p.extract_text() or '' for p in pdf.pages)
lineas = ext.extraer_lineas(texto)
total = ext.extraer_total(texto)
suma = sum(l['base'] * (1 + l['iva']/100) for l in lineas)
print(f'Total factura: {total}')
print(f'Suma lineas:   {round(suma, 2)}')
print(f'Cuadre: {\"OK\" if abs(total - suma) < 0.05 else \"DESCUADRE\"} (diff={round(total-suma, 2)})')
print(f'Fecha: {ext.extraer_fecha(texto)}')
print(f'Ref:   {ext.extraer_referencia(texto)}')
for l in lineas[:5]:
    print(f'  {l}')
"
```

## Paso 8: Actualizar ESQUEMA y confirmar

- Incrementar contador de extractores en ESQUEMA (sección 5.7.5)
- Reportar al usuario: proveedor dado de alta, extractor funcionando, cuadre OK
- Si hubo alguna incidencia (PDF imagen, IVA especial, alias necesario), documentar en `tasks/lessons.md`

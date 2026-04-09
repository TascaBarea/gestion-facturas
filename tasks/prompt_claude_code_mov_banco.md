# TAREA: Integrar script actualizar_movimientos.py en gestion-facturas

## CONTEXTO
Hay un script nuevo `actualizar_movimientos.py` descargado en `C:\Users\jaime\Downloads\actualizar_movimientos.py`.
Este script lee archivos .xls de Banco Sabadell y actualiza el consolidado `Movimientos_Cuenta_26.xlsx`.

El proyecto está en `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\`.
Ya existe un script viejo `scripts/mov_banco.py` — debe ser REEMPLAZADO por el nuevo.

## PASOS A EJECUTAR EN ORDEN

### 1. Copiar script nuevo
```
copy "C:\Users\jaime\Downloads\actualizar_movimientos.py" "scripts\actualizar_movimientos.py"
```

### 2. Verificar que funciona
```
python scripts/actualizar_movimientos.py --info --consolidado datos/Movimientos_Cuenta_26.xlsx
```
Debe mostrar las pestañas Tasca y Comestibles con sus rangos de fechas.

### 3. Test con archivos del banco (DRY-RUN primero)
Buscar archivos .xls en Downloads:
```
dir C:\Users\jaime\Downloads\*.xls
```
Si hay archivos tipo `07042026_0259_*.xls`, ejecutar:
```
python scripts/actualizar_movimientos.py --dry-run --consolidado datos/Movimientos_Cuenta_26.xlsx C:\Users\jaime\Downloads\07042026_0259_0001844495.xls C:\Users\jaime\Downloads\07042026_0259_0001992404.xls
```
Verificar que detecta cuenta (Tasca/Comestibles), cuenta movimientos y duplicados.

### 4. Ejecutar de verdad
Si el dry-run es correcto:
```
python scripts/actualizar_movimientos.py --consolidado datos/Movimientos_Cuenta_26.xlsx C:\Users\jaime\Downloads\07042026_0259_0001844495.xls C:\Users\jaime\Downloads\07042026_0259_0001992404.xls
```
Debe crear backup automático y mostrar resumen.

### 5. Verificar continuidad de saldos
Ejecutar este test:
```python
python -c "
from openpyxl import load_workbook
wb = load_workbook('datos/Movimientos_Cuenta_26.xlsx', data_only=True)
for s in wb.sheetnames:
    ws = wb[s]
    errores = 0
    for r in range(3, ws.max_row+1):
        sa = float(ws.cell(r-1,6).value or 0)
        imp = float(ws.cell(r,5).value or 0)
        sc = float(ws.cell(r,6).value or 0)
        if abs(round(sa+imp,2) - sc) > 0.01:
            errores += 1
    print(f'{s}: {ws.max_row-1} filas | Errores continuidad saldo: {errores}')
"
```
**DEBE dar 0 errores en ambas pestañas.** Si hay errores, PARA y reporta.

### 6. Crear página Streamlit para Operaciones
Crear `streamlit_app/pages/mov_banco.py` con esta funcionalidad:

- Título: "🏦 Actualizar Movimientos Banco"
- Sección info: mostrar estado actual del consolidado (filas, rango fechas por pestaña)
- File uploader: `st.file_uploader` que acepte múltiples .xls
- Al subir archivos:
  - Detectar cuenta automáticamente (mostrar qué cuenta es cada archivo)
  - Mostrar preview: cuántos movimientos tiene cada archivo, rango de fechas
  - Mostrar cuántos son nuevos vs duplicados (dry-run)
- Botón "Actualizar": ejecuta la actualización real
- Mostrar resumen: nuevos incorporados, duplicados ignorados, backup creado
- Verificar y mostrar continuidad de saldos (0 errores = ✅, >0 = ❌)

La página debe importar funciones de `scripts/actualizar_movimientos.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from actualizar_movimientos import actualizar, leer_xls_sabadell, mostrar_info, detectar_cuenta
```

Ruta del consolidado:
```python
CONSOLIDADO = os.path.join(os.path.dirname(__file__), '..', '..', 'datos', 'Movimientos_Cuenta_26.xlsx')
```

### 7. Registrar la página en app.py
Añadir `mov_banco` a la sección OPERACIONES en `app.py`, con icono 🏦 y título "Mov. Banco".

### 8. Tests finales
- `python -c "import ast; ast.parse(open('streamlit_app/pages/mov_banco.py', encoding='utf-8').read()); print('Sintaxis OK')"`
- `python -c "import ast; ast.parse(open('scripts/actualizar_movimientos.py', encoding='utf-8').read()); print('Sintaxis OK')"`
- Verificar que la app arranca: `timeout 10 streamlit run streamlit_app/app.py`

## REGLAS
- NO modifiques el CSS ni la lógica de login de app.py
- NO reordenes movimientos existentes — el orden del consolidado es sagrado (cadena de saldos)
- El script usa xlrd para .xls y openpyxl para .xlsx — NO cambies esas dependencias
- Si algo falla, reporta el error exacto, no intentes arreglarlo creativamente
- Clave deduplicación: F.Operativa + Concepto + Importe + Saldo (los 4 campos juntos)

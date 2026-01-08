# 📋 INSTRUCCIONES - Aplicar cambios FUZZY MATCHING

## 📦 ARCHIVOS A MODIFICAR

Hay **3 archivos** que necesitan cambios:

| Archivo | Cambio | Complejidad |
|---------|--------|-------------|
| `main.py` | Reemplazar completo | ✅ Fácil |
| `nucleo/factura.py` | Añadir 1 línea | ✅ Fácil |
| `salidas/__init__.py` | Añadir columna Excel | ⚠️ Media |

---

## PASO 1: Reemplazar main.py

```
1. Renombrar tu main.py actual:
   main.py → main_backup_v40.py

2. Copiar el nuevo:
   main_v45.py → main.py
```

---

## PASO 2: Modificar nucleo/factura.py

Buscar la clase `LineaFactura` (debería ser un `@dataclass`):

```python
@dataclass
class LineaFactura:
    articulo: str = ''
    base: float = 0.0
    iva: int = 21
    codigo: str = ''
    cantidad: float = None
    precio_ud: float = None
    categoria: str = ''
    id_categoria: str = ''
    # ... otros campos que tengas ...
```

**AÑADIR esta línea** al final de los campos:

```python
    match_info: str = ''   # NUEVO: tipo de match (EXACTO, FUZZY_XX%, SIN_MATCH)
```

Resultado final:

```python
@dataclass
class LineaFactura:
    articulo: str = ''
    base: float = 0.0
    iva: int = 21
    codigo: str = ''
    cantidad: float = None
    precio_ud: float = None
    categoria: str = ''
    id_categoria: str = ''
    match_info: str = ''   # ← AÑADIR ESTA LÍNEA
```

---

## PASO 3: Modificar salidas/__init__.py (o donde generes Excel)

Buscar donde se crean las columnas del Excel. Debería haber algo como:

```python
columnas = ['#', 'FECHA', 'REF', 'PROVEEDOR', 'ARTICULO', 'CATEGORIA', ...]
```

**AÑADIR 'MATCH_INFO'** después de 'CATEGORIA':

```python
columnas = ['#', 'FECHA', 'REF', 'PROVEEDOR', 'ARTICULO', 'CATEGORIA', 'MATCH_INFO', ...]
```

Y donde se escriben los datos de cada línea, añadir:

```python
fila['MATCH_INFO'] = linea.match_info if hasattr(linea, 'match_info') else ''
```

---

## 📊 RESULTADO ESPERADO

Después de aplicar los cambios, tu Excel de salida tendrá una nueva columna:

| PROVEEDOR | ARTICULO | CATEGORIA | **MATCH_INFO** |
|-----------|----------|-----------|----------------|
| CERES | ALH SIN 1/5 RET | CERVEZA | EXACTO |
| CERES | ALHSIN 1/5 RET | CERVEZA | **FUZZY_98%** |
| CERES | PRODUCTO NUEVO | PENDIENTE | SIN_MATCH |

### Cómo interpretar MATCH_INFO:

| Valor | Significado | Acción |
|-------|-------------|--------|
| `EXACTO` | Match por substring (como antes) | ✅ Confiable |
| `FUZZY_XX%` | Match por similitud XX% | ⚠️ Revisar si es correcto |
| `SIN_MATCH` | No se encontró coincidencia | Corregir manualmente |

---

## 🔍 CÓMO REVISAR LOS FUZZY

En Excel:
1. Filtrar columna MATCH_INFO por los que empiezan por "FUZZY"
2. Revisar si la CATEGORIA asignada es correcta
3. Si alguno está mal → corregir y ejecutar `actualizar_diccionario.py`

---

## ⚠️ SI NO QUIERES LA COLUMNA MATCH_INFO

Si prefieres que funcione sin modificar `nucleo/factura.py` ni `salidas/`:

El main.py funcionará igual, pero:
- No verás la columna MATCH_INFO en el Excel
- El fuzzy matching seguirá funcionando
- Solo perderás la trazabilidad de qué fue FUZZY vs EXACTO

Para esto, simplemente **ignora los pasos 2 y 3** y solo reemplaza main.py.

---

## 📋 RESUMEN DE CAMBIOS EN CÓDIGO

### main.py (líneas nuevas/modificadas):

```python
# Línea ~18: NUEVO import
from difflib import SequenceMatcher

# Líneas ~48-65: NUEVA función
def normalizar_proveedor(nombre: str) -> str:
    ...

# Líneas ~83-140: FUNCIÓN MODIFICADA categorizar_linea()
def categorizar_linea(linea, proveedor, indice):
    # Ahora incluye fuzzy matching
    ...
```

### nucleo/factura.py:

```python
# En la clase LineaFactura, añadir:
match_info: str = ''
```

### salidas/__init__.py:

```python
# Añadir columna 'MATCH_INFO' al Excel
```

---

## ✅ VERIFICACIÓN

Después de aplicar los cambios, ejecuta:

```cmd
python main.py -i "C:\_ARCHIVOS\TRABAJO\Facturas\1 TRI 2025" -o test_fuzzy.xlsx
```

Y verifica que:
1. No hay errores
2. El archivo `outputs/test_fuzzy.xlsx` se genera
3. (Opcional) La columna MATCH_INFO aparece

---

*Creado: 22/12/2025*

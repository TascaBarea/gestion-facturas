# SOLUCIÓN DE NORMALIZACIÓN DE PROVEEDORES
## ParsearFacturas v5.12 - 04/01/2026

---

## 📦 ARCHIVOS GENERADOS

| Archivo | Descripción |
|---------|-------------|
| `identificador_proveedor.py` | Módulo principal de identificación inteligente |
| `generar_alias_proveedores.py` | Script para analizar carpetas y generar alias |
| `ALIAS_GENERADOS.py` | 150 alias auto-generados para añadir a main.py |

---

## 🔧 CÓMO INTEGRAR

### Paso 1: Copiar el módulo identificador

```bash
# Copiar a la carpeta nucleo/
cp identificador_proveedor.py ParsearFacturas-main/nucleo/
```

### Paso 2: Añadir alias generados a main.py

Copiar el contenido de `ALIAS_GENERADOS.py` y pegarlo en `ALIAS_DICCIONARIO` en main.py.

### Paso 3: Actualizar procesar_factura en main.py

```python
# Añadir al inicio de main.py
from nucleo.identificador_proveedor import (
    IdentificadorProveedor,
    ListaMaestraProveedores,
    crear_identificador
)

# Crear identificador global (una vez al inicio)
IDENTIFICADOR = None

def inicializar_identificador(ruta_maestra='datos/EXTRACTORES_COMPLETO.xlsx'):
    global IDENTIFICADOR
    lista = ListaMaestraProveedores()
    lista.cargar_desde_excel(ruta_maestra)
    lista.cargar_alias_existentes(ALIAS_DICCIONARIO)
    IDENTIFICADOR = IdentificadorProveedor(lista)

# Modificar procesar_factura():
def procesar_factura(ruta_archivo: Path, indice: dict) -> Factura:
    # NUEVO: Usar identificador inteligente
    if IDENTIFICADOR:
        cif_pdf = extraer_cif(texto) if texto else None
        resultado = IDENTIFICADOR.identificar(ruta_archivo.name, cif_pdf)
        proveedor = resultado['proveedor_canonico']
        if proveedor.startswith('PENDIENTE:'):
            proveedor = resultado['proveedor_crudo']
    else:
        # Fallback al método anterior
        info = parsear_nombre_archivo(ruta_archivo.name)
        proveedor = normalizar_proveedor(info.get('proveedor', 'DESCONOCIDO'))
    
    # ... resto del código
```

---

## 📊 RESULTADOS ESPERADOS

### Antes (v5.11)
- 371 proveedores únicos (fragmentados)
- 72.5% de cuadre

### Después (v5.12)
- ~150 proveedores unificados
- ~78-80% de cuadre estimado

### Alias auto-generados: 150

Ejemplos:
```python
# VIRGEN DE LA SIERRA (todas las variantes → 1 nombre)
'BODEGA VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
'BODEGAS VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
'COOPERATIVA VIRGEN DE LA SIERRA': 'VIRGEN DE LA SIERRA',
'VIRGEN DE LA SIERA': 'VIRGEN DE LA SIERRA',  # typo corregido

# BM SUPERMERCADOS
'BM': 'BM SUPERMERCADOS',
'2 BM': 'BM SUPERMERCADOS',

# CERES (elimina prefijos de fecha)
'1T25 0328 CERES': 'CERES',
'2T25 0422 CERES': 'CERES',
```

---

## ⚠️ PROVEEDORES QUE FALTAN EN LISTA MAESTRA

Estos proveedores aparecen en las facturas pero NO están en EXTRACTORES_COMPLETO.xlsx:

| Proveedor | Facturas | Acción Recomendada |
|-----------|----------|-------------------|
| LA CUCHARA | 9 | Añadir a lista maestra + crear extractor |
| DIA | 6 | Añadir a lista maestra |
| CURRIMAR | 3 | Añadir a lista maestra |
| MAKRO | 3 | Añadir a lista maestra (ya tienes extractor) |
| ALPENDEREZ | 2+ | Añadir a lista maestra |
| LA LLEIDIRIA | 2+ | Añadir a lista maestra |

### Para añadir a EXTRACTORES_COMPLETO.xlsx:

```
PROVEEDOR,CIF,IBAN,FORMA_PAGO,TIPO_CATEGORIA,CATEGORIA_FIJA,TIENE_EXTRACTOR,ARCHIVO_EXTRACTOR
LA CUCHARA,,,,DICCIONARIO,,SI,la_cuchara.py
DIA,A28164754,,,DICCIONARIO,,NO,
CURRIMAR,,,,DICCIONARIO,,NO,
MAKRO,A28647451,,,DICCIONARIO,,SI,makro.py
ALPENDEREZ,,,,DICCIONARIO,,NO,
LA LLEIDIRIA,,,,DICCIONARIO,,NO,
```

---

## 🧪 CÓMO PROBAR

### Test rápido:
```bash
cd ParsearFacturas-main
python -c "
from nucleo.identificador_proveedor import crear_identificador

ident = crear_identificador('datos/EXTRACTORES_COMPLETO.xlsx')

# Probar varios nombres
tests = [
    '2009 2T 0512 BODEGA VIRGEN DE LA SIERRA COOP REC.pdf',
    '1234 1T25 0115 BM TJ.pdf',
    '2T25 0512 VIRGEN DE LA SIERA TF.pdf',
]

for t in tests:
    r = ident.identificar(t)
    print(f'{t[:50]}')
    print(f'  → {r[\"proveedor_canonico\"]} ({r[\"metodo\"]})')
"
```

### Test completo con carpeta:
```bash
python generar_alias_proveedores.py -i "C:\Facturas\1 TRI 2025" -m datos/EXTRACTORES_COMPLETO.xlsx
```

---

## 📋 CARACTERÍSTICAS DEL SISTEMA

### Parseo de nombres de archivo

Soporta TODOS los formatos:

| Formato | Ejemplo |
|---------|---------|
| Numerado | `2009 2T25 0512 PROVEEDOR TF.pdf` |
| Sin numerar | `2T25 0512 PROVEEDOR TF.pdf` |
| Sin año trimestre | `2T 0512 PROVEEDOR TF.pdf` |
| Atrasada numerada | `405 ATRASADA 2T25 0512 PROVEEDOR REC.pdf` |
| Atrasada sin numerar | `ATRASADA 2T25 0512 PROVEEDOR TJ.pdf` |
| Atrasada pegada | `ATRASADA2T25 0512 PROVEEDOR EF.pdf` |
| Doble número | `2001 1251 1T25 0311 PROVEEDOR RC.pdf` |

### Identificación inteligente

1. **Por CIF** (prioridad máxima) - 100% fiable
2. **Match exacto** en lista maestra
3. **Match por alias** existentes
4. **Fuzzy matching** (umbral 70%) con auto-generación de alias
5. **Pendiente** si no hay match

### Limpieza automática

- Elimina prefijos: BODEGA, BODEGAS, COOP, COOPERATIVA, etc.
- Elimina sufijos: SL, SA, SLU, etc.
- Normaliza formas de pago: REC → RC
- Corrige typos por similitud

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Integrar módulo en ParsearFacturas
2. ✅ Añadir alias generados a main.py
3. ⬜ Añadir proveedores faltantes a EXTRACTORES_COMPLETO.xlsx
4. ⬜ Ejecutar métricas para validar mejora
5. ⬜ Revisar pendientes manualmente

---

*Generado por Claude - 04/01/2026*

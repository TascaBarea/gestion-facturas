# INSTRUCCIONES DE INSTALACIÓN - ParsearFacturas v5.1

## 📦 ARCHIVOS INCLUIDOS

| Archivo | Destino | Acción |
|---------|---------|--------|
| `main_v51.py` | `main.py` | Renombrar y reemplazar |
| `bm.py` | `extractores/bm.py` | Reemplazar |
| `mercadona.py` | `extractores/mercadona.py` | Reemplazar |
| `de_luis.py` | `extractores/de_luis.py` | **NUEVO** |
| `angel_loli.py` | `extractores/angel_loli.py` | Reemplazar |
| `julio_garcia.py` | `extractores/julio_garcia.py` | **NUEVO** |
| `la_alacena.py` | `extractores/la_alacena.py` | **NUEVO** |
| `debora_garcia.py` | `extractores/debora_garcia.py` | **NUEVO** |

---

## 🔧 INSTALACIÓN PASO A PASO

### Paso 1: Backup
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

:: Backup main
copy main.py main_backup_v50.py

:: Backup extractores existentes
copy extractores\bm.py extractores\bm_backup.py
copy extractores\mercadona.py extractores\mercadona_backup.py
copy extractores\angel_loli.py extractores\angel_loli_backup.py
```

### Paso 2: Copiar archivos
```cmd
:: Main
copy [descarga]\main_v51.py main.py

:: Extractores
copy [descarga]\bm.py extractores\bm.py
copy [descarga]\mercadona.py extractores\mercadona.py
copy [descarga]\de_luis.py extractores\de_luis.py
copy [descarga]\angel_loli.py extractores\angel_loli.py
copy [descarga]\julio_garcia.py extractores\julio_garcia.py
copy [descarga]\la_alacena.py extractores\la_alacena.py
copy [descarga]\debora_garcia.py extractores\debora_garcia.py
```

### Paso 3: Actualizar __init__.py

Añadir al final de `extractores/__init__.py`:

```python
# ============================================================
# SESION 26/12/2025 - NUEVOS/ACTUALIZADOS EXTRACTORES
# ============================================================

try:
    from extractores import de_luis           # DE LUIS SABORES UNICOS (quesos Cañarejal)
except ImportError:
    pass

try:
    from extractores import julio_garcia      # JULIO GARCIA VIVAS (verduras Ay Madre)
except ImportError:
    pass

try:
    from extractores import la_alacena        # CONSERVAS LA ALACENA (conservas gourmet)
except ImportError:
    pass

try:
    from extractores import debora_garcia     # DEBORA GARCIA TOLEDANO (CO2 cerveza)
except ImportError:
    pass

try:
    from extractores import angel_loli        # ALFARERIA ANGEL Y LOLI (cacharrería)
except ImportError:
    pass
```

---

## ✅ CAMBIOS EN v5.1

### 1. Normalización mejorada de proveedor

Nuevo mapeo ALIAS_DICCIONARIO que traduce:
- `SABORES DE PATERNA` → `SABORES PATERNA`
- `FELISA GOURMET` → `FELISA`
- `QUESERIA ZUCCA` → `ZUCCA`
- `CONSERVAS LA ALACENA` → `LA ALACENA`
- Y 40+ alias más

### 2. BM SUPERMERCADOS - Línea por línea

Antes: Solo extraía resumen por IVA ("PRODUCTOS IVA REDUCIDO 10%")
Ahora: Extrae cada producto individual ("PECHUGA PAVO GRANEL", "BOQUERON ALIÑADO", etc.)

### 3. MERCADONA - Línea por línea

Antes: Solo resumen por IVA
Ahora: Extrae cada producto ("HIGIENICO DOBLE ROLL", "GAMUZA ATRAPAPOLVO", etc.)

### 4. Nuevos extractores con categoria_fija

| Proveedor | Categoría fija |
|-----------|----------------|
| DE LUIS SABORES UNICOS | QUESOS |
| ALFARERIA ANGEL Y LOLI | CACHARRERIA |
| JULIO GARCIA VIVAS | GENERICO PARA VERDURAS |
| DEBORA GARCIA TOLEDANO | Co2 GAS PARA LA CERVEZA |

### 5. CONSERVAS LA ALACENA - Sin categoria_fija

Extrae línea por línea y busca en diccionario (ya tiene 12 artículos).

### 6. Prorrateo de portes en ANGEL Y LOLI

Los 45€ de portes se distribuyen proporcionalmente entre los artículos.

---

## 🧪 VERIFICACIÓN

```cmd
python main.py --listar-extractores
```

Debe mostrar los nuevos extractores:
- DE LUIS SABORES UNICOS
- JULIO GARCIA VIVAS  
- LA ALACENA
- DEBORA GARCIA TOLEDANO
- etc.

```cmd
python main.py -i "C:\...\4 TRI 2025"
```

Deberías ver:
```
============================================================
PARSEAR FACTURAS v5.1
============================================================
```

---

## 📊 RESULTADO ESPERADO

| Métrica | v5.0 | v5.1 (esperado) |
|---------|------|-----------------|
| % PENDIENTES | 43.5% | ~25-30% |
| BM categorizados | 0% | ~80% |
| MERCADONA categorizados | 0% | ~80% |
| SABORES PATERNA | 0% | ~90% |

---

## ⚠️ SI HAY PROBLEMAS

Restaurar backups:
```cmd
copy main_backup_v50.py main.py
copy extractores\bm_backup.py extractores\bm.py
copy extractores\mercadona_backup.py extractores\mercadona.py
```

---

## 📝 PROVEEDORES CON CATEGORIA_FIJA

Estos proveedores ya NO necesitan estar en el diccionario:

| Proveedor | Categoría | IVA |
|-----------|-----------|-----|
| DE LUIS SABORES UNICOS | QUESOS | 4% |
| ALFARERIA ANGEL Y LOLI | CACHARRERIA | 21% |
| JULIO GARCIA VIVAS | GENERICO PARA VERDURAS | 4%/10%/21% |
| DEBORA GARCIA TOLEDANO | Co2 GAS PARA LA CERVEZA | 21% |
| KINEMA | GESTORIA | 21% |
| PANIFIESTO | PAN | 4% |
| FABEIRO | (varios) | - |
| SERRIN NO CHAO | (dic) | - |

---

Fecha: 26/12/2025
Versión: 5.1

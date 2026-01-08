# INSTRUCCIONES DE INSTALACIÓN - ParsearFacturas v5.0

## 📦 ARCHIVOS INCLUIDOS

| Archivo | Descripción | Destino |
|---------|-------------|---------|
| `main_v50.py` | Nueva versión principal | Renombrar a `main.py` |
| `panifiesto.py` | Extractor corregido | `extractores/panifiesto.py` |

---

## 🔧 INSTALACIÓN PASO A PASO

### Paso 1: Backup
```
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# Hacer backup del main actual
copy main.py main_backup_v45.py

# Hacer backup del panifiesto actual
copy extractores\panifiesto.py extractores\panifiesto_backup.py
```

### Paso 2: Copiar archivos nuevos
```
# Copiar main_v50.py y renombrar a main.py
copy [ruta_descarga]\main_v50.py main.py

# Copiar panifiesto.py
copy [ruta_descarga]\panifiesto.py extractores\panifiesto.py
```

### Paso 3: Verificar settings.py
Asegúrate de que `config/settings.py` tiene la ruta correcta:
```python
DICCIONARIO_DEFAULT = r"C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\datos\DiccionarioProveedoresCategoria.xlsx"
```

---

## ✅ CAMBIOS EN v5.0

### 1. Normalización de proveedor usando alias de extractores

Ahora cuando categoriza, busca usando los alias registrados:
- `QUESERIA ZUCCA` → busca como `ZUCCA`
- `FELISA GOURMET` → busca como `FELISA`
- `SABORES DE PATERNA` → busca como `SABORES PATERNA`

### 2. Prorrateo automático de portes/transporte

Keywords que activan prorrateo:
- SERVICIO URGENTE
- PORTE / PORTES
- TRANSPORTE
- ENVIO / ENVÍO
- GASTOS ENVIO / GASTOS DE ENVIO

El importe se distribuye **proporcionalmente** entre los productos.

Keywords excluidas del prorrateo (no reciben portes):
- ENVASE
- CAJA RETORNABLE
- FIANZA
- DEPOSITO

### 3. PANIFIESTO simplificado

Antes: Múltiples líneas (una por albarán/entrega)
Ahora: **UNA sola línea** con:
- Artículo: "Pan"
- Base: Total del cuadro fiscal
- IVA: 4%
- Categoría: PAN

---

## 🧪 VERIFICACIÓN

Ejecuta:
```
python main.py -i "C:\...\4 TRI 2025"
```

Deberías ver:
```
Cargando diccionario...
   50 proveedores indexados

============================================================
PARSEAR FACTURAS v5.0
============================================================
```

Y los PENDIENTES deberían bajar significativamente.

---

## 📊 RESULTADO ESPERADO

| Métrica | Antes (v4.5) | Después (v5.0) |
|---------|--------------|----------------|
| % PENDIENTES | ~60% | ~35-40% |
| PANIFIESTO líneas | 27 por factura | 1 por factura |
| CERES SERVICIO URGENTE | Línea separada | Prorrateado |

---

## ⚠️ NOTAS IMPORTANTES

1. **El prorrateo es global** - Se aplica a TODOS los proveedores que tengan líneas de porte/transporte.

2. **ZUCCA no se ve afectado** - Ya incluye portes en sus productos (IVA 4%).

3. **El fuzzy matching sigue activo** - 80% similitud mínima.

4. **Si hay problemas**, restaura los backups:
   ```
   copy main_backup_v45.py main.py
   copy extractores\panifiesto_backup.py extractores\panifiesto.py
   ```

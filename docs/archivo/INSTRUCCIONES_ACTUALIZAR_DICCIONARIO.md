# 📋 INSTRUCCIONES - actualizar_diccionario.py

## 📦 INSTALACIÓN (una sola vez)

### Paso 1: Copiar el script
```
Copiar: actualizar_diccionario.py
A:      C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\
```

### Paso 2: Crear carpeta datos y mover diccionario
```
1. Crear carpeta: C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\datos\

2. MOVER el archivo:
   DESDE: C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\DiccionarioProveedoresCategoria.xlsx
   A:     C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\datos\DiccionarioProveedoresCategoria.xlsx
```

### Paso 3: Actualizar main.py (opcional pero recomendado)
```python
# Buscar la línea:
DICCIONARIO_DEFAULT = "DiccionarioProveedoresCategoria.xlsx"

# Cambiar a:
DICCIONARIO_DEFAULT = "datos/DiccionarioProveedoresCategoria.xlsx"
```

---

## 🚀 USO

### Opción 1: Doble clic (recomendado)
```
1. Doble clic en actualizar_diccionario.py
2. Se abre ventana de Windows para elegir archivo
3. Seleccionas el Excel de facturas corregido (ej: Facturas_1T25.xlsx)
4. El script muestra los artículos nuevos
5. Confirmas con "S" + Enter
6. ¡Diccionario actualizado!
```

### Opción 2: Desde consola
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

# Abre ventana para elegir archivo
python actualizar_diccionario.py

# Ver cambios sin aplicar
python actualizar_diccionario.py --solo-ver

# Archivo específico
python actualizar_diccionario.py outputs\Facturas_1T25.xlsx
```

---

## 📁 ESTRUCTURA FINAL

```
ParsearFacturas-main/
├── main.py
├── actualizar_diccionario.py        ← NUEVO
├── datos/
│   └── DiccionarioProveedoresCategoria.xlsx  ← MOVIDO AQUÍ
├── outputs/
│   ├── Facturas_1T25.xlsx
│   ├── Facturas_2T25.xlsx
│   └── ...
├── extractores/
└── ...
```

---

## 🔄 TU FLUJO DE TRABAJO

```
1. Ejecutas main.py → genera Facturas_1T25.xlsx en outputs/

2. Abres Facturas_1T25.xlsx en Excel

3. Filtras por CATEGORIA = "PENDIENTE"

4. Corriges los PENDIENTES:
   PENDIENTE → QUESOS
   PENDIENTE → CHACINAS
   etc.

5. Guardas el Excel

6. Ejecutas actualizar_diccionario.py
   - Se abre ventana
   - Seleccionas el Excel corregido
   - Confirmas

7. El diccionario se actualiza automáticamente

8. Próxima vez que ejecutes main.py → menos PENDIENTES
```

---

## ⚠️ NOTAS IMPORTANTES

- **Backup automático:** Cada vez que actualizas, se crea backup en datos/
- **No duplica:** Si un artículo ya existe, no lo añade de nuevo
- **Normaliza proveedores:** "1T25 0331 PANIFIESTO" → "PANIFIESTO"
- **Preserva hojas:** Otras hojas del Excel se mantienen intactas

---

*Creado: 22/12/2025*

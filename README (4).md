# 🚀 SISTEMA INTEGRADO - GESTIÓN DE FACTURAS

**Versión:** v1.0 (En desarrollo)  
**Estado:** ✅ Fase 1 - Cimientos en curso  
**Última actualización:** 09/01/2026

---

## 📖 ¿POR DÓNDE EMPIEZO?

### Opción 1: MENÚ INTERACTIVO (recomendado)
```bash
python main.py
```
Abre un menú visual con todas las opciones.

### Opción 2: Ejecutar clasificador directamente
```bash
python clasificador.py
```
Solo procesa movimientos bancarios.

---

## 📋 ¿QUÉ HACE CADA OPCIÓN?

### 1️⃣ Procesar Facturas (ParsearFacturas)
- Lee PDFs de facturas desde carpeta
- Extrae datos con extractores específicos
- Genera `COMPRAS_XTxx.xlsx`
- **Estado:** ⏳ Pendiente integrar

### 2️⃣ Clasificar Movimientos Bancarios
- Lee archivo XLSX con movimientos bancarios
- Clasificar cada movimiento automáticamente
- Genera `clasificados.xlsx`
- **Estado:** ✅ Funcional

### 3️⃣ Cuadre Compras ↔ Banco
- Cruza facturas con movimientos bancarios
- Asigna ESTADO_PAGO y MOVIMIENTO_#
- **Estado:** ⏳ Pendiente crear

### 4️⃣ Ver Estadísticas
- Resumen de archivos generados
- Tasas de clasificación
- **Estado:** ✅ Funcional

### 5️⃣ Salir
- Sale del programa

---

## 📊 ENTRADA Y SALIDA

### Clasificador de Movimientos

**Entrada:** 
- Archivo: `PROVEEDOR 2025.xlsx` (o similar)
- Hojas requeridas: `Tasca`, `Comestibles`, `Facturas`
- Diccionario: `DiccionarioEmisorTitulo.xlsx`

**Salida:**
- Archivo: `clasificados.xlsx`
- Columnas:
  - `#` (número movimiento)
  - `F. Valor` (fecha)
  - `Concepto` (descripción)
  - `Importe` (cantidad)
  - `CLASIFICACION_TIPO` (compra, transferencia, adeudo, etc.)
  - `CLASIFICACION_DETALLE` (más información)
  - `PROTOCOLO_APLICADO` (regla usada)

---

## 🛠️ ESTRUCTURA DEL PROYECTO

```
gestion-facturas/
├── main.py                   # Menú orquestador
├── clasificador.py           # Clasificación movimientos
│
├── banco/                    # Módulo de movimientos bancarios
│   ├── router.py            # Enrutador (elige qué clasificador)
│   └── clasificadores/      # Clasificadores específicos
│       ├── tpv.py
│       ├── transferencia.py
│       ├── adeudo_recibo.py
│       └── ...
│
├── datos/                    # Archivos maestros
│   ├── MAESTRO_PROVEEDORES.xlsx
│   ├── DICCIONARIO_SINONIMOS.xlsx
│   └── DICCIONARIO_CATEGORIAS.xlsx
│
├── extractores/             # Extractores de PDF (95+)
├── nucleo/                  # Lógica core
├── outputs/                 # Archivos generados
└── docs/                    # Documentación
```

---

## ⚙️ REQUISITOS

- Python 3.8+
- pandas
- openpyxl (para Excel)
- pdfplumber (para PDFs)

**Instalación:**
```bash
pip install pandas openpyxl pdfplumber
```

---

## 🔧 TROUBLESHOOTING

### Error: `ModuleNotFoundError: No module named 'banco'`
→ Asegúrate de estar en la carpeta raíz del proyecto

### Error: `FileNotFoundError: 'DiccionarioEmisorTitulo.xlsx'`
→ Coloca el archivo en la carpeta raíz

### Error: `Sheet 'Tasca' not found`
→ El archivo debe tener exactamente esas hojas: `Tasca`, `Comestibles`, `Facturas`

---

## 📚 DOCUMENTACIÓN

- `ESQUEMA_PROYECTO.md` - Documento maestro de referencia
- `ESTADO_PROYECTO.md` - Métricas y pendientes actuales
- `sesiones/` - Registro de cada sesión de desarrollo

---

## 🎯 PRÓXIMAS FASES

| Fase | Objetivo | Estado |
|------|----------|--------|
| 1 | Cimientos | 🟡 En curso |
| 2 | Consolidar ParsearFacturas | ⏳ Pendiente |
| 3 | Ventas (Loyverse) | ⏳ Futuro |
| 4 | Cuadre completo | ⏳ Futuro |
| 5 | Automatización Gmail | ⏳ Futuro |

---

## 💡 TIPS

- Ejecuta `python main.py` para ver el menú
- La opción 2 es la más completa ahora
- Guarda tus archivos Excel en la misma carpeta
- Revisa `clasificados.xlsx` para ver qué se clasificó

---

*Para más detalles, lee ESQUEMA_PROYECTO.md*

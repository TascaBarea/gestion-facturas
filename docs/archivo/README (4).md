# 📖 ParsearFacturas - Manual del Proyecto

**Versión:** 5.7  
**Última actualización:** 01/01/2026  
**Negocio:** TASCA BAREA S.L.L. (restaurante + distribución gourmet COMESTIBLES BAREA)

---

## 🎯 OBJETIVO DEL PROYECTO

Automatizar el flujo completo de facturas de proveedores:

```
📧 Gmail → 📄 PDF → 🔍 Extracción → 📊 Categorización → 💳 Pago SEPA
```

**Meta final:** Cada viernes a las 07:00, el sistema descarga facturas, las procesa y genera ficheros SEPA para pagar automáticamente.

---

## 📊 ESTADO ACTUAL (01/01/2026)

| Componente | Estado | Progreso |
|------------|--------|----------|
| **ParsearFacturas** | ✅ Funcional | v5.7 - 145+ extractores |
| **Categorización** | ✅ Funcional | Fuzzy matching 80% |
| **Generador SEPA** | ✅ Prototipo | Falta validación IBAN |
| **Extractor Gmail** | 🟡 OAuth2 OK | Falta integrar |
| **Orquestador** | ❌ Pendiente | - |

**Métricas ParsearFacturas v5.7:**
- Cuadre OK: **~66%**
- Con líneas: **~85%**
- Objetivo: **80%**

---

## 🗂️ TABLAS DEL SISTEMA

| Tabla | Origen | Contenido | Uso |
|-------|--------|-----------|-----|
| ARTICULOS LOYVERSE | Loyverse POS | 578 artículos venta | Análisis márgenes |
| VENTAS POR ARTICULOS | Loyverse | Ventas detalladas | Análisis ventas |
| COMPRAS POR ARTICULOS | Este proyecto | 698 artículos, 116 categorías | Análisis costes |
| FACTURAS | Facturas procesadas | Código, Proveedor, Fecha, Total | Contabilidad |
| MOVIMIENTOS BANCO | Banco Sabadell N43 | Movimientos TASCA + COMESTIBLES | Conciliación |
| PROVEEDORES | Manual + facturas | Nombre, CIF, IBAN, método pago | SEPA |

---

## 🚀 USO BÁSICO

### Procesar facturas de un trimestre

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main

python main.py -i "C:\...\FACTURAS 2025\FACTURAS RECIBIDAS\4 TRI 2025"
```

**Salida:**
- `outputs/Facturas_4T25.xlsx` - Excel con líneas extraídas
- `outputs/log_YYYYMMDD_HHMM.txt` - Log de procesamiento

### Probar un extractor específico

```cmd
python tests/probar_extractor.py "BM" "factura.pdf"
python tests/probar_extractor.py "LA ROSQUILLERIA" "factura.pdf" --debug
```

### Listar extractores disponibles

```cmd
python main.py --listar-extractores
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
ParsearFacturas-main/
├── main.py                          # Script principal v5.7
├── actualizar_diccionario.py        # Actualiza categorías
├── generar_proveedores.py           # Genera PROVEEDORES.md
│
├── extractores/                     # 145+ extractores
│   ├── __init__.py                  # Registro automático @registrar
│   ├── base.py                      # Clase ExtractorBase
│   ├── bm.py                        # NUEVO 01/01/2026
│   ├── la_rosquilleria.py           # CORREGIDO 01/01/2026
│   ├── lavapies.py                  # NUEVO 31/12/2025
│   └── ...
│
├── nucleo/                          # Funciones core
├── salidas/                         # Generación Excel/logs
├── datos/                           # DiccionarioProveedoresCategoria.xlsx
├── config/                          # Configuración (settings.py v5.7)
│
├── docs/                            # Documentación
│   ├── README.md                    # Este archivo
│   ├── ESTADO_PROYECTO.md           # Estado actual
│   ├── PROVEEDORES.md               # Lista extractores
│   ├── LEEME_PRIMERO.md             # Guía rápida
│   └── SESION_01_01_2026.md         # Sesión actual
│
├── tests/                           # Testing
└── outputs/                         # Salidas generadas
```

---

## 🔧 REGLAS TÉCNICAS CRÍTICAS

### 1. Siempre pdfplumber (OCR solo si es escaneado)
```python
metodo_pdf = 'pdfplumber'  # SIEMPRE por defecto
metodo_pdf = 'ocr'         # SOLO si es imagen/escaneado
metodo_pdf = 'hibrido'     # Si algunas facturas son escaneadas y otras no
```

### 2. Siempre líneas individuales
```python
# ❌ MAL (agrupado)
lineas.append({'articulo': 'PRODUCTOS IVA 10%', 'base': 500.00})

# ✅ BIEN (individual)
lineas.append({'articulo': 'QUESO MANCHEGO', 'cantidad': 2, 'base': 15.50})
```

### 3. Portes: distribuir o separar según IVA
```python
# Si portes tienen MISMO IVA que productos → prorratear
if portes > 0 and iva_portes == iva_productos:
    for linea in lineas:
        proporcion = linea['base'] / base_total
        linea['base'] += portes * proporcion

# Si portes tienen IVA DIFERENTE → línea separada (ej: LA ROSQUILLERIA)
lineas.append({'articulo': 'GASTOS ENVIO', 'base': 10.00, 'iva': 0})
```

### 4. Tolerancia de cuadre: 0.10€ (0.05€ para tickets pequeños)

### 5. Formato números europeo
```python
def _convertir_europeo(self, texto):
    # "1.234,56" → 1234.56
    texto = texto.replace('.', '').replace(',', '.')
    return float(texto)
```

### 6. IVA incluido → Base (ej: BM SUPERMERCADOS)
```python
base = importe / (1 + tipo_iva / 100)
# Ejemplo: 0.16€ al 21% → 0.16/1.21 = 0.13€
```

### 7. IVA variable: deducir de factura (ej: LAVAPIES)
Para proveedores con errores frecuentes de IVA, deducir el IVA de las bases imponibles de la factura usando algoritmo subset-sum.

### 8. Líneas separadas por IVA diferente (ej: LA ROSQUILLERIA)
```python
# Productos: IVA 10%
lineas.append({'articulo': 'ROSQUILLAS', 'base': 45.90, 'iva': 10})
# Portes: IVA 0%
lineas.append({'articulo': 'GASTOS ENVIO', 'base': 10.00, 'iva': 0})
```

### 9. Bug extraer_referencia (SOLUCIONADO en base.py)
El método `extraer_referencia()` en `base.py` llama automáticamente a `extraer_numero_factura()` si existe. No hace falta añadir alias en cada extractor.

---

## 📋 RUTINA DE TRABAJO CON CLAUDE

### Al INICIAR sesión:
1. Subir estos archivos a Claude:
   - `docs/ESTADO_PROYECTO.md`
   - `docs/PROVEEDORES.md`
   - `docs/LEEME_PRIMERO.md`
   - Facturas PDF del proveedor a trabajar
2. Decir: "Continúo proyecto ParsearFacturas v5.7. Tarea: [describir]"

### Al CERRAR sesión:
1. Pedir: "Prepara documentación de cierre"
2. Descargar archivos actualizados
3. Copiar a `docs/` y hacer commit:
```cmd
git add .
git commit -m "Sesión DD/MM: [resumen cambios]"
git push
```

### Si añades extractores:
1. Copiar archivos `.py` a `extractores/`
2. Limpiar caché: `rmdir /s /q extractores\__pycache__`
3. Ejecutar: `python generar_proveedores.py`
4. Hacer commit de todo

---

## 🔗 ENLACES ÚTILES

- **Repositorio:** https://github.com/TascaBarea/ParsearFacturas
- **Dropbox facturas:** `Dropbox/File inviati/TASCA BAREA S.L.L/CONTABILIDAD/FACTURAS 2025`
- **Banco Sabadell:** BS Online para SEPA

---

## 📞 SOPORTE

Este proyecto se desarrolla con asistencia de Claude (Anthropic).
Para continuar el trabajo, usa el patrón descrito en "Rutina de trabajo con Claude".

---

*Documento actualizado: 01/01/2026 (v5.7)*

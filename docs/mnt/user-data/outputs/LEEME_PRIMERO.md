# 📖 LEEME PRIMERO - ParsearFacturas

**Versión:** v4.5  
**Fecha:** 21/12/2025  
**Autor:** Tasca Barea + Claude  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas (privado)

---

## ⚠️ IMPORTANTE - LEER ANTES DE CONTINUAR

### Estado de los extractores (21/12/2025 PM)

**Sesión tarde - 8 extractores nuevos:**
```
jaime_fernandez.py      # Alquiler (retención IRPF)
benjamin_ortega.py      # Alquiler (retención IRPF)
ibarrako.py             # Piparras vascas
angel_loli.py           # Vajilla artesanal
abbati.py               # Café
panifiesto.py           # Pan artesanal
julio_garcia.py         # Verduras mercado (HÍBRIDO)
productos_adell.py      # Conservas Croquellanas
productos.py            # LIMPIADO (solo ZUBELZU y ANA CABALLO)
__init__.py             # Actualizado
```

### Para verificar que todo funciona
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python -c "from extractores import listar_extractores; print(len(listar_extractores()), 'extractores')"
```

---

## 🎯 ¿QUÉ ES ESTE PROYECTO?

Sistema automatizado para **parsear facturas PDF** de proveedores y extraer líneas de producto con desglose IVA. El objetivo final es generar ficheros SEPA para pago automático por transferencia.

**Flujo del sistema:**
```
PDF factura → Detectar proveedor → Extractor específico → Líneas producto → Excel
                                                                              ↓
                                                           Cruce con MAESTROS (CIF→IBAN)
                                                                              ↓
                                                           Generador SEPA (pain.001)
```

---

## 📊 ESTADO ACTUAL (21/12/2025)

### Métricas de procesamiento

| Trimestre | Facturas | Cuadre OK | % | Con Líneas | Importe |
|-----------|----------|-----------|---|------------|---------|
| 1T25 | 252 | ~175 | **~70%** | ~205 (81%) | 48,173€ |
| 2T25 | 307 | ~175 | **~57%** | ~240 (78%) | 46,720€ |
| 3T25 | 161 | ~95 | **~59%** | ~125 (78%) | 35,539€ |
| 4T25 | 183 | ~100 | **~55%** | ~130 | pendiente |
| **TOTAL** | **903** | **~545** | **~60%** | ~700 | ~130,000€ |

### Evolución del proyecto

| Versión | Fecha | Cuadre 1T25 | Cambio |
|---------|-------|-------------|--------|
| v3.5 | 09/12/2025 | 42% | Baseline |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular |
| v4.3 | 20/12/2025 | 60% | +6 extractores (OCR) |
| v4.4 | 21/12/2025 AM | 66% | +12 extractores mañana |
| **v4.5** | **21/12/2025 PM** | **~70%** | **+8 extractores tarde** |

---

## 📂 ESTRUCTURA DEL PROYECTO

```
ParsearFacturas-main/
│
├── 📄 main.py                 # Punto de entrada principal
├── 📄 requirements.txt        # Dependencias Python
│
├── 📦 extractores/            # ⭐ EXTRACTORES POR PROVEEDOR
│   ├── __init__.py            # Sistema de registro @registrar
│   ├── base.py                # Clase base ExtractorBase
│   ├── [~108 extractores]     # Un archivo por proveedor complejo
│   └── productos.py           # Solo ZUBELZU y ANA CABALLO
│
├── 📁 nucleo/                 # Funciones core
├── 📁 salidas/                # Generación Excel/logs
├── 📁 datos/                  # DiccionarioProveedoresCategoria.xlsx
├── 📁 config/                 # Configuración
├── 📁 docs/                   # Documentación
├── 📁 tests/                  # Testing
└── 📁 outputs/                # Salidas generadas
```

---

## 🔧 CÓMO FUNCIONA

### 1. Sistema de registro automático

```python
# extractores/julio_garcia.py
from extractores import registrar
from extractores.base import ExtractorBase

@registrar('JULIO GARCIA VIVAS', 'GARCIA VIVAS JULIO', 'JULIO GARCIA')
class ExtractorJulioGarcia(ExtractorBase):
    nombre = 'JULIO GARCIA VIVAS'
    cif = 'REDACTED_DNI'
    metodo_pdf = 'hibrido'  # pdfplumber + OCR fallback
    
    def extraer_lineas(self, texto):
        # Lógica específica del proveedor
        ...
```

### 2. Métodos de extracción

| Método | Uso | Proveedores ejemplo |
|--------|-----|---------------------|
| **pdfplumber** | PDF con texto seleccionable | CERES, BM, ZUCCA, PANRUJE |
| **OCR** | PDF escaneado/imagen | LA ROSQUILLERIA, FISHGOURMET |
| **híbrido** | Intenta pdfplumber, fallback OCR | JULIO GARCIA, DE LUIS, ECOMS |

---

## ✅ SESIÓN 21/12/2025 TARDE - 8 EXTRACTORES

| # | Proveedor | CIF/NIF | Facturas | Método | Peculiaridad |
|---|-----------|---------|----------|--------|--------------|
| 1 | JAIME FERNÁNDEZ | REDACTED_DNI | 7/7 ✅ | pdfplumber | Alquiler + retención IRPF |
| 2 | BENJAMÍN ORTEGA | REDACTED_DNI | 7/7 ✅ | pdfplumber | Alquiler + retención IRPF |
| 3 | IBARRAKO PIPARRAK | F20532297 | 3/3 ✅ | pdfplumber | Separado de productos.py |
| 4 | ÁNGEL Y LOLI | REDACTED_DNI | 4/4 ✅ | pdfplumber | Vajilla artesanal |
| 5 | ABBATI CAFFE | B82567876 | 3/3 ✅ | pdfplumber | Pago domiciliación |
| 6 | PANIFIESTO | B87874327 | 10/10 ✅ | pdfplumber | 20-30 albaranes/mes |
| 7 | JULIO GARCIA | REDACTED_DNI | 8/8 ✅ | **híbrido** | Algunas facturas OCR |
| 8 | PRODUCTOS ADELL | B12711636 | 3/3 ✅ | pdfplumber | Columna "Cajas" variable |
| **TOTAL** | | | **45/45** | | **100%** |

### Limpieza realizada

Se eliminaron clases duplicadas de `productos.py`:
- ~~ExtractorMolletes~~ → `artesanos_mollete.py`
- ~~ExtractorIbarrako~~ → `ibarrako.py`
- ~~ExtractorProductosAdell~~ → `productos_adell.py`
- ~~ExtractorGrupoCampero~~ → `territorio_campero.py`
- ~~ExtractorEcoficus~~ → `ecoficus.py`

---

## ⚠️ PROBLEMAS CONOCIDOS Y PENDIENTES

### Errores por tipo

| Error | Cantidad | Causa | Solución |
|-------|----------|-------|----------|
| **FECHA_PENDIENTE** | ~35 | BM, tickets varios | Mejorar extractor |
| **SIN_TOTAL** | ~20 | Formato no reconocido | Crear/ajustar extractor |
| **DESCUADRE** | ~15 | Cálculo incorrecto | Revisar extractor |
| **SIN_LINEAS** | ~8 | Sin extractor o OCR falla | Crear extractor |

### Proveedores prioritarios pendientes

| Proveedor | Facturas | Error | Impacto |
|-----------|----------|-------|---------|
| **JIMELUZ** | 14 | SIN_TOTAL, DESCUADRE | ALTO |
| **BM tickets** | 10 | FECHA_PENDIENTE | MEDIO |
| **PIFEMA** | 4 | DESCUADRE | BAJO |

### IBANs pendientes de recopilar

- JAIME FERNÁNDEZ MORENO (REDACTED_DNI)
- BENJAMÍN ORTEGA ALONSO (REDACTED_DNI)
- ALFARERÍA ÁNGEL Y LOLI (REDACTED_DNI)
- JULIO GARCIA VIVAS (REDACTED_DNI)
- WELLDONE LACTICOS (27292516A)

---

## 🚀 CÓMO USAR

### Procesar carpeta de facturas

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python main.py "C:\path\to\facturas\1 TRI 2025"
```

### Probar un extractor específico

```cmd
python tests/probar_extractor.py "JULIO GARCIA" "factura.pdf"
python tests/probar_extractor.py "JULIO GARCIA" "factura.pdf" --debug
```

### Añadir nuevo extractor

1. Copiar plantilla: `extractores/_plantilla.py` → `extractores/nuevo.py`
2. Cambiar nombre, CIF, variantes en `@registrar()`
3. Implementar `extraer_lineas()` con líneas individuales
4. Probar con facturas reales
5. ¡Listo! Se registra automáticamente

---

## 📚 REGLAS CRÍTICAS

### 1. SIEMPRE líneas individuales

```python
# ❌ MAL - agrupado por IVA
lineas.append({'articulo': 'PRODUCTOS IVA 10%', 'base': 500.00, 'iva': 10})

# ✅ BIEN - cada producto
lineas.append({'articulo': 'QUESO MANCHEGO', 'cantidad': 2, 'base': 15.50, 'iva': 10})
```

### 2. Portes: distribuir proporcionalmente

```python
# Los portes NUNCA van como línea separada
if portes > 0:
    for linea in lineas:
        proporcion = linea['base'] / base_total
        linea['base'] += portes * proporcion
```

### 3. Formato números europeo

```python
def _convertir_europeo(self, texto):
    # "1.234,56" → 1234.56
    texto = texto.replace('.', '').replace(',', '.')
    return float(texto)
```

### 4. Tolerancia de cuadre: 0.10€

---

## 📋 CHECKLIST PARA RETOMAR PROYECTO

Antes de cada sesión de trabajo:

- [ ] ¿Está el Excel de salida cerrado?
- [ ] ¿Hay facturas nuevas por procesar?
- [ ] ¿El último commit de GitHub está actualizado?

Después de añadir extractores:

- [ ] ¿Están copiados a `extractores/`?
- [ ] ¿El `__init__.py` tiene los imports?
- [ ] ¿Se ejecutó test con facturas reales?
- [ ] ¿Se actualizó PROVEEDORES.md?

---

## 📝 HISTORIAL DE CAMBIOS

| Fecha | Versión | Cambios |
|-------|---------|---------|
| **21/12/2025 PM** | **v4.5** | **+8 extractores: JAIME FERNANDEZ, BENJAMIN ORTEGA, IBARRAKO, ANGEL LOLI, ABBATI, PANIFIESTO, JULIO GARCIA (híbrido), PRODUCTOS ADELL. Limpieza productos.py.** |
| 21/12/2025 AM | v4.4 | +12 extractores sesión mañana |
| 20/12/2025 | v4.3 | +6 extractores OCR |
| 19/12/2025 | v4.2 | +12 extractores, bug IVA 0 |
| 18/12/2025 | v4.0 | Arquitectura modular |
| 09/12/2025 | v3.5 | Baseline: 42% cuadre |

---

*Última actualización: 21/12/2025 PM - Sesión tarde 8 extractores*

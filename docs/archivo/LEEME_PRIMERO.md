# 📖 LEEME PRIMERO - ParsearFacturas

**Versión:** v5.9  
**Fecha:** 03/01/2026  
**Autor:** Tasca Barea + Claude  
**Repositorio:** https://github.com/TascaBarea/ParsearFacturas (privado)

---

## ⚠️ IMPORTANTE - LEER ANTES DE CONTINUAR

### Estado actual (03/01/2026 noche)

**Última sesión - Fix categoria_fija:**
```
main.py v5.9           # Fix: categoria_fija como fallback
praizal.py             # NUEVO extractor (Quesos)
fishgourmet.py         # CORREGIDO: SALAZONES (no AHUMADOS PESCADO)
7 extractores          # Añadido categoria_fija
```

**⚠️ PROBLEMA PENDIENTE:** SIN_PROVEEDOR sigue apareciendo. Limpiar TODOS los cachés:
```cmd
rmdir /s /q extractores\__pycache__
rmdir /s /q nucleo\__pycache__
rmdir /s /q salidas\__pycache__
rmdir /s /q __pycache__
```

### Para verificar que todo funciona
```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python main.py --version
```

Debe mostrar: **v5.9**

```cmd
python -c "from extractores import listar_extractores; print(len(listar_extractores()), 'extractores')"
```

Debe mostrar: **~83 extractores**

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

## 📊 ESTADO ACTUAL (03/01/2026)

### Métricas de procesamiento

| Trimestre | Facturas | Cuadre OK | % |
|-----------|----------|-----------|---|
| 1T25 | 252 | 188 | **74.6%** ⭐ |
| 2T25 | 307 | 183 | 59.6% |
| 3T25 | 161 | 99 | 61.5% |
| 4T25 | 217 | 156 | **71.9%** |
| **TOTAL** | **937** | **626** | **~67%** |

**Objetivo:** 80% cuadre OK

### Evolución del proyecto

| Versión | Fecha | Cuadre | Cambio principal |
|---------|-------|--------|------------------|
| v3.5 | 09/12/2025 | 42% | Baseline - 70 extractores |
| v4.0 | 18/12/2025 | 54% | Arquitectura modular @registrar |
| v5.5 | 01/01/2026 | ~62% | +BM SUPERMERCADOS, FELISA |
| v5.7 | 01/01/2026 | ~66% | LA ROSQUILLERIA corregido |
| v5.8 | 02/01/2026 | ~66% | Nueva hoja Facturas (cabeceras) |
| **v5.9** | **03/01/2026** | **~67%** | **Fix categoria_fija, +PRAIZAL** |

---

## 📁 ESTRUCTURA DEL PROYECTO

```
ParsearFacturas-main/
│
├── 📄 main.py                 # Punto de entrada principal v5.9
├── 📄 requirements.txt        # Dependencias Python
│
├── 📦 extractores/            # ⭐ ~83 EXTRACTORES
│   ├── __init__.py            # Sistema de registro @registrar
│   ├── base.py                # Clase base ExtractorBase
│   └── [83+ extractores]      # Un archivo por proveedor
│
├── 📁 nucleo/                 # Funciones core
├── 📁 salidas/                # Generación Excel/logs
│   └── excel.py               # ⭐ v5.8 con hoja Facturas
├── 📁 datos/                  # DiccionarioProveedoresCategoria.xlsx
├── 📁 config/                 # Configuración (settings.py)
├── 📁 docs/                   # Documentación
├── 📁 tests/                  # Testing
└── 📁 outputs/                # Salidas generadas
```

---

## ✅ SESIONES RECIENTES

### 03/01/2026 noche - Sesión actual (v5.9)

| Módulo | Cambio | Estado |
|--------|--------|--------|
| **main.py** | Fix categoria_fija fallback | ✅ LISTO |
| **praizal.py** | Nuevo extractor | ✅ LISTO |
| **fishgourmet.py** | Categoría → SALAZONES | ✅ LISTO |
| **7 extractores** | + categoria_fija | ✅ LISTO |

**Problema pendiente:** SIN_PROVEEDOR (posible caché)

### 02/01/2026 noche - (v5.8)

| Módulo | Cambio | Estado |
|--------|--------|--------|
| **salidas/excel.py** | Nueva hoja "Facturas" | ✅ LISTO |
| **salidas/excel.py** | Integración cuentas | ✅ LISTO |

---

## ⚠️ PROBLEMAS CONOCIDOS Y PENDIENTES

### 🔴 CRÍTICO - Resolver primero

**SIN_PROVEEDOR aparece** a pesar de categoria_fija definida:
```cmd
# Diagnóstico
python -c "from extractores.artesanos_mollete import *; print(ExtractorArtesanosMollete.categoria_fija)"
# Debe mostrar: PAN Y BOLLERIA

# Si muestra error o vacío → problema de importación
# Si muestra bien pero Excel tiene SIN_PROVEEDOR → problema en main.py
```

### Proveedores prioritarios

| # | Proveedor | Errores | Tipo | Dificultad |
|---|-----------|---------|------|------------|
| 1 | **JIMELUZ** | 21 | OCR | 🔴 Alta |
| 2 | **DIA/ECOMS** | 17 | SIN_LINEAS | 🟡 Media |
| 3 | **MARITA COSTA** | 8 | DESCUADRE | 🟡 Media |
| 4 | **LA ROSQUILLERIA** | 7 | SIN_LINEAS | 🟡 Media |

---

## 🚀 CÓMO USAR

### Procesar carpeta de facturas

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python main.py -i "C:\path\to\facturas\2 TRI 2025"
```

### Probar un extractor específico

```cmd
python tests/probar_extractor.py "PRAIZAL" "factura.pdf"
python tests/probar_extractor.py "BM" "factura.pdf" --debug
```

### Añadir nuevo extractor

1. Copiar plantilla: `extractores/_plantilla.py` → `extractores/nuevo.py`
2. Cambiar nombre, CIF, variantes en `@registrar()`
3. Implementar `extraer_lineas()` con líneas individuales
4. Si categoría única → añadir `categoria_fija = 'CATEGORIA'`
5. Probar con facturas reales
6. ¡Listo! Se registra automáticamente

---

## 📚 REGLAS CRÍTICAS

### 1. SIEMPRE líneas individuales

```python
# ❌ MAL - agrupado por IVA
lineas.append({'articulo': 'PRODUCTOS IVA 10%', 'base': 500.00, 'iva': 10})

# ✅ BIEN - cada producto
lineas.append({'articulo': 'QUESO MANCHEGO', 'cantidad': 2, 'base': 15.50, 'iva': 10})
```

### 2. categoria_fija para proveedores mono-categoría

```python
class ExtractorNuevo(ExtractorBase):
    nombre = 'NUEVO PROVEEDOR'
    categoria_fija = 'CATEGORIA'  # Se usa automáticamente si línea no tiene categoría
```

### 3. Portes: distribuir proporcionalmente

```python
# Si portes tienen mismo IVA que productos → prorratear
if portes > 0 and iva_portes == iva_productos:
    for linea in lineas:
        proporcion = linea['base'] / base_total
        linea['base'] += portes * proporcion
```

### 4. Formato números europeo

```python
def _convertir_europeo(self, texto):
    # "1.234,56" → 1234.56
    texto = texto.replace('.', '').replace(',', '.')
    return float(texto)
```

### 5. Tolerancia de cuadre: 0.10€

---

## 📋 CHECKLIST PARA RETOMAR PROYECTO

Antes de cada sesión de trabajo:

- [ ] ¿Está el Excel de salida cerrado?
- [ ] ¿Hay facturas nuevas por procesar?
- [ ] ¿El último commit de GitHub está actualizado?
- [ ] Subir a Claude: ESTADO_PROYECTO.md, LEEME_PRIMERO.md, SESION_XX.md

Después de añadir extractores:

- [ ] ¿Están copiados a `extractores/`?
- [ ] ¿Se limpió el caché? (`rmdir /s /q __pycache__` en TODAS las carpetas)
- [ ] ¿Se ejecutó test con facturas reales?
- [ ] ¿Se actualizó la documentación?

---

## 📝 HISTORIAL DE CAMBIOS

| Fecha | Versión | Cambios |
|-------|---------|---------|
| **03/01/2026 noche** | **v5.9** | **Fix categoria_fija, +PRAIZAL, FISHGOURMET→SALAZONES** |
| 02/01/2026 noche | v5.8 | Nueva hoja Facturas, integración cuentas |
| 01/01/2026 noche | v5.7 | LA ROSQUILLERIA (IVA 10%), +4 verificados |
| 01/01/2026 mañana | v5.5 | +BM SUPERMERCADOS, FELISA |
| 31/12/2025 | v5.4 | +LAVAPIES, MUÑOZ OCR, GREDALES |

---

*Última actualización: 03/01/2026 (noche)*

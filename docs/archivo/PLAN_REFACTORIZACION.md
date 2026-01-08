# 🔄 PLAN DE REFACTORIZACIÓN - ParsearFacturas

**Fecha inicio:** 18/12/2025
**Estado:** EN PROGRESO
**Versión origen:** v3.57 (monolito 7,618 líneas)
**Versión destino:** v4.0 (modular)

---

## 📋 RESUMEN EJECUTIVO

### ¿Por qué refactorizar?

| Problema actual | Impacto | Solución |
|-----------------|---------|----------|
| 7,618 líneas en 1 archivo | Difícil encontrar errores | Dividir en módulos |
| 70 extractores mezclados | Difícil mantener | 1 archivo por extractor |
| Función duplicada (MRM) | Bug silencioso | Eliminar duplicado |
| Sin detección duplicados | Riesgo contable | Registro de facturas |
| 70+ elif en cascada | Propenso a errores | Registro automático |

### Beneficios esperados

1. **Debuggear**: Error en CERES → abrir `extractores/ceres.py`
2. **Añadir extractor**: Copiar plantilla, cambiar contenido
3. **Testing**: Probar 1 extractor sin ejecutar todo
4. **Futuro web**: Estructura lista para Flask/FastAPI

---

## 🏗️ ARQUITECTURA DESTINO

```
ParsearFacturas/
├── main.py                      # Punto de entrada principal
├── config/
│   ├── __init__.py
│   ├── settings.py              # Rutas, constantes
│   └── proveedores.py           # CIFs, IBANs, categorías
├── extractores/
│   ├── __init__.py              # Registro automático
│   ├── base.py                  # Clase ExtractorBase
│   ├── berzal.py                # 1 archivo por proveedor
│   ├── ceres.py
│   ├── madrueño.py
│   └── ... (70 archivos)
├── nucleo/
│   ├── __init__.py
│   ├── pdf.py                   # Extracción texto (pypdf/pdfplumber/OCR)
│   ├── parser.py                # Fecha, CIF, IBAN, total, ref
│   ├── factura.py               # Clase Factura (dataclass)
│   └── validacion.py            # Cuadre, duplicados
├── salidas/
│   ├── __init__.py
│   ├── excel.py                 # Generación Excel
│   └── log.py                   # Generación logs
├── datos/
│   ├── diccionario.xlsx         # Proveedores/Categorías
│   └── registro_facturas.xlsx   # Anti-duplicados
├── tests/
│   ├── pdfs/                    # PDFs ejemplo por proveedor
│   │   ├── CERES/
│   │   ├── JIMELUZ/
│   │   └── ...
│   └── probar_extractor.py      # Script test individual
├── docs/
│   ├── LEEME_PRIMERO.md
│   ├── ESTADO_PROYECTO.md
│   ├── PROVEEDORES.md
│   ├── PLAN_REFACTORIZACION.md  # ESTE ARCHIVO
│   └── COMO_AÑADIR_EXTRACTOR.md
└── legacy/
    └── migracion_historico_2025_v3_57.py  # Backup versión anterior
```

---

## 📅 FASES DE IMPLEMENTACIÓN

### FASE 1: Preparación y Estructura (Sesión 1)
**Duración estimada:** 1-2 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 1.1 Crear estructura de carpetas | 15 min | ⏳ |
| 1.2 Crear archivos `__init__.py` | 10 min | ⏳ |
| 1.3 Backup script actual en `legacy/` | 5 min | ⏳ |
| 1.4 Crear `config/settings.py` | 20 min | ⏳ |
| 1.5 Crear `config/proveedores.py` | 30 min | ⏳ |
| 1.6 Documentar en GitHub | 10 min | ⏳ |

**Entregable:** Estructura vacía + configuración

---

### FASE 2: Núcleo (Sesión 2)
**Duración estimada:** 2-3 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 2.1 Crear `nucleo/factura.py` (dataclass) | 15 min | ⏳ |
| 2.2 Crear `nucleo/pdf.py` (extracción texto) | 30 min | ⏳ |
| 2.3 Crear `nucleo/parser.py` (fecha, CIF, etc.) | 45 min | ⏳ |
| 2.4 Crear `nucleo/validacion.py` (cuadre) | 30 min | ⏳ |
| 2.5 Test unitario del núcleo | 30 min | ⏳ |

**Entregable:** Núcleo funcional independiente

---

### FASE 3: Sistema de Extractores (Sesión 3)
**Duración estimada:** 2 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 3.1 Crear `extractores/base.py` (clase base) | 30 min | ⏳ |
| 3.2 Crear sistema registro automático | 30 min | ⏳ |
| 3.3 Migrar 5 extractores piloto | 45 min | ⏳ |
| 3.4 Test con facturas reales | 15 min | ⏳ |

**Extractores piloto:**
1. BERZAL (simple, referencia)
2. CERES (complejo, varios formatos)
3. BM SUPERMERCADOS (alto volumen)
4. JIMELUZ (OCR)
5. LICORES MADRUEÑO (múltiples albaranes)

**Entregable:** Sistema de extractores funcionando

---

### FASE 4: Migración Masiva (Sesión 4-5)
**Duración estimada:** 3-4 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 4.1 Migrar extractores 6-25 | 1 hora | ⏳ |
| 4.2 Migrar extractores 26-50 | 1 hora | ⏳ |
| 4.3 Migrar extractores 51-70 | 1 hora | ⏳ |
| 4.4 Eliminar duplicado MRM | 5 min | ⏳ |
| 4.5 Test completo 1T25 | 30 min | ⏳ |

**Entregable:** 70 extractores migrados

---

### FASE 5: Salidas y Main (Sesión 6)
**Duración estimada:** 1-2 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 5.1 Crear `salidas/excel.py` | 30 min | ⏳ |
| 5.2 Crear `salidas/log.py` | 20 min | ⏳ |
| 5.3 Crear `main.py` orquestador | 30 min | ⏳ |
| 5.4 Test completo 1T25 + 2T25 | 30 min | ⏳ |

**Entregable:** Sistema completo funcionando

---

### FASE 6: Robustez (Sesión 7)
**Duración estimada:** 2 horas
**Estado:** ⏳ PENDIENTE

| Tarea | Tiempo | Estado |
|-------|--------|--------|
| 6.1 Crear `datos/registro_facturas.xlsx` | 20 min | ⏳ |
| 6.2 Implementar detección duplicados | 40 min | ⏳ |
| 6.3 Crear `tests/probar_extractor.py` | 30 min | ⏳ |
| 6.4 Crear `docs/COMO_AÑADIR_EXTRACTOR.md` | 30 min | ⏳ |

**Entregable:** Sistema robusto con anti-duplicados

---

## 🔧 DECISIONES TÉCNICAS

### 1. Registro automático de extractores

```python
# extractores/__init__.py
EXTRACTORES = {}

def registrar(nombre_proveedor):
    """Decorador para registrar extractores automáticamente"""
    def decorator(cls):
        EXTRACTORES[nombre_proveedor.upper()] = cls
        return cls
    return decorator

# extractores/ceres.py
from extractores import registrar

@registrar('CERES')
class ExtractorCeres(ExtractorBase):
    def extraer_lineas(self, texto):
        # ... lógica específica
```

**Ventaja:** Añadir extractor = crear archivo, sin tocar nada más

### 2. Detección de duplicados

```python
# Criterio: PROVEEDOR + FECHA + TOTAL (con tolerancia 0.01€)
clave = f"{proveedor}|{fecha}|{round(total, 2)}"
```

**Almacenamiento:** Excel simple (`registro_facturas.xlsx`)
- Fácil de consultar manualmente
- Compatible con tu nivel de programación
- Backup automático con Dropbox

### 3. Clase base para extractores

```python
# extractores/base.py
class ExtractorBase:
    nombre: str
    cif: str
    iban: str
    metodo_pdf: str = 'pypdf'  # 'pypdf', 'pdfplumber', 'ocr'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        raise NotImplementedError
    
    def extraer_total(self, texto: str) -> Optional[float]:
        # Implementación por defecto (puede sobrescribirse)
        ...
```

---

## ✅ CRITERIOS DE ÉXITO

| Criterio | Medida |
|----------|--------|
| **Funcionalidad** | Mismo % éxito que v3.57 (~78%) |
| **Modularidad** | 70 archivos de extractor independientes |
| **Testing** | Poder probar 1 extractor aislado |
| **Duplicados** | 0 facturas duplicadas procesadas |
| **Documentación** | README + guía añadir extractores |

---

## ⚠️ RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Romper funcionalidad | Media | Backup en `legacy/`, tests frecuentes |
| Imports circulares | Baja | Estructura bien definida |
| Pérdida de rendimiento | Baja | Python maneja bien imports |
| Confusión con 2 versiones | Media | Eliminar v3.57 tras validar v4.0 |

---

## 📝 NOTAS DE SESIÓN

### Sesión 1 (18/12/2025)
- Hora inicio: _____
- Hora fin: _____
- Tareas completadas: _____
- Problemas encontrados: _____
- Siguiente paso: _____

---

## 🔗 REFERENCIAS

- Script original: `legacy/migracion_historico_2025_v3_57.py`
- Documentación: `docs/`
- GitHub: https://github.com/TascaBarea/ParsearFacturas

---

*Documento creado: 18/12/2025*
*Última actualización: 18/12/2025*

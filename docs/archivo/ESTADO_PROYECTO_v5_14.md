# ESTADO DEL PROYECTO - ParsearFacturas v5.14

**Fecha:** 07/01/2026  
**Versión:** 5.14  
**Tasa de éxito:** 81.2% (supera objetivo 80%)

---

## RESUMEN RÁPIDO

| Métrica | Valor |
|---------|-------|
| Extractores activos | ~95 |
| Proveedores en MAESTROS | ~90 |
| Facturas/trimestre | ~250 |
| Tasa cuadre | 81.2% |
| Objetivo | 80% ✅ ALCANZADO |

---

## CAMBIOS v5.14 (07/01/2026)

### Extractores corregidos:

**SILVA CORDERO:**
- Patrón flexible para códigos con puntos (D.O.P) y pegados (QUESOAZUL)
- Lotes de 6-7 dígitos (antes solo 6)
- Limpieza de descripción

**LA ALACENA:**
- Soporte para lotes largos sin espacio (A240928952)
- Detección de descuento 100% (base = 0)
- Sin categoria_fija (busca en diccionario)

---

## ESTRUCTURA DEL PROYECTO

```
ParsearFacturas/
├── main.py                 # Script principal v5.12
├── extractores/            # ~95 extractores
│   ├── __init__.py
│   ├── base.py
│   ├── silva_cordero.py    # ← ACTUALIZAR v5.14
│   ├── la_alacena.py       # ← ACTUALIZAR v5.14
│   └── ...
├── nucleo/
│   ├── factura.py
│   ├── parser.py
│   └── pdf.py
├── salidas/
│   └── excel.py
├── config/
│   └── settings.py
├── datos/
│   └── DiccionarioProveedoresCategoria.xlsx
└── docs/
    ├── LEEME_PRIMERO.md
    ├── ESTADO_PROYECTO.md  # ← ESTE ARCHIVO
    └── SESION_*.md
```

---

## EXTRACTORES POR ESTADO

### ✅ Funcionando correctamente (~82)
La mayoría de extractores funcionan. Ver EXTRACTORES_COMPLETO.xlsx para lista completa.

### 🔧 Corregidos en v5.14
- SILVA CORDERO
- LA ALACENA

### ⏸️ Pendientes/Aparcados
- JIMELUZ (no prioritario)
- BM SUPERMERCADOS (casos complejos)

### ❌ Sin extractor (9 proveedores)
AMAZON, ANA CABALLO, CARRASCAL, CONTROLPLAGA, EMBUTIDOS FERRIOL, LUCERA, MI PROVEEDOR, PC COMPONENTES, QUESOS ROYCA

---

## FLUJO DE TRABAJO

```
1. Usuario descarga PDFs de Gmail (adjuntos)
        ↓
2. Script renombra automáticamente
        ↓
3. python main.py -i carpeta
        ↓
4. Excel generado con:
   - Hoja "Lineas" (detalle productos)
   - Hoja "Facturas" (cabeceras)
        ↓
5. Usuario revisa descuadres (~19%)
        ↓
6. Corrección manual si necesario
```

---

## MÉTODOS DE PAGO

| Método | % Proveedores | Acción SEPA |
|--------|---------------|-------------|
| Transferencia | ~50% | Generar XML |
| Domiciliación | ~25% | No incluir |
| Efectivo | ~15% | No incluir |
| Tarjeta | ~10% | No incluir |

MAESTROS.xlsx tiene columna de método de pago.

---

## REGLAS CRÍTICAS PARA CLAUDE

1. **SIEMPRE** leer LEEME_PRIMERO, ESTADO_PROYECTO y SESION antes de trabajar
2. **SIEMPRE** verificar si extractor existe antes de crear nuevo
3. **SIEMPRE** entregar archivos .py COMPLETOS, nunca parches de líneas
4. **SIEMPRE** probar con PDFs reales antes de entregar
5. **NUNCA** asumir - preguntar si hay duda
6. **PORTES**: extractor los devuelve como línea, main.py los prorratea

---

## PRÓXIMOS OBJETIVOS

### Corto plazo (esta semana)
- [ ] Instalar extractores v5.14 (SILVA CORDERO, LA ALACENA)
- [ ] Probar con facturas 1T26

### Medio plazo (este mes)
- [ ] Probar generador SEPA con Banco Sabadell
- [ ] Completar IBANs de proveedores por transferencia
- [ ] Documentar proveedores por método de pago

### Largo plazo
- [ ] Automatizar descarga de Gmail
- [ ] Flujo completo Gmail → SEPA
- [ ] Dashboard de métricas

---

## ARCHIVOS CLAVE

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| main.py | raíz | Script principal |
| MAESTROS.xlsx | datos/ | Proveedores, IBANs, métodos pago |
| DiccionarioProveedoresCategoria.xlsx | datos/ | Artículos y categorías |
| EXTRACTORES_COMPLETO.xlsx | docs/ | Inventario extractores |

---

## HISTORIAL DE VERSIONES

| Versión | Fecha | Cambios principales |
|---------|-------|---------------------|
| v5.14 | 07/01/2026 | Fix SILVA CORDERO y LA ALACENA |
| v5.13 | 06/01/2026 | Análisis de bugs |
| v5.12 | 04/01/2026 | Normalización proveedores (371→150) |
| v5.11 | 04/01/2026 | Soporte OCR |
| v5.10 | 04/01/2026 | Mensajes SIN_EXTRACTOR mejorados |

---

*Última actualización: 07/01/2026*

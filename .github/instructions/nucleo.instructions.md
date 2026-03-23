---
applyTo: nucleo/**
---

# Módulo Núcleo — Conocimiento del dominio
<!-- nucleo/ — Actualizado 24/03/2026 -->

## Qué es este módulo
Módulo Python compartido entre `gestion-facturas` y el repo separado `Parseo/`. En `gestion-facturas` existe como **symlink** apuntando a `Parseo/nucleo/`. Cualquier cambio aquí afecta a ambos repos.

## Archivos
| Archivo | Contenido |
|---|---|
| `factura.py` | Clase `Factura` — modelo de datos de una factura extraída |
| `parser.py` | Lógica base de parseo de texto PDF |
| `pdf.py` | Extracción de texto de PDFs (pdfplumber + OCR fallback) |
| `categorias.py` | Asignación de categorías contables a productos |
| `validacion.py` | Validación de facturas extraídas (importes, CIF, fechas) |

## Regla crítica — Portes y envío
**SIEMPRE** distribuir los portes/gastos de envío proporcionalmente entre los productos de la factura.  
**NUNCA** incluir portes como línea separada en la factura extraída.

```python
# Correcto: distribuir proporcionalmente
coste_con_porte = coste_unitario * (1 + ratio_portes)

# Incorrecto: línea separada
lineas.append({"nombre": "Portes", "importe": 5.50})  # ← NUNCA hacer esto
```

## Tipos de IVA en alimentación (España)
| Tipo | % | Aplica a |
|---|---|---|
| Superreducido | 4% | Pan, lácteos, huevos, frutas, verduras |
| Reducido | 10% | Alimentación general, restauración |
| General | 21% | Alcohol, servicios, productos no alimentarios |

## Relación con Parseo/
- Los extractores de proveedores viven en `Parseo/extractores/`
- Cada extractor importa desde `nucleo` para usar las clases base
- Si se modifica `nucleo/`, probar que los extractores existentes siguen funcionando

---
description: Reglas para crear y depurar extractores de facturas PDF
globs: nucleo/parser.py,nucleo/maestro.py,gmail/identificar.py
---

- Aplica también a: `Parseo/extractores/` (repo hermano)
- Workflow: extraer texto PDF → analizar formato → verificar MAESTRO → crear extractor → test con PDF real
- Naming: archivo `snake_case.py` sin tildes, clase `ExtractorCamelCase`
- Decorador: `@registrar("NOMBRE OFICIAL", "ALIAS1", "ALIAS2")` en MAYÚSCULAS
- Métodos:
  - `extraer_lineas(texto) -> List[Dict]` OBLIGATORIO (keys: articulo, base, iva)
  - Opcionales: `extraer_referencia`, `extraer_fecha`, `extraer_total`, `extraer_texto`
- Portes: NUNCA como línea separada → distribuir proporcionalmente
- OCR primario solo: JIMELUZ, CASA DEL DUQUE, LA LLILDIRIA. Resto: pdfplumber con `fallback_ocr=True`
- CRÍTICO: limpiar `__pycache__` en TODAS las carpetas después de cualquier cambio
- Test obligatorio: con PDF real, verificar cuadre total vs suma líneas (margen ±0.05€)
- `extraer_numero_factura` eliminado v5.18 → usar `extraer_referencia`
- REF: mínimo `len >= 2`
- Importes: formato español (1.234,56) → usar `self._convertir_importe()`
- Ante fallo: devolver datos parciales, nunca lanzar excepción

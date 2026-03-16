# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Sesión actual
**Fecha:** 2026-03-13
**Objetivo:** Reorganización documentación + fixes extractores + análisis Gmail

### Plan
- [x] Analizar log Gmail 13/03/2026
- [x] Investigar BERNAL sin REF → fix gmail.py umbral len>=2
- [x] Eliminar código muerto `extraer_numero_factura` en gmail.py
- [x] Fix ODOO extractor: soporte entidad española + patrón REF INV/
- [x] Fix La Llildiria: total incorrecto (93.94→172.75) + OCR primario + líneas
- [x] Investigar Arganza no procesado → ya en FACTURAS_PROCESADAS (manual)
- [x] Reescribir CLAUDE.md v3.0 (sin redundancias)
- [x] Crear tasks/lessons.md
- [x] Crear tasks/todo.md
- [x] Ajustar ESQUEMA (fix versiones + Skills)
- [x] Limpiar memory/
- [x] Crear skills /lecciones y /plan

### Notas
- ODOO cambió de entidad belga a española desde marzo 2026 (nuevo CIF, IBAN, formato REF, IVA 21%)
- La Llildiria: PDF imagen pura, PyPDF/pdfplumber no extraen tabla totales, OCR sí
- gmail.py:2394 tenía código muerto de `extraer_numero_factura` (eliminado)
- Reorganización docs: CLAUDE.md v3.0, tasks/lessons.md, tasks/todo.md, 2 skills nuevos

### Resultado
Sesión completada. Cambios principales:
- **gmail.py**: eliminado bloque muerto extraer_numero_factura, umbral REF >=2
- **odoo.py**: reescrito con soporte entidad española (INV/, 21%, IBAN ES)
- **la_lleidiria.py**: fix total (93.94→172.75), OCR primario, líneas con impuesto opcional
- **CLAUDE.md v3.0**: sin redundancias, con comportamiento autónomo, 9 skills
- **tasks/**: lessons.md + todo.md creados
- **ESQUEMA**: Ventas v4.0→v4.7, sección §14 Skills añadida

---

## Historial

| Fecha | Objetivo | Estado | Notas |
|-------|----------|--------|-------|
| 2026-03-12 | Auditoría Parseo v5.18 + limpieza | ✅ | 70 _convertir_europeo consolidados, dead code, VERSION unificada |
| 2026-03-13 | Análisis Gmail + docs + extractores | 🟡 | En curso |

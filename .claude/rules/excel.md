---
description: Reglas críticas para operaciones con archivos Excel
globs: datos/**,ventas_semana/**,cuadre/**,salidas/**,gmail/gmail.py
---

- AVISAR SIEMPRE antes de escribir cualquier Excel (puede estar abierto en Windows)
- Leer antes de escribir: `save_to_excel()` lee hoja existente, dedup por `unique_col`
- Backup OBLIGATORIO: en `datos/backups/` con timestamp antes de primera escritura
- openpyxl fallo silencioso: si falla sin error visible → Excel estaba abierto. DETENER y avisar.
- Verificar no abierto: rename temporal (como `verificar_no_abierto()` en maestro.py), NO `open('a')`
- Formato fechas Excel: DD-MM-YY (no YYYY-MM-DD)
- Archivos 2024: coma decimal → convertir antes de operar
- Archivos 2025+: punto decimal estándar
- Formato moneda: siempre 1.234,56 € (punto miles, coma decimales) — usar `fmt_eur()` de `nucleo/utils.py`

# README FACTURAS

## Uso del CLI

El comando principal es:

```bash
python -m src.facturas.cli RUTA_FACTURA.pdf [opciones]
```

### Opciones principales

- `--lines` → analiza también las líneas de producto.
- `--tsv RUTA` → exporta TSV con el esquema oficial (`NumeroArchivo | Fecha | NºFactura | Proveedor | Descripcion | Categoria | BaseImponible | TipoIVA | Observaciones`).
- `--excel RUTA` → exporta Excel individual de la factura.
- `--outdir CARPETA` → carpeta de salida para Excel/maestro.
- `--keep-portes` → conserva línea(s) PORTES en lugar de prorratearlas.

### Opciones de control de totales

- `--total "999,99"` → especifica manualmente el total con IVA (formato europeo). Útil si el OCR del pie no lo detecta o si quieres forzar un valor en pruebas.
- `--no-reconcile` → ejecuta todo el flujo sin intentar cuadrar contra el total con IVA. **Solo para depuración**, no se actualiza el maestro anual.

### Ejemplos de uso

Exportar TSV con portes prorrateados y total manual:
```bash
python -m src.facturas.cli "facturas/ejemplo.pdf" --lines --tsv "out/salida.tsv" --total "250,07"
```

Exportar TSV sin reconciliar (no comprueba el total ni escribe maestro):
```bash
python -m src.facturas.cli "facturas/ejemplo.pdf" --lines --tsv "out/salida.tsv" --no-reconcile
```

### Notas

- El prorrateo de PORTES se reparte proporcionalmente entre todas las líneas de producto.
- Si no se indica `--total` ni `--no-reconcile`, el sistema intenta detectar el total automáticamente del PDF; si no lo consigue, pedirá el dato por consola.
- El maestro anual se guarda en `FACTURAS_AAAA.xlsx` dentro de la carpeta indicada con `--outdir` (o en la actual si no se indica).

---

## Próximos pasos
- Añadir overlays específicos para proveedores con formatos difíciles (ej. CERES).
- Ampliar set de pruebas automáticas en `tests/` con más proveedores.
- Documentar en `docs/` los flujos de uso más comunes y casos de revisión manual.

# Overlays de Proveedor (`patterns/*.yml`)

Los *overlays* son plantillas **por proveedor** que mejoran la lectura del PDF cuando el parser genérico no es suficiente (cabeceras raras, columnas irregulares, líneas de PORTES, etc.). Si existe un YAML para el proveedor, el sistema lo usa **automáticamente** sin romper el flujo actual.

---

## Dónde van

```
patterns/
  ALCAMPO.yml
  BM.yml
  CERES.yml
  ...
```

---

## Cómo se usan en el pipeline

1. **detect\_blocks.py**

   * Busca overlay por proveedor.
   * Si existe:

     * Extrae `fecha` y `nº de factura` con regex del YAML.
     * Recorta el **bloque de líneas** entre `start_after` y `stop_before`.
2. **parse\_lines.py**

   * Si el overlay define `regex_linea`, intenta parsear cada línea con ese patrón.
   * Si no hay overlay o no hace match, cae al **parser genérico**.
   * Marca `EsPortes=True` cuando `portes.keywords` coincide en la descripción.

> La clasificación (Descripción→Categoría) sigue yendo por el **diccionario** (Excel/JSON). Los YAML solo afectan a **lectura** y **limpieza**.

---

## Esquema YAML recomendado

Campos opcionales; usa solo los que necesites.

```yaml
provider: "CERES"               # Nombre principal del proveedor
aliases: ["CERES RC"]           # Alternativas para reconocerlo

# Cabecera
date:
  regex: "\b(\d{2})/(\d{2})/(\d{2,4})\b"  # captura d, m, y
ref:
  regex: "(?:Nº\s*Factura|Factura N\.|SERIE)[:\s-]*([A-Z0-9/-]{4,})"

# Bloque de líneas
lines:
  start_after: "DESCRIPCIÓN"     # texto desde el que empiezan las líneas
  stop_before: "BASE IMPONIBLE"  # texto antes del pie (subtotales/totales)
  regex_linea: "^(?P<descripcion>.+?)\s+(?P<base>\d{1,3}(?:\.\d{3})*,\d{2})$"
  ignore_if_contains: ["SUBTOTAL", "DTO", "BASE", "IVA", "TOTAL"]
  normalize:
    drop_units: true              # quita 125G, 0,75L, 70%
    drop_codes: true              # quita códigos numéricos largos

# Portes
portes:
  keywords: ["PORTES", "TRANSPORTE", "ENVÍO"]

# IVA (pistas informativas – el IVA final lo decide la lógica central)
iva:
  default: 10
  overrides:
    - when: "LIBROS|PRENSA"
      tipo: 4

# Números
numbers:
  decimal: ","                  # separador decimal en el PDF
  thousands: "."                # separador de miles en el PDF
```

### Notas de diseño

* `regex_linea`: se recomienda capturar **solo** `descripcion` y `base`. Cantidades/IVA por línea pueden añadirse más adelante, pero mantenerlo simple reduce errores.
* `ignore_if_contains`: filtra líneas de pie o subtotales que se cuelan en el cuerpo.
* `numbers`: permite normalizar **1,234.56** → **1.234,56**.

---

## Validación de YAMLs

Antes de usar nuevos/actualizados overlays:

```bash
python scripts/validar_patterns.py --dir patterns --strict
```

* Compila las regex y busca colisiones de `provider`/`aliases`.
* `--strict` trata los *warnings* como error para un CI más estricto.

---

## Buenas prácticas

* **Un proveedor = un YAML**. Evita mezclar varios proveedores en un mismo archivo.
* Empieza con lo mínimo: `date.regex`, `ref.regex`, `lines.start_after/stop_before`, `regex_linea`.
* Sé **conservador**: si `regex_linea` no matchea, el sistema caerá al parser genérico.
* Documenta casos raros en comentarios al inicio del YAML.

---

## Ejemplo completo (CERES)

```yaml
provider: "CERES"
aliases: ["CERES RC"]

date:
  regex: "\b(\d{2})/(\d{2})/(\d{2,4})\b"
ref:
  regex: "(?:Factura|Nº Factura|SERIE)[:\s-]*([A-Z0-9/-]{4,})"

lines:
  start_after: "DESCRIPCIÓN"
  stop_before: "BASE IMPONIBLE"
  regex_linea: "^(?P<descripcion>.+?)\s+(?P<base>\d{1,3}(?:\.\d{3})*,\d{2})$"
  ignore_if_contains: ["SUBTOTAL", "DTO", "BASE", "IVA", "TOTAL"]
  normalize:
    drop_units: true
    drop_codes: true

portes:
  keywords: ["PORTES", "TRANSPORTE"]

numbers:
  decimal: ","
  thousands: "."
```

---

## Integración técnica (resumen)

* `detect_blocks.py` → usa `apply_overlay_header` y `apply_overlay_lines`.
* `parse_lines.py` → intenta `parse_line_with_overlay`; si no, parser genérico; `mark_is_portes` para flags.
* `cli.py` → ya pasa el `proveedor` a `parse_lines_text` y detecta total en `full_text`.

---

## Problemas típicos y solución

* **No detecta fecha/nº** → revisa `date.regex`/`ref.regex` y prueba en regex101.
* **Se cuelan totales en el cuerpo** → añade a `ignore_if_contains` y/o ajusta `stop_before`.
* **Bases con punto en vez de coma** → configura `numbers.decimal/thousands`.
* **No matchea ninguna línea** → relaja `regex_linea` o elimina temporalmente para usar el parser genérico.

---

## Roadmap (mejoras futuras)

* Compilar todos los YAML a un `patterns_compilado.json` para arranque más rápido.
* Añadir tests por proveedor en `tests/` con 1 PDF real + `.total`.
* Opción de *prioridades* por patrón de línea si algún proveedor alterna formatos.

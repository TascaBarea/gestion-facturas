# Auditoría de Extractores — 06/04/2026 (actualizada)
> 111 extractores analizados (excluyendo generico.py, base.py, _plantilla.py)

## Resumen

| Campo | Tienen | Faltan | % |
|-------|--------|--------|---|
| extraer_lineas | 111 | 0 | 100% |
| extraer_total | 111 | 0 | 100% |
| extraer_fecha | 111 | 0 | 100% |
| extraer_referencia | 111 | 0 | 100% |
| cantidad | 111 | 0 | 100% |
| precio_ud | 111 | 0 | 100% |
| IVA | 110 | 1 | 99% |
| CIF | 111 | 0 | 100% |
| codigo | 97 | 14 | 87% |
| categoria | 62 | 49 | 55% |
| Método OCR | 23 | — | 20% |

## Campos completados en esta auditoría

### CANTIDAD y PRECIO_UD — antes: 104, ahora: 111
Corregidos (7): dist_levantina, emjamesa, garua, horno_santo_cristo,
jesus_figueroa_carrero, odoo, organia_oleum.

### FECHA — antes: 104, ahora: 111
Añadido `extraer_fecha` (7): alambique, aquarius, cafes_pozo, icatu, ikea, isifar, viandantes.

### REF — antes: 108, ahora: 111
Añadido `extraer_referencia` (3): garda, montbrione, quesos_felix.

## Pendientes por campo

### Sin CODIGO (14)
- aquarius, bm, garua, horno_santo_cristo, jesus_figueroa_carrero
- jimeluz, la_rosquilleria, lajas, lautre, makro
- odoo, organia_oleum, pago_alto_landon, quesos_cati

### Sin CATEGORIA (49) — dependen del Diccionario
- abbati, alambique, alcampo, ana_caballo, aquarius, arganza, benjamin_ortega
- bernal, berzal, bm, borboton, cafes_pozo, carlos_navas, ceres
- dist_levantina, ecoficus, ecoms, el_carrascal, felisa, fernando_moro
- fishgourmet, francisco_guerra, garcia_de_la_cruz, grupo_disber, ibarrako
- icatu, ikea, isifar, jaime_fernandez, la_alacena, la_lleidiria, lidl
- madrueño, manipulados_abellan, martin_abenza, molienda_verde, montbrione
- mrm, pifema, pilar_rodriguez, porvaz, productos_adell, quesos_felix
- sabores_paterna, serrin_no_chan, territorio_campero, tirso, viandantes
- virgen_de_la_sierra

### Sin IVA (1)
- bm (usa IVA incluido en precio, se calcula desde tabla IVA del ticket)

### Método OCR (23)
- alcampo, angel_borja, bodegas_munoz, casa_del_duque, ceres
- ecoms, embutidos_ferriol, fishgourmet, gaditaun, jimeluz
- julio_garcia, la_cuchara, la_lleidiria, la_rosquilleria
- manipulados_abellan, tirso, virgen_de_la_sierra, welldone
- alambique, aquarius, ikea, isifar, viandantes

## Notas

- **codigo**: muchos proveedores no usan códigos de artículo en sus facturas (servicios, tickets). No es un bug, es limitación del formato.
- **categoria**: requiere mapeo manual en el extractor o integración con `DiccionarioProveedoresCategoria.xlsx`. Prioridad baja para la mayoría.
- **bm (sin IVA)**: caso especial — precios del ticket incluyen IVA. Se resuelve vía tabla de tipos IVA por producto en el propio extractor.

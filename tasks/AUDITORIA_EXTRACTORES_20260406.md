# Auditoría de Extractores — 06/04/2026
> 112 extractores analizados (excluyendo generico.py, base.py, _plantilla.py)

## Resumen

| Campo | Tienen | Faltan | % |
|-------|--------|--------|---|
| extraer_lineas | 112 | 0 | 100% |
| extraer_total | 112 | 0 | 100% |
| IVA | 111 | 1 | 99% |
| extraer_fecha | 105 | 7 | 94% |
| extraer_referencia | 109 | 3 | 97% |
| cantidad | 104 | 8 | 93% |
| precio_ud | 104 | 8 | 93% |
| codigo | 98 | 14 | 88% |
| categoria | 85 | 27 | 76% |
| CIF | 106 | 6 | 95% |
| Método OCR | 18 | — | 16% |

## Pendientes por campo

### Sin CANTIDAD ni PRECIO_UD (8) — PRIORIDAD ALTA
Estos solo extraen artículo + base, sin desglose unitario:
- dist_levantina
- emjamesa
- garua
- horno_santo_cristo
- jesus_figueroa_carrero
- odoo
- organia_oleum
- pago_alto_landon

### Sin CODIGO (14)
- aquarius, bm, garua, horno_santo_cristo, jesus_figueroa_carrero
- jimeluz, la_rosquilleria, lajas, lautre, makro
- odoo, organia_oleum, pago_alto_landon, quesos_cati

### Sin CATEGORIA (27) — dependen del Diccionario
- alcampo, arganza, bernal, berzal, bm, borboton, carlos_navas
- ceres, dist_levantina, ecoficus, ecoms, el_carrascal, felisa
- francisco_guerra, grupo_disber, isifar, la_lleidiria, lidl
- madruño, molienda_verde, montbrione, mrm, porvaz
- quesos_felix, sabores_paterna, serrin_no_chan, virgen_de_la_sierra

### Sin FECHA (7)
- alambique, aquarius, cafes_pozo, icatu, ikea, isifar, viandantes

### Sin REF (3)
- garda, montbrione, quesos_felix

### Sin IVA (1)
- bm (usa IVA incluido en precio, se calcula desde tabla IVA del ticket)

### Método OCR (18)
- alcampo, angel_borja, bodegas_munoz, casa_del_duque, ceres
- ecoms, embutidos_ferriol, fishgourmet, gaditaun, jimeluz
- julio_garcia, la_cuchara, la_lleidiria, la_rosquilleria
- manipulados_abellan, tirso, virgen_de_la_sierra, welldone

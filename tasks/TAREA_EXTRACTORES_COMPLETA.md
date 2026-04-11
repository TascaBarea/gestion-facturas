# TAREA: Mejora completa de extractores — CAMPOS + CENTRALIZACIÓN
<!-- Para ejecutar con: claude --autoaccept -->
<!-- Sesión nocturna — 11/04/2026 -->

> Ruta extractores: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\`
> Ruta main.py: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\main.py`
> Ruta nucleo/parser.py: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\nucleo\parser.py`
> Ruta SPEC: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\docs\SPEC_GESTION_FACTURAS_v4.md`

---

## PARTE 1: CANTIDAD + PRECIO_UD (7 extractores)

### 1.1 emjamesa.py — TRIVIAL
Variables `uds` y `precio_str` ya capturadas. Añadir al dict en AMBOS bloques de `lineas.append`:
```python
'cantidad': self._convertir_importe(uds),
'precio_ud': self._convertir_importe(precio_str),
```

### 1.2 odoo.py — TRIVIAL
**Patrón belga** (el que matchea "Users"): group(2) = cantidad, group(3) = precio.
```python
cantidad = float(match.group(2))
precio_unitario = float(match.group(3))
# Añadir al dict:
'cantidad': cantidad,
'precio_ud': precio_unitario,
```
**Patrón español y fallback:** Añadir `'cantidad': 1, 'precio_ud': abs(round(importe, 2))`.

### 1.3 organia_oleum.py — FÁCIL
Cambiar regex para capturar precio_ud:
```python
# ANTES
r'^(\d+)\s+UD\s+(.+?)\s+L\.\d+\s+[\d,]+\s+([\d,]+)\s*$'
# DESPUÉS
r'^(\d+)\s+UD\s+(.+?)\s+L\.\d+\s+([\d,]+)\s+([\d,]+)\s*$'
```
Actualizar extracción:
```python
cantidad = int(m.group(1))
precio_ud = self._convertir_importe(m.group(3))
base = self._convertir_importe(m.group(4))
```
Añadir `'cantidad': cantidad, 'precio_ud': precio_ud` al dict.

### 1.4 jesus_figueroa_carrero.py — FÁCIL
Cambiar regex para capturar cantidad y precio:
```python
# ANTES
r'[\d,]+\s+bot\s+[\d,]+\s*€'
# DESPUÉS — añadir paréntesis de captura:
r'([\d,]+)\s+bot\s+([\d,]+)\s*€'
```
Los groups se desplazan: group(2)→cantidad, group(3)→precio_ud, group(4)→base (antes era group(2)).
Añadir `'cantidad': cantidad, 'precio_ud': precio_ud` al dict.

### 1.5 horno_santo_cristo.py — FÁCIL
Cambiar regex:
```python
# ANTES
r'(?:\d{8,}\s+)?(.+?)\s+10\s*%\s+[\d,]+\s*€\s+\d+\s+([\d,]+)\s*€'
# DESPUÉS
r'(?:\d{8,}\s+)?(.+?)\s+10\s*%\s+([\d,]+)\s*€\s+(\d+)\s+([\d,]+)\s*€'
```
group(2)=precio_ud, group(3)=cantidad, group(4)=base.
Añadir `'cantidad': int(m.group(3)), 'precio_ud': self._convertir_importe(m.group(2))` al dict.

### 1.6 dist_levantina.py — FÁCIL
Cambiar regex:
```python
# ANTES
r'^(\d{5})\s*=\s*(.+?)\s+\d+,\d{3}\s+[CU]\s+\d+,\d{3}\s+(\d+,\d{2})$'
# DESPUÉS
r'^(\d{5})\s*=\s*(.+?)\s+(\d+,\d{3})\s+[CU]\s+(\d+,\d{3})\s+(\d+,\d{2})$'
```
group(3)=cantidad, group(4)=precio_ud, group(5)=base.
Actualizar las referencias a groups y añadir `'cantidad', 'precio_ud'` al dict.

### 1.7 pago_alto_landon.py — YA ARREGLADO
Copiar la versión corregida desde `C:\Users\jaime\Downloads\pago_alto_landon.py` si existe,
o verificar que ya tiene cantidad, precio_ud, y consolidación SIN CARGO con precio_real.
Si NO existe el archivo descargado, aplicar los mismos cambios:
- Descomentar group(2) y group(3) como cantidad y precio_ud
- Añadir consolidación SIN CARGO: buscar líneas SIN CARGO, sumar cantidad al producto correspondiente
- Calcular precio_real = base * (1 + iva/100) / cantidad_total
- Mantener precio_ud como precio de catálogo original

---

## PARTE 2: PRECIO_REAL en Borbotón

### 2.1 borboton.py
Ya consolida cantidad (pagadas + regaladas) y recalcula precio_ud.
Añadir `precio_real` solo cuando hay unidades gratis:
```python
# Después de calcular base_final y cantidad_final:
entry = {
    'codigo': item['codigo'],
    'articulo': item['articulo'],
    'cantidad': cantidad_final,
    'precio_ud': round(base_final / cantidad_final, 2) if cantidad_final > 0 else item['precio_ud'],
    'iva': 21,
    'base': base_final
}
if cantidad_final != item['cantidad']:
    entry['precio_real'] = round(base_final * 1.21 / cantidad_final, 4)
lineas_finales.append(entry)
```

---

## PARTE 3: CATEGORÍA — Opción C (híbrido)

### 3.1 Cambio en main.py — centralizar lookup (5 líneas)
Después de ejecutar el extractor y obtener las líneas, añadir lookup de diccionario como fallback:
```python
# Buscar en main.py la función que procesa las líneas del extractor
# Después de obtener lineas = extractor.extraer_lineas(texto), añadir:
for linea in lineas:
    if not linea.get('categoria'):
        cat = diccionario.buscar(linea.get('articulo', '')) if diccionario else ''
        if cat:
            linea['categoria'] = cat
```
IMPORTANTE: Verificar cómo se llama la función de búsqueda en el diccionario.
Buscar en main.py: `cargar_diccionario`, `buscar_categoria`, `indice`, `DICCIONARIO`.
Adaptar la llamada al método real que exista.

### 3.2 Grupo A: Añadir 'categoria': self.categoria_fija al dict (21 extractores)
Para cada uno de estos extractores, buscar TODOS los `lineas.append({...})` y añadir
`'categoria': self.categoria_fija` si no lo tiene:

- abbati, alambique, ana_caballo, aquarius, benjamin_ortega, cafes_pozo
- fernando_moro, fishgourmet, ibarrako, icatu, ikea, jaime_fernandez
- manipulados_abellan, tirso, viandantes

NOTA: la_alacena, pifema, pilar_rodriguez, productos_adell, territorio_campero
tienen categoria_fija pero necesitan ajustes (ver 3.3).

### 3.3 Correcciones de categoria_fija
```python
# martin_abenza.py — cambiar:
categoria_fija = 'CONSERVAS'
# a:
categoria_fija = 'CONSERVAS VEGETALES'

# pifema.py — añadir si no existe, o cambiar:
categoria_fija = 'VINOS'

# pilar_rodriguez.py — añadir si no existe, o cambiar:
categoria_fija = 'DESPENSA'

# territorio_campero.py — lógica condicional:
# Si el artículo contiene "PATATAS FRITAS ARTESANAS" → 'PATATAS FRITAS APERITIVO'
# Si no → buscar en diccionario (no poner categoria_fija, dejar que main.py busque)
# Implementar así:
categoria_fija = None  # O eliminar la línea
# Y en extraer_lineas, para cada línea:
# if 'PATATAS' in articulo.upper():
#     linea['categoria'] = 'PATATAS FRITAS APERITIVO'
# (si no, main.py buscará en diccionario)
```

### 3.4 Grupo B: Nuevos categoria_fija (mono-producto)
Añadir `categoria_fija = '...'` y `'categoria': self.categoria_fija` en el dict:

```python
# carlos_navas.py
categoria_fija = 'QUESOS'

# la_lleidiria.py (la_lleidiria.py o la_llildiria.py — buscar el nombre correcto)
categoria_fija = 'QUESOS'

# quesos_felix.py
categoria_fija = 'QUESOS'

# isifar.py
categoria_fija = 'DULCES'

# porvaz.py
categoria_fija = 'CONSERVAS MAR'
```

### 3.5 Grupo B: Multi-producto (NO poner categoria_fija, main.py buscará en diccionario)
Estos NO se tocan — main.py hará el lookup automático (ver 3.1):
- arganza, ceres, montbrione, virgen_de_la_sierra, serrin_no_chan
- francisco_guerra, molienda_verde

### 3.6 Grupo C: Multi-producto sin nada (ya cubiertos por 3.1)
Estos tampoco se tocan — main.py buscará en diccionario:
- bernal, berzal, dist_levantina, ecoficus, felisa, grupo_disber, lidl, sabores_paterna

---

## PARTE 4: TOTAL — Fallback genérico + TOTAL_CALCULADO

### 4.1 En main.py, después de obtener líneas
Siempre calcular TOTAL_CALCULADO:
```python
total_calculado = round(sum(
    linea.get('base', 0) * (1 + linea.get('iva', 0) / 100)
    for linea in lineas
), 2)
```

### 4.2 Fallback para TOTAL_PDF
Si el extractor no devuelve total, usar el genérico de nucleo/parser.py:
```python
total_pdf = extractor.extraer_total(texto)
if total_pdf is None:
    total_pdf = extraer_total(texto)  # de nucleo.parser
```
Verificar que `extraer_total` está importado de `nucleo.parser`.

### 4.3 Cuadre
```python
if total_pdf is not None and total_calculado is not None:
    diff = abs(total_pdf - total_calculado)
    if diff <= 0.50:
        cuadre = 'OK'
    else:
        cuadre = f'DESCUADRE {total_pdf - total_calculado:+.2f}€'
else:
    cuadre = 'SIN TOTAL PDF'
```
Tolerancia: **0,50€**. El TOTAL_PDF manda para contabilidad. El descuadre solo marca, no bloquea.

---

## PARTE 5: FECHA — Fallback genérico + comparación con archivo

### 5.1 En main.py
Si el extractor no devuelve fecha, usar el genérico:
```python
fecha_pdf = extractor.extraer_fecha(texto) if hasattr(extractor, 'extraer_fecha') else None
if fecha_pdf is None:
    fecha_pdf = extraer_fecha(texto)  # de nucleo.parser
```

### 5.2 Comparar con fecha del nombre de archivo
```python
# Extraer MMDD del nombre de archivo (posición fija en convención TTYY MMDD PROVEEDOR)
fecha_archivo = extraer_fecha_de_nombre(nombre_archivo)  # implementar si no existe

if fecha_pdf and fecha_archivo:
    diff_dias = abs((fecha_pdf - fecha_archivo).days)
    if diff_dias > 15:
        flag = f'FECHA_DISCREPANTE: PDF={fecha_pdf:%d/%m} vs Archivo={fecha_archivo:%d/%m}'
```
Tolerancia: 15 días (normal por retrasos en envío/recepción).

---

## PARTE 6: REF — Fallback genérico

### 6.1 En main.py
Si el extractor no devuelve referencia, usar el genérico:
```python
ref = extractor.extraer_referencia(texto) if hasattr(extractor, 'extraer_referencia') else None
if not ref:
    ref = extraer_referencia(texto)  # de nucleo.parser
```
Sin REF de ninguna fuente → campo vacío, flag "SIN_REF" en observaciones.

---

## PARTE 7: VERIFICACIÓN

### 7.1 Verificar sintaxis de cada extractor modificado
```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores
for f in emjamesa.py odoo.py organia_oleum.py jesus_figueroa_carrero.py horno_santo_cristo.py dist_levantina.py borboton.py pago_alto_landon.py martin_abenza.py pifema.py pilar_rodriguez.py territorio_campero.py carlos_navas.py la_lleidiria.py quesos_felix.py isifar.py porvaz.py abbati.py alambique.py ana_caballo.py aquarius.py benjamin_ortega.py cafes_pozo.py fernando_moro.py fishgourmet.py ibarrako.py icatu.py ikea.py jaime_fernandez.py manipulados_abellan.py tirso.py viandantes.py; do
  python -c "import ast; ast.parse(open('$f', encoding='utf-8').read())" && echo "OK: $f" || echo "FAIL: $f"
done
```

### 7.2 Test con una factura si disponible
Para cada extractor con CANTIDAD/PRECIO_UD modificado, buscar factura en Dropbox:
```
dir "C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\FACTURAS 2026\FACTURAS RECIBIDAS" /s /b | findstr /i "PROVEEDOR"
```
Si hay factura, ejecutar test rápido:
```python
import sys
sys.path.insert(0, r'C:\_ARCHIVOS\TRABAJO\Facturas\Parseo')
import pdfplumber
from extractores.NOMBRE import ExtractorNombre

with pdfplumber.open("ruta_factura.pdf") as pdf:
    texto = "\n".join(p.extract_text() or "" for p in pdf.pages)

ext = ExtractorNombre()
lineas = ext.extraer_lineas(texto)
for l in lineas:
    print(f"  {l.get('articulo','')[:30]} | cant={l.get('cantidad','?')} | pu={l.get('precio_ud','?')} | base={l.get('base','?')} | cat={l.get('categoria','?')}")
```

### 7.3 Test de main.py
```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\Parseo
python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read()); print('main.py OK')"
```

### 7.4 Ejecutar pytest
```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
python -m pytest tests/unit/ -v --ignore=tests/unit/test_api_security.py
```
(Ignorar test_api_security.py porque falla por pytest-asyncio, no por estos cambios.)

---

## PARTE 8: ACTUALIZAR SPEC

Añadir al changelog de `docs/SPEC_GESTION_FACTURAS_v4.md`:

```markdown
### v5.8 (11/04/2026) — EXTRACTORES: CAMPOS + CENTRALIZACIÓN + CONTROL CALIDAD

**CANTIDAD/PRECIO_UD añadidos (7 extractores):**
- Trivial (datos ya capturados): emjamesa, odoo
- Regex ampliado: organia_oleum, jesus_figueroa_carrero, horno_santo_cristo, dist_levantina
- Con consolidación SIN CARGO + precio_real: pago_alto_landon

**precio_real (nuevo campo):**
- Coste efectivo con IVA por unidad cuando hay producto gratis (SIN CARGO / promociones)
- Fórmula: `base × (1 + iva/100) / cantidad_total`
- Implementado en: pago_alto_landon, borboton

**CATEGORÍA centralizada (Opción C — híbrido):**
- Extractor propone con `categoria_fija` (mono-producto) → main.py completa con Diccionario (multi-producto)
- 15 extractores: añadido `'categoria': self.categoria_fija` al dict
- 5 correcciones: martin_abenza→CONSERVAS VEGETALES, pifema→VINOS, pilar_rodriguez→DESPENSA, carlos_navas/la_lleidiria/quesos_felix→QUESOS, isifar→DULCES, porvaz→CONSERVAS MAR
- territorio_campero: condicional (PATATAS si match, sino diccionario)
- 7 multi-producto delegados a diccionario: arganza, ceres, montbrione, virgen_de_la_sierra, serrin_no_chan, francisco_guerra, molienda_verde
- main.py: lookup automático en DiccionarioProveedoresCategoria para líneas sin categoría

**TOTAL — doble control:**
- TOTAL_PDF: del extractor o fallback genérico (nucleo/parser.py)
- TOTAL_CALCULADO: siempre sum(base × (1 + iva/100))
- Tolerancia cuadre: ±0,50€. Descuadre marca flag, no bloquea
- TOTAL_PDF manda para contabilidad

**FECHA — fallback + verificación:**
- FECHA_PDF: del extractor o fallback genérico
- Comparación con fecha del nombre de archivo (convención TTYY MMDD)
- Flag FECHA_DISCREPANTE si diferencia > 15 días

**REF — fallback genérico:**
- Del extractor o fallback nucleo/parser.py
- Flag SIN_REF si no se encuentra

**gmail.py v1.15 (mismo día):**
- Deduplicación Dropbox multi-señal (SHA-256 + tamaño en toda la carpeta destino)
- Fail-fast Excel bloqueado (detecta PermissionError al arrancar)
- subir_archivo() devuelve Tuple[str, bool] — salta Excel si duplicado

**Infraestructura:**
- gestion.tascabarea.com activo (Cloudflare Tunnel → VPS Contabo → Streamlit 8501)
- DNS migrado: registro `gestion` de A record → CNAME tunnel
- Sección 18 SPEC: infraestructura cloud documentada
- Página "Ejecutar Scripts" reescrita: 4 tarjetas + log tiempo real + 5 scripts secundarios
```

También actualizar la tabla de resumen de extractores en la sección correspondiente de la SPEC
si existe (campos extraídos, porcentajes).

---

## ORDEN DE EJECUCIÓN

1. Parte 1: CANTIDAD/PRECIO_UD (7 extractores)
2. Parte 2: precio_real en borboton
3. Parte 3: CATEGORÍA (main.py + 21 extractores grupo A + correcciones + grupo B)
4. Parte 4: TOTAL fallback + TOTAL_CALCULADO (main.py)
5. Parte 5: FECHA fallback + comparación (main.py)
6. Parte 6: REF fallback (main.py)
7. Parte 7: Verificación
8. Parte 8: Actualizar SPEC

## REGLAS

- NO tocar garua.py (imposible — no tiene líneas individuales)
- NO tocar ana_caballo, ecoficus, molletes, pifema respecto a producto gratis (son productos DIFERENTES)
- Si un regex modificado rompe el parseo (0 líneas donde antes había >0), REVERTIR inmediatamente
- `_convertir_importe()` es heredado de ExtractorBase — usarlo siempre
- Al añadir paréntesis al regex, verificar que los group() siguientes se ajustan
- Tolerancia cuadre TOTAL: 0,50€
- Tolerancia FECHA discrepante: 15 días
- TOTAL_PDF manda para contabilidad. Descuadre solo marca, NO bloquea
- Al modificar main.py, NO cambiar la lógica existente de validar_cuadre si existe — solo añadir/complementar
- Verificar sintaxis de CADA archivo modificado antes de pasar al siguiente

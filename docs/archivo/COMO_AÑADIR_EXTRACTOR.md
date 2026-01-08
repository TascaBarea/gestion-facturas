# 🔧 CÓMO AÑADIR UN EXTRACTOR NUEVO

**Versión:** 5.3  
**Última actualización:** 28/12/2025

---

## 🎯 RESUMEN RÁPIDO

```
1. Copia la plantilla: extractores/_plantilla.py → extractores/nuevo_proveedor.py
2. Cambia el nombre, CIF y variantes en @registrar()
3. Implementa extraer_lineas() → SIEMPRE líneas individuales
4. Prueba: python tests/probar_extractor.py "PROVEEDOR" factura.pdf
5. ¡Listo! El extractor se registra automáticamente
6. Ejecuta: python generar_proveedores.py (actualiza docs)
```

---

## 🔑 REGLAS CRÍTICAS

### 1. SIEMPRE pdfplumber (OCR solo para escaneados)
```python
metodo_pdf = 'pdfplumber'  # SIEMPRE por defecto
metodo_pdf = 'ocr'         # SOLO si es imagen/escaneado
metodo_pdf = 'hibrido'     # Si algunas facturas son escaneadas y otras no
```

### 2. SIEMPRE líneas individuales
**1 artículo = 1 línea en el Excel**

```python
# ❌ MAL (desglose fiscal agrupado)
lineas.append({
    'articulo': 'PRODUCTOS VARIOS IVA 21%',
    'base': 646.55,
    'iva': 21
})

# ✅ BIEN (líneas individuales)
lineas.append({
    'codigo': '1594',
    'articulo': 'FEVER-TREE',
    'cantidad': 24,
    'precio_ud': 0.80,
    'iva': 21,
    'base': 19.20
})
```

### 3. Columnas obligatorias
```python
{
    'codigo': str,        # Código del producto ('' si no hay)
    'articulo': str,      # Nombre del artículo (max 50 chars)
    'cantidad': int/float,   # Unidades
    'precio_ud': float,   # Precio unitario
    'iva': int,           # 4, 10 o 21
    'base': float         # Importe SIN IVA
}
```

### 4. Incluir TODAS las variantes del nombre
```python
@registrar('PROVEEDOR', 'VARIANTE1', 'VARIANTE2', 'VARIANTE3')
```

### 5. Portes: distribuir proporcionalmente
```python
# Si hay portes, distribuir entre productos
if portes > 0:
    base_productos = sum(l['base'] for l in lineas)
    for linea in lineas:
        proporcion = linea['base'] / base_productos
        linea['base'] += portes * proporcion
```

---

## 🆕 PATRONES APRENDIDOS (28/12/2025)

### Problema: PDF mixto (algunos escaneados, otros no)
**Síntoma:** Algunas facturas del proveedor son PDFs digitales, otras escaneadas

**Solución:** Implementar método híbrido
```python
metodo_pdf = 'hibrido'

def extraer_texto(self, pdf_path: str) -> str:
    """Intenta pdfplumber primero, OCR como fallback."""
    texto = self.extraer_texto_pdfplumber(pdf_path)
    
    # Si hay poco texto, usar OCR
    if len(texto.strip()) < 100:
        texto = self.extraer_texto_ocr(pdf_path)
    
    return texto
```
**Proveedores afectados:** ECOMS, VIRGEN DE LA SIERRA, CASA DEL DUQUE

---

### Problema: Letras de IVA en lugar de porcentajes
**Síntoma:** Factura usa A, B, C en lugar de 4%, 10%, 21%

**Solución:** Mapear letras a porcentajes
```python
MAPA_IVA = {
    'A': 4,   # Superreducido (alimentos básicos)
    'B': 10,  # Reducido (alimentos procesados)
    'C': 21,  # General (bebidas alcohólicas, limpieza)
    'D': 0,   # Exento
}

def _obtener_iva_desde_letra(self, letra: str) -> int:
    return self.MAPA_IVA.get(letra.upper(), 21)
```
**Proveedores afectados:** ECOMS SUPERMARKET

---

### Problema: Códigos de producto con espacios
**Síntoma:** Código "LR 010" se corta mal

**Solución:** Patrón regex flexible para códigos
```python
# Código puede tener espacios: "LR 010", "CA 005"
patron = re.compile(
    r'^([A-Z]{2}\s*\d{3})\s+'    # Código con espacio opcional
    r'(.+?)\s+'                   # Descripción
    r'(\d+)\s+'                   # Cantidad
    r'([\d,]+)\s*€?$'             # Precio
, re.MULTILINE)
```
**Proveedores afectados:** MARITA COSTA

---

### Problema: IVA mixto en misma factura (4% y 10%)
**Síntoma:** Algunos productos llevan 4% (AOVE, picos) y otros 10%

**Solución:** Clasificar IVA por tipo de producto
```python
def _detectar_iva_producto(self, descripcion: str) -> int:
    """Detecta IVA según tipo de producto."""
    desc_upper = descripcion.upper()
    
    # IVA 4% - Superreducido
    if any(x in desc_upper for x in ['AOVE', 'ACEITE OLIVA', 'PICOS', 'PAN']):
        return 4
    
    # IVA 21% - General  
    if any(x in desc_upper for x in ['VINO', 'CERVEZA', 'LICOR']):
        return 21
    
    # IVA 10% - Default para alimentación
    return 10
```
**Proveedores afectados:** MARITA COSTA, BM, FELISA GOURMET

---

### Problema: SaaS extranjero sin IVA español
**Síntoma:** Factura de USA/UE sin IVA, importe en USD

**Solución:** IVA 0% y conversión de moneda
```python
class ExtractorSaaS(ExtractorBase):
    iva_default = 0  # Sin IVA español
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        # Extraer importe (puede estar en USD)
        m = re.search(r'\$\s*([\d,]+\.?\d*)', texto)
        if m:
            importe_usd = float(m.group(1).replace(',', ''))
            # Usar tipo de cambio aproximado o de la factura
            importe_eur = importe_usd * 0.92  # O extraer de factura
            lineas.append({
                'articulo': 'SUSCRIPCIÓN SAAS',
                'cantidad': 1,
                'base': round(importe_eur, 2),
                'iva': 0
            })
        return lineas
```
**Proveedores afectados:** CELONIS/MAKE, OPENAI, ANTHROPIC

---

### Problema: Multi-albaranes en una factura
**Síntoma:** Factura agrupa varios albaranes con productos repetidos

**Solución:** Iterar por secciones de albarán
```python
def extraer_lineas(self, texto: str) -> List[Dict]:
    lineas = []
    
    # Dividir por albaranes
    secciones = re.split(r'ALBARÁN\s*:?\s*(\d+)', texto)
    
    for seccion in secciones:
        # Extraer productos de cada sección
        for match in patron_producto.finditer(seccion):
            lineas.append({...})
    
    return lineas
```
**Proveedores afectados:** PIFEMA, VIRGEN DE LA SIERRA

---

## 🆕 PATRONES APRENDIDOS (26/12/2025)

### Problema: Etiquetas de IVA intercambiadas
**Síntoma:** DESCUADRE porque "BASE IMP. AL 10%" tiene IVA real del 21%

**Solución:** Calcular IVA real dividiendo cuota/base
```python
def _detectar_iva_real(self, base: float, cuota: float) -> int:
    """Calcula el IVA real independiente de la etiqueta."""
    if base <= 0:
        return 21  # default
    iva_real = round(cuota / base * 100)
    return iva_real if iva_real in [4, 10, 21] else 21
```
**Proveedores afectados:** DISTRIBUCIONES LAVAPIES

---

### Problema: Símbolo € corrupto
**Síntoma:** El regex no encuentra "TOTAL 84,73 €" porque el € aparece como `â‚¬`

**Solución:** Buscar `€` en el regex (el símbolo real)
```python
# ❌ MAL - busca carácter corrupto
m = re.search(r'TOTAL\s+([\d,]+)\s*â‚¬', texto)

# ✅ BIEN - busca símbolo real
m = re.search(r'TOTAL\s+([\d,]+)\s*€', texto)
```
**Proveedores afectados:** BENJAMIN ORTEGA, JAIME FERNANDEZ

---

### Problema: Total no encontrado (SIN_TOTAL)
**Síntoma:** extraer_total() devuelve None

**Solución:** Buscar en múltiples lugares
```python
def extraer_total(self, texto: str) -> Optional[float]:
    # 1. Buscar "TOTAL" directo
    m = re.search(r'TOTAL\s+([\d,]+)\s*€', texto)
    if m:
        return self._convertir_europeo(m.group(1))
    
    # 2. Buscar en vencimiento (fecha + importe + importe)
    m = re.search(r'(\d{2}/\d{2}/\d{2})\s+([\d,]+)\s*€\s+([\d,]+)\s*€', texto)
    if m:
        return self._convertir_europeo(m.group(3))
    
    # 3. Buscar cuadro fiscal (5 números al final)
    # Formato: BRUTO BASE %IVA IVA TOTAL
    m = re.search(r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$', texto, re.MULTILINE)
    if m:
        return self._convertir_europeo(m.group(5))
    
    # 4. Calcular desde bases
    lineas = self.extraer_lineas(texto)
    if lineas:
        return round(sum(l['base'] * (1 + l['iva']/100) for l in lineas), 2)
    
    return None
```
**Proveedores afectados:** PANRUJE, JIMELUZ, CELONIS

---

### Problema: PDF escaneado (imagen)
**Síntoma:** pdfplumber no extrae texto

**Solución:** Implementar OCR con tesseract
```python
def _extraer_texto_ocr(self, pdf_path: str) -> str:
    import subprocess
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Convertir PDF a imágenes
        subprocess.run(['pdftoppm', '-png', '-r', '300', pdf_path, f'{tmpdir}/page'])
        
        # OCR cada imagen
        texto = ""
        for img in sorted(os.listdir(tmpdir)):
            if img.endswith('.png'):
                result = subprocess.run(
                    ['tesseract', f'{tmpdir}/{img}', 'stdout', '-l', 'spa'],
                    capture_output=True, text=True
                )
                texto += result.stdout
        return texto
```
**Proveedores afectados:** JULIO GARCIA VIVAS, LA ROSQUILLERIA, FISHGOURMET, CASA DEL DUQUE

---

## 📝 PLANTILLA COMPLETA

```python
"""
Extractor para [NOMBRE PROVEEDOR]

[Descripción del proveedor]
CIF: [CIF]
IBAN: [IBAN si lo tienes]

Formato factura (pdfplumber):
[Describir formato]

IVA: [Tipos aplicables]

Creado: [FECHA]
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re
import pdfplumber


@registrar('PROVEEDOR', 'VARIANTE1', 'VARIANTE2')
class ExtractorProveedor(ExtractorBase):
    """Extractor para facturas de PROVEEDOR."""
    
    nombre = 'PROVEEDOR'
    cif = 'B12345678'
    iban = 'ES00 0000 0000 0000 0000 0000'
    metodo_pdf = 'pdfplumber'  # o 'ocr' o 'hibrido'
    # categoria_fija = 'CATEGORIA'  # Solo si SIEMPRE es la misma
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = str(texto).strip().replace('€', '').replace(' ', '')
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas INDIVIDUALES de productos.
        
        IMPORTANTE: 1 artículo = 1 línea
        """
        lineas = []
        
        # Patrón para líneas de producto
        patron_linea = re.compile(
            r'^(\d{4,6})\s+'              # Código
            r'(.+?)\s+'                    # Descripción
            r'(\d+)\s+'                    # Cantidad
            r'(\d+,\d{2})\s+'              # Precio
            r'(\d+,\d{2})$'                # Importe
        , re.MULTILINE)
        
        for match in patron_linea.finditer(texto):
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            cantidad = int(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            importe = self._convertir_europeo(match.group(5))
            
            # Filtrar cabeceras
            if any(x in descripcion.upper() for x in ['DESCRIPCION', 'TOTAL']):
                continue
            
            if importe < 0.01:
                continue
            
            lineas.append({
                'codigo': codigo,
                'articulo': descripcion[:50],
                'cantidad': cantidad,
                'precio_ud': round(precio, 2),
                'iva': 21,  # O detectar del PDF
                'base': round(importe, 2)
            })
        
        return lineas
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Método 1: TOTAL directo
        patron = re.search(r'TOTAL\s+([\d,]+)\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        
        # Método 2: Calcular desde líneas
        lineas = self.extraer_lineas(texto)
        if lineas:
            return round(sum(l['base'] * (1 + l['iva']/100) for l in lineas), 2)
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        patron = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
```

---

## 📋 PATRONES REGEX COMUNES

### Tabla estándar
```python
# CODIGO DESCRIPCION CANTIDAD PRECIO IMPORTE
r'^(\d{4,6})\s+(.+?)\s+(\d+)\s+(\d+,\d{2})\s+(\d+,\d{2})$'
```

### Con precio 3 decimales
```python
# 01071 MZ LATAS 5 KG 3 19,900 59,70
r'^(\d{4,6})\s+(.+?)\s+(\d+)\s+(\d+,\d{2,3})\s+(\d+,\d{2})$'
```

### Con cantidad decimal (kg)
```python
# CA0005 ANCHOA 10,00% 12,0000 24,0000 288,00
r'^([A-Z]{2}\d{4})\s+(.+?)\s+(\d+,\d{4})\s+(\d+,\d{4})\s+(\d+,\d{2})$'
```

### Cuadro fiscal (5 números)
```python
# BRUTO BASE %IVA IVA TOTAL
# 89,28 89,28 4,0 3,57 92,85
r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$'
```

### Base + IVA en línea
```python
# BASE IMP. AL 10% 71,76 IVA 10% 7,18
r'BASE\s+IMP\.\s+AL\s+(\d+)%\s+([\d,]+)\s+IVA\s+\d+%\s+([\d,]+)'
```

---

## 🏷️ CATEGORÍA FIJA vs DICCIONARIO

### Usar categoria_fija cuando:
- El proveedor SIEMPRE vende lo mismo
- Ejemplos: KINEMA (gestoría), YOIGO (teléfono), SEGURMA (alarma)

```python
class ExtractorKinema(ExtractorBase):
    nombre = 'KINEMA'
    categoria_fija = 'GESTORIA'
```

### Usar diccionario cuando:
- El proveedor tiene productos variados
- Ejemplos: CERES (cervezas), MERCADONA (supermercado)

```python
class ExtractorCeres(ExtractorBase):
    nombre = 'CERES'
    # Sin categoria_fija → busca en diccionario
```

---

## ⚠️ ERRORES COMUNES

| Error | Causa | Solución |
|-------|-------|----------|
| "Extractor no encontrado" | Nombre en @registrar() no coincide | Añadir más variantes |
| "No se encontraron líneas" | Patrón regex incorrecto | Probar con --debug |
| "Solo 1 línea con desglose" | Usa desglose fiscal | REHACER con líneas individuales |
| "Total no cuadra" | Base mal calculada o portes | Verificar y distribuir portes |
| "IVA incorrecto" | IVA hardcodeado | Detectar IVA real: cuota/base*100 |
| "Algunas facturas fallan" | Formato mixto | Usar extractor híbrido |
| "€ no se encuentra" | Símbolo corrupto | Buscar `€` no `â‚¬` |
| "Etiquetas intercambiadas" | 10% y 21% al revés | Calcular IVA real |
| "PDF sin texto" | Es imagen/escaneado | Usar OCR o método híbrido |

---

## 🧪 TESTING

```cmd
# Test rápido
python tests/probar_extractor.py "PROVEEDOR" "factura.pdf"

# Con debug (ver texto extraído)
python tests/probar_extractor.py "PROVEEDOR" "factura.pdf" --debug
```

---

## 📚 EJEMPLOS REALES

### Por método de extracción

| Método | Proveedores ejemplo |
|--------|---------------------|
| **pdfplumber** | CERES, BM, ZUCCA, FABEIRO, KINEMA, LIDL, CELONIS |
| **OCR** | LA ROSQUILLERIA, FISHGOURMET, GADITAUN, CASA DEL DUQUE |
| **Híbrido** | ECOMS, VIRGEN DE LA SIERRA, JULIO GARCIA |

### Por tipo especial

| Tipo | Proveedores | Nota |
|------|-------------|------|
| Con portes | SILVA CORDERO, ARGANZA, BIELLEBI, PANRUJE, VIRGEN DE LA SIERRA | Distribuir proporcionalmente |
| Categoría fija | KINEMA, YOIGO, SEGURMA, CELONIS | No busca en diccionario |
| IVA mixto | FABEIRO, MERCADONA, BM, MARITA COSTA, FELISA GOURMET | Detectar por línea |
| Retención IRPF | JAIME FERNANDEZ, BENJAMIN ORTEGA | Alquileres |
| Moneda extranjera | OPENAI (USD), ANTHROPIC | Convertir a EUR |
| Letras IVA | ECOMS (A=4%, B=10%, C=21%) | Mapear |
| IVA intercambiado | LAVAPIES | Calcular IVA real |
| SaaS extranjero | CELONIS/MAKE, OPENAI, ANTHROPIC | IVA 0% |
| Multi-albaranes | PIFEMA, VIRGEN DE LA SIERRA | Iterar secciones |

---

## ✅ CHECKLIST NUEVO EXTRACTOR

- [ ] Copiar plantilla a `extractores/nuevo.py`
- [ ] Definir nombre, CIF, variantes en @registrar()
- [ ] Definir IBAN si lo tienes
- [ ] Elegir método: pdfplumber, ocr, o híbrido
- [ ] Implementar extraer_lineas() con líneas individuales
- [ ] Manejar portes (distribuir, no línea separada)
- [ ] Verificar símbolo € (no usar â‚¬)
- [ ] Si IVA mixto: detectar por producto o usar cuadro fiscal
- [ ] Probar con 3+ facturas reales
- [ ] Verificar que cuadra (tolerancia 0.10€)
- [ ] Ejecutar `python generar_proveedores.py`
- [ ] Hacer commit y push

---

*Última actualización: 28/12/2025 - v5.3*

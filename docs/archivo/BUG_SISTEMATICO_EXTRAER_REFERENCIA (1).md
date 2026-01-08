# 🐛 BUG SISTEMÁTICO SOLUCIONADO DEFINITIVAMENTE

## Fecha: 29/12/2025
## Solución: Modificar `base.py` (UN SOLO ARCHIVO)

---

## 📋 EL PROBLEMA

### Síntoma
Los extractores tenían `extraer_numero_factura()` que funcionaba, pero `main.py` llamaba a `extraer_referencia()` y no encontraba nada.

### Causa raíz
**DESAJUSTE DE NOMBRES:**

| Componente | Método |
|------------|--------|
| `main.py` | Llama a `extraer_referencia()` |
| Extractores | Definen `extraer_numero_factura()` |

---

## ✅ SOLUCIÓN DEFINITIVA

**Modificar `base.py`** para que `extraer_referencia()` llame automáticamente a `extraer_numero_factura()` si existe.

### Código añadido en `ExtractorBase.extraer_referencia()`:

```python
def extraer_referencia(self, texto: str) -> Optional[str]:
    # =========================================================
    # COMPATIBILIDAD: Si la subclase define extraer_numero_factura,
    # usarlo automáticamente (fix bug 29/12/2025)
    # =========================================================
    if hasattr(self, 'extraer_numero_factura'):
        resultado = self.extraer_numero_factura(texto)
        if resultado:
            return resultado
    
    # Fallback: patrones genéricos
    patrones = [...]
```

---

## 📦 INSTALACIÓN

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main\extractores

REM 1. IMPORTANTE: Borrar caché
rmdir /s /q __pycache__

REM 2. Copiar SOLO base.py (soluciona TODOS los extractores)
copy /Y "RUTA_DESCARGA\base.py" .
```

**¡ESO ES TODO!** No hay que modificar ningún otro extractor.

---

## 🎯 BENEFICIOS

1. **UN solo archivo modificado** → menos riesgo de errores
2. **Todos los extractores se benefician** automáticamente
3. **Futuros extractores funcionan** sin cambios adicionales
4. **Compatibilidad total** → funciona con ambos nombres de método

---

## 🔍 VERIFICACIÓN

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\ParsearFacturas-main
python -c "from extractores.ceres import ExtractorCeres; import pdfplumber; e = ExtractorCeres(); pdf = pdfplumber.open(r'RUTA_FACTURA_CERES.pdf'); texto = ''.join([p.extract_text() or '' for p in pdf.pages]); print('REF:', e.extraer_referencia(texto))"
```

Debe devolver: `REF: 2539610` (o el número de la factura)

---

## 📊 RESUMEN

| Antes | Después |
|-------|---------|
| Cada extractor necesitaba alias | Solo modificar `base.py` |
| Fácil olvidar el alias | Automático para siempre |
| 50+ archivos a revisar | 1 archivo modificado |

---

*Solucionado el 29/12/2025*

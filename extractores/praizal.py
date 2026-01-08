# -*- coding: utf-8 -*-
"""
Extractor para PRAIZAL (PILAR BLANCO GUTIÉRREZ)

Quesería artesanal de oveja de León (Jabares de los Oteros)
NIF: 09768240W
IBAN: ES23 3035 0271 3627 1410 2115

Formato factura (PDF digital):
- Líneas producto: ARTICULO CANTIDAD PRECIO € SUBTOTAL € %IVA TOTAL €
- Ejemplo: KG Queso pata de mulo semi (3 piezas) 4,960 20,50 € 101,68 € 4,00% 105,75 €
- Ignorar líneas de lote: "Lote 130825 fech. Cons. Pref. 280226"

IVA: 4% (quesos)
Categoría fija: QUESOS

Creado: 03/01/2026
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('PRAIZAL', 'PILAR BLANCO', 'PILAR BLANCO GUTIERREZ', 'PRAIZAL PILAR BLANCO')
class ExtractorPraizal(ExtractorBase):
    """Extractor para facturas de PRAIZAL (Quesería Pilar Blanco)."""
    
    nombre = 'PRAIZAL'
    cif = '09768240W'
    iban = 'ES23 3035 0271 3627 1410 2115'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'QUESOS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        """
        Extrae líneas de productos (quesos).
        
        Formato:
        KG Queso pata de mulo semi (3 piezas) 4,960 20,50 € 101,68 € 4,00% 105,75 €
        Ud. Queso pasta blanda CUMULO 6 piezas) 1,735 22,00 € 38,17 € 4,00% 39,70 €
        """
        lineas = []
        
        # Patrón para líneas de producto
        # UNIDAD + DESCRIPCION + CANTIDAD + PRECIO € + SUBTOTAL € + %IVA + TOTAL €
        patron = re.compile(
            r'^(KG|Ud\.|kg\.?)\s+'                    # Unidad (KG, Ud., kg.)
            r'(Queso[^€]+?)\s+'                       # Descripción (empieza con Queso)
            r'(\d+,\d{3})\s+'                         # Cantidad (3 decimales)
            r'(\d+,\d{2})\s*€\s+'                     # Precio unitario
            r'(\d+,\d{2})\s*€\s+'                     # Subtotal (BASE)
            r'(\d+,\d{2})%\s+'                        # % IVA
            r'(\d+,\d{2})\s*€'                        # Total con IVA
        , re.MULTILINE | re.IGNORECASE)
        
        for match in patron.finditer(texto):
            unidad = match.group(1).upper().replace('.', '')
            descripcion = match.group(2).strip()
            cantidad = self._convertir_europeo(match.group(3))
            precio = self._convertir_europeo(match.group(4))
            base = self._convertir_europeo(match.group(5))
            iva = int(self._convertir_europeo(match.group(6)))
            
            # Limpiar descripción (quitar info de piezas entre paréntesis al final)
            descripcion = re.sub(r'\s*\(\d+\s*pieza[s1]?\)\s*$', '', descripcion, flags=re.IGNORECASE)
            descripcion = descripcion.strip()
            
            # Añadir unidad al inicio si no está
            if unidad == 'KG' and not descripcion.upper().startswith('KG'):
                articulo = f"KG {descripcion}"
            elif unidad == 'UD' and not descripcion.upper().startswith('UD'):
                articulo = f"Ud. {descripcion}"
            else:
                articulo = descripcion
            
            lineas.append({
                'codigo': '',
                'articulo': articulo[:50],
                'cantidad': round(cantidad, 3),
                'precio_ud': round(precio, 2),
                'iva': iva if iva > 0 else 4,  # Default 4% para quesos
                'base': round(base, 2)
            })
        
        return lineas
    
    def _convertir_europeo(self, texto: str) -> float:
        """Convierte formato europeo (1.234,56) a float."""
        if not texto:
            return 0.0
        texto = texto.strip()
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except:
            return 0.0
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        # Formato: TOTAL FACTURA 105,75 €
        patron = re.search(r'TOTAL\s+FACTURA\s+(\d+,\d{2})\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_europeo(patron.group(1))
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        # Formato: Fecha: 22/09/2024 o Fecha: 10/06/2025
        patron = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', texto)
        if patron:
            return patron.group(1)
        return None
    
    def extraer_referencia(self, texto: str) -> Optional[str]:
        """Extrae número de factura."""
        # Formato: Factura nº: 5292025
        patron = re.search(r'Factura\s*n[ºo°]?:?\s*(\d+)', texto, re.IGNORECASE)
        if patron:
            return patron.group(1)
        return None

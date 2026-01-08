"""
Extractor para EMJAMESA S.L. (Ibéricos).

Jamones y embutidos ibéricos.
CIF: B37352077
IBAN: REDACTED_IBAN

Formato factura:
FACTURA Nº: 002500641 V
Fecha: 15/01/2025
...
CÓDIGO DESCRIPCIÓN UDS KILOS PRECIO IMPORTE € IVA
01 LONGANIZA DE CERDO IBERICO... 2 4,52 7,78 35,14€ 10

Número factura: 002500641 V (9 dígitos + espacio + letra opcional)

Creado: 18/12/2025
Actualizado: 07/01/2026 - Añadido extraer_numero_factura(), categoria_fija
"""
from extractores.base import ExtractorBase
from extractores import registrar
from typing import List, Dict, Optional
import re


@registrar('EMJAMESA')
class ExtractorEmjamesa(ExtractorBase):
    nombre = 'EMJAMESA'
    cif = 'B37352077'
    iban = 'REDACTED_IBAN'
    metodo_pdf = 'pdfplumber'
    categoria_fija = 'CHACINAS'
    
    def extraer_lineas(self, texto: str) -> List[Dict]:
        lineas = []
        
        # Preprocesar: unir líneas partidas
        lineas_texto = texto.split('\n')
        texto_unido = []
        i = 0
        while i < len(lineas_texto):
            linea = lineas_texto[i].strip()
            if re.match(r'^\d{1,4}\s+[A-Z]', linea):
                if re.search(r'\d+[.,]\d{2}\s*€(\s+\d+)?$', linea):
                    texto_unido.append(linea)
                else:
                    linea_completa = linea
                    j = i + 1
                    while j < len(lineas_texto):
                        sig = lineas_texto[j].strip()
                        if sig.startswith('Lote:') or sig.startswith('ALBARÁN') or re.match(r'^\d{1,4}\s+[A-Z]', sig):
                            break
                        linea_completa += ' ' + sig
                        if re.search(r'\d+[.,]\d{2}\s*€(\s+\d+)?$', linea_completa):
                            i = j
                            break
                        j += 1
                    texto_unido.append(linea_completa)
            else:
                texto_unido.append(linea)
            i += 1
        
        texto_procesado = '\n'.join(texto_unido)
        
        # Patrón CON columna IVA
        patron_con_iva = re.compile(
            r'^(\d{1,4})\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*€\s+(\d+)$',
            re.MULTILINE
        )
        # Patrón SIN columna IVA
        patron_sin_iva = re.compile(
            r'^(\d{1,4})\s+(.+?)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*€$',
            re.MULTILINE
        )
        
        matches_con_iva = list(patron_con_iva.finditer(texto_procesado))
        matches_sin_iva = list(patron_sin_iva.finditer(texto_procesado))
        
        if len(matches_con_iva) >= len(matches_sin_iva):
            for match in matches_con_iva:
                codigo, desc, uds, kilos, precio_str, importe_str, iva_str = match.groups()
                desc = re.sub(r'\s*Lote:\s*\S+', '', desc).strip()
                lineas.append({
                    'codigo': codigo,
                    'articulo': desc.strip(),
                    'iva': int(iva_str),
                    'base': self._convertir_importe(importe_str),
                    'categoria': self.categoria_fija
                })
        else:
            for match in matches_sin_iva:
                codigo, desc, uds, kilos, precio_str, importe_str = match.groups()
                desc = re.sub(r'\s*Lote:\s*\S+', '', desc).strip()
                desc = re.sub(r'\s+[A-Z]{2,4}[-]?\d{4}$', '', desc).strip()
                iva = 21 if codigo == '01' else 10
                lineas.append({
                    'codigo': codigo,
                    'articulo': desc.strip(),
                    'iva': iva,
                    'base': self._convertir_importe(importe_str),
                    'categoria': self.categoria_fija
                })
        
        return lineas
    
    def extraer_numero_factura(self, texto: str) -> Optional[str]:
        """
        Extrae número de factura.
        
        Formato: FACTURA Nº: 002500641 V
        (9 dígitos + espacio opcional + letra opcional)
        """
        # Buscar "FACTURA Nº:" seguido de número
        patron = re.search(
            r'FACTURA\s*[Nn]º[:\s]*(\d{9}\s*[A-Z]?)',
            texto,
            re.IGNORECASE
        )
        if patron:
            return patron.group(1).strip()
        
        # Alternativa: buscar número de 9 dígitos seguido de letra
        patron2 = re.search(r'\b(\d{9})\s+([A-Z])\b', texto)
        if patron2:
            return f"{patron2.group(1)} {patron2.group(2)}"
        
        return None
    
    def extraer_fecha(self, texto: str) -> Optional[str]:
        """Extrae fecha de la factura."""
        patron = re.search(r'Fecha[:\s]*(\d{2})/(\d{2})/(\d{4})', texto, re.IGNORECASE)
        if patron:
            return f"{patron.group(1)}/{patron.group(2)}/{patron.group(3)}"
        return None
    
    def extraer_total(self, texto: str) -> Optional[float]:
        """Extrae total de la factura."""
        patron = re.search(r'TOTAL[:\s]*([\d.,]+)\s*€', texto, re.IGNORECASE)
        if patron:
            return self._convertir_importe(patron.group(1))
        return None

"""
Módulo de categorización de artículos.

Busca en DiccionarioProveedoresCategoria.xlsx para asignar:
- CATEGORIA: Categoría del artículo
- TIPO_IVA: Tipo de IVA (4, 10, 21)

Usa matching parcial con normalización para tolerar variaciones en nombres.

Creado: 19/12/2025
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class CategorizadorArticulos:
    """
    Categoriza artículos usando el diccionario de proveedores.
    
    Uso:
        cat = CategorizadorArticulos('datos/DiccionarioProveedoresCategoria.xlsx')
        categoria, iva = cat.buscar('LICORES MADRUEÑO', 'FEVER-TREE 24x200ml')
    """
    
    def __init__(self, ruta_diccionario: str):
        """
        Inicializa el categorizador cargando el diccionario.
        
        Args:
            ruta_diccionario: Ruta al archivo Excel con el diccionario
        """
        self.ruta = Path(ruta_diccionario)
        self.diccionario = {}  # {proveedor_norm: [(articulo_norm, categoria, iva), ...]}
        self.pendientes = []   # Lista de artículos no encontrados
        self._cargar_diccionario()
    
    def _cargar_diccionario(self):
        """Carga y normaliza el diccionario de categorías."""
        if not self.ruta.exists():
            print(f"⚠️ Diccionario no encontrado: {self.ruta}")
            return
        
        df = pd.read_excel(self.ruta)
        
        for _, row in df.iterrows():
            proveedor = self._normalizar(row['PROVEEDOR'])
            articulo = self._normalizar(row['ARTICULO'])
            categoria = row['CATEGORIA'] if pd.notna(row['CATEGORIA']) else 'PENDIENTE'
            iva = int(row['TIPO_IVA']) if pd.notna(row['TIPO_IVA']) else 21
            
            if proveedor not in self.diccionario:
                self.diccionario[proveedor] = []
            
            self.diccionario[proveedor].append((articulo, categoria, iva))
        
        print(f"✅ Diccionario cargado: {len(df)} artículos de {len(self.diccionario)} proveedores")
    
    def _normalizar(self, texto: str) -> str:
        """
        Normaliza texto para matching flexible.
        
        Quita espacios, guiones, puntos, acentos y pasa a mayúsculas.
        """
        if pd.isna(texto) or texto is None:
            return ""
        
        texto = str(texto).upper().strip()
        
        # Quitar caracteres especiales
        texto = texto.replace('-', '').replace(' ', '').replace('.', '').replace(',', '')
        texto = texto.replace('/', '').replace('\\', '').replace('(', '').replace(')', '')
        texto = texto.replace('"', '').replace("'", '').replace('´', '').replace('`', '')
        
        # Quitar acentos
        texto = texto.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        texto = texto.replace('Ó', 'O').replace('Ú', 'U').replace('Ü', 'U')
        texto = texto.replace('Ñ', 'N')
        
        return texto
    
    def _normalizar_proveedor(self, proveedor: str) -> str:
        """
        Normaliza nombre de proveedor para búsqueda.
        
        Maneja variantes comunes como:
        - 'LICORES MADRUEÑO' → 'LICORESMADRUENO'
        - 'SABORES DE PATERNA' → 'SABORESDEPATERNA'
        """
        norm = self._normalizar(proveedor)
        
        # Mapeo de variantes conocidas
        variantes = {
            'LICORESMADRUENO': 'LICORESMADRUENO',
            'MADRUENO': 'LICORESMADRUENO',
            'MARIANOMADRUENO': 'LICORESMADRUENO',
            'SABORESPATERNA': 'SABORESPATERNA',
            'SABORESDEPATERNA': 'SABORESPATERNA',
            'EMBUTIDOSBERNAL': 'EMBUTIDOSBERNAL',
            'JAMONESBERNAL': 'EMBUTIDOSBERNAL',
            'BERNAL': 'EMBUTIDOSBERNAL',
            'BERZAL': 'BERZAL',
            'BERZALHERMANOS': 'BERZALHERMANOS',
            'FRANCISCOGUERRA': 'FRANCISCOGUERRA',
            'MARITA': 'MARITA',
            'MARITACOSTA': 'MARITA',
        }
        
        return variantes.get(norm, norm)
    
    def buscar(self, proveedor: str, articulo: str, iva_factura: Optional[int] = None) -> Tuple[str, int]:
        """
        Busca categoría e IVA para un artículo.
        
        Args:
            proveedor: Nombre del proveedor
            articulo: Nombre del artículo
            iva_factura: IVA extraído de la factura (tiene prioridad)
            
        Returns:
            Tupla (categoria, iva)
        """
        prov_norm = self._normalizar_proveedor(proveedor)
        art_norm = self._normalizar(articulo)
        
        # Si no hay diccionario para este proveedor
        if prov_norm not in self.diccionario:
            # Buscar en todos los proveedores por si hay match parcial del nombre
            for prov_key in self.diccionario.keys():
                if prov_key in prov_norm or prov_norm in prov_key:
                    prov_norm = prov_key
                    break
            else:
                # No encontrado
                self._registrar_pendiente(proveedor, articulo, iva_factura)
                return ('PENDIENTE', iva_factura if iva_factura else 21)
        
        # Buscar artículo con matching parcial
        for dict_art, categoria, iva_dict in self.diccionario.get(prov_norm, []):
            # Match exacto
            if dict_art == art_norm:
                return (categoria, iva_factura if iva_factura else iva_dict)
            
            # Match parcial: el artículo del diccionario está contenido en el de la factura
            if dict_art and len(dict_art) >= 4 and dict_art in art_norm:
                return (categoria, iva_factura if iva_factura else iva_dict)
            
            # Match parcial inverso: el artículo de la factura está contenido en el diccionario
            if art_norm and len(art_norm) >= 4 and art_norm in dict_art:
                return (categoria, iva_factura if iva_factura else iva_dict)
        
        # No encontrado
        self._registrar_pendiente(proveedor, articulo, iva_factura)
        return ('PENDIENTE', iva_factura if iva_factura else 21)
    
    def _registrar_pendiente(self, proveedor: str, articulo: str, iva: Optional[int]):
        """Registra un artículo no encontrado para revisión posterior."""
        pendiente = {
            'proveedor': proveedor,
            'articulo': articulo,
            'iva': iva if iva else 21
        }
        
        # Evitar duplicados
        if pendiente not in self.pendientes:
            self.pendientes.append(pendiente)
    
    def categorizar_lineas(self, proveedor: str, lineas: List[Dict]) -> List[Dict]:
        """
        Categoriza una lista de líneas extraídas.
        
        Args:
            proveedor: Nombre del proveedor
            lineas: Lista de diccionarios con líneas extraídas
            
        Returns:
            Lista de diccionarios con CATEGORIA añadida
        """
        resultado = []
        
        for linea in lineas:
            articulo = linea.get('articulo', '')
            iva_factura = linea.get('iva')
            
            categoria, iva_final = self.buscar(proveedor, articulo, iva_factura)
            
            linea_cat = linea.copy()
            linea_cat['categoria'] = categoria
            linea_cat['iva'] = iva_final
            
            resultado.append(linea_cat)
        
        return resultado
    
    def obtener_pendientes(self) -> List[Dict]:
        """Devuelve la lista de artículos no encontrados."""
        return self.pendientes.copy()
    
    def limpiar_pendientes(self):
        """Limpia la lista de pendientes."""
        self.pendientes = []
    
    def resumen_pendientes(self) -> str:
        """Genera un resumen de artículos pendientes."""
        if not self.pendientes:
            return "✅ Todos los artículos categorizados"
        
        resumen = f"⚠️ {len(self.pendientes)} artículos PENDIENTES de categorizar:\n"
        
        # Agrupar por proveedor
        por_proveedor = {}
        for p in self.pendientes:
            prov = p['proveedor']
            if prov not in por_proveedor:
                por_proveedor[prov] = []
            por_proveedor[prov].append(p['articulo'])
        
        for prov, arts in sorted(por_proveedor.items()):
            resumen += f"\n  {prov} ({len(arts)} artículos):\n"
            for art in arts[:5]:  # Mostrar máximo 5 por proveedor
                resumen += f"    - {art}\n"
            if len(arts) > 5:
                resumen += f"    ... y {len(arts) - 5} más\n"
        
        return resumen


# Función de conveniencia para uso rápido
_categorizador = None

def categorizar(proveedor: str, articulo: str, iva_factura: Optional[int] = None, 
                ruta_diccionario: str = 'datos/DiccionarioProveedoresCategoria.xlsx') -> Tuple[str, int]:
    """
    Función de conveniencia para categorizar un artículo.
    
    Uso:
        from nucleo.categorias import categorizar
        categoria, iva = categorizar('MADRUEÑO', 'FEVER-TREE')
    """
    global _categorizador
    
    if _categorizador is None:
        _categorizador = CategorizadorArticulos(ruta_diccionario)
    
    return _categorizador.buscar(proveedor, articulo, iva_factura)

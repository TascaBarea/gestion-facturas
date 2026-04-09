"""Diagnóstico de los 5 PDFs problemáticos del último parseo"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from main import procesar_factura, cargar_diccionario, normalizar_proveedor
from extractores import obtener_extractor
from nucleo.pdf import extraer_texto_pdf

_, _, indice = cargar_diccionario(Path('datos/DiccionarioProveedoresCategoria.xlsx'))

carpeta = Path(r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\FACTURAS 2026\FACTURAS RECIBIDAS\2 TRIMESTRE 2026\ATRASADAS")

problemas = [
    "ATRASADA 1T26 0327 BERZAL HERMANOS SA TF.pdf",
    "ATRASADA 1T26 0331 GUERRA OLLER FRANCISCO TF.pdf",
    "ATRASADA 2T25 0401 SOM ENERGIA SCCL RC.pdf",
    "ATRASADA 1T26 0323 SABORES DE PATERNA SCA TF.pdf",
    "ATRASADA 1T26 0331 PANIFIESTO LAVAPIES SL TF.pdf",
]

for nombre in problemas:
    ruta = carpeta / nombre
    if not ruta.exists():
        print(f"\n{'='*70}")
        print(f"❌ NO EXISTE: {nombre}")
        continue
    
    print(f"\n{'='*70}")
    print(f"📄 {nombre}")
    print(f"{'='*70}")
    
    # 1. Extractor
    # Simular lo que hace procesar_factura
    prov_norm = normalizar_proveedor(nombre.replace('.pdf', '').replace('.PDF', ''))
    ext = obtener_extractor(prov_norm)
    ext_name = ext.__class__.__name__ if ext else "None (usará genérico)"
    metodo = ext.metodo_pdf if ext and hasattr(ext, 'metodo_pdf') else 'pypdf'
    print(f"  Proveedor normalizado: {prov_norm}")
    print(f"  Extractor: {ext_name}")
    print(f"  Método PDF: {metodo}")
    
    # 2. Texto
    texto = extraer_texto_pdf(ruta, metodo=metodo, fallback=True)
    texto_preview = texto[:1500] if texto else "(VACÍO)"
    print(f"  Texto ({len(texto) if texto else 0} chars):")
    print(f"  ---")
    for line in texto_preview.split('\n')[:30]:
        print(f"  | {line}")
    print(f"  ---")
    
    # 3. Procesar
    f = procesar_factura(ruta, indice)
    print(f"  Total extraído: {f.total}")
    print(f"  Líneas: {len(f.lineas)}")
    print(f"  Cuadre: {f.cuadre}")
    print(f"  Errores: {f.errores}")
    if f.lineas:
        for l in f.lineas[:5]:
            print(f"    → {l.articulo:40s} base={l.base} cat={l.categoria}")

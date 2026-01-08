"""
Datos de proveedores conocidos.

Este archivo contiene:
- PROVEEDORES_CONOCIDOS: diccionario con CIF e IBAN de cada proveedor
- CIF_A_PROVEEDOR: diccionario inverso para detectar proveedor por CIF
- EXTRACTOR_PDF_PROVEEDOR: método de extracción PDF por proveedor
- PROVEEDOR_ALIAS: alias para normalización de nombres

Actualizado: 18/12/2025 - v4.0
"""

# =============================================================================
# CONFIGURACIÓN BÁSICA
# =============================================================================

CIF_PROPIO = "B87760575"

# Bancos a evitar en IBAN (cuando hay varios)
BANCOS_EVITAR = ["0049"]

# =============================================================================
# ALIAS DE PROVEEDORES
# =============================================================================

# Para búsqueda en diccionario de categorías
PROVEEDOR_ALIAS_DICCIONARIO = {
    'JAMONES BERNAL': 'EMBUTIDOS BERNAL',
    'BERNAL': 'EMBUTIDOS BERNAL',
}

# Para normalización de nombre en salida
PROVEEDOR_NOMBRE_SALIDA = {
    'JAVIER ALBORES': 'CONTROLPLAGA',
    'JAVIER ARBORES': 'CONTROLPLAGA',
    'ALBORES': 'CONTROLPLAGA',
    'ARBORES': 'CONTROLPLAGA',
}

# =============================================================================
# DATOS DE PROVEEDORES (CIF e IBAN)
# =============================================================================

PROVEEDORES_CONOCIDOS = {
    # --- SERRÍN NO CHAN ---
    'SERRIN': {'cif': 'B87214755', 'iban': 'REDACTED_IBAN'},
    'SERRÍN': {'cif': 'B87214755', 'iban': 'REDACTED_IBAN'},
    'SERRIN NO CHAN': {'cif': 'B87214755', 'iban': 'REDACTED_IBAN'},
    
    # --- FABEIRO ---
    'FABEIRO': {'cif': 'B79992079', 'iban': 'REDACTED_IBAN'},
    
    # --- DISTRIBUCIONES LAVAPIES ---
    'LAVAPIES': {'cif': 'F88424072', 'iban': 'REDACTED_IBAN'},
    'DISTRIBUCIONES LAVAPIES': {'cif': 'F88424072', 'iban': 'REDACTED_IBAN'},
    
    # --- ALQUILERES (personas físicas) ---
    'BENJAMIN ORTEGA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'ORTEGA ALONSO': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'JAIME FERNANDEZ': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'FERNANDEZ MORENO': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- SABORES DE PATERNA ---
    'SABORES DE PATERNA': {'cif': 'B96771832', 'iban': 'REDACTED_IBAN'},
    'SABORES': {'cif': 'B96771832', 'iban': 'REDACTED_IBAN'},
    'PATERNA': {'cif': 'B96771832', 'iban': 'REDACTED_IBAN'},
    
    # --- MARTIN ARBENZA / EL MODESTO ---
    'MARTIN ARBENZA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'MARTIN ABENZA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'EL MODESTO': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- FRANCISCO GUERRA ---
    'FRANCISCO GUERRA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- TRUCCO / ISAAC RODRIGUEZ ---
    'TRUCCO': {'cif': 'REDACTED_DNI', 'iban': ''},
    'TRUCCO COPIAS': {'cif': 'REDACTED_DNI', 'iban': ''},
    'ISAAC RODRIGUEZ': {'cif': 'REDACTED_DNI', 'iban': ''},
    'ISAAC RODRIGUEZ PACHA': {'cif': 'REDACTED_DNI', 'iban': ''},
    
    # --- ISTA ---
    'ISTA': {'cif': 'A50090133', 'iban': ''},
    
    # --- AMAZON ---
    'AMAZON': {'cif': 'W0184081H', 'iban': ''},
    
    # --- VINOS DE ARGANZA ---
    'VINOS DE ARGANZA': {'cif': 'B24416869', 'iban': 'REDACTED_IBAN'},
    'ARGANZA': {'cif': 'B24416869', 'iban': 'REDACTED_IBAN'},
    
    # --- LA PURISIMA ---
    'LA PURISIMA': {'cif': 'F30005193', 'iban': 'REDACTED_IBAN'},
    'PURISIMA': {'cif': 'F30005193', 'iban': 'REDACTED_IBAN'},
    
    # --- MOLLETES ARTESANOS ---
    'MOLLETES': {'cif': 'B93662708', 'iban': 'REDACTED_IBAN'},
    'MOLLETES ARTESANOS': {'cif': 'B93662708', 'iban': 'REDACTED_IBAN'},
    
    # --- BODEGAS BORBOTON ---
    'BODEGAS BORBOTON': {'cif': 'B45851755', 'iban': 'REDACTED_IBAN'},
    'BORBOTON': {'cif': 'B45851755', 'iban': 'REDACTED_IBAN'},
    
    # --- LOS GREDALES ---
    'LOS GREDALES': {'cif': 'B83594150', 'iban': 'REDACTED_IBAN'},
    'GREDALES': {'cif': 'B83594150', 'iban': 'REDACTED_IBAN'},
    'LOS GREDALES DEL TOBOSO': {'cif': 'B83594150', 'iban': 'REDACTED_IBAN'},
    
    # --- GADITAUN / María Linarejos ---
    'GADITAUN': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'MARILINA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'MARIA LINAREJOS': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- ECOMS / DIA ---
    'ECOMS': {'cif': 'B72738602', 'iban': ''},
    'ECOMS SUPERMARKET': {'cif': 'B72738602', 'iban': ''},
    'DIA': {'cif': 'B72738602', 'iban': ''},
    
    # --- FELISA GOURMET ---
    'FELISA GOURMET': {'cif': 'B72113897', 'iban': 'REDACTED_IBAN'},
    'FELISA': {'cif': 'B72113897', 'iban': 'REDACTED_IBAN'},
    
    # --- JAMONES BERNAL ---
    'JAMONES BERNAL': {'cif': 'B67784231', 'iban': 'REDACTED_IBAN'},
    'BERNAL': {'cif': 'B67784231', 'iban': 'REDACTED_IBAN'},
    'EMBUTIDOS BERNAL': {'cif': 'B67784231', 'iban': 'REDACTED_IBAN'},
    
    # --- EMJAMESA ---
    'EMJAMESA': {'cif': 'B37352077', 'iban': 'REDACTED_IBAN'},
    
    # --- MAKRO ---
    'MAKRO': {'cif': 'A28647451', 'iban': ''},
    
    # --- LA MOLIENDA VERDE ---
    'LA MOLIENDA VERDE': {'cif': 'B06936140', 'iban': 'REDACTED_IBAN'},
    'MOLIENDA VERDE': {'cif': 'B06936140', 'iban': 'REDACTED_IBAN'},
    
    # --- ZUBELZU ---
    'ZUBELZU': {'cif': 'B75079608', 'iban': 'REDACTED_IBAN'},
    'ZUBELZU PIPARRAK': {'cif': 'B75079608', 'iban': 'REDACTED_IBAN'},
    
    # --- EL CARRASCAL ---
    'CARRASCAL': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'EL CARRASCAL': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'JOSE LUIS SANCHEZ': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- SILVA CORDERO ---
    'SILVA CORDERO': {'cif': 'B09861535', 'iban': 'REDACTED_IBAN'},
    'QUESOS SILVA CORDERO': {'cif': 'B09861535', 'iban': 'REDACTED_IBAN'},
    'ACEHUCHE': {'cif': 'B09861535', 'iban': 'REDACTED_IBAN'},
    
    # --- JIMELUZ ---
    'JIMELUZ': {'cif': 'B84527068', 'iban': ''},
    'JIMELUZ EMPRENDEDORES': {'cif': 'B84527068', 'iban': ''},
    
    # --- LA ROSQUILLERIA ---
    'LA ROSQUILLERIA': {'cif': 'B73814949', 'iban': 'REDACTED_IBAN'},
    'ROSQUILLERIA': {'cif': 'B73814949', 'iban': 'REDACTED_IBAN'},
    
    # --- IBARRAKO PIPARRAK ---
    'IBARRAKO PIPARRAK': {'cif': 'F20532297', 'iban': 'REDACTED_IBAN'},
    'IBARRAKO PIPARRA': {'cif': 'F20532297', 'iban': 'REDACTED_IBAN'},
    'IBARRAKO': {'cif': 'F20532297', 'iban': 'REDACTED_IBAN'},
    
    # --- MANIPULADOS ABELLAN ---
    'MANIPULADOS ABELLAN': {'cif': 'B30473326', 'iban': 'REDACTED_IBAN'},
    'ABELLAN': {'cif': 'B30473326', 'iban': 'REDACTED_IBAN'},
    'EL LABRADOR': {'cif': 'B30473326', 'iban': 'REDACTED_IBAN'},
    
    # --- ZUCCA / FORMAGGIARTE ---
    'ZUCCA': {'cif': 'B42861948', 'iban': 'REDACTED_IBAN'},
    'FORMAGGIARTE': {'cif': 'B42861948', 'iban': 'REDACTED_IBAN'},
    'QUESERIA ZUCCA': {'cif': 'B42861948', 'iban': 'REDACTED_IBAN'},
    
    # --- CVNE ---
    'CVNE': {'cif': 'A48002893', 'iban': 'REDACTED_IBAN'},
    'COMPAÑIA VINICOLA': {'cif': 'A48002893', 'iban': 'REDACTED_IBAN'},
    
    # --- ADEUDOS (sin IBAN) ---
    'YOIGO': {'cif': 'A82528548', 'iban': ''},
    'XFERA': {'cif': 'A82528548', 'iban': ''},
    'SOM ENERGIA': {'cif': 'F55091367', 'iban': ''},
    'LUCERA': {'cif': 'B98670003', 'iban': ''},
    'SEGURMA': {'cif': 'A48198626', 'iban': ''},
    'KINEMA': {'cif': 'F84600022', 'iban': ''},
    
    # --- MIGUEZ CAL / FORPLAN ---
    'MIGUEZ CAL': {'cif': 'B79868006', 'iban': 'REDACTED_IBAN'},
    'FORPLAN': {'cif': 'B79868006', 'iban': 'REDACTED_IBAN'},
    
    # --- MARITA COSTA ---
    'MARITA COSTA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- PILAR RODRIGUEZ / EL MAJADAL ---
    'PILAR RODRIGUEZ': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'EL MAJADAL': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'HUEVOS EL MAJADAL': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- PANIFIESTO ---
    'PANIFIESTO': {'cif': 'B87874327', 'iban': ''},
    'PANIFIESTO LAVAPIES': {'cif': 'B87874327', 'iban': ''},
    
    # --- JULIO GARCIA VIVAS ---
    'JULIO GARCIA VIVAS': {'cif': 'REDACTED_DNI', 'iban': ''},
    'GARCIA VIVAS': {'cif': 'REDACTED_DNI', 'iban': ''},
    
    # --- MRM ---
    'MRM': {'cif': 'A80280845', 'iban': 'REDACTED_IBAN'},
    'MRM-2': {'cif': 'A80280845', 'iban': 'REDACTED_IBAN'},
    'INDUSTRIAS CARNICAS MRM': {'cif': 'A80280845', 'iban': 'REDACTED_IBAN'},
    
    # --- DISBER ---
    'DISBER': {'cif': 'B46144424', 'iban': 'REDACTED_IBAN'},
    'GRUPO DISBER': {'cif': 'B46144424', 'iban': 'REDACTED_IBAN'},
    
    # --- LA BARRA DULCE ---
    'LA BARRA DULCE': {'cif': 'B19981141', 'iban': 'REDACTED_IBAN'},
    'BARRA DULCE': {'cif': 'B19981141', 'iban': 'REDACTED_IBAN'},
    
    # --- GRUPO CAMPERO ---
    'GRUPO TERRITORIO CAMPERO': {'cif': 'B16690141', 'iban': 'REDACTED_IBAN'},
    'TERRITORIO CAMPERO': {'cif': 'B16690141', 'iban': 'REDACTED_IBAN'},
    'GRUPO CAMPERO': {'cif': 'B16690141', 'iban': 'REDACTED_IBAN'},
    
    # --- PRODUCTOS ADELL ---
    'PRODUCTOS ADELL': {'cif': 'B12711636', 'iban': 'REDACTED_IBAN'},
    'CROQUELLANAS': {'cif': 'B12711636', 'iban': 'REDACTED_IBAN'},
    
    # --- ECOFICUS ---
    'ECOFICUS': {'cif': 'B10214021', 'iban': 'REDACTED_IBAN'},
    
    # --- QUESOS ROYCA ---
    'QUESOS ROYCA': {'cif': 'E06388631', 'iban': ''},
    'COMERCIAL ROYCA': {'cif': 'E06388631', 'iban': ''},
    'ROYCA': {'cif': 'E06388631', 'iban': ''},
    
    # --- ANA CABALLO ---
    'ANA CABALLO': {'cif': 'B87925970', 'iban': 'REDACTED_IBAN'},
    'ANA CABALLO VERMOUTH': {'cif': 'B87925970', 'iban': 'REDACTED_IBAN'},
    
    # --- QUESOS FELIX ---
    'QUESOS FELIX': {'cif': 'B47440136', 'iban': 'REDACTED_IBAN'},
    'ARMANDO SANZ': {'cif': 'B47440136', 'iban': 'REDACTED_IBAN'},
    'FELIX': {'cif': 'B47440136', 'iban': 'REDACTED_IBAN'},
    
    # --- PANRUJE ---
    'PANRUJE': {'cif': 'B13858014', 'iban': 'REDACTED_IBAN'},
    'ROSQUILLAS LA ERMITA': {'cif': 'B13858014', 'iban': 'REDACTED_IBAN'},
    'LA ERMITA': {'cif': 'B13858014', 'iban': 'REDACTED_IBAN'},
    
    # --- CARLOS NAVAS ---
    'CARLOS NAVAS': {'cif': 'B37416419', 'iban': 'REDACTED_IBAN'},
    'QUESERIA CARLOS NAVAS': {'cif': 'B37416419', 'iban': 'REDACTED_IBAN'},
    'QUESERIA NAVAS': {'cif': 'B37416419', 'iban': 'REDACTED_IBAN'},
    'QUESOS NAVAS': {'cif': 'B37416419', 'iban': 'REDACTED_IBAN'},
    
    # --- PORVAZ ---
    'PORVAZ': {'cif': 'B36281087', 'iban': 'REDACTED_IBAN'},
    'PORVAZ VILAGARCIA': {'cif': 'B36281087', 'iban': 'REDACTED_IBAN'},
    'CONSERVAS TITO': {'cif': 'B36281087', 'iban': 'REDACTED_IBAN'},
    'TITO': {'cif': 'B36281087', 'iban': 'REDACTED_IBAN'},
    
    # --- CONTROLPLAGA ---
    'CONTROLPLAGA': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'JAVIER ALBORES': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    'JAVIER ARBORES': {'cif': 'REDACTED_DNI', 'iban': 'REDACTED_IBAN'},
    
    # --- ANGEL Y LOLI ---
    'ANGEL Y LOLI': {'cif': 'REDACTED_DNI', 'iban': ''},
    'ALFARERIA ANGEL': {'cif': 'REDACTED_DNI', 'iban': ''},
    
    # --- QUESOS DEL CATI ---
    'QUESOS DEL CATI': {'cif': 'F12499455', 'iban': 'REDACTED_IBAN'},
    'QUESOS CATI': {'cif': 'F12499455', 'iban': 'REDACTED_IBAN'},
    
    # --- BIELLEBI ---
    'BIELLEBI': {'cif': '06089700725', 'iban': 'REDACTED_IBAN'},
    'BIELLEBI SRL': {'cif': '06089700725', 'iban': 'REDACTED_IBAN'},
    
    # --- FERRIOL ---
    'EMBUTIDOS FERRIOL': {'cif': 'B57955098', 'iban': 'REDACTED_IBAN'},
    'EMBOTITS FERRIOL': {'cif': 'B57955098', 'iban': 'REDACTED_IBAN'},
    'FERRIOL': {'cif': 'B57955098', 'iban': 'REDACTED_IBAN'},
    
    # --- ABBATI ---
    'ABBATI CAFFE': {'cif': 'B82567876', 'iban': ''},
    'ABBATI': {'cif': 'B82567876', 'iban': ''},
    
    # --- BODEGAS MUÑOZ MARTIN ---
    'BODEGAS MUÑOZ MARTIN': {'cif': 'E83182683', 'iban': 'REDACTED_IBAN'},
    'MUÑOZ MARTIN': {'cif': 'E83182683', 'iban': 'REDACTED_IBAN'},
    
    # --- CERES ---
    'CERES': {'cif': 'B83478669', 'iban': ''},
    'CERES CERVEZA': {'cif': 'B83478669', 'iban': ''},
    
    # --- BERZAL ---
    'BERZAL': {'cif': 'A78490182', 'iban': 'REDACTED_IBAN'},
    'BERZAL HERMANOS': {'cif': 'A78490182', 'iban': 'REDACTED_IBAN'},
    
    # --- BM SUPERMERCADOS ---
    'BM': {'cif': 'B20099586', 'iban': ''},
    'BM SUPERMERCADOS': {'cif': 'B20099586', 'iban': ''},
    
    # --- LIDL ---
    'LIDL': {'cif': 'A60195278', 'iban': ''},
    
    # --- PC COMPONENTES ---
    'PC COMPONENTES': {'cif': 'B73347494', 'iban': ''},
    
    # --- LICORES MADRUEÑO ---
    'LICORES MADRUEÑO': {'cif': 'B86705126', 'iban': 'REDACTED_IBAN'},
    'MADRUEÑO': {'cif': 'B86705126', 'iban': 'REDACTED_IBAN'},
}


# =============================================================================
# DICCIONARIO INVERSO CIF → PROVEEDOR
# =============================================================================

CIF_A_PROVEEDOR = {
    'B83478669': 'CERES',
    'B87214755': 'SERRIN',
    'B79992079': 'FABEIRO',
    'F88424072': 'DISTRIBUCIONES LAVAPIES',
    'REDACTED_DNI': 'BENJAMIN ORTEGA',
    'REDACTED_DNI': 'JAIME FERNANDEZ',
    'B96771832': 'SABORES DE PATERNA',
    'REDACTED_DNI': 'MARTIN ABENZA',
    'REDACTED_DNI': 'FRANCISCO GUERRA',
    'REDACTED_DNI': 'TRUCCO',
    'A50090133': 'ISTA',
    'W0184081H': 'AMAZON',
    'B24416869': 'VINOS DE ARGANZA',
    'F30005193': 'LA PURISIMA',
    'B93662708': 'MOLLETES ARTESANOS',
    'B45851755': 'BORBOTON',
    'B83594150': 'LOS GREDALES',
    'REDACTED_DNI': 'GADITAUN',
    'B72738602': 'ECOMS',
    'B72113897': 'FELISA',
    'B67784231': 'JAMONES BERNAL',
    'B37352077': 'EMJAMESA',
    'A28647451': 'MAKRO',
    'B42861948': 'ZUCCA',
    'A48002893': 'CVNE',
    'A82528548': 'YOIGO',
    'F55091367': 'SOM ENERGIA',
    'B98670003': 'LUCERA',
    'A48198626': 'SEGURMA',
    'F84600022': 'KINEMA',
    'B79868006': 'MIGUEZ CAL',
    'REDACTED_DNI': 'MARITA COSTA',
    'REDACTED_DNI': 'PILAR RODRIGUEZ',
    'B87874327': 'PANIFIESTO',
    'REDACTED_DNI': 'JULIO GARCIA VIVAS',
    'A80280845': 'MRM',
    'B46144424': 'DISBER',
    'B19981141': 'LA BARRA DULCE',
    'B16690141': 'GRUPO CAMPERO',
    'B75079608': 'ZUBELZU',
    'B12711636': 'PRODUCTOS ADELL',
    'B10214021': 'ECOFICUS',
    'E06388631': 'QUESOS ROYCA',
    'F20532297': 'IBARRAKO PIPARRAK',
    'B87925970': 'ANA CABALLO',
    'B47440136': 'QUESOS FELIX',
    'B13858014': 'PANRUJE',
    'B37416419': 'CARLOS NAVAS',
    'B36281087': 'PORVAZ',
    'REDACTED_DNI': 'CONTROLPLAGA',
    'REDACTED_DNI': 'ANGEL Y LOLI',
    'F12499455': 'QUESOS DEL CATI',
    '06089700725': 'BIELLEBI',
    'B57955098': 'FERRIOL',
    'B82567876': 'ABBATI CAFE',
    'E83182683': 'BODEGAS MUÑOZ MARTIN',
    'A78490182': 'BERZAL',
    'B20099586': 'BM SUPERMERCADOS',
    'A60195278': 'LIDL',
    'B73347494': 'PC COMPONENTES',
    'B06936140': 'LA MOLIENDA VERDE',
    'B84527068': 'JIMELUZ',
    'B73814949': 'LA ROSQUILLERIA',
    'B30473326': 'MANIPULADOS ABELLAN',
    'B09861535': 'SILVA CORDERO',
    'REDACTED_DNI': 'EL CARRASCAL',
    'B86705126': 'LICORES MADRUEÑO',
}


# =============================================================================
# MÉTODO DE EXTRACCIÓN PDF POR PROVEEDOR
# =============================================================================

EXTRACTOR_PDF_PROVEEDOR = {
    # Proveedores que funcionan mejor con pdfplumber
    'CERES': 'pdfplumber',
    'BODEGAS BORBOTON': 'pdfplumber',
    'BORBOTON': 'pdfplumber',
    'FELISA GOURMET': 'pdfplumber',
    'FELISA': 'pdfplumber',
    'DISTRIBUCIONES LAVAPIES': 'pdfplumber',
    'LAVAPIES': 'pdfplumber',
    'LIDL': 'pdfplumber',
    'BODEGAS MUÑOZ MARTIN': 'pdfplumber',
    'MUÑOZ MARTIN': 'pdfplumber',
    'EMJAMESA': 'pdfplumber',
    'MOLIENDA VERDE': 'pdfplumber',
    'LA MOLIENDA VERDE': 'pdfplumber',
    'ZUBELZU': 'pdfplumber',
    'IBARRAKO PIPARRAK': 'pdfplumber',
    'IBARRAKO PIPARRA': 'pdfplumber',
    'IBARRAKO': 'pdfplumber',
    
    # Proveedores OCR (PDFs escaneados)
    'JIMELUZ': 'ocr',
    'LA ROSQUILLERIA': 'ocr',
    'ROSQUILLERIA': 'ocr',
    'MANIPULADOS ABELLAN': 'ocr',
    'FISHGOURMET': 'ocr',
    'MARIA LINAREJOS': 'ocr',
}


def obtener_datos_proveedor(nombre: str) -> dict:
    """
    Obtiene CIF e IBAN de un proveedor.
    
    Args:
        nombre: Nombre del proveedor
        
    Returns:
        {'cif': '...', 'iban': '...'} o {'cif': '', 'iban': ''} si no existe
    """
    nombre_upper = nombre.upper()
    
    # Buscar coincidencia exacta
    if nombre_upper in PROVEEDORES_CONOCIDOS:
        return PROVEEDORES_CONOCIDOS[nombre_upper]
    
    # Buscar coincidencia parcial
    for clave, datos in PROVEEDORES_CONOCIDOS.items():
        if clave in nombre_upper or nombre_upper in clave:
            return datos
    
    return {'cif': '', 'iban': ''}


def obtener_proveedor_por_cif(cif: str) -> str:
    """
    Obtiene el nombre del proveedor a partir de su CIF.
    
    Args:
        cif: CIF del proveedor
        
    Returns:
        Nombre del proveedor o cadena vacía si no existe
    """
    # Limpiar CIF
    cif_limpio = cif.replace('-', '').replace(' ', '').upper()
    
    return CIF_A_PROVEEDOR.get(cif_limpio, '')


def obtener_metodo_pdf(proveedor: str) -> str:
    """
    Obtiene el método de extracción PDF para un proveedor.
    
    Args:
        proveedor: Nombre del proveedor
        
    Returns:
        'pypdf', 'pdfplumber' u 'ocr'
    """
    proveedor_upper = proveedor.upper()
    
    return EXTRACTOR_PDF_PROVEEDOR.get(proveedor_upper, 'pypdf')

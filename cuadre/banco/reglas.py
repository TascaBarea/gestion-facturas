"""
cuadre/banco/reglas.py — Reglas de clasificación como datos.
Centraliza constantes, patrones y tablas de lookup usados por cuadre.py.
"""

# ── Comercios TPV (código → nombre) ─────────────────────────────────────────
COMERCIOS_TPV = {
    "0337410674": "TASCA",
    "0354768939": "COMESTIBLES",
    "0354272759": "TALLERES",
}

# ── Reglas especiales compra tarjeta ─────────────────────────────────────────
REGLAS_ESPECIALES_TARJETA = [
    {"clave": "PANIFIESTO LAVAPIES", "titulo": "PANIFIESTO LAVAPIES SL"},
    {"clave": "AY MADRE LA FRUTA", "titulo": "GARCIA VIVAS JULIO"},
]

# ── Suscripciones sin factura ────────────────────────────────────────────────
SUSCRIPCIONES_SIN_FACTURA = [
    {"clave": "LOYVERSE", "tipo": "LOYVERSE", "detalle": "Sin factura"},
    {"clave": "SPOTIFY", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
    {"clave": "NETFLIX", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
    {"clave": "AMAZON PRIME", "tipo": "GASTOS VARIOS", "detalle": "Sin factura"},
]

# ── Suscripciones CON factura ────────────────────────────────────────────────
SUSCRIPCIONES_CON_FACTURA = [
    {"clave": "MAKE.COM", "titulo": "CELONIS INC.", "aliases": ["CELONIS", "MAKE", "ONE WORLD TRADE"]},
    {"clave": "OPENAI", "titulo": "OPENAI LLC", "aliases": ["OPENAI", "CHATGPT"]},
]

# ── Umbrales fuzzy ───────────────────────────────────────────────────────────
UMBRAL_FUZZY_MINIMO = 0.70
UMBRAL_FUZZY_INDICAR = 0.85

# ── Casos simples (concepto → (tipo, detalle)) ──────────────────────────────
# Cada regla: (palabras_clave, tipo, detalle)
# Si alguna palabra_clave está en el concepto (upper), se clasifica
CASOS_SIMPLES = [
    (["TRASPASO"], "TRASPASO", ""),
    (["COMISIÓN DIVISA", "COMISION DIVISA"], "COMISION DIVISA", "Pago en moneda no euro"),
    (["IMPUESTO", "TGSS", "AEAT"], "IMPUESTOS", ""),
    (["NÓMINA", "NOMINA"], "NOMINAS", ""),
    (["TRANSFERENCIA A ELENA DE MIGUEL"], "NOMINAS", "Elena de Miguel"),
    (["SERVICIO DE TPV"], "SERVICIO DE TPV", ""),
]

# Regla especial: concepto que empieza con estas palabras
CASOS_SIMPLES_STARTSWITH = [
    ("INGRESO", "INGRESO", ""),
]

# ── Nombres alquiler ─────────────────────────────────────────────────────────
NOMBRES_ALQUILER = [
    "BENJAMIN ORTEGA Y JAIME",
    "ORTEGA ALONSO BENJAMIN",
    "FERNANDEZ MORENO JAIME",
]

# ── Patrones proveedores especiales ──────────────────────────────────────────
PATRONES_COMUNIDAD = ["COM PROP", "COMUNIDAD PROP"]
PATRON_ISTA = "ISTA METERING"
PATRON_SOM_ENERGIA = "SOM ENERGIA"
PATRON_YOIGO = "YOIGO"
PATRON_YOIGO_REGEX = r"Y?(C\d{9,})"
PATRON_SOM_REF = r"(FE?\d{6,})"
PATRON_TPV_REMESA = r"\b\d{10}\b"
PATRON_TPV_COMERCIOS = r"\b(" + "|".join(COMERCIOS_TPV.keys()) + r")\b"

# ── Proveedores con pagos parciales ──────────────────────────────────────────
PROVEEDORES_PAGOS_PARCIALES = ["GARCIA VIVAS", "PANIFIESTO"]

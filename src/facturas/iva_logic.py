# src/facturas/iva_logic.py
from __future__ import annotations
from typing import List, Union

# Devuelve 4/10/21 o "REVISAR".
def detect_iva_tipo(descripcion: str, proveedor: str, fecha_ddmmaa: str) -> Union[int, str]:
    if not descripcion:
        return "REVISAR"

    desc = descripcion.lower()
    prov = (proveedor or "").upper().strip()

    # ---- Reglas por proveedor (mínimas v1) ----
    # FABEIRO: alimentación variada. Default 10; queso 4.
    if prov == "FABEIRO":
        if any(k in desc for k in ("queso", "quesitos", "lacteo", "leche", "lácteo")):
            return 4
        return 10

    # CERES (bebidas): aguas 10; resto 21 (cerveza, vermut, refrescos, etc.)
    if prov == "CERES":
        if any(k in desc for k in ("agua", "sousas", "gas", "sin gas", "con gas")):
            return 10
        return 21

    # SEGURMA: servicios de alarma
    if prov == "SEGURMA":
        if "alarma" in desc or "central receptora" in desc or "mantenimiento" in desc:
            return 21
        return 21

    # Genéricas
    if any(k in desc for k in ("queso", "lacteo", "lácteo", "leche")):
        return 4
    if any(k in desc for k in ("agua", "mineral", "manantial")):
        return 10

    # Por defecto (según tipo consumo): si no sabemos, revisar.
    return "REVISAR"


# Devuelve índices de posibles líneas de portes/transporte para excluirlas o marcarlas
def detect_portes(articulos: List[str]) -> List[int]:
    hits: List[int] = []
    if not articulos:
        return hits

    keys = [
        "porte", "portes", "transporte", "envío", "envio", "gastos de envío",
        "gastos envio", "cargo transporte", "manipulado", "reparto", "flete",
        "cla:", "clà:", "clá:", "logística", "logistica",
    ]
    for i, a in enumerate(articulos):
        s = (a or "").lower()
        if any(k in s for k in keys):
            hits.append(i)
    return hits

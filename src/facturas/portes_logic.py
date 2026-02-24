# src/facturas/portes_logic.py
from __future__ import annotations

from typing import List, Dict, Tuple

# Detección básica por flag o por keywords
_PORTES_KWS = {"PORTE", "PORTES", "TRANSPORTE", "ENVIO", "ENVÍO", "GASTOS TRANSPORTE", "GASTOS ENVIO"}

def _es_portes(row: Dict[str, str]) -> bool:
    # Si ya viene marcado por patterns_loader
    if str(row.get("EsPortes", "")).lower() in {"true", "1"}:
        return True
    desc = (row.get("Descripcion") or "").upper()
    return any(kw in desc for kw in _PORTES_KWS)

def _eu_to_float(s: str) -> float:
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def _float_to_eu(x: float) -> str:
    # Redondeo a céntimo con coma decimal
    x = round(x + 1e-9, 2)
    entero = int(abs(x))
    frac = int(round((abs(x) - entero) * 100))
    sign = "-" if x < 0 else ""
    ent_str = f"{entero:,}".replace(",", ".")
    return f"{sign}{ent_str},{frac:02d}"

def prorratear_portes_en_bruto(rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], float]:
    """
    Busca líneas de PORTES, suma su base y la reparte proporcionalmente entre
    el resto de líneas según su BaseImponible. Devuelve (rows_sin_portes, portes_total).

    - No toca el TipoIVA (se mantiene por línea).
    - Mantiene formato europeo en BaseImponible.
    - Si no hay líneas con base o el total de bases es 0, devuelve tal cual.
    """
    if not rows:
        return rows, 0.0

    # Separar portes de no-portes
    normales: List[Dict[str, str]] = []
    portes_total = 0.0
    for r in rows:
        if _es_portes(r):
            portes_total += _eu_to_float(r.get("BaseImponible", ""))
        else:
            normales.append(dict(r))  # copia superficial

    if portes_total <= 0 or not normales:
        return rows, 0.0

    # Suma de bases de las líneas normales
    bases = [_eu_to_float(r.get("BaseImponible", "")) for r in normales]
    total_bases = sum(bases)

    if total_bases <= 0:
        # No podemos prorratear: devolver sin cambios
        return rows, 0.0

    # Reparto proporcional y ajuste de redondeo al mayor
    asignaciones = [portes_total * (b / total_bases) for b in bases]
    asignaciones_red = [round(x, 2) for x in asignaciones]
    diff = round(portes_total - sum(asignaciones_red), 2)

    # Índice de la línea con mayor base para ajustar céntimos residuales
    idx_max = max(range(len(bases)), key=lambda i: bases[i])

    for i, r in enumerate(normales):
        nueva_base = bases[i] + asignaciones_red[i]
        if i == idx_max:
            nueva_base = round(nueva_base + diff, 2)  # ajuste residual
        r["BaseImponible"] = _float_to_eu(nueva_base)

    return normales, portes_total

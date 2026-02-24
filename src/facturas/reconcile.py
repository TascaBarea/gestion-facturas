from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Optional
import re

TOTAL_HINTS = [
    "total factura", "importe total", "total a pagar", "total:", "importe a pagar"
]
EU_MONEY_RX = re.compile(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b")

def detectar_total_con_iva(lines_text: List[str]) -> Optional[str]:
    for line in lines_text[::-1]:  # buscar desde el final
        if any(k in line.lower() for k in TOTAL_HINTS):
            match = EU_MONEY_RX.search(line)
            if match:
                return match.group(0)
    return None

def reconciliar_totales(bases: List[str], total_con_iva: str, tipo_ivas: List[int]) -> Tuple[List[str], str]:
    def str_to_decimal(eu: str) -> Decimal:
        return Decimal(eu.replace(".", "").replace(",", "."))

    def dec_to_str(d: Decimal) -> str:
        return f"{d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}".replace(".", ",")

    bases_dec = [str_to_decimal(b) for b in bases]
    tipos = tipo_ivas
    if len(bases_dec) != len(tipos):
        return (bases, "DESCUDRE_GRAVE")

    total_teorico = sum(b * (1 + Decimal(t) / 100) for b, t in zip(bases_dec, tipos))
    total_real = str_to_decimal(total_con_iva)
    diferencia = total_real - total_teorico

    if abs(diferencia) <= Decimal("0.02"):
        if abs(diferencia) == 0:
            return (bases, "OK")
        else:
            idx_max = max(range(len(bases_dec)), key=lambda i: bases_dec[i])
            bases_dec[idx_max] += diferencia / (1 + Decimal(tipos[idx_max]) / 100)
            ajustadas = [dec_to_str(b) for b in bases_dec]
            return (ajustadas, "AJUSTADO")

    return (bases, "DESCUDRE_GRAVE")

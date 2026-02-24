# tests/test_parse_lines.py (robustizado)
import pytest
from facturas.parse_lines import parse_lines_text


def _eu(s: str) -> str:
    """Normaliza 10.00 -> 10,00 para comparar en formato europeo."""
    if s is None:
        return ""
    s = str(s).strip()
    return s.replace(".", ",")


def test_parse_lines_basic():
    txt = (
        "MH CLASICA BARRIL 144,00\n"
        "SOUSAS GAS 18,50\n"
        "VERMUT BENDITO 10.00\n"
        "Línea sin importe final"
    )

    rows = parse_lines_text(blocks["lines_text"])


    # Debe parsear al menos 3 líneas de producto
    assert len(rows) >= 3

    # Debe existir una línea que mencione BARRIL en la descripción
    assert any("BARRIL" in (r.get("Descripcion", "").upper()) for r in rows)

    # Las bases esperadas deben aparecer (en formato europeo)
    bases = [_eu(r.get("BaseImponible", "")) for r in rows]
    for esperado in ("144,00", "18,50", "10,00"):
        assert esperado in bases, f"Falta base {esperado} en {bases}"

    # Debe existir al menos una línea sin importe (la de cierre)
    assert "" in bases, "Debe haber una línea sin BaseImponible (vacía)"


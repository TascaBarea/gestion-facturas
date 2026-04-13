"""
Tests para la ventana de gracia trimestral en gmail.py.
Valida la lógica de determinar_destino_factura() que decide
si una factura va como NORMAL, GRACIA, PENDIENTE o ATRASADA.
"""
import pytest
from datetime import datetime

import sys
import importlib.util
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Importar gmail.py directamente (sin pasar por gmail/__init__.py que carga auth.py)
_gmail_path = Path(_ROOT) / "gmail" / "gmail.py"
_spec = importlib.util.spec_from_file_location("gmail_module", _gmail_path)
_gmail_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gmail_mod)

determinar_destino_factura = _gmail_mod.determinar_destino_factura
trimestre_de_fecha = _gmail_mod.trimestre_de_fecha
es_trimestre_inmediatamente_anterior = _gmail_mod.es_trimestre_inmediatamente_anterior


class TestTrimestre:
    """Tests para funciones auxiliares de trimestre."""

    def test_trimestre_enero(self):
        assert trimestre_de_fecha(datetime(2026, 1, 15)) == (1, 2026)

    def test_trimestre_marzo(self):
        assert trimestre_de_fecha(datetime(2026, 3, 31)) == (1, 2026)

    def test_trimestre_abril(self):
        assert trimestre_de_fecha(datetime(2026, 4, 1)) == (2, 2026)

    def test_trimestre_diciembre(self):
        assert trimestre_de_fecha(datetime(2025, 12, 31)) == (4, 2025)


class TestTrimAnterior:
    """Tests para es_trimestre_inmediatamente_anterior."""

    def test_1t_es_anterior_a_2t(self):
        assert es_trimestre_inmediatamente_anterior(1, 2026, 2, 2026) is True

    def test_4t_es_anterior_a_1t_siguiente(self):
        assert es_trimestre_inmediatamente_anterior(4, 2025, 1, 2026) is True

    def test_3t_no_es_anterior_a_1t(self):
        assert es_trimestre_inmediatamente_anterior(3, 2025, 1, 2026) is False

    def test_1t_no_es_anterior_a_3t(self):
        assert es_trimestre_inmediatamente_anterior(1, 2026, 3, 2026) is False


class TestVentanaGracia:
    """Tests para la ventana de gracia trimestral."""

    # --- NORMAL: factura del trimestre actual ---
    def test_factura_trimestre_actual(self):
        assert determinar_destino_factura(datetime(2026, 4, 15), datetime(2026, 4, 20)) == 'NORMAL'

    def test_factura_trimestre_actual_mismo_dia(self):
        assert determinar_destino_factura(datetime(2026, 4, 1), datetime(2026, 4, 1)) == 'NORMAL'

    # --- GRACIA: días 1-11 del primer mes ---
    def test_gracia_dia_1_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 28), datetime(2026, 4, 1)) == 'GRACIA'

    def test_gracia_dia_11_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 31), datetime(2026, 4, 11)) == 'GRACIA'

    def test_gracia_dia_5_enero_4t_anterior(self):
        """1T: gracia para factura de 4T del año anterior."""
        assert determinar_destino_factura(datetime(2025, 12, 20), datetime(2026, 1, 5)) == 'GRACIA'

    def test_gracia_dia_8_julio(self):
        assert determinar_destino_factura(datetime(2026, 6, 25), datetime(2026, 7, 8)) == 'GRACIA'

    def test_gracia_dia_3_octubre(self):
        assert determinar_destino_factura(datetime(2026, 9, 15), datetime(2026, 10, 3)) == 'GRACIA'

    # --- PENDIENTE: días 12-20 del primer mes ---
    def test_pendiente_dia_12_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 28), datetime(2026, 4, 12)) == 'PENDIENTE_UBICACION'

    def test_pendiente_dia_20_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 31), datetime(2026, 4, 20)) == 'PENDIENTE_UBICACION'

    def test_pendiente_dia_15_enero(self):
        assert determinar_destino_factura(datetime(2025, 12, 10), datetime(2026, 1, 15)) == 'PENDIENTE_UBICACION'

    # --- ATRASADA: día 21+ del primer mes ---
    def test_atrasada_dia_21_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 28), datetime(2026, 4, 21)) == 'ATRASADA'

    def test_atrasada_dia_30_abril(self):
        assert determinar_destino_factura(datetime(2026, 3, 15), datetime(2026, 4, 30)) == 'ATRASADA'

    # --- ATRASADA: 2º/3er mes del trimestre ---
    def test_atrasada_mayo_factura_1t(self):
        """Mayo es 2º mes del 2T — sin ventana de gracia."""
        assert determinar_destino_factura(datetime(2026, 3, 28), datetime(2026, 5, 5)) == 'ATRASADA'

    def test_atrasada_junio_factura_1t(self):
        assert determinar_destino_factura(datetime(2026, 3, 28), datetime(2026, 6, 1)) == 'ATRASADA'

    # --- ATRASADA: trimestre NO inmediatamente anterior ---
    def test_atrasada_trimestre_lejano(self):
        """Factura de 3T25 procesada en 2T26 — siempre ATRASADA."""
        assert determinar_destino_factura(datetime(2025, 9, 15), datetime(2026, 4, 5)) == 'ATRASADA'

    def test_atrasada_dos_trimestres_atras(self):
        """Factura de 4T25 procesada en 2T26 — no es inmediatamente anterior."""
        assert determinar_destino_factura(datetime(2025, 12, 20), datetime(2026, 4, 5)) == 'ATRASADA'

    # --- Caso borde: cambio de año ---
    def test_gracia_cambio_ano(self):
        """Factura 4T25 procesada el 3 de enero 2026 — GRACIA."""
        assert determinar_destino_factura(datetime(2025, 12, 31), datetime(2026, 1, 3)) == 'GRACIA'

    def test_pendiente_cambio_ano(self):
        """Factura 4T25 procesada el 15 de enero 2026 — PENDIENTE."""
        assert determinar_destino_factura(datetime(2025, 11, 28), datetime(2026, 1, 15)) == 'PENDIENTE_UBICACION'

    def test_atrasada_cambio_ano_dia_25(self):
        """Factura 4T25 procesada el 25 de enero 2026 — ATRASADA."""
        assert determinar_destino_factura(datetime(2025, 12, 15), datetime(2026, 1, 25)) == 'ATRASADA'

    # --- Caso borde: mismo trimestre, distinto mes ---
    def test_normal_mismo_trimestre_mes_diferente(self):
        """Factura y proceso en mismo trimestre pero distinto mes -> NORMAL."""
        assert determinar_destino_factura(datetime(2026, 4, 5), datetime(2026, 5, 15)) == 'NORMAL'

    # --- Caso borde: sin fecha_proceso ---
    def test_fecha_proceso_none(self):
        """Si fecha_proceso es None, no debe crashear."""
        resultado = determinar_destino_factura(datetime(2026, 4, 1))
        assert resultado in ('NORMAL', 'GRACIA', 'PENDIENTE_UBICACION', 'ATRASADA')

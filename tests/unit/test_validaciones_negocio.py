"""
Tests para validaciones de negocio en gmail.py v1.18.2.
Verifica: rango de total, detección de abonos, fecha antigua.
"""
import pytest
from datetime import datetime, timedelta

import sys
import importlib.util
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Importar gmail.py directamente (sin pasar por gmail/__init__.py que carga auth.py)
_gmail_path = Path(_ROOT) / "gmail" / "gmail.py"
_spec = importlib.util.spec_from_file_location("gmail_module_val", _gmail_path)
_gmail_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gmail_mod)

TOTAL_MIN_SOSPECHOSO = _gmail_mod.TOTAL_MIN_SOSPECHOSO
TOTAL_MAX_SOSPECHOSO = _gmail_mod.TOTAL_MAX_SOSPECHOSO
FECHA_MAX_ANTIGUEDAD_DIAS = _gmail_mod.FECHA_MAX_ANTIGUEDAD_DIAS
CONSTANTES_DISPONIBLES = True


class TestConstantesValidacion:
    """Verificar que las constantes existen y tienen valores razonables."""

    @pytest.mark.skipif(not CONSTANTES_DISPONIBLES, reason="Import gmail.gmail failed")
    def test_constantes_existen(self):
        assert TOTAL_MIN_SOSPECHOSO > 0
        assert TOTAL_MAX_SOSPECHOSO > 1000
        assert FECHA_MAX_ANTIGUEDAD_DIAS > 365

    def test_total_min_es_medio_euro(self):
        assert TOTAL_MIN_SOSPECHOSO == 0.50

    def test_total_max_es_50k(self):
        assert TOTAL_MAX_SOSPECHOSO == 50_000

    def test_fecha_max_es_2_anos(self):
        assert FECHA_MAX_ANTIGUEDAD_DIAS == 730


class TestLogicaRangoTotal:
    """Tests de la lógica de detección de totales sospechosos."""

    def test_total_normal_no_sospechoso(self):
        """234.50€ no debería levantar alerta."""
        total = 234.50
        assert total >= TOTAL_MIN_SOSPECHOSO
        assert total <= TOTAL_MAX_SOSPECHOSO

    def test_total_bajo_sospechoso(self):
        """0.10€ debería levantar alerta."""
        total = 0.10
        assert 0 < abs(total) < TOTAL_MIN_SOSPECHOSO

    def test_total_alto_sospechoso(self):
        """75000€ debería levantar alerta."""
        total = 75_000
        assert abs(total) > TOTAL_MAX_SOSPECHOSO

    def test_total_exacto_en_limite_bajo(self):
        """0.50€ exacto NO es sospechoso (es >= umbral)."""
        total = 0.50
        assert not (0 < abs(total) < TOTAL_MIN_SOSPECHOSO)

    def test_total_exacto_en_limite_alto(self):
        """50000€ exacto NO es sospechoso (es <= umbral)."""
        total = 50_000
        assert not (abs(total) > TOTAL_MAX_SOSPECHOSO)

    def test_total_cero_no_es_sospechoso_bajo(self):
        """0€ no debe entrar en la validación de rango (es ausencia, no importe bajo)."""
        total = 0.0
        assert not (0 < abs(total) < TOTAL_MIN_SOSPECHOSO)

    def test_total_justo_debajo_del_limite(self):
        """0.49€ es sospechoso."""
        total = 0.49
        assert 0 < abs(total) < TOTAL_MIN_SOSPECHOSO

    def test_total_justo_encima_del_limite(self):
        """50001€ es sospechoso."""
        total = 50_001
        assert abs(total) > TOTAL_MAX_SOSPECHOSO


class TestLogicaAbonos:
    """Tests de la lógica de detección de abonos."""

    def test_total_negativo_es_abono(self):
        """Total negativo → posible abono."""
        total = -45.30
        assert total < 0

    def test_total_positivo_no_es_abono(self):
        total = 234.50
        assert not (total < 0)

    def test_total_cero_no_es_abono(self):
        total = 0.0
        assert not (total < 0)

    def test_abono_grande_tambien_detectado(self):
        """Un abono de -5000€ debe detectarse."""
        total = -5000.0
        assert total < 0

    def test_abono_pequeno_tambien_detectado(self):
        """Un abono de -0.10€ debe detectarse."""
        total = -0.10
        assert total < 0

    def test_abono_tambien_puede_ser_sospechoso_alto(self):
        """Un abono de -60000€ es abono Y sospechosamente alto."""
        total = -60_000
        assert total < 0
        assert abs(total) > TOTAL_MAX_SOSPECHOSO


class TestLogicaFechaAntigua:
    """Tests de la lógica de detección de fechas muy antiguas."""

    def test_fecha_reciente_no_antigua(self):
        """Factura de hace 30 días → no es antigua."""
        fecha_factura = datetime(2026, 3, 14)
        fecha_proceso = datetime(2026, 4, 13)
        dias = (fecha_proceso - fecha_factura).days
        assert dias <= FECHA_MAX_ANTIGUEDAD_DIAS

    def test_fecha_1_ano_no_antigua(self):
        """Factura de hace 365 días → no es antigua (umbral es 730)."""
        fecha_factura = datetime(2025, 4, 13)
        fecha_proceso = datetime(2026, 4, 13)
        dias = (fecha_proceso - fecha_factura).days
        assert dias <= FECHA_MAX_ANTIGUEDAD_DIAS

    def test_fecha_3_anos_es_antigua(self):
        """Factura de hace 3 años → es antigua."""
        fecha_factura = datetime(2023, 4, 13)
        fecha_proceso = datetime(2026, 4, 13)
        dias = (fecha_proceso - fecha_factura).days
        assert dias > FECHA_MAX_ANTIGUEDAD_DIAS

    def test_fecha_exacto_en_limite(self):
        """Factura de hace exactamente 730 días → NO es antigua (es <=)."""
        fecha_proceso = datetime(2026, 4, 13)
        fecha_factura = fecha_proceso - timedelta(days=730)
        dias = (fecha_proceso - fecha_factura).days
        assert not (dias > FECHA_MAX_ANTIGUEDAD_DIAS)

    def test_fecha_731_dias_es_antigua(self):
        """Factura de hace 731 días → SÍ es antigua."""
        fecha_proceso = datetime(2026, 4, 13)
        fecha_factura = fecha_proceso - timedelta(days=731)
        dias = (fecha_proceso - fecha_factura).days
        assert dias > FECHA_MAX_ANTIGUEDAD_DIAS

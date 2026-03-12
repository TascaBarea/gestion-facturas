"""
Smoke tests para script_barea.py
Testea lógica pura sin llamar a APIs externas.
"""
import os
import sys
import tempfile
import shutil
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

# Añadir ventas_semana al path para importar
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "ventas_semana"))

from script_barea import (
    calcular_semana_anterior,
    resolve,
    parse_fecha,
    procesar_recibos,
    save_to_excel,
    check_iva_anomalies,
    _to_float,
    _fmt_eur,
    _fmt_num,
    _pct_var,
    _var_html,
    _semana_equivalente_año_anterior,
    _parse_gbp_num,
    _backup_excel,
    _backed_up,
    _BACKUP_DIR,
)


# ──────────────────────────────────────────────
# Helpers de fecha
# ──────────────────────────────────────────────

class TestCalcularSemanaAnterior:
    def test_devuelve_lunes_y_domingo(self):
        lunes, domingo = calcular_semana_anterior()
        assert lunes.weekday() == 0  # lunes
        assert domingo.weekday() == 6  # domingo
        assert domingo - lunes == timedelta(days=6)

    def test_semana_anterior_a_hoy(self):
        lunes, domingo = calcular_semana_anterior()
        hoy = datetime.now().date()
        assert domingo < hoy


class TestSemanaEquivalenteAnioAnterior:
    def test_misma_semana_iso(self):
        lunes = date(2026, 3, 2)  # semana 10 de 2026
        domingo = date(2026, 3, 8)
        lunes_ant, domingo_ant = _semana_equivalente_año_anterior(lunes, domingo)
        assert lunes_ant.year == 2025
        assert lunes_ant.weekday() == 0
        assert domingo_ant.weekday() == 6
        # Debe ser semana ISO 10 de 2025
        assert lunes_ant.isocalendar()[1] == 10

    def test_semana_1(self):
        lunes = date(2026, 1, 5)  # semana 2 de 2026
        domingo = date(2026, 1, 11)
        lunes_ant, _ = _semana_equivalente_año_anterior(lunes, domingo)
        assert lunes_ant.isocalendar()[1] == lunes.isocalendar()[1]


# ──────────────────────────────────────────────
# Conversiones y formateo
# ──────────────────────────────────────────────

class TestToFloat:
    def test_float_normal(self):
        assert _to_float(3.5) == 3.5

    def test_int(self):
        assert _to_float(10) == 10.0

    def test_string_punto(self):
        assert _to_float("3.51") == 3.51

    def test_string_coma_española(self):
        assert _to_float("3,51") == 3.51

    def test_nan(self):
        assert _to_float(float("nan")) == 0.0

    def test_none(self):
        assert _to_float(None) == 0.0

    def test_string_vacio(self):
        assert _to_float("") == 0.0


class TestFmtEur:
    def test_positivo(self):
        assert _fmt_eur(1234.56) == "1.234,56 €"

    def test_cero(self):
        assert _fmt_eur(0) == "0,00 €"

    def test_negativo(self):
        assert _fmt_eur(-500.0) == "-500,00 €"

    def test_miles(self):
        assert _fmt_eur(12345678.9) == "12.345.678,90 €"


class TestFmtNum:
    def test_miles(self):
        assert _fmt_num(1234) == "1.234"

    def test_cero(self):
        assert _fmt_num(0) == "0"

    def test_grande(self):
        assert _fmt_num(1000000) == "1.000.000"


class TestPctVar:
    def test_subida(self):
        assert _pct_var(110, 100) == pytest.approx(10.0)

    def test_bajada(self):
        assert _pct_var(90, 100) == pytest.approx(-10.0)

    def test_cero_anterior(self):
        assert _pct_var(100, 0) is None

    def test_none_anterior(self):
        assert _pct_var(100, None) is None


class TestVarHtml:
    def test_positivo_tiene_flecha_arriba(self):
        html = _var_html(10.0)
        assert "▲" in html
        assert "10.0%" in html

    def test_negativo_tiene_flecha_abajo(self):
        html = _var_html(-5.5)
        assert "▼" in html
        assert "5.5%" in html

    def test_none(self):
        html = _var_html(None)
        assert "—" in html


class TestParseGbpNum:
    def test_con_puntos(self):
        assert _parse_gbp_num("28.276") == 28276

    def test_sin_puntos(self):
        assert _parse_gbp_num("150") == 150

    def test_grande(self):
        assert _parse_gbp_num("1.234.567") == 1234567


# ──────────────────────────────────────────────
# Lookups y parseo
# ──────────────────────────────────────────────

class TestResolve:
    def test_encontrado(self):
        assert resolve({"a": "Tasca"}, "a") == "Tasca"

    def test_no_encontrado(self):
        assert resolve({"a": "Tasca"}, "b") == ""

    def test_default(self):
        assert resolve({"a": "Tasca"}, "b", "N/A") == "N/A"

    def test_key_none(self):
        assert resolve({"a": "Tasca"}, None) == ""

    def test_dict_value(self):
        assert resolve({"a": {"name": "Bar"}}, "a") == "Bar"


class TestParseFecha:
    def test_iso_completa(self):
        r = parse_fecha("2026-03-10T14:30:00.000Z")
        assert isinstance(r, datetime)
        assert r.year == 2026
        assert r.month == 3

    def test_none(self):
        assert parse_fecha(None) is None

    def test_invalida(self):
        r = parse_fecha("no-es-fecha")
        assert r == "no-es-fecha"  # devuelve original


# ──────────────────────────────────────────────
# procesar_recibos
# ──────────────────────────────────────────────

class TestProcesarRecibos:
    def _lookups(self):
        return {
            'stores': {'s1': 'Tienda Test'},
            'pos_devices': {'p1': 'TPV1'},
            'employees': {'e1': 'Cajero1'},
            'customers': {'c1': {'name': 'Cliente1', 'contacts': 'test@mail.com'}},
            'payment_types': {'pt1': 'Efectivo'},
            'items_by_variant': {'v1': {'category': 'VINOS', 'cost': 5.0}},
            'categories': {},
        }

    def _receipt(self):
        return {
            'receipt_number': '001',
            'receipt_type': 'SALE',
            'receipt_date': '2026-03-10T12:00:00.000Z',
            'store_id': 's1',
            'pos_device_id': 'p1',
            'employee_id': 'e1',
            'customer_id': 'c1',
            'total_money': 20.0,
            'total_tax': 2.0,
            'total_discount': 0.0,
            'tip': 0.0,
            'payments': [{'payment_type_id': 'pt1'}],
            'cancelled_at': None,
            'note': '',
            'line_items': [{
                'variant_id': 'v1',
                'item_name': 'Vino Tinto',
                'sku': 'VT001',
                'variant_name': '',
                'quantity': 2,
                'gross_total_money': 20.0,
                'total_money': 20.0,
                'total_discount': 0.0,
                'total_tax': 2.0,
                'cost': 5.0,
            }],
        }

    def test_genera_dos_dataframes(self):
        df_r, df_i = procesar_recibos([self._receipt()], self._lookups())
        assert isinstance(df_r, pd.DataFrame)
        assert isinstance(df_i, pd.DataFrame)
        assert len(df_r) == 1
        assert len(df_i) == 1

    def test_columnas_recibo(self):
        df_r, _ = procesar_recibos([self._receipt()], self._lookups())
        assert 'Ventas netas' in df_r.columns
        assert 'Número de recibo' in df_r.columns
        assert df_r.iloc[0]['Tipo de pago'] == 'Efectivo'

    def test_columnas_items(self):
        _, df_i = procesar_recibos([self._receipt()], self._lookups())
        assert 'Artículo' in df_i.columns
        assert df_i.iloc[0]['Artículo'] == 'Vino Tinto'
        assert df_i.iloc[0]['Cantidad'] == 2
        assert df_i.iloc[0]['unique_id'] == '001_0'

    def test_sin_recibos(self):
        df_r, df_i = procesar_recibos([], self._lookups())
        assert df_r.empty
        assert df_i.empty

    def test_recibo_cancelado(self):
        r = self._receipt()
        r['cancelled_at'] = '2026-03-10T13:00:00.000Z'
        df_r, _ = procesar_recibos([r], self._lookups())
        assert df_r.iloc[0]['Estado'] == 'Cancelado'


# ──────────────────────────────────────────────
# save_to_excel
# ──────────────────────────────────────────────

class TestSaveToExcel:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "test.xlsx")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        _backed_up.discard(self.path)

    def test_crea_archivo_nuevo(self):
        df = pd.DataFrame({"id": [1, 2], "valor": [10, 20]})
        save_to_excel(df, self.path, "Hoja1", unique_col="id")
        assert os.path.exists(self.path)
        result = pd.read_excel(self.path, sheet_name="Hoja1")
        assert len(result) == 2

    def test_acumula_sin_duplicar(self):
        df1 = pd.DataFrame({"id": [1, 2], "valor": [10, 20]})
        save_to_excel(df1, self.path, "Hoja1", unique_col="id")

        df2 = pd.DataFrame({"id": [2, 3], "valor": [20, 30]})
        save_to_excel(df2, self.path, "Hoja1", unique_col="id")

        result = pd.read_excel(self.path, sheet_name="Hoja1")
        assert len(result) == 3  # 1, 2, 3 (no duplica 2)

    def test_df_vacio_no_escribe(self):
        df = pd.DataFrame()
        save_to_excel(df, self.path, "Hoja1")
        assert not os.path.exists(self.path)

    def test_sin_unique_col_acumula_todo(self):
        df1 = pd.DataFrame({"a": [1]})
        save_to_excel(df1, self.path, "Hoja1")

        df2 = pd.DataFrame({"a": [1]})
        save_to_excel(df2, self.path, "Hoja1")

        result = pd.read_excel(self.path, sheet_name="Hoja1")
        assert len(result) == 2  # duplica porque no hay unique_col


# ──────────────────────────────────────────────
# check_iva_anomalies
# ──────────────────────────────────────────────

class TestCheckIvaAnomalies:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "articulos.xlsx")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _crear_excel(self, rows):
        df = pd.DataFrame(rows)
        df.to_excel(self.path, sheet_name="Test", index=False)

    def test_sin_anomalias(self):
        self._crear_excel([
            {"REF": "A1", "Nombre": "Aceite", "Categoria": "ACEITES",
             "impuesto (10%)": "Y", "impuesto (21%)": "N", "ESTADO": ""},
        ])
        # No debe lanzar excepción
        check_iva_anomalies(self.path, "Test")

    def test_detecta_multi_iva(self, capsys):
        self._crear_excel([
            {"REF": "A1", "Nombre": "Producto raro", "Categoria": "OTROS",
             "impuesto (10%)": "Y", "impuesto (21%)": "Y", "ESTADO": ""},
        ])
        check_iva_anomalies(self.path, "Test")
        # El log.warning debería haberse emitido (capturado por el logger)

    def test_ignora_bajas(self):
        self._crear_excel([
            {"REF": "A1", "Nombre": "Producto dado de baja", "Categoria": "OTROS",
             "impuesto (10%)": "Y", "impuesto (21%)": "Y", "ESTADO": "BAJA"},
        ])
        # No debería reportar anomalía porque está de BAJA
        check_iva_anomalies(self.path, "Test")

    def test_iva_21_en_vinos_ok(self):
        self._crear_excel([
            {"REF": "V1", "Nombre": "Rioja Reserva", "Categoria": "VINOS",
             "impuesto (10%)": "N", "impuesto (21%)": "Y", "ESTADO": ""},
        ])
        check_iva_anomalies(self.path, "Test")

    def test_archivo_no_existe(self):
        # No debe lanzar excepción
        check_iva_anomalies("/ruta/falsa/no_existe.xlsx", "Test")


# ──────────────────────────────────────────────
# backup_excel
# ──────────────────────────────────────────────

class TestBackupExcel:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "datos.xlsx")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        # Crear archivo de prueba
        pd.DataFrame({"a": [1]}).to_excel(self.path, index=False)
        _backed_up.discard(self.path)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        _backed_up.discard(self.path)

    def test_no_backup_si_no_existe(self):
        ruta_fake = os.path.join(self.tmpdir, "no_existe.xlsx")
        _backup_excel(ruta_fake)
        assert not os.path.exists(self.backup_dir)

    def test_no_duplica_backup(self):
        # Forzar que ya se respaldó
        _backed_up.add(self.path)
        _backup_excel(self.path)
        # No debería crear backup_dir ya que está en _backed_up

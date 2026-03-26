"""
Tests para nucleo/maestro.py y api/maestro.py — gestión de MAESTRO_PROVEEDORES.
"""

import os
import pytest

from nucleo.maestro import (
    Proveedor,
    MaestroProveedores,
    normalizar_nombre_proveedor,
    SUFIJOS_ELIMINAR,
)


# ── normalizar_nombre_proveedor ──────────────────────────────────────────────

@pytest.mark.unit
class TestNormalizarNombre:

    def test_basico(self):
        assert normalizar_nombre_proveedor("Aceites Jaleo") == "ACEITES JALEO"

    def test_acentos(self):
        assert normalizar_nombre_proveedor("José García") == "JOSE GARCIA"

    def test_sufijo_sl(self):
        result = normalizar_nombre_proveedor("Distribuciones Pérez S.L.")
        assert "S.L." not in result
        assert "DISTRIBUCIONES PEREZ" in result

    def test_sufijo_sa(self):
        result = normalizar_nombre_proveedor("Empresa Grande S.A.")
        assert "S.A." not in result

    def test_sufijo_slu(self):
        result = normalizar_nombre_proveedor("Micro S.L.U.")
        assert "S.L.U." not in result

    def test_ampersand(self):
        assert "Y" in normalizar_nombre_proveedor("Fish & Chips")

    def test_parentesis_eliminados(self):
        result = normalizar_nombre_proveedor("Empresa (Madrid)")
        assert "MADRID" not in result
        assert "EMPRESA" in result

    def test_vacio(self):
        assert normalizar_nombre_proveedor("") == ""

    def test_none_guard(self):
        # Si recibe None, debería devolver "" sin explotar
        assert normalizar_nombre_proveedor(None) == ""  # type: ignore

    def test_espacios_multiples(self):
        result = normalizar_nombre_proveedor("  Mucho   Espacio  ")
        assert "  " not in result  # Sin dobles espacios

    def test_apostrofe(self):
        result = normalizar_nombre_proveedor("L'Oliva")
        assert "'" not in result


# ── Proveedor dataclass ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestProveedorDataclass:

    def test_defaults(self):
        p = Proveedor(nombre="TEST")
        assert p.nombre == "TEST"
        assert p.cif == ""
        assert p.alias == []
        assert p.tiene_extractor is False

    def test_con_datos(self):
        p = Proveedor(
            nombre="JALEO", cif="B12345678",
            alias=["ACEITES JALEO", "JALEO ACEITE"],
            tiene_extractor=True, archivo_extractor="aceites_jaleo.py",
        )
        assert len(p.alias) == 2
        assert p.tiene_extractor is True


# ── MaestroProveedores ───────────────────────────────────────────────────────

@pytest.mark.unit
class TestMaestroProveedores:

    def test_carga_proveedores(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert len(m.proveedores) == 2

    def test_proveedor_por_nombre(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert "ACEITES JALEO" in m.proveedores

    def test_buscar_por_email(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_email("info@jaleo.com")
        assert prov is not None
        assert prov.nombre == "ACEITES JALEO"

    def test_buscar_por_email_no_existe(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert m.buscar_por_email("nadie@nowhere.com") is None

    def test_buscar_por_email_con_angulos(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_email("Jaleo <info@jaleo.com>")
        assert prov is not None

    def test_buscar_por_alias_exacto(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_alias("ACEITES JALEO")
        assert prov is not None
        assert prov.nombre == "ACEITES JALEO"

    def test_buscar_por_alias_parcial(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_alias("Factura de JALEO ACEITE para enero")
        assert prov is not None

    def test_buscar_por_alias_no_existe(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert m.buscar_por_alias("PROVEEDOR FANTASMA") is None

    def test_buscar_por_cif(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_cif("B12345678")
        assert prov is not None
        assert prov.nombre == "ACEITES JALEO"

    def test_buscar_por_cif_con_espacios(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.buscar_por_cif("B 1234 5678")
        assert prov is not None

    def test_buscar_por_cif_no_existe(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert m.buscar_por_cif("X99999999") is None

    def test_buscar_fuzzy(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        resultado = m.buscar_fuzzy("ACEITES JALEO", umbral=80)
        assert resultado is not None
        prov, score = resultado
        assert prov.nombre == "ACEITES JALEO"
        assert score >= 80

    def test_buscar_fuzzy_no_match(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert m.buscar_fuzzy("XYZZY NADA QUE VER", umbral=95) is None

    def test_buscar_fuzzy_vacio(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert m.buscar_fuzzy("") is None

    def test_identificar_proveedor_por_email(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.identificar_proveedor("info@jaleo.com", "Jaleo", "Factura")
        assert prov is not None
        assert prov.nombre == "ACEITES JALEO"

    def test_identificar_proveedor_por_alias(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.identificar_proveedor("otro@email.com", "CERES", "Factura cerveza")
        assert prov is not None
        assert prov.nombre == "CERES CERVEZA"

    def test_identificar_proveedor_no_encontrado(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        prov = m.identificar_proveedor("x@x.com", "ZZZZ", "AAAA")
        assert prov is None

    def test_datos_proveedor(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        p = m.proveedores["ACEITES JALEO"]
        assert p.cif == "B12345678"
        assert p.forma_pago == "TF"
        assert p.tiene_extractor is True
        assert p.archivo_extractor == "aceites_jaleo.py"

    def test_indices_email(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert "info@jaleo.com" in m.emails

    def test_indices_cif(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        assert "B12345678" in m.cifs

    def test_indices_alias(self, temp_excel):
        m = MaestroProveedores(temp_excel)
        # El fixture tiene "ACEITES JALEO|JALEO ACEITE" como alias
        assert "ACEITES JALEO" in m.alias or "JALEO ACEITE" in m.alias


# ── api/maestro.py — validar_proveedor ───────────────────────────────────────

@pytest.mark.unit
class TestValidarProveedor:

    def test_valido(self):
        from api.maestro import validar_proveedor
        errores = validar_proveedor({"PROVEEDOR": "TEST", "FORMA_PAGO": "TF"})
        assert errores == []

    def test_forma_pago_invalida(self):
        from api.maestro import validar_proveedor
        errores = validar_proveedor({"FORMA_PAGO": "BITCOIN"})
        assert len(errores) == 1
        assert "FORMA_PAGO" in errores[0]

    def test_forma_pago_vacia_ok(self):
        from api.maestro import validar_proveedor
        errores = validar_proveedor({"FORMA_PAGO": ""})
        assert errores == []

    def test_nuevo_sin_nombre(self):
        from api.maestro import validar_proveedor
        errores = validar_proveedor({}, es_nuevo=True)
        assert any("PROVEEDOR" in e for e in errores)

    def test_nuevo_con_nombre(self):
        from api.maestro import validar_proveedor
        errores = validar_proveedor({"PROVEEDOR": "NUEVO TEST"}, es_nuevo=True)
        assert errores == []

    def test_formas_pago_validas(self):
        from api.maestro import validar_proveedor
        for fp in ["TF", "TJ", "RC", "EF"]:
            errores = validar_proveedor({"FORMA_PAGO": fp})
            assert errores == [], f"FORMA_PAGO '{fp}' debería ser válida"


# ── api/maestro.py — leer + guardar roundtrip ───────────────────────────────

@pytest.mark.unit
class TestLeerGuardarMaestro:

    def test_leer_maestro(self, temp_excel, monkeypatch):
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)

        cabeceras, proveedores = am.leer_maestro()
        assert len(cabeceras) > 0
        assert "PROVEEDOR" in cabeceras
        assert len(proveedores) == 2
        assert proveedores[0]["PROVEEDOR"] == "ACEITES JALEO"

    def test_alias_como_lista(self, temp_excel, monkeypatch):
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)

        _, proveedores = am.leer_maestro()
        alias = proveedores[0]["ALIAS"]
        assert isinstance(alias, list)
        assert len(alias) >= 2

    def test_guardar_y_releer(self, temp_excel, monkeypatch):
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)

        cabeceras, proveedores = am.leer_maestro()
        original_count = len(proveedores)

        # Modificar y guardar
        proveedores[0]["NOTAS"] = "Modificado en test"
        am.guardar_maestro(cabeceras, proveedores)

        # Releer
        _, proveedores2 = am.leer_maestro()
        assert len(proveedores2) == original_count
        assert proveedores2[0]["NOTAS"] == "Modificado en test"

    def test_alias_roundtrip(self, temp_excel, monkeypatch):
        """ALIAS lista → string separado por comas → lista de nuevo."""
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)

        cabeceras, proveedores = am.leer_maestro()
        am.guardar_maestro(cabeceras, proveedores)
        _, proveedores2 = am.leer_maestro()

        assert isinstance(proveedores2[0]["ALIAS"], list)
        assert len(proveedores2[0]["ALIAS"]) >= 2

    def test_leer_maestro_simple(self, temp_excel, monkeypatch):
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)

        proveedores = am.leer_maestro_simple()
        assert len(proveedores) == 2

    def test_backup_maestro(self, temp_excel, temp_dir, monkeypatch):
        import api.maestro as am
        monkeypatch.setattr(am, "MAESTRO_PATH", temp_excel)
        monkeypatch.setattr(am, "BACKUP_DIR", os.path.join(temp_dir, "backups"))

        path = am.backup_maestro()
        assert os.path.exists(path)
        assert "MAESTRO_PROVEEDORES" in path

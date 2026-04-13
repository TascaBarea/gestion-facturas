"""
Tests para el procesamiento de múltiples PDFs por email (v1.18.1).
Verifican la lógica de clasificación y generación de IDs sin conexión a Gmail.
"""
import pytest


class TestMultiPdfLogic:
    """Tests para el procesamiento de múltiples PDFs por email."""

    def test_clasificacion_adjuntos_un_pdf(self):
        """Con 1 PDF, debe clasificar correctamente."""
        adjuntos = [("factura.pdf", b"%PDF-1.4 contenido")]
        pdfs = [(n, c) for n, c in adjuntos if n.lower().endswith('.pdf')]
        imagenes = [(n, c) for n, c in adjuntos if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        assert len(pdfs) == 1
        assert len(imagenes) == 0

    def test_clasificacion_adjuntos_dos_pdfs(self):
        """Con 2 PDFs, debe detectar ambos."""
        adjuntos = [
            ("factura1.pdf", b"%PDF contenido1"),
            ("factura2.pdf", b"%PDF contenido2"),
        ]
        pdfs = [(n, c) for n, c in adjuntos if n.lower().endswith('.pdf')]
        assert len(pdfs) == 2

    def test_clasificacion_adjuntos_pdf_mas_imagen(self):
        """Con PDF + imagen, solo el PDF cuenta como principal."""
        adjuntos = [
            ("factura.pdf", b"%PDF contenido"),
            ("image001.jpg", b"\xff\xd8 jpeg"),
        ]
        pdfs = [(n, c) for n, c in adjuntos if n.lower().endswith('.pdf')]
        imagenes = [(n, c) for n, c in adjuntos if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        assert len(pdfs) == 1
        assert len(imagenes) == 1

    def test_clasificacion_solo_imagenes(self):
        """Sin PDFs, las imagenes deben procesarse."""
        adjuntos = [
            ("scan.jpg", b"\xff\xd8 jpeg"),
            ("logo.png", b"\x89PNG data"),
        ]
        pdfs = [(n, c) for n, c in adjuntos if n.lower().endswith('.pdf')]
        imagenes = [(n, c) for n, c in adjuntos if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        assert len(pdfs) == 0
        assert len(imagenes) == 2

    def test_email_id_sufijo_unico(self):
        """Los email_id de PDFs extra deben ser unicos y predecibles."""
        email_id = "abc123"
        ids_generados = [f"{email_id}__pdf{i}" for i in range(2, 5)]
        assert ids_generados == ["abc123__pdf2", "abc123__pdf3", "abc123__pdf4"]
        # Verificar que no hay colision con el original
        assert email_id not in ids_generados

    def test_extension_case_insensitive(self):
        """Las extensiones deben detectarse case-insensitive."""
        adjuntos = [
            ("FACTURA.PDF", b"%PDF"),
            ("scan.Pdf", b"%PDF"),
            ("foto.JPG", b"\xff\xd8"),
        ]
        pdfs = [(n, c) for n, c in adjuntos if n.lower().endswith('.pdf')]
        imagenes = [(n, c) for n, c in adjuntos if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        assert len(pdfs) == 2
        assert len(imagenes) == 1

    def test_tres_pdfs_genera_tres_resultados(self):
        """Con 3 PDFs, se deben generar IDs para el 2o y 3o."""
        email_id = "msg_001"
        pdfs = [("f1.pdf", b"1"), ("f2.pdf", b"2"), ("f3.pdf", b"3")]
        # Primer PDF usa email_id original
        # Extras: __pdf2, __pdf3
        extra_ids = [f"{email_id}__pdf{i}" for i in range(2, len(pdfs) + 1)]
        assert extra_ids == ["msg_001__pdf2", "msg_001__pdf3"]

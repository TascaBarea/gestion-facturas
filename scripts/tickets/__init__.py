"""
scripts/tickets/ — Módulo unificado de adquisición de tickets de proveedores.

Centraliza la descarga/procesamiento de tickets de compra para gestion-facturas.
Cada proveedor tiene su script específico, todos comparten lógica común via comun.py.

Proveedores:
  - bm.py   : BM Supermercados (semi-manual, app BM+ → PDF → PC)
  - dia.py  : DIA (automático, API + Playwright login)
  - makro.py: Makro (pendiente de implementar)

Uso:
  python -m scripts.tickets.bm --dry-run
  python -m scripts.tickets.dia --list
"""

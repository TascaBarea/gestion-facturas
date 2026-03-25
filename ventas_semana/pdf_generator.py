"""
pdf_generator.py — Funciones de generación de PDF extraídas de generar_dashboard.py.

Contiene toda la lógica de generación de informes PDF (resumen combinado
Tasca+Comestibles y PDF solo Comestibles), incluyendo gráficos matplotlib,
tablas de KPIs, categorías y acumulados YTD.
"""

import os
import tempfile
import shutil
from datetime import datetime
from collections import defaultdict

import pandas as pd

from nucleo.utils import fmt_eur as _fmt_eur, round_safe as _round
from nucleo.utils import MESES as MESES_CORTO, MESES_FULL

# ── Constantes ──────────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)

PATH_LOGO_TASCA = os.path.join(_SCRIPT_DIR, "LOGO Tasca.jpg")
PATH_LOGO_COMES = os.path.join(_SCRIPT_DIR, "LOGO Comestibles .jpg")

YEAR_LIST = ["2025", "2026"]
TASCA_YEAR_LIST = ["2023", "2024", "2025", "2026"]

MESES_PARCIALES = [8]

try:
    from config.datos_sensibles import NETLIFY_URL
except ImportError:
    NETLIFY_URL = ""
GITHUB_PAGES_URL = NETLIFY_URL


# ── Funciones ───────────────────────────────────────────────────────────────

def _setup_pdf_fonts():
    """Registra Calibri y devuelve (font_normal, font_bold)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    paths = {
        "Calibri": "C:/Windows/Fonts/calibri.ttf",
        "CalibriBold": "C:/Windows/Fonts/calibrib.ttf",
    }
    for name, path in paths.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    fn = "Calibri" if os.path.exists(paths["Calibri"]) else "Helvetica"
    fb = "CalibriBold" if os.path.exists(paths["CalibriBold"]) else "Helvetica-Bold"
    return fn, fb


def _generar_graficos_pdf(D, RAW, mes_cerrado, year_actual):
    """Genera 4 PNGs con graficos de linea mejorados."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    tmp_dir = tempfile.mkdtemp(prefix="barea_pdf_")
    fmt_euros = FuncFormatter(lambda x, _: _fmt_eur(x, 0))

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#F8F9FA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.alpha': 0.25,
        'grid.color': '#CCCCCC',
        'font.size': 9,
    })

    tasca_colors = {"2023": "#B4D4E8", "2024": "#7BAFD4",
                    "2025": "#4A8DB8", "2026": "#1F4E79"}
    comes_colors = {"2025": "#82B878", "2026": "#375623"}

    def _plot_segments(ax, xs, vals, color, lw, alpha, zorder, label=None):
        """Dibuja línea por segmentos: sólida normal, discontinua en parciales."""
        labeled = False
        for i in range(1, len(xs)):
            parcial = (xs[i] in MESES_PARCIALES or xs[i-1] in MESES_PARCIALES)
            kw = dict(color=color, linewidth=lw, zorder=zorder)
            if parcial:
                kw.update(linestyle='--', alpha=alpha * 0.4)
            else:
                kw['alpha'] = alpha
            if not labeled and label:
                kw['label'] = label
                labeled = True
            ax.plot([xs[i-1], xs[i]], [vals[i-1], vals[i]], **kw)
        if not labeled and label:
            ax.plot([], [], color=color, linewidth=lw, alpha=alpha, label=label)

    def _plot_markers(ax, xs, vals, color, ms, alpha, zorder):
        """Dibuja marcadores: pequeños y transparentes en meses parciales."""
        for x, v in zip(xs, vals):
            parcial = x in MESES_PARCIALES
            ax.plot(x, v, 'o', color=color,
                    markersize=3 if parcial else ms,
                    alpha=0.3 if parcial else alpha,
                    zorder=zorder + 1)

    def _plot_annotations(ax, xs, vals, color):
        """Anotaciones de valor + 'parcial' en meses parciales."""
        for x, v in zip(xs, vals):
            parcial = x in MESES_PARCIALES
            txt = _fmt_eur(v, 0) + ('*' if parcial else '')
            ax.annotate(txt, (x, v),
                        textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=7, color=color,
                        fontweight="bold")
            if parcial:
                ax.annotate('parcial', (x, v),
                            textcoords="offset points", xytext=(0, -12),
                            ha="center", fontsize=6, color="#999",
                            fontstyle="italic")

    def _ax_base(ax, title, fmt):
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12,
                     color="#1a1a1a")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES_CORTO, fontsize=8)
        ax.yaxis.set_major_formatter(fmt)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.9,
                  edgecolor="#DDD")
        ax.set_xlim(0.5, 12.5)
        ax.grid(True, axis="y", alpha=0.25)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color("#CCCCCC")

    def _plot_modern(ax, data_dict, year_list, yr_colors, title, current_yr):
        for yr in year_list:
            if yr not in data_dict:
                continue
            mensual = data_dict[yr]["mensual"]
            xs, vals = [], []
            for m in range(1, 13):
                e = mensual.get(str(m), {}).get("euros", 0)
                if e and e > 0:
                    xs.append(m)
                    vals.append(e)
            if not vals:
                continue
            color = yr_colors.get(yr, "#999")
            is_cur = (yr == current_yr)
            lw = 2.5 if is_cur else 1.5
            ms = 6 if is_cur else 3
            a = 1.0 if is_cur else 0.45
            z = 3 if is_cur else 2

            _plot_segments(ax, xs, vals, color, lw, a, z, label=yr)
            _plot_markers(ax, xs, vals, color, ms, a, z)
            if is_cur:
                ax.fill_between(xs, vals, alpha=0.07, color=color)
                _plot_annotations(ax, xs, vals, color)
        _ax_base(ax, title, fmt_euros)

    # Grafico 1: Tasca
    fig1, ax1 = plt.subplots(figsize=(9, 3.8))
    _plot_modern(ax1, RAW, TASCA_YEAR_LIST, tasca_colors,
                 "Tasca Barea — Facturación mensual", year_actual)
    fig1.tight_layout(pad=1.5)
    path1 = os.path.join(tmp_dir, "chart_tasca.png")
    fig1.savefig(path1, dpi=180, bbox_inches="tight")
    plt.close(fig1)

    # Grafico 2: Comestibles
    fig2, ax2 = plt.subplots(figsize=(9, 3.8))
    _plot_modern(ax2, D, YEAR_LIST, comes_colors,
                 "Comestibles Barea — Facturación mensual", year_actual)
    fig2.tight_layout(pad=1.5)
    path2 = os.path.join(tmp_dir, "chart_comes.png")
    fig2.savefig(path2, dpi=180, bbox_inches="tight")
    plt.close(fig2)

    # Grafico 3: Comparativa
    fig3, ax3 = plt.subplots(figsize=(9, 3.8))
    yr = year_actual
    for lbl, data, color, mkr, off_y in [
        (f"Tasca {yr}", RAW, "#1F4E79", "o", 10),
        (f"Comestibles {yr}", D, "#375623", "s", -14),
    ]:
        mensual = data.get(yr, {}).get("mensual", {})
        xs, vs = [], []
        for m in range(1, 13):
            e = mensual.get(str(m), {}).get("euros", 0)
            if e and e > 0:
                xs.append(m)
                vs.append(e)
        if vs:
            _plot_segments(ax3, xs, vs, color, 2.5, 1.0, 3, label=lbl)
            _plot_markers(ax3, xs, vs, color, 6, 1.0, 3)
            ax3.fill_between(xs, vs, alpha=0.07, color=color)
            for x, v in zip(xs, vs):
                parcial = x in MESES_PARCIALES
                txt = _fmt_eur(v, 0) + ('*' if parcial else '')
                ax3.annotate(txt, (x, v),
                             textcoords="offset points", xytext=(0, off_y),
                             ha="center", fontsize=7, color=color,
                             fontweight="bold")
    _ax_base(ax3, f"Comparativa Tasca vs Comestibles — {yr}", fmt_euros)
    fig3.tight_layout(pad=1.5)
    path3 = os.path.join(tmp_dir, "chart_conjunto.png")
    fig3.savefig(path3, dpi=180, bbox_inches="tight")
    plt.close(fig3)

    # Grafico 4: Evolución conjunta continua (Tasca+Comes)
    # Excluir meses parciales (agosto) — conectar Jul→Sep con discontinua
    timeline_raw = []
    for y in sorted(set(YEAR_LIST) | set(TASCA_YEAR_LIST)):
        for m in range(1, 13):
            t_e = (RAW.get(y, {}).get("mensual", {})
                   .get(str(m), {}).get("euros", 0) or 0)
            c_e = (D.get(y, {}).get("mensual", {})
                   .get(str(m), {}).get("euros", 0) or 0)
            total = t_e + c_e
            if total > 0:
                timeline_raw.append((y, m, total))

    # Separar puntos normales y parciales (para trazar saltos)
    timeline = [(y, m, v) for y, m, v in timeline_raw
                if m not in MESES_PARCIALES]
    parciales_set = {(y, m) for y, m, _ in timeline_raw
                     if m in MESES_PARCIALES}

    fig4, ax4 = plt.subplots(figsize=(9, 3.5))
    if timeline:
        xs4 = list(range(len(timeline)))
        vals4 = [t[2] for t in timeline]
        months4 = [t[1] for t in timeline]
        years4 = [t[0] for t in timeline]

        color4 = "#CC0000"

        # Detectar saltos por mes parcial entre puntos consecutivos
        def _hay_parcial_entre(i):
            """True si entre punto i-1 e i se saltó un mes parcial."""
            y0, m0 = years4[i-1], months4[i-1]
            y1, m1 = years4[i], months4[i]
            # Comprobar si algún mes intermedio era parcial
            ym0 = int(y0) * 12 + m0
            ym1 = int(y1) * 12 + m1
            for ym in range(ym0 + 1, ym1):
                yy, mm = divmod(ym - 1, 12)
                mm += 1
                if (str(yy), mm) in parciales_set:
                    return True
            return False

        # Segmentos: sólido normal, discontinuo donde se saltó parcial
        for i in range(1, len(xs4)):
            salto = _hay_parcial_entre(i)
            kw = dict(color=color4, linewidth=2.5, zorder=3)
            if salto:
                kw.update(linestyle='--', alpha=0.3, linewidth=1.5)
            ax4.plot([xs4[i-1], xs4[i]], [vals4[i-1], vals4[i]], **kw)

        # Marcadores
        ax4.plot(xs4, vals4, 'o', color=color4, markersize=3.5,
                 zorder=4, alpha=0.85)

        # Media móvil 3 meses (línea de tendencia suave)
        if len(vals4) >= 3:
            ma = []
            for i in range(len(vals4)):
                if i < 2:
                    ma.append(None)
                else:
                    ma.append(sum(vals4[i-2:i+1]) / 3)
            xs_ma = [x for x, v in zip(xs4, ma) if v is not None]
            vs_ma = [v for v in ma if v is not None]
            ax4.plot(xs_ma, vs_ma, color=color4, linewidth=1.2,
                     alpha=0.25, zorder=2, linestyle='-')

        # Anotaciones: max, min, primero, último — con anti-solapamiento
        idx_max = max(range(len(vals4)), key=lambda i: vals4[i])
        idx_min = min(range(len(vals4)), key=lambda i: vals4[i])
        idx_first = 0
        idx_last = len(vals4) - 1
        anotar = {}
        for idx in [idx_first, idx_last, idx_min, idx_max]:
            anotar[idx] = vals4[idx]

        # Anti-solapamiento: si dos puntos están a ≤2 posiciones, alternar arriba/abajo
        anotar_sorted = sorted(anotar.keys())
        offsets = {}
        for j, idx in enumerate(anotar_sorted):
            arriba = True
            for prev_idx in anotar_sorted[:j]:
                if abs(idx - prev_idx) <= 2:
                    arriba = offsets.get(prev_idx, True) is False
            offsets[idx] = arriba

        for idx in anotar:
            v = vals4[idx]
            oy = 11 if offsets[idx] else -13
            ax4.annotate(_fmt_eur(v, 0), (xs4[idx], v),
                         textcoords="offset points",
                         xytext=(0, oy),
                         ha="center", fontsize=6.5, color="#333",
                         fontweight="bold")

        # Eje X: etiqueta cada trimestre (Ene, Abr, Jul, Oct)
        tick_pos = []
        tick_lbl = []
        for i, (y, m) in enumerate(zip(years4, months4)):
            if m in (1, 4, 7, 10):
                tick_pos.append(xs4[i])
                tick_lbl.append(f"{MESES_CORTO[m-1]} {y[2:]}")
        ax4.set_xticks(tick_pos)
        ax4.set_xticklabels(tick_lbl, fontsize=7.5, color="#555")

        # Bandas alternas de fondo por año (sutil)
        año_actual = None
        band_start = 0
        colores_band = ["#F8F8F8", "#FFFFFF"]
        band_idx = 0
        for i in range(len(years4)):
            if years4[i] != año_actual:
                if año_actual is not None:
                    ax4.axvspan(band_start - 0.5, xs4[i] - 0.5,
                                color=colores_band[band_idx % 2],
                                alpha=0.6, zorder=0)
                    band_idx += 1
                año_actual = years4[i]
                band_start = xs4[i]
        # Última banda
        ax4.axvspan(band_start - 0.5, xs4[-1] + 0.5,
                    color=colores_band[band_idx % 2],
                    alpha=0.6, zorder=0)

        # Eje Y: rango 15K–50K
        ax4.set_ylim(15000, 50000)
        ax4.yaxis.set_major_formatter(fmt_euros)
        ax4.yaxis.set_major_locator(plt.MultipleLocator(5000))
        ax4.tick_params(axis="y", labelsize=7.5, colors="#555")

    ax4.set_title("Evolución facturación total — Tasca + Comestibles",
                  fontsize=11, fontweight="bold", pad=10, color="#1a1a1a")
    ax4.grid(True, axis="y", alpha=0.2, linewidth=0.5)
    for spine in ax4.spines.values():
        spine.set_visible(False)
    ax4.tick_params(axis="both", length=0)
    fig4.tight_layout(pad=1.2)
    path4 = os.path.join(tmp_dir, "chart_total.png")
    fig4.savefig(path4, dpi=180, bbox_inches="tight")
    plt.close(fig4)

    plt.rcParams.update(plt.rcParamsDefault)
    return path1, path2, path3, path4, tmp_dir


def _calcular_dia_fuerte(items_por_año, year, mes):
    """Devuelve (dia_nombre, media_diaria) del dia con mas ventas."""
    df_items = items_por_año.get(year)
    if df_items is None or df_items.empty:
        return "-", 0

    df = df_items.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Estado" in df.columns:
        df = df[df["Estado"] != "Cancelado"]
    if "Tipo de recibo" in df.columns:
        df = df[df["Tipo de recibo"] == "Venta"]
    df = df[df["Fecha"].dt.month == mes]
    if df.empty:
        return "-", 0

    df["dia_semana"] = df["Fecha"].dt.dayofweek
    ventas_dia = df.groupby("dia_semana")["Ventas netas"].sum()
    if ventas_dia.empty:
        return "-", 0

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
            "Sábado", "Domingo"]
    mejor = ventas_dia.idxmax()
    n_dias = df[df["dia_semana"] == mejor]["Fecha"].dt.date.nunique()
    media = ventas_dia[mejor] / n_dias if n_dias > 0 else 0
    return dias[int(mejor)], round(media, 2)


def _top3_productos(pbm_data, mes, pbm_data_prev_year=None):
    """Devuelve top 3 productos con euros, cant y variación vs mes anterior."""
    mes_data = pbm_data.get(str(mes), {})
    all_prods = []
    for cat_prods in mes_data.values():
        all_prods.extend(cat_prods)
    all_prods.sort(key=lambda x: x.get("euros", 0), reverse=True)
    top3 = all_prods[:3]

    # Datos del mes anterior para comparar
    if mes > 1:
        ant_data = pbm_data.get(str(mes - 1), {})
    elif pbm_data_prev_year:
        ant_data = pbm_data_prev_year.get("12", {})
    else:
        ant_data = {}
    ant_prods = {}
    for cat_prods in ant_data.values():
        for p in cat_prods:
            ant_prods[p["art"]] = p

    result = []
    for p in top3:
        euros_ant = ant_prods.get(p["art"], {}).get("euros", 0)
        var_pct = ((p["euros"] - euros_ant) / euros_ant * 100
                   if euros_ant > 0 else None)
        result.append({
            "art": p["art"], "euros": p["euros"],
            "cant": p["cant"], "var_pct": var_pct,
        })
    return result


def _var_html(euros, euros_ref):
    """Genera HTML de variación porcentual con flecha y color."""
    if euros_ref > 0:
        pct = (euros - euros_ref) / euros_ref * 100
        color = "#2E7D32" if pct >= 0 else "#C62828"
        arrow = "▲" if pct >= 0 else "▼"
        return f'<font color="{color}"><b>{arrow} {pct:+.1f}%</b></font>'
    return '<font color="#999">—</font>'


def _kpi_card(nombre, data_dict, year, mes, pbm_data, items_dict,
              color_accent, color_bg, font_name, font_bold,
              pbm_data_prev_year=None):
    """Genera tabla-card de KPIs para un negocio."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    d_mes = data_dict.get(year, {}).get("mensual", {}).get(str(mes), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    # vs año anterior
    year_ant = str(int(year) - 1)
    euros_ant_year = (data_dict.get(year_ant, {}).get("mensual", {})
                      .get(str(mes), {}).get("euros", 0))

    # vs mes anterior
    if mes > 1:
        euros_ant_mes = (data_dict.get(year, {}).get("mensual", {})
                         .get(str(mes - 1), {}).get("euros", 0))
    else:
        euros_ant_mes = (data_dict.get(year_ant, {}).get("mensual", {})
                         .get("12", {}).get("euros", 0))

    top3 = _top3_productos(pbm_data, mes, pbm_data_prev_year)
    dia, dia_media = _calcular_dia_fuerte(items_dict, year, mes)

    uid = nombre.replace(" ", "_")
    s_hdr = ParagraphStyle(f"kc_h_{uid}", fontName=font_bold, fontSize=11,
                           textColor=white, leading=14)
    s_big = ParagraphStyle(f"kc_b_{uid}", fontName=font_bold, fontSize=24,
                           textColor=HexColor("#1a1a1a"), leading=28)
    s_var = ParagraphStyle(f"kc_v_{uid}", fontName=font_name, fontSize=9,
                           textColor=HexColor("#555"), leading=12)
    s_det = ParagraphStyle(f"kc_d_{uid}", fontName=font_name, fontSize=9,
                           textColor=HexColor("#444"), leading=13)

    card_w = 82 * mm
    rows = [
        [Paragraph(nombre, s_hdr)],
        [Paragraph(_fmt_eur(euros, 0), s_big)],
        [Paragraph(f"vs año ant.: {_var_html(euros, euros_ant_year)}", s_var)],
        [Paragraph(f"vs mes ant.: {_var_html(euros, euros_ant_mes)}", s_var)],
        [Paragraph(f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
                   f"<b>{_fmt_eur(prom)}</b> ticket medio", s_det)],
        [Paragraph(f"Día fuerte: <b>{dia}</b> &nbsp;·&nbsp; "
                   f"media {_fmt_eur(dia_media)}", s_det)],
    ]
    if top3:
        lines = []
        for p in top3:
            if p["var_pct"] is not None:
                vc = "#2E7D32" if p["var_pct"] >= 0 else "#C62828"
                va = "▲" if p["var_pct"] >= 0 else "▼"
                vs = f' <font color="{vc}"><b>{va}{abs(p["var_pct"]):.0f}%</b></font>'
            else:
                vs = ' <font color="#999">nuevo</font>'
            lines.append(
                f'&nbsp;&nbsp;· {p["art"]}<br/>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;{p["cant"]:.0f} uds · '
                f'{_fmt_eur(p["euros"])}{vs}')
        rows.append([Paragraph(
            f"Top productos:<br/>{'<br/>'.join(lines)}", s_det)])

    t = Table(rows, colWidths=[card_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), HexColor(color_accent)),
        ("BACKGROUND", (0, 1), (0, -1), HexColor(color_bg)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (0, 1), 8),
        ("BOTTOMPADDING", (0, 2), (0, 3), 1),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(color_accent)),
        ("LINEBELOW", (0, 0), (0, 0), 1, HexColor(color_accent)),
    ]))
    return t


def _tabla_categorias_pdf(data_dict, year, mes, mes_nombre, color_header,
                          font_name, font_bold, color_odd_row="#F7F8FA"):
    """Genera tabla de categorias con filas alternadas."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import Table, TableStyle

    if "categorias_mes" in data_dict.get(year, {}):
        cats_mes = data_dict[year]["categorias_mes"].get(str(mes), {})
    else:
        cats_mes = data_dict.get(year, {}).get("mensual", {}).get(
            str(mes), {}).get("cats", {})
    euros_mes = data_dict.get(year, {}).get("mensual", {}).get(
        str(mes), {}).get("euros", 0)

    cats_ytd = defaultdict(float)
    total_ytd = 0
    for m in range(1, mes + 1):
        m_euros = data_dict.get(year, {}).get("mensual", {}).get(
            str(m), {}).get("euros", 0)
        total_ytd += m_euros
        if "categorias_mes" in data_dict.get(year, {}):
            cm = data_dict[year]["categorias_mes"].get(str(m), {})
        else:
            cm = data_dict.get(year, {}).get("mensual", {}).get(
                str(m), {}).get("cats", {})
        for cat, pct in cm.items():
            cats_ytd[cat] += pct / 100 * m_euros

    all_cats = sorted(set(list(cats_mes.keys()) + list(cats_ytd.keys())))
    rows = [["Categoría", mes_nombre, "% mes", "Acum. YTD", "% YTD"]]
    for cat in all_cats:
        pct_m = cats_mes.get(cat, 0)
        e_m = pct_m / 100 * euros_mes if euros_mes > 0 else 0
        e_ytd = cats_ytd.get(cat, 0)
        p_ytd = (e_ytd / total_ytd * 100) if total_ytd > 0 else 0
        rows.append([cat, _fmt_eur(e_m), f"{pct_m:.1f}%",
                     _fmt_eur(e_ytd), f"{p_ytd:.1f}%"])
    rows.append(["TOTAL", _fmt_eur(euros_mes), "100%",
                 _fmt_eur(total_ytd), "100%"])

    t = Table(rows, colWidths=[38*mm, 22*mm, 14*mm, 24*mm, 14*mm])
    cmds = [
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("FONTNAME", (0, -1), (-1, -1), font_bold),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(color_header)),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#EEEEEE")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(rows) - 1):
        if i % 2 == 1:
            cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor(color_odd_row)))
    t.setStyle(TableStyle(cmds))
    return t


def generar_pdf_resumen(D, RAW, PBM_tasca, comes_items, tasca_items):
    """Genera PDF A4 con resumen mensual de ambos negocios."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, Table, TableStyle, PageBreak)
    except ImportError:
        print("  Aviso: reportlab no instalado, no se genera PDF")
        return None

    font_name, font_bold = _setup_pdf_fonts()
    W, H = A4

    mes_cerrado = datetime.now().month - 1
    year_actual = YEAR_LIST[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = MESES_FULL[mes_cerrado - 1]

    chart_tasca, chart_comes, chart_conjunto, chart_total, tmp_dir = \
        _generar_graficos_pdf(D, RAW, mes_cerrado, year_actual)

    pdf_name = f"informe_barea_{mes_nombre.lower()}_{year_actual}.pdf"
    pdf_path = os.path.join(_SCRIPT_DIR, "dashboards", pdf_name)

    # ── Canvas callbacks ──
    def _on_first_page(canvas, doc):
        canvas.saveState()
        # Banda cabecera roja (ambos establecimientos)
        canvas.setFillColor(HexColor("#FF0000"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        # Linea inferior
        canvas.setStrokeColor(HexColor("#CC0000"))
        canvas.setLineWidth(2)
        canvas.line(0, H - 30*mm, W, H - 30*mm)
        # Titulo
        canvas.setFillColor(white)
        canvas.setFont(font_bold, 18)
        canvas.drawCentredString(W / 2, H - 15*mm, "Informe Mensual")
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#B0BEC5"))
        canvas.drawCentredString(W / 2, H - 23*mm,
                                 f"{mes_nombre} {year_actual}")
        # Logos
        try:
            if os.path.exists(PATH_LOGO_TASCA):
                canvas.drawImage(PATH_LOGO_TASCA, 12*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        try:
            if os.path.exists(PATH_LOGO_COMES):
                canvas.drawImage(PATH_LOGO_COMES, W - 34*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        _draw_footer(canvas, doc)
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#FF0000"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#FF0000"))
        canvas.drawString(15*mm, H - 8*mm,
                          f"Informe Mensual — {mes_nombre} {year_actual}")
        _draw_footer(canvas, doc)
        canvas.restoreState()

    def _draw_footer(canvas, doc):
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 13*mm, W - 15*mm, 13*mm)
        canvas.setFillColor(HexColor("#999999"))
        canvas.setFont(font_name, 7)
        canvas.drawString(
            15*mm, 8*mm,
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(W - 15*mm, 8*mm,
                               f"Página {doc.page}")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=18*mm)
    elements = []

    # Estilos
    s_heading = ParagraphStyle(
        "pr_h", fontName=font_bold, fontSize=14,
        textColor=HexColor("#FF0000"), spaceBefore=4*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle(
        "pr_b", fontName=font_name, fontSize=10,
        textColor=HexColor("#333"), leading=14)
    s_section = ParagraphStyle(
        "pr_s", fontName=font_bold, fontSize=11,
        textColor=HexColor("#FF0000"), spaceBefore=2*mm, spaceAfter=2*mm)

    # ── PAGINA 1: KPIs + Comparativa ──
    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("Resumen del mes", s_heading))

    year_ant = str(int(year_actual) - 1)
    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    comes_pbm_prev = D.get(year_ant, {}).get("pbm", {})
    card_t = _kpi_card("TASCA BAREA", RAW, year_actual, mes_cerrado,
                       PBM_tasca.get(year_actual, {}), tasca_items,
                       "#1F4E79", "#DEEAF1", font_name, font_bold,
                       PBM_tasca.get(year_ant, {}))
    card_c = _kpi_card("COMESTIBLES BAREA", D, year_actual, mes_cerrado,
                       comes_pbm, comes_items,
                       "#375623", "#C6EFCE", font_name, font_bold,
                       comes_pbm_prev)
    cards = Table([[card_t, "", card_c]], colWidths=[84*mm, 6*mm, 84*mm])
    cards.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(cards)
    elements.append(Spacer(1, 6*mm))

    # ── Tabla YTD ──
    def _ytd_kpis(data_dict, year, hasta_mes):
        ventas, tickets = 0, 0
        for m in range(1, hasta_mes + 1):
            d = data_dict.get(year, {}).get("mensual", {}).get(str(m), {})
            ventas += d.get("euros", 0)
            tickets += d.get("tickets", 0)
        ticket_medio = ventas / tickets if tickets > 0 else 0
        return ventas, tickets, ticket_medio

    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.colors import HexColor

    def _tabla_ytd_pdf(titulo, color_accent, color_bg, data_actual, data_ant):
        v_act, t_act, tm_act = data_actual
        v_ant, t_ant, tm_ant = data_ant

        def pct(a, b):
            if b == 0:
                return "—"
            p = (a - b) / b * 100
            signo = "▲" if p >= 0 else "▼"
            return f"{signo}{abs(p):.1f}%"

        s_hdr = ParagraphStyle(f"ytd_h_{titulo}", fontName=font_bold,
                               fontSize=9, textColor=HexColor("#FFFFFF"))
        s_lbl = ParagraphStyle(f"ytd_l_{titulo}", fontName=font_bold,
                               fontSize=9, textColor=HexColor("#333"))
        s_val = ParagraphStyle(f"ytd_v_{titulo}", fontName=font_name,
                               fontSize=9, textColor=HexColor("#333"))

        rows = [
            [Paragraph(f"YTD {year_actual}", s_hdr),
             Paragraph("Acumulado", s_hdr),
             Paragraph(year_ant, s_hdr),
             Paragraph(f"vs YTD {year_ant}", s_hdr)],
            [Paragraph("Ventas netas", s_lbl),
             Paragraph(_fmt_eur(v_act), s_val),
             Paragraph(_fmt_eur(v_ant), s_val),
             Paragraph(pct(v_act, v_ant), s_val)],
            [Paragraph("Tickets", s_lbl),
             Paragraph(f"{t_act:,}".replace(",", "."), s_val),
             Paragraph(f"{t_ant:,}".replace(",", "."), s_val),
             Paragraph(pct(t_act, t_ant), s_val)],
            [Paragraph("Ticket medio", s_lbl),
             Paragraph(_fmt_eur(tm_act), s_val),
             Paragraph(_fmt_eur(tm_ant), s_val),
             Paragraph(pct(tm_act, tm_ant), s_val)],
        ]
        t = Table(rows, colWidths=[40*mm, 37*mm, 37*mm, 37*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(color_accent)),
            ("BACKGROUND", (0, 1), (-1, -1), HexColor(color_bg)),
            ("BACKGROUND", (0, 2), (-1, 2), HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ]))
        return t

    elements.append(Paragraph("Acumulado año (YTD)", s_heading))
    ytd_t_act = _ytd_kpis(RAW, year_actual, mes_cerrado)
    ytd_t_ant = _ytd_kpis(RAW, year_ant, mes_cerrado)
    ytd_c_act = _ytd_kpis(D, year_actual, mes_cerrado)
    ytd_c_ant = _ytd_kpis(D, year_ant, mes_cerrado)

    elements.append(Paragraph("Tasca Barea", ParagraphStyle(
        "ytd_st", fontName=font_bold, fontSize=10,
        textColor=HexColor("#1F4E79"), spaceAfter=2*mm)))
    elements.append(_tabla_ytd_pdf(
        "tasca", "#1F4E79", "#DEEAF1", ytd_t_act, ytd_t_ant))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("Comestibles Barea", ParagraphStyle(
        "ytd_sc", fontName=font_bold, fontSize=10,
        textColor=HexColor("#375623"), spaceAfter=2*mm)))
    elements.append(_tabla_ytd_pdf(
        "comes", "#375623", "#C6EFCE", ytd_c_act, ytd_c_ant))
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comparativa", s_heading))
    elements.append(Image(chart_conjunto, width=170*mm, height=62*mm))

    # ── PAGINA 2: Evolucion por negocio ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        "Evolución de facturación", s_heading))
    elements.append(Spacer(1, 2*mm))
    elements.append(Image(chart_total, width=170*mm, height=65*mm))
    elements.append(Spacer(1, 6*mm))
    elements.append(Image(chart_tasca, width=170*mm, height=55*mm))
    elements.append(Spacer(1, 6*mm))
    elements.append(Image(chart_comes, width=170*mm, height=55*mm))

    # ── PAGINA 3: Categorias ──
    elements.append(PageBreak())
    elements.append(Paragraph(
        f"Ventas por categoría — {mes_nombre} {year_actual}",
        s_heading))

    elements.append(Paragraph("Tasca Barea", ParagraphStyle(
        "pr_ct", parent=s_section, textColor=HexColor("#1F4E79"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        RAW, year_actual, mes_cerrado, mes_nombre,
        "#1F4E79", font_name, font_bold, "#DEEAF1"))
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph("Comestibles Barea", ParagraphStyle(
        "pr_cc", parent=s_section, textColor=HexColor("#375623"))))
    elements.append(Spacer(1, 1*mm))
    elements.append(_tabla_categorias_pdf(
        D, year_actual, mes_cerrado, mes_nombre,
        "#375623", font_name, font_bold, "#C6EFCE"))
    elements.append(Spacer(1, 8*mm))

    if GITHUB_PAGES_URL:
        url_c = GITHUB_PAGES_URL + "comestibles.html"
        url_t = GITHUB_PAGES_URL + "tasca.html"
        elements.append(Paragraph(
            f'<b>Dashboards interactivos:</b><br/>'
            f'<a href="{url_c}" color="#1565C0">{url_c}</a><br/>'
            f'<a href="{url_t}" color="#1565C0">{url_t}</a>',
            s_body))

    doc.build(elements, onFirstPage=_on_first_page,
              onLaterPages=_on_later_pages)

    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"  PDF generado: {pdf_path}")
    return pdf_path


def generar_pdf_comestibles(D, comes_items):
    """Genera PDF A4 solo Comestibles - diseño profesional."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, Table, TableStyle)
    except ImportError:
        print("  Aviso: reportlab no instalado, no se genera PDF Comestibles")
        return None

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    font_name, font_bold = _setup_pdf_fonts()
    W, H = A4

    mes_cerrado = datetime.now().month - 1
    year_actual = YEAR_LIST[-1]
    if mes_cerrado < 1:
        mes_cerrado = 12
        year_actual = str(int(year_actual) - 1)
    mes_nombre = MESES_FULL[mes_cerrado - 1]

    # Grafico con estilo mejorado
    tmp_dir = tempfile.mkdtemp(prefix="barea_pdf_comes_")
    fmt_euros = FuncFormatter(lambda x, _: _fmt_eur(x, 0))
    comes_colors = {"2025": "#82B878", "2026": "#375623"}

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#F8F9FA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.alpha': 0.25,
        'font.size': 9,
    })

    fig, ax = plt.subplots(figsize=(9, 4))
    for yr in YEAR_LIST:
        if yr not in D:
            continue
        mensual = D[yr]["mensual"]
        xs, vals = [], []
        for m in range(1, 13):
            e = mensual.get(str(m), {}).get("euros", 0)
            if e and e > 0:
                xs.append(m)
                vals.append(e)
        if not vals:
            continue
        color = comes_colors.get(yr, "#999")
        is_cur = (yr == year_actual)
        lw = 2.5 if is_cur else 1.5
        ms = 6 if is_cur else 3
        a = 1.0 if is_cur else 0.45
        z = 3 if is_cur else 2
        # Segmentos con parcial
        labeled = False
        for i in range(1, len(xs)):
            parcial = (xs[i] in MESES_PARCIALES or xs[i-1] in MESES_PARCIALES)
            kw = dict(color=color, linewidth=lw, zorder=z)
            if parcial:
                kw.update(linestyle='--', alpha=a * 0.4)
            else:
                kw['alpha'] = a
            if not labeled:
                kw['label'] = yr
                labeled = True
            ax.plot([xs[i-1], xs[i]], [vals[i-1], vals[i]], **kw)
        if not labeled:
            ax.plot([], [], color=color, linewidth=lw, alpha=a, label=yr)
        for x, v in zip(xs, vals):
            p = x in MESES_PARCIALES
            ax.plot(x, v, 'o', color=color,
                    markersize=3 if p else ms,
                    alpha=0.3 if p else a, zorder=z + 1)
        if is_cur:
            ax.fill_between(xs, vals, alpha=0.07, color=color)
            for x, v in zip(xs, vals):
                p = x in MESES_PARCIALES
                txt = _fmt_eur(v, 0) + ('*' if p else '')
                ax.annotate(txt, (x, v),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=7, color=color,
                            fontweight="bold")
                if p:
                    ax.annotate('parcial', (x, v),
                                textcoords="offset points", xytext=(0, -12),
                                ha="center", fontsize=6, color="#999",
                                fontstyle="italic")
    ax.set_title("Comestibles Barea — Facturación mensual",
                 fontsize=12, fontweight="bold", pad=12, color="#1a1a1a")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MESES_CORTO, fontsize=8)
    ax.yaxis.set_major_formatter(fmt_euros)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9, edgecolor="#DDD")
    ax.grid(True, axis="y", alpha=0.25)
    ax.set_xlim(0.5, 12.5)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#CCCCCC")
    fig.tight_layout(pad=1.5)
    chart_path = os.path.join(tmp_dir, "chart_comes.png")
    fig.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    plt.rcParams.update(plt.rcParamsDefault)

    # ── PDF ──
    pdf_name = f"informe_comestibles_{mes_nombre.lower()}_{year_actual}.pdf"
    pdf_path = os.path.join(_SCRIPT_DIR, "dashboards", pdf_name)

    def _on_first_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(HexColor("#375623"))
        canvas.rect(0, H - 30*mm, W, 30*mm, fill=1, stroke=0)
        canvas.setStrokeColor(HexColor("#C6EFCE"))
        canvas.setLineWidth(2)
        canvas.line(0, H - 30*mm, W, H - 30*mm)
        canvas.setFillColor(white)
        canvas.setFont(font_bold, 18)
        canvas.drawCentredString(W / 2, H - 15*mm, "Comestibles Barea")
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#C6EFCE"))
        canvas.drawCentredString(W / 2, H - 23*mm,
                                 f"Informe {mes_nombre} {year_actual}")
        try:
            if os.path.exists(PATH_LOGO_COMES):
                canvas.drawImage(PATH_LOGO_COMES, 12*mm, H - 28*mm,
                                 22*mm, 22*mm, preserveAspectRatio=True)
        except Exception:
            pass
        _draw_footer_c(canvas, doc)
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#375623"))
        canvas.setLineWidth(1.5)
        canvas.line(15*mm, H - 10*mm, W - 15*mm, H - 10*mm)
        canvas.setFont(font_bold, 8)
        canvas.setFillColor(HexColor("#375623"))
        canvas.drawString(15*mm, H - 8*mm,
                          f"Comestibles Barea — {mes_nombre} {year_actual}")
        _draw_footer_c(canvas, doc)
        canvas.restoreState()

    def _draw_footer_c(canvas, doc):
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 13*mm, W - 15*mm, 13*mm)
        canvas.setFillColor(HexColor("#999"))
        canvas.setFont(font_name, 7)
        canvas.drawString(
            15*mm, 8*mm,
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(W - 15*mm, 8*mm,
                               f"Página {doc.page}")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=18*mm)
    elements = []

    s_heading = ParagraphStyle(
        "pc_h", fontName=font_bold, fontSize=14,
        textColor=HexColor("#375623"), spaceBefore=4*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle(
        "pc_b", fontName=font_name, fontSize=10,
        textColor=HexColor("#333"), leading=14)
    s_det = ParagraphStyle(
        "pc_det", fontName=font_name, fontSize=10,
        textColor=HexColor("#444"), leading=14)

    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("Resumen del mes", s_heading))

    # KPIs como card unica
    d_mes = D.get(year_actual, {}).get("mensual", {}).get(
        str(mes_cerrado), {})
    euros = d_mes.get("euros", 0)
    tickets = d_mes.get("tickets", 0)
    prom = d_mes.get("prom_ticket", 0)

    year_ant = str(int(year_actual) - 1)
    euros_ant_year = (D.get(year_ant, {}).get("mensual", {})
                      .get(str(mes_cerrado), {}).get("euros", 0))
    if mes_cerrado > 1:
        euros_ant_mes = (D.get(year_actual, {}).get("mensual", {})
                         .get(str(mes_cerrado - 1), {}).get("euros", 0))
    else:
        euros_ant_mes = (D.get(year_ant, {}).get("mensual", {})
                         .get("12", {}).get("euros", 0))

    comes_pbm = D.get(year_actual, {}).get("pbm", {})
    comes_pbm_prev = D.get(year_ant, {}).get("pbm", {})
    top3 = _top3_productos(comes_pbm, mes_cerrado, comes_pbm_prev)
    dia, dia_media = _calcular_dia_fuerte(comes_items, year_actual,
                                          mes_cerrado)

    s_big = ParagraphStyle("pc_big", fontName=font_bold, fontSize=28,
                           textColor=HexColor("#1a1a1a"), leading=32)
    s_var = ParagraphStyle("pc_var", fontName=font_name, fontSize=10,
                           textColor=HexColor("#555"), leading=13)

    kpi_rows = [
        [Paragraph(_fmt_eur(euros, 0), s_big), ""],
        [Paragraph(
            f"vs año ant.: {_var_html(euros, euros_ant_year)} "
            f"&nbsp;·&nbsp; vs mes ant.: "
            f"{_var_html(euros, euros_ant_mes)}", s_var), ""],
        [Paragraph(
            f"<b>{tickets}</b> tickets &nbsp;·&nbsp; "
            f"<b>{_fmt_eur(prom)}</b> ticket medio &nbsp;·&nbsp; "
            f"Día fuerte: <b>{dia}</b> (media {_fmt_eur(dia_media)})",
            s_det), ""],
    ]
    if top3:
        lines = []
        for p in top3:
            if p["var_pct"] is not None:
                vc = "#2E7D32" if p["var_pct"] >= 0 else "#C62828"
                va = "▲" if p["var_pct"] >= 0 else "▼"
                vs = (f' <font color="{vc}"><b>'
                      f'{va}{abs(p["var_pct"]):.0f}%</b></font>')
            else:
                vs = ' <font color="#999">nuevo</font>'
            lines.append(
                f'{p["art"]} — {p["cant"]:.0f} uds · '
                f'{_fmt_eur(p["euros"])}{vs}')
        items_html = " &nbsp;·&nbsp; ".join(lines)
        kpi_rows.append([Paragraph(
            f"Top productos: {items_html}", s_det), ""])

    kpi_t = Table(kpi_rows, colWidths=[100*mm, 70*mm])
    kpi_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#C6EFCE")),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#375623")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(kpi_t)
    elements.append(Spacer(1, 6*mm))

    # ── Tabla YTD Comestibles ──
    def _ytd_sum(data_dict, yr, hasta_mes):
        ventas, tickets = 0, 0
        for m in range(1, hasta_mes + 1):
            d = data_dict.get(yr, {}).get("mensual", {}).get(str(m), {})
            ventas += d.get("euros", 0)
            tickets += d.get("tickets", 0)
        tm = ventas / tickets if tickets > 0 else 0
        return ventas, tickets, tm

    def pct_str(a, b):
        if b == 0:
            return "—"
        p = (a - b) / b * 100
        return ("▲" if p >= 0 else "▼") + f"{abs(p):.1f}%"

    v_act, t_act, tm_act = _ytd_sum(D, year_actual, mes_cerrado)
    v_ant, t_ant, tm_ant = _ytd_sum(D, year_ant, mes_cerrado)

    s_ytd_h = ParagraphStyle("pc_yh", fontName=font_bold, fontSize=9,
                             textColor=HexColor("#FFFFFF"))
    s_ytd_l = ParagraphStyle("pc_yl", fontName=font_bold, fontSize=9,
                             textColor=HexColor("#333"))
    s_ytd_v = ParagraphStyle("pc_yv", fontName=font_name, fontSize=9,
                             textColor=HexColor("#333"))
    ytd_rows = [
        [Paragraph(f"YTD {year_actual}", s_ytd_h),
         Paragraph("Acumulado", s_ytd_h),
         Paragraph(year_ant, s_ytd_h),
         Paragraph(f"vs YTD {year_ant}", s_ytd_h)],
        [Paragraph("Ventas netas", s_ytd_l),
         Paragraph(_fmt_eur(v_act), s_ytd_v),
         Paragraph(_fmt_eur(v_ant), s_ytd_v),
         Paragraph(pct_str(v_act, v_ant), s_ytd_v)],
        [Paragraph("Tickets", s_ytd_l),
         Paragraph(f"{t_act:,}".replace(",", "."), s_ytd_v),
         Paragraph(f"{t_ant:,}".replace(",", "."), s_ytd_v),
         Paragraph(pct_str(t_act, t_ant), s_ytd_v)],
        [Paragraph("Ticket medio", s_ytd_l),
         Paragraph(_fmt_eur(tm_act), s_ytd_v),
         Paragraph(_fmt_eur(tm_ant), s_ytd_v),
         Paragraph(pct_str(tm_act, tm_ant), s_ytd_v)],
    ]
    ytd_t = Table(ytd_rows, colWidths=[40*mm, 37*mm, 37*mm, 37*mm])
    ytd_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#375623")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#C6EFCE")),
        ("BACKGROUND", (0, 2), (-1, 2), HexColor("#FFFFFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
    ]))
    elements.append(Paragraph("Acumulado año (YTD)", s_heading))
    elements.append(ytd_t)
    elements.append(Spacer(1, 6*mm))

    # Grafico
    elements.append(Paragraph(
        "Evolución de facturación", s_heading))
    elements.append(Image(chart_path, width=170*mm, height=68*mm))
    elements.append(Spacer(1, 6*mm))

    # Categorias
    elements.append(Paragraph(
        f"Ventas por categoría — {mes_nombre} {year_actual}",
        s_heading))
    elements.append(_tabla_categorias_pdf(
        D, year_actual, mes_cerrado, mes_nombre,
        "#375623", font_name, font_bold, "#C6EFCE"))
    elements.append(Spacer(1, 8*mm))

    if GITHUB_PAGES_URL:
        url_c = GITHUB_PAGES_URL + "comestibles.html"
        elements.append(Paragraph(
            f'<b>Dashboard interactivo:</b> '
            f'<a href="{url_c}" color="#1565C0">{url_c}</a>', s_body))

    doc.build(elements, onFirstPage=_on_first_page,
              onLaterPages=_on_later_pages)

    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"  PDF Comestibles generado: {pdf_path}")
    return pdf_path

"""
ventas_semana/netlify_publisher.py — Exportación JSON y publicación Netlify.

Extrae la lógica de publicación de generar_dashboard.py para reducir tamaño.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime

import numpy as np

from nucleo.utils import NumpyEncoder

# ── Config Netlify (import seguro) ───────────────────────────────────────────
try:
    from config.datos_sensibles import (NETLIFY_TOKEN, NETLIFY_SITE_ID,
                                        NETLIFY_URL)
except ImportError:
    NETLIFY_TOKEN = ""
    NETLIFY_SITE_ID = ""
    NETLIFY_URL = ""


def _generar_index_github_pages():
    """Genera el index.html landing page para Netlify."""
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barea · Dashboards</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#0f0e0c;color:#f0ece4;font-family:'Segoe UI',sans-serif;
      min-height:100vh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;padding:40px 20px;}}
h1{{font-size:28px;color:#e8c97a;margin-bottom:8px;}}
.sub{{color:#9a9488;font-size:13px;margin-bottom:40px;}}
.cards{{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;}}
.card{{background:#1a1916;border:1px solid #2e2c28;border-radius:12px;
       padding:32px 40px;text-align:center;text-decoration:none;
       transition:all .2s;min-width:240px;}}
.card:hover{{border-color:#c9a84c;transform:translateY(-2px);
             box-shadow:0 8px 24px rgba(0,0,0,.4);}}
.card h2{{font-size:18px;margin-bottom:6px;}}
.card p{{font-size:12px;color:#9a9488;}}
.card.tasca h2{{color:#e8c97a;}}
.card.comes h2{{color:#a8e8c0;}}
.footer{{margin-top:40px;font-size:11px;color:#5a5650;}}
</style>
</head>
<body>
  <h1>Barea</h1>
  <p class="sub">Dashboards de ventas</p>
  <div class="cards">
    <a href="tasca.html" class="card tasca">
      <h2>Tasca Barea</h2>
      <p>2023 – 2026</p>
    </a>
    <a href="comestibles.html" class="card comes">
      <h2>Comestibles Barea</h2>
      <p>2025 – 2026</p>
    </a>
  </div>
  <p class="footer">Actualizado: {fecha}</p>
</body>
</html>"""


def exportar_json_streamlit(D, MD, DIAS, RAW, PBM):
    """Exporta datos agregados como JSON para el puente Streamlit <-> Netlify.

    Genera ficheros en un directorio temporal data/ que se incluirán en el
    ZIP de Netlify. Solo contiene datos agregados (sin CIFs, IBANs, etc.).
    """
    data_dir = os.path.join(tempfile.gettempdir(), "barea_streamlit_data", "data")
    os.makedirs(data_dir, exist_ok=True)

    # ── ventas_comes.json ──
    comes = {"años": {}, "woo": {}}
    for year in D:
        if year == "woo":
            for mes, val in D["woo"].items():
                comes["woo"][mes] = {
                    "euros": round(val.get("euros", 0), 2),
                    "pedidos": val.get("pedidos", 0)
                }
            continue
        y = D[year]
        comes["años"][year] = {"mensual": {}, "categorias": {}, "top_productos": {}, "margenes": {}}
        for mes, val in y.get("mensual", {}).items():
            comes["años"][year]["mensual"][mes] = {
                "euros": round(val.get("euros", 0), 2),
                "unidades": round(val.get("unidades", 0), 1),
                "tickets": val.get("tickets", 0),
                "prom_ticket": round(val.get("prom_ticket", 0), 2)
            }
            comes["años"][year]["categorias"][mes] = val.get("cats", {})
        for mes, cats in y.get("pbm", {}).items():
            top_mes = []
            for cat, productos in cats.items():
                for p in sorted(productos, key=lambda x: x.get("euros", 0), reverse=True)[:10]:
                    top_mes.append({"art": p["art"], "cat": cat,
                                    "euros": round(p.get("euros", 0), 2),
                                    "cant": round(p.get("cant", 0), 1)})
            comes["años"][year]["top_productos"][mes] = sorted(
                top_mes, key=lambda x: x["euros"], reverse=True)[:20]
        if year in MD:
            for mes, val in MD[year].items():
                cats_margen = {}
                for cat, datos in val.get("cats", {}).items():
                    cats_margen[cat] = {
                        "euros": round(datos.get("euros", 0), 2),
                        "margen_pct": round(datos.get("margen_pct", 0), 1)
                    }
                comes["años"][year]["margenes"][mes] = cats_margen

    with open(os.path.join(data_dir, "ventas_comes.json"), "w", encoding="utf-8") as f:
        json.dump(comes, f, ensure_ascii=False, separators=(",", ":"), cls=NumpyEncoder)
    print(f"  ventas_comes.json generado")

    # ── ventas_tasca.json ──
    tasca = {"años": {}, "dias_semana": {}}
    for year in RAW:
        r = RAW[year]
        tasca["años"][year] = {"mensual": {}, "categorias": {}, "top_productos": {}}
        for mes, val in r.get("mensual", {}).items():
            tasca["años"][year]["mensual"][mes] = {
                "euros": round(val.get("euros", 0), 2),
                "unidades": round(val.get("unidades", 0), 1),
                "tickets": val.get("tickets", 0),
                "prom_ticket": round(val.get("prom_ticket", 0), 2)
            }
        for mes, cats in r.get("categorias_mes", {}).items():
            tasca["años"][year]["categorias"][mes] = cats
        if year in PBM:
            for mes, cats in PBM[year].items():
                top_mes = []
                for cat, productos in cats.items():
                    for p in sorted(productos, key=lambda x: x.get("euros", 0), reverse=True)[:10]:
                        top_mes.append({"art": p["art"], "cat": cat,
                                        "euros": round(p.get("euros", 0), 2),
                                        "cant": round(p.get("cant", 0), 1)})
                tasca["años"][year]["top_productos"][mes] = sorted(
                    top_mes, key=lambda x: x["euros"], reverse=True)[:20]
    for year in DIAS:
        if year == "dias_nombres":
            continue
        tasca["dias_semana"][year] = {}
        for dia_idx, val in DIAS[year].items():
            if dia_idx == "heatmap":
                continue
            tasca["dias_semana"][year][str(dia_idx)] = {
                "euros": round(val.get("euros", 0), 2),
                "tickets": val.get("tickets", 0),
                "ticket_medio": round(val.get("ticket_medio", 0), 2)
            }

    with open(os.path.join(data_dir, "ventas_tasca.json"), "w", encoding="utf-8") as f:
        json.dump(tasca, f, ensure_ascii=False, separators=(",", ":"), cls=NumpyEncoder)
    print(f"  ventas_tasca.json generado")

    # ── Copiar gmail_resumen.json y cuadre_resumen.json si existen ──
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archivos_opcionales = [
        (os.path.join(base_dir, "outputs", "logs_gmail", "gmail_resumen.json"), "gmail.json"),
        (os.path.join(base_dir, "outputs", "cuadre_resumen.json"), "cuadre.json"),
    ]
    for src, dst in archivos_opcionales:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(data_dir, dst))
            print(f"  {dst} copiado desde {os.path.basename(src)}")

    # ── monitor.json ──
    procesos = {}
    logs_gmail = os.path.join(base_dir, "outputs", "logs_gmail")
    logs_barea = os.path.join(base_dir, "outputs", "logs_barea")
    for nombre, directorio in [("gmail", logs_gmail), ("ventas", logs_barea)]:
        if os.path.isdir(directorio):
            auto_logs = sorted([f for f in os.listdir(directorio)
                                if f.startswith("auto_") and f.endswith(".log")])
            if auto_logs:
                ultimo = auto_logs[-1]
                fecha_str = ultimo.replace("auto_", "").replace(".log", "")
                procesos[nombre] = {"ultima_ejecucion": fecha_str, "log": ultimo}
    cuadre_json_path = os.path.join(base_dir, "outputs", "cuadre_resumen.json")
    if os.path.exists(cuadre_json_path):
        try:
            with open(cuadre_json_path, "r", encoding="utf-8") as f:
                cuadre_data = json.load(f)
            procesos["cuadre"] = {"ultima_ejecucion": cuadre_data.get("fecha_ejecucion", "")}
        except Exception:
            pass

    with open(os.path.join(data_dir, "monitor.json"), "w", encoding="utf-8") as f:
        json.dump({"procesos": procesos}, f, ensure_ascii=False, indent=2)
    print(f"  monitor.json generado")

    # ── meta.json ──
    archivos_presentes = [f for f in os.listdir(data_dir)
                          if f.endswith(".json") and f != "meta.json"]
    meta = {
        "exportado": datetime.now().isoformat(timespec="seconds"),
        "version": "1.0",
        "archivos": sorted(archivos_presentes)
    }
    with open(os.path.join(data_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  meta.json generado ({len(archivos_presentes)} ficheros)")

    return os.path.dirname(data_dir)


def publicar_github_pages(path_comes, path_tasca, data_dir=None):
    """Publica ambos dashboards en Netlify (reemplaza GitHub Pages)."""
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID:
        print("  Aviso: NETLIFY_TOKEN o NETLIFY_SITE_ID no configurados")
        return

    import zipfile
    import urllib.request

    try:
        tmp_zip = os.path.join(tempfile.gettempdir(), "barea_dashboards.zip")
        index_html = _generar_index_github_pages()

        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(path_comes, "comestibles.html")
            zf.write(path_tasca, "tasca.html")
            zf.writestr("index.html", index_html)
            if data_dir:
                json_dir = os.path.join(data_dir, "data")
                if os.path.isdir(json_dir):
                    for fname in os.listdir(json_dir):
                        if fname.endswith(".json"):
                            zf.write(os.path.join(json_dir, fname), f"data/{fname}")
                    print(f"  JSON incluidos en ZIP: {len(os.listdir(json_dir))} ficheros")

        url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
        with open(tmp_zip, "rb") as f:
            data = f.read()

        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "Authorization": f"Bearer {NETLIFY_TOKEN}",
                "Content-Type": "application/zip",
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())

        os.remove(tmp_zip)
        print(f"  Netlify actualizado: {NETLIFY_URL}")
        return result.get("deploy_ssl_url", NETLIFY_URL)

    except Exception as e:
        print(f"  Aviso Netlify: {e}")

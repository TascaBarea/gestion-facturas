"""
ventas_semana/netlify_publisher.py — Exportación JSON y publicación GitHub Pages.

Extrae la lógica de publicación de generar_dashboard.py para reducir tamaño.
Migrado de Netlify a GitHub Pages (27/03/2026).
"""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

import numpy as np

from nucleo.utils import NumpyEncoder

GITHUB_PAGES_URL = "https://tascabarea.github.io/gestion-facturas"


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


def exportar_json_streamlit(D, MD, DIAS, RAW, PBM, DIAS_TASCA=None):
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
    # Días de la semana: usar DIAS_TASCA (calculado con datos Tasca)
    dias_src = DIAS_TASCA if DIAS_TASCA is not None else DIAS
    for year in dias_src:
        if year == "dias_nombres":
            continue
        tasca["dias_semana"][year] = {}
        for dia_idx, val in dias_src[year].items():
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

    # ── maestro.json (campos públicos, sin CIF/IBAN/EMAIL) ──
    try:
        import pandas as pd
        maestro_path = os.path.join(base_dir, "datos", "MAESTRO_PROVEEDORES.xlsx")
        if os.path.exists(maestro_path):
            df_m = pd.read_excel(maestro_path, dtype=str).fillna("")
            # Solo campos seguros (sin CIF, IBAN, EMAIL)
            campos_safe = ["PROVEEDOR", "CUENTA", "FORMA_PAGO", "TIENE_EXTRACTOR",
                           "ARCHIVO_EXTRACTOR", "CATEGORIA_FIJA", "ACTIVO", "NOTAS", "ALIAS"]
            proveedores_safe = []
            for _, row in df_m.iterrows():
                nombre = str(row.get("PROVEEDOR", "")).strip()
                if not nombre:
                    continue
                alias_raw = str(row.get("ALIAS", ""))
                sep = "," if "," in alias_raw else "|"
                n_aliases = len([a for a in alias_raw.split(sep) if a.strip()]) if alias_raw else 0
                proveedores_safe.append({
                    "PROVEEDOR": nombre,
                    "CUENTA": str(row.get("CUENTA", "")).strip(),
                    "FORMA_PAGO": str(row.get("FORMA_PAGO", "")).strip().upper(),
                    "TIENE_EXTRACTOR": str(row.get("TIENE_EXTRACTOR", "")).strip().upper(),
                    "ARCHIVO_EXTRACTOR": str(row.get("ARCHIVO_EXTRACTOR", "")).strip(),
                    "CATEGORIA_FIJA": str(row.get("CATEGORIA_FIJA", "")).strip(),
                    "ACTIVO": str(row.get("ACTIVO", "")).strip().upper(),
                    "NOTAS": str(row.get("NOTAS", "")).strip(),
                    "ALIASES": n_aliases,
                })
            with open(os.path.join(data_dir, "maestro.json"), "w", encoding="utf-8") as f:
                json.dump({"proveedores": proveedores_safe, "total": len(proveedores_safe)},
                          f, ensure_ascii=False, separators=(",", ":"))
            print(f"  maestro.json generado ({len(proveedores_safe)} proveedores)")
    except Exception as e:
        print(f"  Aviso: no se pudo generar maestro.json: {e}")

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
    """Publica dashboards + JSONs en GitHub Pages (rama gh-pages).

    Usa git worktree temporal para no afectar el working tree actual.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    worktree_dir = os.path.join(tempfile.gettempdir(), "barea_gh_pages")

    try:
        # Limpiar worktree previo si existe
        if os.path.exists(worktree_dir):
            subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_dir],
                cwd=project_root, capture_output=True,
            )
            if os.path.exists(worktree_dir):
                shutil.rmtree(worktree_dir, ignore_errors=True)

        # Verificar si gh-pages existe en remote
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "gh-pages"],
            cwd=project_root, capture_output=True, text=True,
        )
        gh_pages_exists = "gh-pages" in result.stdout

        if gh_pages_exists:
            # Crear worktree desde rama existente
            subprocess.run(
                ["git", "worktree", "add", worktree_dir, "gh-pages"],
                cwd=project_root, check=True, capture_output=True,
            )
        else:
            # Crear rama orphan gh-pages
            subprocess.run(
                ["git", "worktree", "add", "--detach", worktree_dir],
                cwd=project_root, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "--orphan", "gh-pages"],
                cwd=worktree_dir, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=worktree_dir, check=True, capture_output=True,
            )

        # Limpiar contenido existente (excepto .git)
        for item in os.listdir(worktree_dir):
            if item == ".git":
                continue
            path = os.path.join(worktree_dir, item)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

        # Copiar archivos
        index_html = _generar_index_github_pages()
        with open(os.path.join(worktree_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        shutil.copy2(path_comes, os.path.join(worktree_dir, "comestibles.html"))
        shutil.copy2(path_tasca, os.path.join(worktree_dir, "tasca.html"))

        # Copiar JSONs de datos
        n_json = 0
        if data_dir:
            json_src = os.path.join(data_dir, "data")
            if os.path.isdir(json_src):
                json_dst = os.path.join(worktree_dir, "data")
                os.makedirs(json_dst, exist_ok=True)
                for fname in os.listdir(json_src):
                    if fname.endswith(".json"):
                        shutil.copy2(
                            os.path.join(json_src, fname),
                            os.path.join(json_dst, fname),
                        )
                        n_json += 1

        # .nojekyll para que GitHub Pages sirva ficheros sin procesar
        with open(os.path.join(worktree_dir, ".nojekyll"), "w") as f:
            pass

        # Commit y push
        subprocess.run(["git", "add", "-A"], cwd=worktree_dir, check=True, capture_output=True)

        # Verificar si hay cambios
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_dir, capture_output=True, text=True,
        )
        if not status.stdout.strip():
            print(f"  GitHub Pages: sin cambios, no se publica")
            return GITHUB_PAGES_URL

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"Deploy dashboards {fecha}"],
            cwd=worktree_dir, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "gh-pages", "--force"],
            cwd=worktree_dir, check=True, capture_output=True,
        )

        print(f"  GitHub Pages actualizado: {GITHUB_PAGES_URL} ({n_json} JSONs)")
        return GITHUB_PAGES_URL

    except Exception as e:
        print(f"  Error GitHub Pages: {e}")
        return None

    finally:
        # Limpiar worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_dir],
                cwd=project_root, capture_output=True,
            )
        except Exception:
            pass

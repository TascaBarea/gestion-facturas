#!/usr/bin/env python3
"""
investigacion.py — Pipeline de investigación multicanal para Tasca Barea SLL
Busca en YouTube, webs y Reddit, genera un resumen consolidado,
y opcionalmente envía las fuentes a NotebookLM.

Uso:
    python investigacion.py "skills en Claude Code"
    python investigacion.py "claude code mcp tutorial" --max 5
    python investigacion.py "odoo reconciliacion bancaria" --sin-reddit

Dependencias:
    pip install youtube-transcript-api duckduckgo-search requests
"""

import sys
import os
import re
import json
import time
import webbrowser
import argparse
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

# ── Colores para terminal ──────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    GRAY   = "\033[90m"
    BLUE   = "\033[94m"

def banner(text, color=C.CYAN):
    print(f"\n{color}{C.BOLD}{text}{C.RESET}")

def step(emoji, text, color=C.RESET):
    print(f"   {emoji}  {color}{text}{C.RESET}")

def ok(text):
    print(f"   {C.GREEN}✅ {text}{C.RESET}")

def warn(text):
    print(f"   {C.YELLOW}⚠️  {text}{C.RESET}")

def err(text):
    print(f"   {C.RED}❌ {text}{C.RESET}")

def ask(prompt) -> str:
    return input(f"\n{C.BOLD}{C.BLUE}❓ {prompt}{C.RESET} ").strip()

# ── Rutas ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent  # gestion-facturas/
NOTES_FILE   = PROJECT_ROOT / "docs" / "youtube-research-notes.md"
SOURCES_FILE = PROJECT_ROOT / "docs" / "investigacion-fuentes-temp.txt"

NOTEBOOKLM_URL = "https://notebooklm.google.com/"

# ── Extracción de video ID ─────────────────────────────────────────────────
def extract_video_id(url: str) -> str | None:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

# ── Búsqueda DuckDuckGo ────────────────────────────────────────────────────
def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Busca vídeos de YouTube via DuckDuckGo."""
    step("🔍", f"Buscando vídeos YouTube: '{query}'...", C.CYAN)
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(
                f"site:youtube.com {query}",
                max_results=max_results * 2
            ):
                url = r.get('href', '')
                vid_id = extract_video_id(url)
                if not vid_id:
                    continue
                results.append({
                    'tipo': 'youtube',
                    'titulo': r.get('title', 'Sin título'),
                    'url': f"https://www.youtube.com/watch?v={vid_id}",
                    'video_id': vid_id,
                    'snippet': r.get('body', ''),
                    'fiabilidad': None,
                    'transcript': None,
                })
                if len(results) >= max_results:
                    break
        ok(f"{len(results)} vídeos encontrados")
    except Exception as e:
        warn(f"Error buscando YouTube: {e}")
    return results


def search_web(query: str, max_results: int = 4) -> list[dict]:
    """Busca artículos web (excluyendo YouTube y Reddit)."""
    step("🌐", f"Buscando artículos web: '{query}'...", C.CYAN)
    results = []
    try:
        from ddgs import DDGS
        skip_domains = ['youtube.com', 'reddit.com', 'youtu.be']
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 3):
                url = r.get('href', '')
                domain = urlparse(url).netloc.replace('www.', '')
                if any(s in domain for s in skip_domains):
                    continue
                results.append({
                    'tipo': 'web',
                    'titulo': r.get('title', 'Sin título'),
                    'url': url,
                    'dominio': domain,
                    'snippet': r.get('body', ''),
                    'fiabilidad': None,
                })
                if len(results) >= max_results:
                    break
        ok(f"{len(results)} artículos web encontrados")
    except Exception as e:
        warn(f"Error buscando web: {e}")
    return results


def search_reddit(query: str, max_results: int = 3) -> list[dict]:
    """Busca posts en Reddit."""
    step("💬", f"Buscando en Reddit: '{query}'...", C.CYAN)
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(
                f"site:reddit.com {query}",
                max_results=max_results * 2
            ):
                url = r.get('href', '')
                if 'reddit.com' not in url:
                    continue
                results.append({
                    'tipo': 'reddit',
                    'titulo': r.get('title', 'Sin título'),
                    'url': url,
                    'snippet': r.get('body', ''),
                    'fiabilidad': None,
                })
                if len(results) >= max_results:
                    break
        ok(f"{len(results)} posts Reddit encontrados")
    except Exception as e:
        warn(f"Error buscando Reddit: {e}")
    return results

# ── Transcript YouTube ─────────────────────────────────────────────────────
def get_transcript(video_id: str) -> str | None:
    """Intenta obtener el transcript de un vídeo."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        for langs in [['es', 'es-ES'], ['en', 'en-US', 'en-GB'], None]:
            try:
                if langs:
                    segs = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                else:
                    tlist = YouTubeTranscriptApi.list_transcripts(video_id)
                    segs = next(iter(tlist)).fetch()
                return ' '.join(s['text'] for s in segs)
            except Exception:
                continue
    except ImportError:
        pass
    return None

# ── Scoring de fiabilidad ──────────────────────────────────────────────────
FUENTES_FIABLES = [
    'anthropic.com', 'docs.anthropic.com', 'github.com',
    'towardsdatascience.com', 'medium.com', 'dev.to',
    'stackoverflow.com', 'arxiv.org', 'huggingface.co',
]
FUENTES_DUDOSAS = [
    'pinterest', 'quora.com', 'answers.com', 'ehow',
]

def puntuar_fuente(fuente: dict) -> int:
    """Devuelve 1-3 estrellas según fiabilidad estimada."""
    if fuente['tipo'] == 'youtube':
        return 3  # YouTube siempre relevante para tutoriales
    dominio = fuente.get('dominio', fuente.get('url', ''))
    if any(f in dominio for f in FUENTES_FIABLES):
        return 3
    if any(f in dominio for f in FUENTES_DUDOSAS):
        return 1
    return 2

def estrellas(n: int) -> str:
    return '★' * n + '☆' * (3 - n)

# ── Resumen consolidado ────────────────────────────────────────────────────
def generar_resumen(query: str, fuentes: list[dict]) -> str:
    """Genera un resumen estructurado a partir de las fuentes."""
    lines = []
    lines.append(f"## 🔎 Investigación: \"{query}\"")
    lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Fuentes analizadas:** {len(fuentes)}")
    lines.append("")

    # Snippets agrupados por tipo
    for tipo, emoji, label in [
        ('youtube', '📺', 'Vídeos YouTube'),
        ('web',     '🌐', 'Artículos Web'),
        ('reddit',  '💬', 'Reddit'),
    ]:
        grupo = [f for f in fuentes if f['tipo'] == tipo]
        if not grupo:
            continue
        lines.append(f"### {emoji} {label}")
        for f in grupo:
            stars = estrellas(f.get('fiabilidad') or puntuar_fuente(f))
            lines.append(f"- **[{stars}] [{f['titulo']}]({f['url']})**")
            snippet = f.get('snippet', '').strip()
            if snippet:
                # Truncar snippet a 200 chars
                snippet_short = textwrap.shorten(snippet, width=200, placeholder='...')
                lines.append(f"  > {snippet_short}")
            if f.get('transcript'):
                resumen_t = textwrap.shorten(f['transcript'], width=400, placeholder='...')
                lines.append(f"  > 📝 *Transcript:* {resumen_t}")
        lines.append("")

    # Resumen conjunto
    all_snippets = ' '.join(
        f.get('transcript') or f.get('snippet', '')
        for f in fuentes
    )
    lines.append("### 🗒️ Resumen consolidado")
    if all_snippets:
        # Extraer frases únicas relevantes (heurística simple)
        sentences = re.split(r'[.!?]+', all_snippets)
        query_words = set(query.lower().split())
        relevant = []
        seen = set()
        for s in sentences:
            s = s.strip()
            if len(s) < 30:
                continue
            s_lower = s.lower()
            if any(w in s_lower for w in query_words) and s_lower not in seen:
                relevant.append(s)
                seen.add(s_lower)
            if len(relevant) >= 8:
                break
        if relevant:
            for r in relevant[:8]:
                lines.append(f"- {r.strip()}.")
        else:
            lines.append("*Resumen automático no disponible — revisa las fuentes directamente.*")
    else:
        lines.append("*Sin contenido suficiente para generar resumen automático.*")
    lines.append("")
    lines.append("---")
    return '\n'.join(lines)

# ── Guardar notas ──────────────────────────────────────────────────────────
def guardar_notas(contenido: str):
    """Añade el resumen al archivo acumulativo de notas."""
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    cabecera = (
        "# 📚 Investigación YouTube & Web — Tasca Barea SLL\n"
        "> Notas acumulativas generadas por investigacion.py\n"
        "> Los registros más recientes aparecen primero.\n\n---\n\n"
    )
    if NOTES_FILE.exists():
        existing = NOTES_FILE.read_text(encoding='utf-8')
        # Insertar después de la cabecera (tras el primer ---)
        if '---' in existing:
            idx = existing.index('---') + 3
            nuevo = existing[:idx] + '\n\n' + contenido + existing[idx:]
        else:
            nuevo = existing + '\n\n' + contenido
    else:
        nuevo = cabecera + contenido

    NOTES_FILE.write_text(nuevo, encoding='utf-8')

    # Contar entradas
    n_entradas = nuevo.count('## 🔎')
    ok(f"Guardado en {NOTES_FILE.relative_to(PROJECT_ROOT)} ({n_entradas} investigaciones en total)")

# ── Envío a NotebookLM ─────────────────────────────────────────────────────
def enviar_notebooklm(fuentes: list[dict]):
    """Abre NotebookLM en el navegador y guarda las URLs en un fichero."""
    urls = [f['url'] for f in fuentes]

    # Guardar URLs en fichero temporal para copiar fácilmente
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text('\n'.join(urls), encoding='utf-8')

    step("📋", f"URLs guardadas en: {SOURCES_FILE.name}", C.YELLOW)
    step("🌐", "Abriendo NotebookLM en el navegador...", C.YELLOW)

    webbrowser.open(NOTEBOOKLM_URL)
    time.sleep(1)

    print(f"""
{C.YELLOW}{C.BOLD}  ╔══════════════════════════════════════════════════════════╗
  ║  PASOS EN NOTEBOOKLM:                                    ║
  ║  1. Crea un nuevo notebook o abre uno existente          ║
  ║  2. Haz clic en "Añadir fuente" → "URL"                  ║
  ║  3. Pega las {len(urls)} URLs del fichero:                         ║
  ║     {str(SOURCES_FILE)[:50]:<50}  ║
  ║  4. NotebookLM generará un resumen completo              ║
  ╚══════════════════════════════════════════════════════════╝{C.RESET}
""")

# ── Mostrar fuentes en terminal ────────────────────────────────────────────
def mostrar_fuentes(fuentes: list[dict]):
    banner("📋 FUENTES ENCONTRADAS", C.BOLD)
    for i, f in enumerate(fuentes, 1):
        stars = estrellas(f.get('fiabilidad') or puntuar_fuente(f))
        tipo_label = {'youtube': '▶ YouTube', 'web': '🌐 Web   ', 'reddit': '💬 Reddit'}
        label = tipo_label.get(f['tipo'], f['tipo'])
        titulo = textwrap.shorten(f['titulo'], width=55, placeholder='...')
        print(f"   {C.BOLD}[{i}]{C.RESET} {stars} {label}  {titulo}")
        print(f"       {C.GRAY}{f['url']}{C.RESET}")

# ── Pipeline principal ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Pipeline de investigación para Tasca Barea SLL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Ejemplos:
              python investigacion.py "skills claude code"
              python investigacion.py "odoo reconciliacion bancaria" --max 4
              python investigacion.py "claude code mcp" --sin-reddit
        """)
    )
    parser.add_argument('query', help='Tema a investigar')
    parser.add_argument('--max', type=int, default=4,
                        help='Máximo de resultados por fuente (default: 4)')
    parser.add_argument('--sin-reddit', action='store_true',
                        help='Omitir búsqueda en Reddit')
    parser.add_argument('--sin-transcripts', action='store_true',
                        help='No descargar transcripts de YouTube')
    args = parser.parse_args()

    query = args.query

    # ── Cabecera ──
    print(f"\n{C.CYAN}{C.BOLD}{'═'*60}")
    print(f"  🔬 INVESTIGACIÓN: {query}")
    print(f"{'═'*60}{C.RESET}")
    print(f"   {C.GRAY}Tasca Barea SLL — {datetime.now().strftime('%Y-%m-%d %H:%M')}{C.RESET}")

    # ── Paso 1: Búsqueda ──
    banner("PASO 1 — Buscando fuentes", C.CYAN)
    fuentes = []
    fuentes += search_youtube(query, max_results=args.max)
    fuentes += search_web(query, max_results=args.max)
    if not args.sin_reddit:
        fuentes += search_reddit(query, max_results=3)

    if not fuentes:
        err("No se encontraron fuentes. Prueba con otros términos.")
        sys.exit(1)

    # ── Paso 2: Transcripts ──
    if not args.sin_transcripts:
        banner("PASO 2 — Descargando transcripts YouTube", C.CYAN)
        yt_fuentes = [f for f in fuentes if f['tipo'] == 'youtube']
        for f in yt_fuentes:
            vid_id = f.get('video_id', '')
            step("⬇️", f"Transcript: {textwrap.shorten(f['titulo'], 50, placeholder='...')}")
            t = get_transcript(vid_id)
            if t:
                f['transcript'] = t
                ok(f"Obtenido ({len(t.split())} palabras)")
            else:
                warn("No disponible — usando snippet")
            time.sleep(0.5)  # cortesía

    # ── Paso 3: Scoring ──
    banner("PASO 3 — Evaluando fiabilidad", C.CYAN)
    for f in fuentes:
        f['fiabilidad'] = puntuar_fuente(f)
    fuentes.sort(key=lambda x: x['fiabilidad'], reverse=True)
    ok("Fuentes ordenadas por fiabilidad")

    # ── Paso 4: Mostrar ──
    banner("PASO 4 — RESULTADOS", C.GREEN)
    mostrar_fuentes(fuentes)

    # ── Paso 5: Resumen ──
    banner("PASO 5 — Generando resumen consolidado", C.CYAN)
    resumen = generar_resumen(query, fuentes)
    print(f"\n{C.GRAY}{'─'*60}{C.RESET}")
    # Mostrar preview del resumen (primeras 30 líneas)
    preview_lines = resumen.split('\n')[:30]
    print('\n'.join(f"   {l}" for l in preview_lines))
    if len(resumen.split('\n')) > 30:
        print(f"   {C.GRAY}... (ver archivo completo para el resto){C.RESET}")
    print(f"{C.GRAY}{'─'*60}{C.RESET}")

    # ── Paso 6: Guardar ──
    banner("PASO 6 — Guardando notas", C.CYAN)
    guardar_notas(resumen)

    # ── Paso 7: Decisión NotebookLM ──
    banner("PASO 7 — NotebookLM", C.YELLOW)
    print(f"\n   Se encontraron {C.BOLD}{len(fuentes)} fuentes{C.RESET}.")

    # Mostrar fuentes con fiabilidad para que el usuario decida
    fiables   = [f for f in fuentes if f.get('fiabilidad', 0) >= 2]
    dudosas   = [f for f in fuentes if f.get('fiabilidad', 0) < 2]

    if fiables:
        print(f"\n   {C.GREEN}Fuentes fiables ({len(fiables)}):{C.RESET}")
        for f in fiables:
            print(f"   {C.GREEN}  ✓{C.RESET} [{estrellas(f['fiabilidad'])}] {textwrap.shorten(f['titulo'], 55, placeholder='...')}")
    if dudosas:
        print(f"\n   {C.YELLOW}Fuentes dudosas ({len(dudosas)}):{C.RESET}")
        for f in dudosas:
            print(f"   {C.YELLOW}  ?{C.RESET} [{estrellas(f['fiabilidad'])}] {textwrap.shorten(f['titulo'], 55, placeholder='...')}")

    respuesta = ask(
        f"¿Enviar las {len(fiables)} fuentes fiables a NotebookLM? "
        f"[s=solo fiables / t=todas / n=no]: "
    ).lower()

    if respuesta in ('s', 'si', 'sí', 'y', 'yes'):
        enviar_notebooklm(fiables)
    elif respuesta == 't':
        enviar_notebooklm(fuentes)
    else:
        step("⏭️", "NotebookLM omitido.", C.GRAY)

    # ── Fin ──
    print(f"\n{C.GREEN}{C.BOLD}{'═'*60}")
    print(f"  ✅ INVESTIGACIÓN COMPLETADA")
    print(f"     Notas: {NOTES_FILE}")
    print(f"{'═'*60}{C.RESET}\n")


if __name__ == '__main__':
    main()

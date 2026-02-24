# tools/fix_patterns.py
from pathlib import Path
import re
import sys

# Uso: python tools/fix_patterns.py patterns
root = Path(sys.argv[1] if len(sys.argv) > 1 else "patterns")

# patrón: línea que empieza con espacios, luego "regex:", luego lo que sea
RX = re.compile(r'^(\s*regex:\s*)(.+?)\s*$', re.UNICODE)

def needs_quotes(s: str) -> bool:
    s = s.strip()
    # ya está entre comillas simples o dobles
    if (len(s) >= 2) and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        return False
    # si contiene : o \ o []{}()|+?*^$ o espacios -> mejor comillas
    return any(c in s for c in r':\[]{}()|+?*^$\ ') or '\\' in s

changed = 0
for yml in sorted(root.glob("*.yml")):
    text = yml.read_text(encoding="utf-8").splitlines()
    out = []
    file_changed = False
    for line in text:
        m = RX.match(line)
        if m:
            prefix, value = m.groups()
            v = value.strip()
            if needs_quotes(v):
                # si venía con comillas dobles, pásalo a comillas simples sin tocar las barras
                if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                # escapar comillas simples internas duplicándolas (YAML)
                v = v.replace("'", "''")
                line = f"{prefix}'{v}'"
                file_changed = True
        out.append(line)
    if file_changed:
        yml.write_text("\n".join(out) + "\n", encoding="utf-8")
        changed += 1
        print(f"[fix] {yml}")
print(f"\nHe modificado {changed} archivo(s).")

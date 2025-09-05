#!/usr/bin/env python3
import re
from pathlib import Path

ROOTS = ["app"]  # podés agregar más carpetas si hace falta

# Patrones que vamos a reemplazar:
# - default=lambda: datetime.now(timezone.utc)
# - default=lambda: datetime.now(tz=timezone.utc)
# - default = datetime.now(timezone.utc)
# - default = datetime.now(tz=timezone.utc)
# - onupdate=... (mismos casos)
RE_NOW_TZ = re.compile(
    r"""
    (                               # grupo 1: clave (default|onupdate) y '='
      (?:default|onupdate)\s*=\s*
    )
    (?:lambda:\s*)?                 # opcional 'lambda:'
    datetime\.now                   # 'datetime.now'
    \s*\(\s*                        # '(' con espacios opcionales
    (?:tz\s*=\s*)?timezone\.utc     # 'timezone.utc' con o sin 'tz='
    \s*\)                           # ')'
    """,
    re.VERBOSE,
)

# También contemplamos datetime.now( timezone.utc ) con espacios raros
RE_NOW_TZ_LOOSE = re.compile(
    r"""
    (                               # grupo 1: clave (default|onupdate) y '='
      (?:default|onupdate)\s*=\s*
    )
    (?:lambda:\s*)?                 
    datetime\.now                   
    \s*\(\s*
    (?:tz\s*=\s*)?timezone\s*\.\s*utc
    \s*\)
    """,
    re.VERBOSE,
)

# Limpieza de imports: 'from datetime import datetime, timezone' -> 'from datetime import datetime'
RE_IMPORT_DT_TZ = re.compile(
    r"from\s+datetime\s+import\s+datetime\s*,\s*timezone"
)

def fix_file(path: Path) -> bool:
    original = text = path.read_text(encoding="utf-8")

    # Reemplazos de default/onupdate con timezone.utc -> datetime.utcnow
    text = RE_NOW_TZ.sub(r"\1datetime.utcnow", text)
    text = RE_NOW_TZ_LOOSE.sub(r"\1datetime.utcnow", text)

    # Normalizamos casos tipo 'default = lambda: datetime.utcnow' -> 'default=datetime.utcnow'
    text = re.sub(
        r"((?:default|onupdate)\s*=\s*)lambda:\s*datetime\.utcnow",
        r"\1datetime.utcnow",
        text,
    )

    # Limpieza de import timezone si quedó de más
    text = RE_IMPORT_DT_TZ.sub("from datetime import datetime", text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False

def main():
    changed = 0
    scanned = 0
    for root in ROOTS:
        for p in Path(root).rglob("*.py"):
            # evitamos virtualenvs, caches, etc.
            if any(x in p.parts for x in (".venv", "venv", "__pycache__", "site-packages")):
                continue
            scanned += 1
            if fix_file(p):
                changed += 1
                print(f"[MOD] {p}")
    print(f"\nAnalizados: {scanned} | Modificados: {changed}")

if __name__ == "__main__":
    main()
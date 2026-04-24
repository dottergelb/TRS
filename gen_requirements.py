from __future__ import annotations

import ast
import sys
from pathlib import Path
from importlib import metadata

EXCLUDE_DIRS = {
    ".venv", "venv", "env", "__pycache__", "node_modules",
    "static", "media", "migrations"
}

                                                    
MODULE_TO_DIST = {
    "rest_framework": "djangorestframework",
    "corsheaders": "django-cors-headers",
    "PIL": "Pillow",
    "cv2": "opencv-python",
}

def iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        yield p

def local_top_level_names(root: Path) -> set[str]:
    names = set()
    for p in root.iterdir():
        if p.is_dir() and (p / "__init__.py").exists():
            names.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            names.add(p.stem)
    return names

def collect_import_modules(root: Path) -> set[str]:
    mods = set()
    for f in iter_py_files(root):
        try:
            src = f.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(src, filename=str(f))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    mods.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                if node.module:
                    mods.add(node.module.split(".")[0])
    return mods

def main():
    root = Path(__file__).resolve().parent
    stdlib = getattr(sys, "stdlib_module_names", set())
    locals_ = local_top_level_names(root)

    imported = collect_import_modules(root)
    imported = {m for m in imported if m and m not in stdlib and m not in locals_}

    pkg_map = metadata.packages_distributions()
    dists = set()

    for m in sorted(imported):
        if m in MODULE_TO_DIST:
            dists.add(MODULE_TO_DIST[m])
            continue
        if m in pkg_map and pkg_map[m]:
            dists.add(pkg_map[m][0])

    lines = []
    for dist in sorted(dists, key=str.lower):
        try:
            ver = metadata.version(dist)
            lines.append(f"{dist}=={ver}")
        except Exception:
            lines.append(dist)

    out = root / "requirements.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: {out} ({len(lines)} packages)")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QGIS APP-6(D) Plugin Packager
=============================
Crea un archivio ZIP pronto per la distribuzione / installazione nel
plugin manager di QGIS / QGIS 3.

Uso
---
    python package_plugin.py              # → qgis_app6d-0.1.0.zip
    python package_plugin.py --output dist/myplugin.zip
    python package_plugin.py --bump 0.2.0 # aggiorna metadata.txt e crea lo zip

Lo ZIP contiene la cartella radice ``qgis_app6d/`` con tutti i file
necessari. La cartella ``resources/`` non viene inclusa.

    qgis_app6d/
    ├── __init__.py
    ├── metadata.txt
    ├── plugin.py
    ├── logger.py
    ├── core/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── sidc.py
    │   └── utils.py
    ├── gui/
    │   ├── __init__.py
    │   ├── canvas_drop_filter.py
    │   ├── catalog_dock.py
    │   ├── layer_manager_dock.py
    │   ├── map_tool.py
    │   ├── mil_renderer.py
    │   ├── orbat_dialogs.py
    │   ├── orbat_dock.py
    │   ├── project_io.py
    │   ├── settings_dock.py
    │   ├── symbol_editor_dock.py
    │   ├── symbol_layer.py
    │   ├── symbol_move_tool.py
    │   └── temporal.py
    ├── server/
    │   ├── __init__.py
    │   └── symbol_server.py
    └── symbology/
        ├── __init__.py
        ├── catalog_data.py
        ├── frames.py
        ├── icons.py
        ├── milsymbol_engine.py
        ├── modifiers.py
        └── renderer.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ── Costanti ──────────────────────────────────────────────────────────

PLUGIN_DIR_NAME = "qgis_app6d"
METADATA_FILE = "metadata.txt"

# Pattern di file/cartelle da escludere dallo ZIP
EXCLUDE_PATTERNS: list[str] = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".gitignore",
    ".vscode",
    ".idea",
    "*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    "*.orig",
    "*.bak",
    "*.swp",
    "Thumbs.db",
    ".DS_Store",
]

# Estensioni binarie che NON devono mai finire nello ZIP del plugin
EXCLUDE_EXTENSIONS: set[str] = {".pdf", ".docx", ".xlsx"}


# ── Utility ───────────────────────────────────────────────────────────


def _should_exclude(rel_path: str) -> bool:
    """Restituisce True se *rel_path* corrisponde ai pattern di esclusione."""
    parts = Path(rel_path).parts
    name = Path(rel_path).name
    suffix = Path(rel_path).suffix.lower()

    if suffix in EXCLUDE_EXTENSIONS:
        return True

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            # Confronto suffisso (es. *.pyc)
            if name.endswith(pattern[1:]):
                return True
        else:
            # Confronto nome esatto su qualsiasi componente
            if pattern in parts:
                return True
    return False


def _read_metadata_version(metadata_path: Path) -> str:
    """Legge la versione corrente da metadata.txt."""
    text = metadata_path.read_text(encoding="utf-8")
    match = re.search(r"^version\s*=\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"Campo 'version' non trovato in {metadata_path}")
    return match.group(1).strip()


def _bump_version(metadata_path: Path, new_version: str) -> None:
    """Aggiorna il campo *version* in metadata.txt."""
    text = metadata_path.read_text(encoding="utf-8")
    text = re.sub(
        r"^version\s*=\s*.+$",
        f"version={new_version}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    metadata_path.write_text(text, encoding="utf-8")
    print(f"  ✔ metadata.txt version aggiornata a {new_version}")


def _collect_files(root: Path) -> list[tuple[Path, str]]:
    """Raccoglie tutti i file da includere nello ZIP.

    Restituisce coppie (percorso_assoluto, arcname_dentro_lo_zip).
    Il livello radice nello ZIP è ``qgis_app6d/``.
    """
    files: list[tuple[Path, str]] = []

    # 1) File del package Python (qgis_app6d/)
    plugin_dir = root / PLUGIN_DIR_NAME
    if not plugin_dir.is_dir():
        raise FileNotFoundError(f"Cartella plugin non trovata: {plugin_dir}")

    for dirpath, _dirnames, filenames in os.walk(plugin_dir):
        for fn in sorted(filenames):
            abs_path = Path(dirpath) / fn
            rel = abs_path.relative_to(root)
            if _should_exclude(str(rel)):
                continue
            # arcname = qgis_app6d/…
            files.append((abs_path, str(rel)))

    # 2) File radice: LICENSE e README.md inclusi dentro qgis_app6d/
    for extra in ("LICENSE", "README.md"):
        extra_path = root / extra
        if extra_path.is_file():
            arc = str(Path(PLUGIN_DIR_NAME) / extra)
            files.append((extra_path, arc))

    # 3) La cartella resources/ non viene inclusa nel pacchetto ZIP.
    return files


def _create_zip(files: list[tuple[Path, str]], output: Path) -> None:
    """Scrive lo ZIP con compressione deflate."""
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arcname in files:
            zf.write(abs_path, arcname)

    size_kb = output.stat().st_size / 1024
    print(f"  ✔ {len(files)} file archiviati → {output}  ({size_kb:.1f} KB)")


# ── Main ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pacchettizza il plugin QGIS APP-6(D) in un file ZIP.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Percorso del file ZIP di output (default: qgis_app6d-<version>.zip)",
    )
    parser.add_argument(
        "-b",
        "--bump",
        type=str,
        default=None,
        metavar="VERSION",
        help="Aggiorna metadata.txt alla versione indicata prima di creare lo ZIP.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra i file che sarebbero inclusi senza creare lo ZIP.",
    )
    args = parser.parse_args()

    # Determina la cartella radice del progetto (dove si trova questo script)
    root = Path(__file__).resolve().parent

    metadata_path = root / PLUGIN_DIR_NAME / METADATA_FILE
    if not metadata_path.exists():
        print(f"ERRORE: {metadata_path} non trovato", file=sys.stderr)
        sys.exit(1)

    # Bump di versione (opzionale)
    if args.bump:
        _bump_version(metadata_path, args.bump)

    version = _read_metadata_version(metadata_path)
    print(f"Plugin: {PLUGIN_DIR_NAME}  v{version}")
    print(f"Data:   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # Raccolta file
    files = _collect_files(root)
    if not files:
        print("ERRORE: nessun file raccolto!", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("File che sarebbero inclusi nello ZIP:")
        for _, arcname in files:
            print(f"  {arcname}")
        print(f"\nTotale: {len(files)} file")
        return

    # Nome output
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = root / f"{PLUGIN_DIR_NAME}-{version}.zip"

    _create_zip(files, out_path)

    print()
    print("Per installare in QGIS:")
    print("  1. Apri Plugin Manager → Installa da ZIP")
    print(f"  2. Seleziona: {out_path.name}")
    print(f"  3. Oppure copia la cartella '{PLUGIN_DIR_NAME}/' in:")
    print("     ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/")


if __name__ == "__main__":
    main()


# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.7] – 2026-05-18

### Changed
- `CatalogEntry` dataclass: removed `name_de`, `name_fr`, `name_it` fields; only the English `name` is retained.
- All catalog entry instantiations updated accordingly (no positional language arguments).

### Added
- **Land Unit** symbol set: new **UAS / Drone** category with four entries:
  - `Unmanned Aerial Vehicle (UAS)` – generic
  - `UAS – Attack` (M1=03)
  - `UAS – Reconnaissance` (M1=18)
  - `UAS – Logistics / Cargo` (M1=69)

---

## [0.1.6] – 2026-05-14

### Added
- Layer Manager dock: **Import layers** panel with two buttons:
  - *Import layers from APP-6D JSON file…* — browse any path on the filesystem.
  - *Import from data folder…* — opens directly in the MilSymb data directory (convenient for bundled or previously saved files).
  - Imported layers are appended to the current project; duplicate names get an automatic numeric suffix (`Layer (2)`, …).
  - Supports all three JSON formats: multi-layer (`layers`), single-layer (`layer`), and legacy flat (`symbols`).
- `SymbolLayerManager.import_layer()` — new public method that appends a pre-populated `SymbolLayer` to the project and registers the backing `QgsVectorLayer` on the QGIS canvas.

### Changed
- Layer Manager dock: export and import file dialogs now use the `*.app6d.json` extension (replacing the generic `*.json`) to avoid confusion with other JSON files; KMZ dialogs unchanged.
- Symbol Editor dock: **Text Modifiers** section is now a stable collapsible panel (closed by default).
  - Replaced `QGroupBox.setCheckable()` — which disrupted dock geometry when anchored — with a `QToolButton` header (`▶`/`▼`) + a hidden `QWidget` body.
  - Removed all `adjustSize()` calls from `edit_symbol`, `load_from_catalog`, and `_toggle_text_modifiers`; the surrounding `QScrollArea` handles height changes without disturbing the dock layout.

---

### Fixed
- `milsymbol_engine.py`: `SyntaxError` in generated JS due to missing `f` prefix on last two lines of `as_svg` JS template (`}}` was not being interpreted as escaped braces, producing malformed JS).

### Added
- Layer Manager dock: **Export all layers as KMZ** and **Export current layer as KMZ** buttons.
  - KMZ = ZIP archive containing `doc.kml` + `icons/<sidc>.png` for each placed symbol.
  - Icons rendered via `milsymbol_engine` → `QSvgRenderer` → `QImage` → PNG.
  - KML built with plain string concatenation + `html.escape()` (no `xml.etree.ElementTree.register_namespace`).

---

## [0.1.5] (previous – reverted) – 2026-05-14

### Reverted
- KMZ export feature (introduced in this version) caused a symbol rendering
  regression in the catalog and on the map canvas.  The feature has been
  reverted pending root-cause investigation and a clean reimplementation.

## [0.1.4] – 2026-05-13

### Changed
- Code style: binary operators moved to start of continuation lines (W503/W504 fix)
  across `plugin.py`, `catalog_dock.py`, `symbol_editor_dock.py`, `catalog_data.py`,
  `orbat_dock.py`, `symbol_move_tool.py`
- Removed unnecessary `f`-prefix from 43 string literals without interpolation
  (F541) across 11 files
- `metadata.txt`: corrected `license` identifier to `GPL-2`; fixed typo
  `buymeacoffe` → `buymeacoffee`; added required `changelog` field; added
  `server=False` / `hasServerInterface=False`; bumped version to 0.1.4;
  noted bundled milsymbol.js in `about` field (no external Python deps)
- GitHub Actions lint workflow: restricted to manual trigger only (`workflow_dispatch`)

## [0.1.3] – 2026-05-13

### Changed
- Full PEP 8 / Flake8 style cleanup across all plugin modules (blank line at EOF,
  inline comment spacing, comma whitespace, ambiguous variable names E741)
- Bandit security scan: fixed W291 trailing whitespace, E303 excess blank lines;
  `subprocess` import annotated with `# noqa: B404` (used only for OS log viewer)
- `plugin.py`: plugin constants (`name`, `version`, `author`, `repository`) now
  read dynamically from `metadata.txt` – no more hardcoded strings
- `package_plugin.py`: `resources/` folder excluded from distributed ZIP

## [0.1.2] – 2026-05-13

### Fixed
- `mil_renderer.py`: `hashlib.md5()` call now passes `usedforsecurity=False`
  to satisfy Bandit B324 check
- `models.py`: renamed ambiguous loop variable `l` → `layer` (Flake8 E741)

## [0.1.1] – 2026-05-13

### Removed
- "Swiss Conventional" symbol category removed from the APP-6(D) catalog

## [0.1.0] – 2026-05-12

### Added
- Initial public release as a standalone **QGIS 3.16+** plugin
- APP-6(D) Symbol Catalog dock with full-text search and drag-and-drop onto map canvas
- Symbol Editor dock: 20-character SIDC builder, text modifiers (designation, higher formation, DTG, …)
- ORBAT Manager: hierarchical Order of Battle editor, import/export to `.orbat.json`
- Built-in HTTP symbol rendering server powered by [milsymbol.js](https://github.com/spatialillusions/milsymbol)
- Layer Manager dock: named symbol layers, per-layer JSON export
- Temporal filtering integrated with the QGIS Temporal Controller

[Unreleased]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.7...HEAD
[0.1.7]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/intelligeo/qgis-app6d-plugin/releases/tag/v0.1.0

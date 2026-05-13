# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/intelligeo/qgis-app6d-plugin/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/intelligeo/qgis-app6d-plugin/releases/tag/v0.1.0

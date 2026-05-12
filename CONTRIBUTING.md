# Contributing to QGIS APP-6(D)

Thank you for considering a contribution! Please read this guide before opening issues or pull requests.

## Reporting bugs

1. Search [existing issues](https://github.com/intelligeo/qgis-app6d-plugin/issues) first.
2. Open a new issue using the **Bug report** template.
3. Include: QGIS version, OS, steps to reproduce, expected vs actual behaviour, and the plugin log file (`Plugins → APP-6(D) → Open log file`).

## Requesting features

Open a **Feature request** issue describing the use case and the expected behaviour.

## Submitting pull requests

### Setup

```bash
git clone https://github.com/intelligeo/qgis-app6d-plugin.git
cd qgis-app6d-plugin
```

No extra Python packages are required for the plugin itself.  
For linting / testing install the dev tools:

```bash
pip install ruff pytest
```

### Coding style

- Follow [PEP 8](https://peps.python.org/pep-0008/); line length ≤ 120 characters.
- Use `ruff check .` before committing.
- All public methods must have a docstring.
- Prefer explicit imports over wildcard (`from module import *`).
- Use `qgis.PyQt` wrappers, not raw `PyQt5` / `PyQt6` imports.

### Branch naming

| Type | Pattern |
|---|---|
| Feature | `feat/short-description` |
| Bug fix | `fix/short-description` |
| Chore / docs | `chore/short-description` |

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add ORBAT export to GeoJSON
fix: correct temporal filter for symbols without end date
docs: update installation instructions
```

### Pull request checklist

- [ ] Code follows the style guidelines above
- [ ] `ruff check .` passes with no errors
- [ ] Existing behaviour is not broken (test manually in QGIS)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Branch is up-to-date with `main`

## License

By contributing you agree that your contributions will be licensed under the [GPL-2.0 License](LICENSE).

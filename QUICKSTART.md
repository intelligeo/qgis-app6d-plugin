# Quick Start Guide — QGIS APP-6(D)

> Get up and running in 5 minutes.

---

## 1 — Install the plugin

1. Download `qgis_app6d-<version>.zip` from the [Releases page](https://github.com/intelligeo/qgis-app6d-plugin/releases).
2. Open QGIS → **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the ZIP file and click **Install Plugin**.
4. In the **Installed** tab make sure **QGIS APP-6(D)** is checked.

A new **APP-6(D) toolbar** appears at the top of the QGIS window and a **Plugins → APP-6(&D)** menu entry is added.

---

## 2 — Load the symbol catalog

Click the **Symbol Catalog** button (flag icon) in the toolbar, or go to **Plugins → APP-6(&D) → Symbol Catalog**.

The dock opens on the right side. You can:

- **Search** by name, SIDC or keyword (e.g. "infantry", "armor", "air defense")
- **Filter** by Symbol Set using the drop-down at the top
- **Preview** each symbol in the list

---

## 3 — Place your first symbol

1. Find a symbol in the catalog (e.g. type "infantry" in the search box).
2. **Drag and drop** it onto the map canvas.
3. A new **symbol layer** is created automatically in the QGIS layer panel.
4. The symbol is placed at the drop location in **WGS-84 (EPSG:4326)**.

> **Tip:** You can drag multiple symbols in sequence — each one is added to the active layer.

---

## 4 — Edit a symbol

**Double-click** any symbol on the map canvas to open the **Symbol Editor** dock.

From the editor you can change:

| Field | Description |
|---|---|
| SIDC | 20-character APP-6(D) code — edit manually or use the picker |
| Designation | Short unit label shown on the map (modifier T) |
| Higher Formation | Superior unit name (modifier M) |
| Comment | Free-text annotation |
| Temporal extent | Start / End DTG for temporal filtering |

Click **Apply** to update the symbol on the map.

---

## 5 — Move a symbol

1. Click the **Move Symbol** tool in the toolbar (arrow icon).
2. Click and drag any symbol to a new position.
3. Click the **Select** tool (or press `Esc`) to exit move mode.

---

## 6 — Manage layers

Click **Layer Manager** in the toolbar to open the layer management dock.

- **Add layer** (`+`) — create a new named symbol layer
- **Rename** (`✎`) — rename the selected layer
- **Delete** (`−`) — remove a layer and all its symbols
- **Export** — save all layers or the current layer as a `.json` file

---

## 7 — Build an Order of Battle (ORBAT)

Click **ORBAT Manager** in the toolbar.

1. Click **New ORBAT** or import an existing `.orbat.json` file.
2. Use the **Add Unit** button to create the top-level HQ unit.
3. Select a unit and click **Add Child** to add subordinate units.
4. Double-click a unit to edit its name, SIDC, and temporal extent.
5. Click **Place on Map** to link a unit to a map symbol.
6. Click **Export** to save the ORBAT as `.orbat.json`.

---

## 8 — Temporal filtering

1. Set **Start DTG** and **End DTG** in the Symbol Editor for each symbol you want to filter.
2. Open the QGIS Temporal Controller: **View → Panels → Temporal Controller**.
3. Enable the controller and set an animation range.
4. As you scrub through time, the plugin automatically shows/hides symbols based on their temporal extent.

---

## 9 — Settings

Click **Settings** in the toolbar to adjust:

- **Symbol size** — rendered SVG size in pixels
- **Text modifiers** — show/hide designation and higher formation labels on the map

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Esc` | Exit current map tool |
| `Del` | Delete selected symbol (when catalog dock is focused) |
| `F5` | Refresh all symbol layers |

---

## Getting help

- **Issues / bug reports:** [GitHub Issues](https://github.com/intelligeo/qgis-app6d-plugin/issues)
- **Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md)
- **Full changelog:** see [CHANGELOG.md](CHANGELOG.md)

# -*- coding: utf-8 -*-
"""
Layer management dock widget to add, rename, delete symbol layers and
export data per-layer or as a single multi-layer JSON file.

Integrated into the main plugin panel as a collapsible group at the top
of the catalog dock, or as a standalone dock accessible from the ribbon.
"""

from __future__ import annotations

import html
import io
import json
import os
import zipfile
from typing import List, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import MilSymbProject, SymbolLayer
from ..core.utils import milsymb_data_dir
from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.layer_manager_dock")


class LayerManagerDockWidget(QDockWidget):
    """Dock for managing multiple MilSymb symbol layers.

    Features
    --------
    * Layer selector (QComboBox) to pick the active layer
    * Add / Rename / Delete buttons
    * Export panel to single multi-layer JSON **or** one file per layer

    Signals
    -------
    active_layer_changed(str)
        Emitted with the ``SymbolLayer.id`` when the user picks a
        different layer in the combo box.
    """

    active_layer_changed = pyqtSignal(str)

    def __init__(self, iface=None, action=None, parent=None):
        super().__init__("Layer Manager", parent)
        self._iface = iface
        self._action = action

        self._project_data: Optional[MilSymbProject] = None
        self._layer_manager = None  # set externally

        self._build_ui()

    # ------------------------------------------------------------------
    # Dock lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # External bindings
    # ------------------------------------------------------------------

    def set_project_data(self, proj: MilSymbProject) -> None:
        self._project_data = proj
        self._refresh_combo()

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr
        if mgr is not None:
            mgr.layer_added.connect(self._on_layer_added)
            mgr.layer_removed.connect(self._on_layer_removed)
            mgr.layer_renamed.connect(self._on_layer_renamed)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        root = QVBoxLayout(container)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ---- Layer selector group ----
        grp = QGroupBox("Symbol Layers")
        grp_layout = QVBoxLayout(grp)

        # Combo + buttons row
        sel_row = QHBoxLayout()
        self._layer_combo = QComboBox()
        self._layer_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._layer_combo.currentIndexChanged.connect(self._on_combo_changed)
        sel_row.addWidget(self._layer_combo, 1)

        self._add_btn = QToolButton()
        self._add_btn.setText("+")
        self._add_btn.setToolTip("Add layer")
        self._add_btn.clicked.connect(self._on_add)
        sel_row.addWidget(self._add_btn)

        self._rename_btn = QToolButton()
        self._rename_btn.setText("Rename")
        self._rename_btn.setToolTip("Rename layer")
        self._rename_btn.clicked.connect(self._on_rename)
        sel_row.addWidget(self._rename_btn)

        self._del_btn = QToolButton()
        self._del_btn.setText("-")
        self._del_btn.setToolTip("Delete layer")
        self._del_btn.clicked.connect(self._on_delete)
        sel_row.addWidget(self._del_btn)

        grp_layout.addLayout(sel_row)

        # Info label
        self._info_lbl = QLabel("")
        self._info_lbl.setWordWrap(True)
        grp_layout.addWidget(self._info_lbl)

        root.addWidget(grp)

        # ---- Export group ----
        exp_grp = QGroupBox("Export")
        exp_layout = QVBoxLayout(exp_grp)

        row1 = QHBoxLayout()
        self._export_all_btn = QPushButton("Export all layers (single file)")
        self._export_all_btn.clicked.connect(self._on_export_all)
        row1.addWidget(self._export_all_btn)
        exp_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self._export_each_btn = QPushButton("Export each layer separately")
        self._export_each_btn.clicked.connect(self._on_export_each)
        row2.addWidget(self._export_each_btn)
        exp_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self._export_current_btn = QPushButton("Export current layer")
        self._export_current_btn.clicked.connect(self._on_export_current)
        row3.addWidget(self._export_current_btn)
        exp_layout.addLayout(row3)

        row4 = QHBoxLayout()
        self._export_all_kmz_btn = QPushButton("Export all layers as KMZ")
        self._export_all_kmz_btn.clicked.connect(self._on_export_all_kmz)
        row4.addWidget(self._export_all_kmz_btn)
        exp_layout.addLayout(row4)

        row5 = QHBoxLayout()
        self._export_current_kmz_btn = QPushButton("Export current layer as KMZ")
        self._export_current_kmz_btn.clicked.connect(self._on_export_current_kmz)
        row5.addWidget(self._export_current_kmz_btn)
        exp_layout.addLayout(row5)

        root.addWidget(exp_grp)

        # ---- Import group ----
        imp_grp = QGroupBox("Import")
        imp_layout = QVBoxLayout(imp_grp)

        imp_row1 = QHBoxLayout()
        self._import_file_btn = QPushButton("Import layers from JSON file…")
        self._import_file_btn.setToolTip(
            "Import symbol layers from a MilSymb JSON file and append them "
            "to the current project."
        )
        self._import_file_btn.clicked.connect(self._on_import_from_file)
        imp_row1.addWidget(self._import_file_btn)
        imp_layout.addLayout(imp_row1)

        imp_row2 = QHBoxLayout()
        self._import_folder_btn = QPushButton("Import from data folder…")
        self._import_folder_btn.setToolTip(
            "Browse and pick a JSON file from the MilSymb data folder "
            "(bundled or previously saved files)."
        )
        self._import_folder_btn.clicked.connect(self._on_import_from_data_folder)
        imp_row2.addWidget(self._import_folder_btn)
        imp_layout.addLayout(imp_row2)

        root.addWidget(imp_grp)

        root.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Combo helpers
    # ------------------------------------------------------------------

    def _refresh_combo(self) -> None:
        """Rebuild the combo box from the project layers list."""
        self._layer_combo.blockSignals(True)
        self._layer_combo.clear()
        if self._project_data is None:
            self._layer_combo.blockSignals(False)
            return
        active_id = None
        if self._layer_manager is not None:
            active_id = self._layer_manager.active_layer_id
        sel_idx = 0
        for i, sl in enumerate(self._project_data.layers):
            label = f"{sl.name}  ({len(sl.symbols)} sym)"
            self._layer_combo.addItem(label, sl.id)
            if sl.id == active_id:
                sel_idx = i
        self._layer_combo.setCurrentIndex(sel_idx)
        self._layer_combo.blockSignals(False)
        self._update_info()

    def _current_layer_id(self) -> str | None:
        idx = self._layer_combo.currentIndex()
        if idx < 0:
            return None
        return self._layer_combo.itemData(idx)

    def _update_info(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            self._info_lbl.setText("")
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            self._info_lbl.setText("")
            return
        self._info_lbl.setText(f"Symbols: {len(sl.symbols)}")

    # ------------------------------------------------------------------
    # Slots to combo
    # ------------------------------------------------------------------

    def _on_combo_changed(self, idx: int) -> None:
        lid = self._current_layer_id()
        if lid is None:
            return
        if self._layer_manager is not None:
            self._layer_manager.set_active_layer(lid)
        self.active_layer_changed.emit(lid)
        self._update_info()

    # ------------------------------------------------------------------
    # Slots to add / rename / delete
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Layer", "Layer name:", text="New Layer",
        )
        if not ok or not name.strip():
            return
        if self._layer_manager is not None:
            sl = self._layer_manager.add_layer(name.strip())
            self._layer_manager.set_active_layer(sl.id)
        elif self._project_data is not None:
            self._project_data.add_layer(name.strip())
        self._refresh_combo()

    def _on_rename(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Layer", "New name:", text=sl.name,
        )
        if not ok or not new_name.strip():
            return
        if self._layer_manager is not None:
            self._layer_manager.rename_layer(lid, new_name.strip())
        else:
            self._project_data.rename_layer(lid, new_name.strip())
        self._refresh_combo()

    def _on_delete(self) -> None:
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        if len(self._project_data.layers) <= 1:
            QMessageBox.information(
                self, "Cannot delete",
                "At least one symbol layer must exist.",
            )
            return
        sl = self._project_data.layer_by_id(lid)
        name = sl.name if sl else "?"
        btn = QMessageBox.question(
            self, "Delete Layer",
            f"Delete layer \"{name}\" and all its {len(sl.symbols)} symbol(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if btn != QMessageBox.Yes:
            return
        if self._layer_manager is not None:
            self._layer_manager.remove_layer(lid)
        else:
            self._project_data.remove_layer(lid)
        self._refresh_combo()

    # ------------------------------------------------------------------
    # Slots to layer_manager signals
    # ------------------------------------------------------------------

    def _on_layer_added(self, _lid: str) -> None:
        self._refresh_combo()

    def _on_layer_removed(self, _lid: str) -> None:
        self._refresh_combo()

    def _on_layer_renamed(self, _lid: str, _name: str) -> None:
        self._refresh_combo()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _import_project(self, imported: MilSymbProject) -> int:
        """Merge *imported* layers into the current project.

        Returns the number of layers actually added.
        Existing layer names get a numeric suffix to avoid duplicates.
        """
        if self._project_data is None:
            return 0

        existing_names = {sl.name for sl in self._project_data.layers}
        added = 0
        first_new_id: str | None = None

        for sl in imported.layers:
            # Resolve name conflict
            name = sl.name
            if name in existing_names:
                base = name
                counter = 2
                while name in existing_names:
                    name = f"{base} ({counter})"
                    counter += 1
                sl.name = name
            existing_names.add(sl.name)

            if self._layer_manager is not None:
                self._layer_manager.import_layer(sl)
            else:
                self._project_data.layers.append(sl)

            if first_new_id is None:
                first_new_id = sl.id
            added += 1

        self._refresh_combo()

        # Switch to the first newly imported layer
        if first_new_id is not None and self._layer_manager is not None:
            self._layer_manager.set_active_layer(first_new_id)

        return added

    def _on_import_from_file(self) -> None:
        """Browse filesystem and import layers from a MilSymb APP-6D JSON file."""
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import layers from APP-6D JSON file",
            default_dir,
            "APP-6D JSON (*.app6d.json);;All files (*)",
        )
        if not path:
            return
        self._import_json_file(path)

    def _on_import_from_data_folder(self) -> None:
        """Browse the MilSymb data folder for APP-6D JSON files to import."""
        data_dir = milsymb_data_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import layers from data folder",
            data_dir,
            "APP-6D JSON (*.app6d.json);;All files (*)",
        )
        if not path:
            return
        self._import_json_file(path)

    def _import_json_file(self, path: str) -> None:
        """Parse *path* as a MilSymb JSON file and merge its layers."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            imported = MilSymbProject.from_json(text)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.critical(self, "Import error",
                                 f"Could not read {os.path.basename(path)}:\n{exc}")
            return

        n_layers = len(imported.layers)
        if n_layers == 0:
            QMessageBox.information(self, "Import", "No layers found in the file.")
            return

        added = self._import_project(imported)
        QMessageBox.information(
            self, "Import complete",
            f"Imported {added} layer(s) from\n{path}",
        )
        LOG.info("Imported %d layer(s) from %s", added, path)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export_all(self) -> None:
        """Export all layers into a single JSON file."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers",
            os.path.join(default_dir, "milsymb_all_layers.app6d.json"),
            "APP-6D JSON (*.app6d.json);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._project_data.to_json())
            n_sym = len(self._project_data.symbols)
            n_lyr = len(self._project_data.layers)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {n_lyr} layer(s) with {n_sym} symbol(s) to\n{path}",
            )
            LOG.info("Exported all layers to %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_each(self) -> None:
        """Export each layer as a separate JSON file into a chosen folder."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        folder = QFileDialog.getExistingDirectory(
            self, "Choose export folder", default_dir,
        )
        if not folder:
            return
        try:
            exported = 0
            for sl in self._project_data.layers:
                safe_name = sl.name.replace(" ", "_").replace("/", "_")
                fname = f"milsymb_layer_{safe_name}.app6d.json"
                path = os.path.join(folder, fname)
                data = self._project_data.layer_to_json(sl.id)
                if data is None:
                    continue
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(data)
                exported += 1
                LOG.info("Exported layer '%s' to %s", sl.name, path)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {exported} layer file(s) to\n{folder}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_current(self) -> None:
        """Export only the currently selected layer."""
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return
        default_dir = milsymb_data_dir()
        safe_name = sl.name.replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export layer \"{sl.name}\"",
            os.path.join(default_dir, f"milsymb_layer_{safe_name}.app6d.json"),
            "APP-6D JSON (*.app6d.json);;All files (*)",
        )
        if not path:
            return
        try:
            data = self._project_data.layer_to_json(lid)
            if data is None:
                QMessageBox.warning(self, "Error", "Layer data not found.")
                return
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(data)
            QMessageBox.information(
                self, "Export complete",
                f"Exported layer \"{sl.name}\" ({len(sl.symbols)} symbols) to\n{path}",
            )
            LOG.info("Exported layer '%s' to %s", sl.name, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
    def _on_export_all_kmz(self) -> None:
        """Export all layers as a single KMZ file with embedded PNG icons."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers as KMZ",
            os.path.join(default_dir, "milsymb_all_layers.kmz"),
            "KMZ file (*.kmz);;All files (*)",
        )
        if not path:
            return
        try:
            self._write_kmz(path, self._project_data.layers)
            n_sym = sum(len(sl.symbols) for sl in self._project_data.layers)
            n_lyr = len(self._project_data.layers)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {n_lyr} layer(s) with {n_sym} symbol(s) to\n{path}",
            )
            LOG.info("Exported all layers as KMZ to %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_current_kmz(self) -> None:
        """Export the currently selected layer as a KMZ file."""
        lid = self._current_layer_id()
        if lid is None or self._project_data is None:
            return
        sl = self._project_data.layer_by_id(lid)
        if sl is None:
            return
        default_dir = milsymb_data_dir()
        safe_name = sl.name.replace(" ", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export layer \"{sl.name}\" as KMZ",
            os.path.join(default_dir, f"milsymb_layer_{safe_name}.kmz"),
            "KMZ file (*.kmz);;All files (*)",
        )
        if not path:
            return
        try:
            self._write_kmz(path, [sl])
            QMessageBox.information(
                self, "Export complete",
                f"Exported layer \"{sl.name}\" ({len(sl.symbols)} symbols) to\n{path}",
            )
            LOG.info("Exported layer '%s' as KMZ to %s", sl.name, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    # ------------------------------------------------------------------
    # KMZ helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sidc_to_png_bytes(sidc: str, size: int = 64) -> Optional[bytes]:
        """Render a symbol SIDC to PNG bytes via milsymbol engine.

        Returns ``None`` if the engine is unavailable or rendering fails.
        """
        try:
            from ..symbology.milsymbol_engine import get_engine
            from qgis.PyQt.QtCore import QByteArray, QBuffer
            from qgis.PyQt.QtGui import QImage, QPainter
            from qgis.PyQt.QtSvg import QSvgRenderer

            engine = get_engine()
            if not engine.is_ready:
                return None
            svg_str = engine.as_svg(sidc, size=size)
            if not svg_str:
                return None

            renderer = QSvgRenderer()
            renderer.load(svg_str.encode("utf-8"))
            if not renderer.isValid():
                return None

            img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
            img.fill(0)  # transparent
            painter = QPainter(img)
            renderer.render(painter)
            painter.end()

            buf = QBuffer()
            buf.open(QBuffer.WriteOnly)
            img.save(buf, "PNG")
            buf.close()
            return bytes(buf.data())
        except Exception:
            return None

    @staticmethod
    def _build_kml(layers, icon_files: dict) -> str:
        """Build a KML string for the given layers.

        Parameters
        ----------
        layers:
            Iterable of ``SymbolLayer`` objects.
        icon_files : dict
            Mapping ``sidc -> 'icons/<sidc>.png'`` for icons that were
            successfully rendered.  Used to set ``<href>`` in KML.
        """
        lines: List[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
        lines.append('  <Document>')

        # One Folder per layer
        for sl in layers:
            lines.append('    <Folder>')
            lines.append(f'      <name>{html.escape(sl.name)}</name>')

            for sym in sl.symbols:
                if sym.longitude == 0.0 and sym.latitude == 0.0:
                    continue  # skip unplaced symbols

                icon_href = icon_files.get(sym.sidc, "")

                lines.append('      <Placemark>')
                label = sym.designation or sym.sidc
                lines.append(f'        <name>{html.escape(label)}</name>')

                # Build description from available amplifiers
                desc_parts: List[str] = []
                if sym.sidc:
                    desc_parts.append(f"SIDC: {html.escape(sym.sidc)}")
                if sym.higher_formation:
                    desc_parts.append(f"Higher: {html.escape(sym.higher_formation)}")
                if sym.comment:
                    desc_parts.append(html.escape(sym.comment))
                if desc_parts:
                    lines.append(
                        f'        <description>{" | ".join(desc_parts)}</description>'
                    )

                if icon_href:
                    lines.append('        <Style>')
                    lines.append('          <IconStyle>')
                    lines.append(f'            <Icon><href>{html.escape(icon_href)}</href></Icon>')
                    lines.append('          </IconStyle>')
                    lines.append('        </Style>')

                lines.append('        <Point>')
                lines.append(
                    f'          <coordinates>'
                    f'{sym.longitude:.7f},{sym.latitude:.7f},0'
                    f'</coordinates>'
                )
                lines.append('        </Point>')
                lines.append('      </Placemark>')

            lines.append('    </Folder>')

        lines.append('  </Document>')
        lines.append('</kml>')
        return "\n".join(lines)

    def _write_kmz(self, path: str, layers) -> None:
        """Write KMZ (ZIP of doc.kml + icons/*.png) to *path*."""
        # Collect unique SIDCs from placed symbols
        all_sidcs: set = set()
        for sl in layers:
            for sym in sl.symbols:
                if sym.longitude != 0.0 or sym.latitude != 0.0:
                    all_sidcs.add(sym.sidc)

        # Render icons (no ElementTree, no register_namespace)
        icon_files: dict = {}   # sidc -> archive path string
        icon_data: dict = {}    # archive path -> bytes
        for sidc in all_sidcs:
            png = self._sidc_to_png_bytes(sidc, size=64)
            if png:
                arc_path = f"icons/{sidc}.png"
                icon_files[sidc] = arc_path
                icon_data[arc_path] = png

        kml_str = self._build_kml(layers, icon_files)

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("doc.kml", kml_str.encode("utf-8"))
            for arc_path, data in icon_data.items():
                zf.writestr(arc_path, data)

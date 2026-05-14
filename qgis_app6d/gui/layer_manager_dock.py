# -*- coding: utf-8 -*-
"""
Layer management dock widget – add, rename, delete symbol layers and
export data per-layer or as a single multi-layer JSON file.

Integrated into the main plugin panel as a collapsible group at the top
of the catalog dock, or as a standalone dock accessible from the ribbon.
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import Optional
from xml.etree import ElementTree as ET

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
from ..core.models import MilSymbProject
from ..core.utils import milsymb_data_dir
from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.layer_manager_dock")


class LayerManagerDockWidget(QDockWidget):
    """Dock for managing multiple MilSymb symbol layers.

    Features
    --------
    * Layer selector (QComboBox) – pick the active layer
    * Add / Rename / Delete buttons
    * Export panel – single multi-layer JSON **or** one file per layer

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
        self._rename_btn.setText("✎")
        self._rename_btn.setToolTip("Rename layer")
        self._rename_btn.clicked.connect(self._on_rename)
        sel_row.addWidget(self._rename_btn)

        self._del_btn = QToolButton()
        self._del_btn.setText("−")
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
        self._export_kmz_all_btn = QPushButton("Export all layers as KMZ")
        self._export_kmz_all_btn.clicked.connect(self._on_export_kmz_all)
        row4.addWidget(self._export_kmz_all_btn)
        exp_layout.addLayout(row4)

        row5 = QHBoxLayout()
        self._export_kmz_current_btn = QPushButton("Export current layer as KMZ")
        self._export_kmz_current_btn.clicked.connect(self._on_export_kmz_current)
        row5.addWidget(self._export_kmz_current_btn)
        exp_layout.addLayout(row5)

        root.addWidget(exp_grp)

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
    # Slots – combo
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
    # Slots – add / rename / delete
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
    # Slots – layer_manager signals
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

    def _on_export_all(self) -> None:
        """Export all layers into a single JSON file."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers",
            os.path.join(default_dir, "milsymb_all_layers.json"),
            "MilSymb JSON (*.json);;All files (*)",
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
                fname = f"milsymb_layer_{safe_name}.json"
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
            os.path.join(default_dir, f"milsymb_layer_{safe_name}.json"),
            "MilSymb JSON (*.json);;All files (*)",
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

    # ------------------------------------------------------------------
    # KMZ helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_kml(layers_data: list[tuple[str, list]]) -> bytes:
        """Build a KML document from a list of (layer_name, symbols) tuples.

        Returns the KML as UTF-8 encoded bytes.
        """
        KML_NS = "http://www.opengis.net/kml/2.2"
        ET.register_namespace("", KML_NS)

        def tag(name: str) -> str:
            return f"{{{KML_NS}}}{name}"

        kml_root = ET.Element(tag("kml"))
        doc = ET.SubElement(kml_root, tag("Document"))
        doc_name = ET.SubElement(doc, tag("name"))
        doc_name.text = "MilSymb Export"

        for layer_name, symbols in layers_data:
            folder = ET.SubElement(doc, tag("Folder"))
            fn = ET.SubElement(folder, tag("name"))
            fn.text = layer_name

            for sym in symbols:
                pm = ET.SubElement(folder, tag("Placemark"))

                nm = ET.SubElement(pm, tag("name"))
                nm.text = sym.designation or sym.sidc

                parts = []
                if sym.sidc:
                    parts.append(f"SIDC: {sym.sidc}")
                if sym.higher_formation:
                    parts.append(f"Higher formation: {sym.higher_formation}")
                if sym.comment:
                    parts.append(f"Comment: {sym.comment}")
                if sym.staff_comments:
                    parts.append(f"Staff comments: {sym.staff_comments}")
                if sym.additional_information:
                    parts.append(f"Additional info: {sym.additional_information}")
                if sym.dtg:
                    parts.append(f"DTG: {sym.dtg}")
                if sym.speed:
                    parts.append(f"Speed: {sym.speed}")
                if sym.altitude_depth:
                    parts.append(f"Altitude/Depth: {sym.altitude_depth}")
                if parts:
                    desc = ET.SubElement(pm, tag("description"))
                    desc.text = "\n".join(parts)

                if sym.direction is not None:
                    ext = ET.SubElement(pm, tag("ExtendedData"))
                    ed = ET.SubElement(ext, tag("Data"))
                    ed.set("name", "direction")
                    val = ET.SubElement(ed, tag("value"))
                    val.text = str(sym.direction)

                pt = ET.SubElement(pm, tag("Point"))
                coords = ET.SubElement(pt, tag("coordinates"))
                coords.text = f"{sym.longitude},{sym.latitude},0"

        tree = ET.ElementTree(kml_root)
        buf = io.BytesIO()
        tree.write(buf, encoding="utf-8", xml_declaration=True)
        return buf.getvalue()

    @staticmethod
    def _write_kmz(kml_bytes: bytes, kmz_path: str) -> None:
        """Wrap *kml_bytes* inside a .kmz archive at *kmz_path*."""
        with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("doc.kml", kml_bytes)

    # ------------------------------------------------------------------
    # Slots – KMZ export
    # ------------------------------------------------------------------

    def _on_export_kmz_all(self) -> None:
        """Export all layers into a single KMZ file."""
        if self._project_data is None:
            return
        default_dir = milsymb_data_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export all layers as KMZ",
            os.path.join(default_dir, "milsymb_all_layers.kmz"),
            "KMZ (*.kmz);;All files (*)",
        )
        if not path:
            return
        try:
            layers_data = [
                (sl.name, sl.symbols)
                for sl in self._project_data.layers
            ]
            kml_bytes = self._build_kml(layers_data)
            self._write_kmz(kml_bytes, path)
            n_sym = sum(len(sl.symbols) for sl in self._project_data.layers)
            n_lyr = len(self._project_data.layers)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {n_lyr} layer(s) with {n_sym} symbol(s) to\n{path}",
            )
            LOG.info("Exported all layers as KMZ to %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def _on_export_kmz_current(self) -> None:
        """Export only the currently selected layer as KMZ."""
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
            "KMZ (*.kmz);;All files (*)",
        )
        if not path:
            return
        try:
            kml_bytes = self._build_kml([(sl.name, sl.symbols)])
            self._write_kmz(kml_bytes, path)
            QMessageBox.information(
                self, "Export complete",
                f"Exported layer \"{sl.name}\" ({len(sl.symbols)} symbols) to\n{path}",
            )
            LOG.info("Exported layer '%s' as KMZ to %s", sl.name, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

# -*- coding: utf-8 -*-
"""
Layer management dock widget – add, rename, delete symbol layers and
export data per-layer or as a single multi-layer JSON file.

Integrated into the main plugin panel as a collapsible group at the top
of the catalog dock, or as a standalone dock accessible from the ribbon.
"""

from __future__ import annotations

import os
from typing import Optional

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

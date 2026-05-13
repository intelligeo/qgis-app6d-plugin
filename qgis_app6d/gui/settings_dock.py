# -*- coding: utf-8 -*-
"""
Settings dock widget – plugin configuration and project persistence.

Sections
--------
1. **Symbol Server** – status, port, restart button
2. **Defaults** – default identity, echelon, status
3. **Project I/O** – save / load MilSymbProject JSON
4. **About** – version, links
"""

from __future__ import annotations

import configparser
import os
from typing import Optional

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import DARK_THEME_SS
from ..core.models import MilSymbProject
from ..core.sidc import Echelon, StandardIdentity, Status
from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.settings_dock")


# ======================================================================
# SettingsDockWidget
# ======================================================================

class SettingsDockWidget(QDockWidget):
    """Plugin settings and project save/load dock.

    """

    project_loaded = pyqtSignal(object)  # MilSymbProject (kept for back-compat)
    project_saved = pyqtSignal(str)  # file path (kept for back-compat)
    symbol_size_changed = pyqtSignal(int)  # new size in pixels
    show_text_modifiers_changed = pyqtSignal(bool)  # toggle to show extended text on map

    def __init__(self, iface, action=None, parent=None):
        super().__init__("MilSymb Settings", parent)
        self._iface = iface
        self._action = action
        self._project_data: Optional[MilSymbProject] = None
        self._symbol_server = None
        self._layer_manager = None

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

    def set_symbol_server(self, srv) -> None:
        self._symbol_server = srv
        self._update_server_status()

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # ---- Symbol Server group ----
        srv_group = QGroupBox("Symbol Server")
        srv_layout = QFormLayout(srv_group)

        self._server_status_lbl = QLabel("–")
        srv_layout.addRow("Status:", self._server_status_lbl)

        self._server_port_lbl = QLabel("–")
        srv_layout.addRow("Port:", self._server_port_lbl)

        self._restart_btn = QPushButton("Restart Server")
        self._restart_btn.clicked.connect(self._on_restart_server)
        srv_layout.addRow(self._restart_btn)

        layout.addWidget(srv_group)

        # ---- Defaults group ----
        def_group = QGroupBox("Defaults")
        def_layout = QFormLayout(def_group)

        self._def_identity_combo = QComboBox()
        for si in StandardIdentity:
            self._def_identity_combo.addItem(si.name.replace("_", " ").title(), si)
        self._def_identity_combo.setCurrentIndex(3)  # FRIEND
        def_layout.addRow("Identity:", self._def_identity_combo)

        self._def_echelon_combo = QComboBox()
        for ech in Echelon:
            self._def_echelon_combo.addItem(ech.name.replace("_", " ").title(), ech)
        def_layout.addRow("Echelon:", self._def_echelon_combo)

        self._def_status_combo = QComboBox()
        for st in Status:
            self._def_status_combo.addItem(st.name.title(), st)
        def_layout.addRow("Status:", self._def_status_combo)

        self._symbol_size_spin = QSlider(Qt.Horizontal)
        self._symbol_size_spin.setMinimum(16)
        self._symbol_size_spin.setMaximum(256)
        self._symbol_size_spin.setValue(64)
        self._symbol_size_spin.valueChanged.connect(self.symbol_size_changed)
        def_layout.addRow("Symbol size:", self._symbol_size_spin)

        from qgis.PyQt.QtWidgets import QCheckBox
        self._show_text_modifiers_cb = QCheckBox("Display text fields around symbols")
        self._show_text_modifiers_cb.setToolTip("Show extra text fields (quantity, speed, evaluation, etc.) in map symbol drawing.")
        self._show_text_modifiers_cb.setChecked(False)
        self._show_text_modifiers_cb.toggled.connect(self.show_text_modifiers_changed.emit)
        def_layout.addRow(self._show_text_modifiers_cb)

        layout.addWidget(def_group)

        # ---- About button ----
        self._about_btn = QPushButton("ℹ  About QGIS APP-6(D)")
        self._about_btn.clicked.connect(self._on_about)
        layout.addWidget(self._about_btn)

        # ---- Spacer ----
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Server management
    # ------------------------------------------------------------------

    def _update_server_status(self) -> None:
        if self._symbol_server is not None:
            self._server_status_lbl.setText(
                '<span style="color:green;">Running</span>'
            )
            self._server_port_lbl.setText(str(self._symbol_server.port))
        else:
            self._server_status_lbl.setText(
                '<span style="color:red;">Stopped</span>'
            )
            self._server_port_lbl.setText("–")

    def _on_restart_server(self) -> None:
        """Stop and restart the symbol server."""
        if self._symbol_server is not None:
            self._symbol_server.stop()
            self._symbol_server.start()
            LOG.info("Symbol server restarted on port %d",
                     self._symbol_server.port)
        self._update_server_status()

    def _on_about(self) -> None:
        """Show an About dialog populated from metadata.txt."""
        meta_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "metadata.txt"
        )
        cfg = configparser.ConfigParser()
        cfg.read(meta_path, encoding="utf-8")
        g = cfg["general"] if "general" in cfg else {}

        name = g.get("name", "QGIS APP-6(D)")
        version = g.get("version", "\u2014")
        author = g.get("author", "\u2014")
        email = g.get("email", "")
        description = g.get("description", "")
        about = g.get("about", "")
        homepage = g.get("homepage", "")
        tracker = g.get("tracker", "")
        repository = g.get("repository", "")
        bmc = g.get("buymeacoffe", "")
        license_ = g.get("license", "")
        qgis_min = g.get("qgisminimumversion", "")
        tags = g.get("tags", "")

        lines = []
        lines.append(f"<h2>{name} &nbsp; <small>v{version}</small></h2>")
        if description:
            lines.append(f"<p>{description}</p>")
        if about:
            lines.append(f"<p>{about}</p>")
        lines.append("<hr>")
        if author:
            contact = f"<a href='mailto:{email}'>{email}</a>" if email else email
            lines.append(f"<b>Author:</b> {author}")
            if email:
                lines.append(f" &mdash; {contact}")
            lines.append("<br>")
        if license_:
            lines.append(f"<b>License:</b> {license_}<br>")
        if qgis_min:
            lines.append(f"<b>QGIS minimum version:</b> {qgis_min}<br>")
        if tags:
            lines.append(f"<b>Tags:</b> {tags}<br>")
        lines.append("<br>")
        if homepage:
            lines.append(f"<b>Homepage:</b> <a href='{homepage}'>{homepage}</a><br>")
        if repository:
            lines.append(f"<b>Repository:</b> <a href='{repository}'>{repository}</a><br>")
        if tracker:
            lines.append(f"<b>Bug tracker:</b> <a href='{tracker}'>{tracker}</a><br>")
        if bmc:
            lines.append(f"<b>Support the project:</b> <a href='{bmc}'>{bmc}</a><br>")

        box = QMessageBox(self)
        box.setWindowTitle(f"About {name}")
        box.setTextFormat(Qt.RichText)
        box.setText("".join(lines))
        box.setTextInteractionFlags(
            Qt.TextBrowserInteraction
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()

    # ------------------------------------------------------------------
    # Public accessors for defaults
    # ------------------------------------------------------------------

    @property
    def default_identity(self) -> StandardIdentity:
        return self._def_identity_combo.currentData()

    @property
    def default_echelon(self) -> Echelon:
        return self._def_echelon_combo.currentData()

    @property
    def default_status(self) -> Status:
        return self._def_status_combo.currentData()

    @property
    def symbol_size(self) -> int:
        return self._symbol_size_spin.value()

    @property
    def show_text_modifiers(self) -> bool:
        return self._show_text_modifiers_cb.isChecked()

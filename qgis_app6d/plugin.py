# -*- coding: utf-8 -*-
"""
Main plugin class for QGIS APP-6(D).

Provides:
- Military symbol catalog browser (dock)
- ORBAT Manager (dock)
- Temporal integration via QGIS Temporal Controller
- Built-in symbol rendering server (SVG/PNG)

Compatible with QGIS 3.16+.  Uses the standard QgisInterface API
(toolbar + Plugins menu).
"""

import os
import configparser
import subprocess  # noqa: B404
import sys

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QMessageBox, QToolBar

from .core.models import MilSymbProject
from .core.utils import plugin_path, milsymb_data_dir
from .logger import get_logger

LOG = get_logger()


def _load_plugin_metadata() -> dict[str, str]:
    metadata_path = os.path.join(os.path.dirname(__file__), "metadata.txt")
    parser = configparser.ConfigParser()
    parser.read(metadata_path, encoding="utf-8")

    if not parser.has_section("general"):
        return {}

    return {
        key: value.strip() for key, value in parser.items("general")
    }


_PLUGIN_METADATA = _load_plugin_metadata()
_PLUGIN_NAME = _PLUGIN_METADATA.get("name", "")
_PLUGIN_VERSION = _PLUGIN_METADATA.get("version", "")
_PLUGIN_AUTHOR = _PLUGIN_METADATA.get("author", "")
_PLUGIN_URL = (
    _PLUGIN_METADATA.get("repository")
    or _PLUGIN_METADATA.get("homepage", "")
)


class QgisApp6Plugin:
    """QGIS APP-6(D) – military symbology plugin.

    Instantiated by ``classFactory`` in ``__init__.py``.
    QGIS calls ``initGui()`` once the plugin is enabled and ``unload()``
    when it is disabled or the application is closed.

    Actions are registered in a dedicated toolbar and under the
    ``Plugins > APP-6(D)`` menu so the plugin works on any standard
    QGIS 3.x installation.
    """

    def __init__(self, iface):
        # iface is a QgisInterface instance (QGIS 3.16+)
        self.iface = iface

        # Project data model
        self._project_data = MilSymbProject()

        # Symbol layer manager
        self._layer_manager = None

        # Dock widget instances (created lazily)
        self._catalog_dock = None
        self._orbat_dock = None
        self._settings_dock = None

        # Floating symbol editor dialog
        self._editor_dock = None

        # Canvas interaction filter (drag&drop + double-click)
        self._canvas_filter = None
        # Layer manager dock
        self._layer_manager_dock = None

        # Symbol rendering server
        self._symbol_server = None

        # Temporal manager
        self._temporal_manager = None

        # Project I/O (automatic save/load)
        self._project_io = None

        # Actions list for cleanup
        self._actions: list = []

        # Plugin toolbar and menu
        self._toolbar: QToolBar | None = None
        self._menu: QMenu | None = None

        LOG.info("%s plugin instantiated (v%s)", _PLUGIN_NAME, _PLUGIN_VERSION)

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initGui(self) -> None:  # noqa: N802
        """Create toolbar, Plugins menu entries and dock widgets."""
        # ---- Symbol Catalog action (checkable toggle) ----
        self._catalog_action = self._make_action(
            icon_path=plugin_path("icons", "milsymb.svg"),
            text=self.tr("Symbol Catalog"),
            tooltip=self.tr("Open / close the military symbol catalog"),
            checkable=True,
            callback=self._toggle_catalog_dock,
        )

        # ---- Symbol Editor action (checkable toggle) ----
        self._editor_action = self._make_action(
            icon_path=plugin_path("icons", "symbol_editor.svg"),
            text=self.tr("Symbol Editor"),
            tooltip=self.tr("Open the Symbol Editor to create or inspect a symbol"),
            checkable=True,
            callback=self._toggle_editor_dock,
        )

        # ---- ORBAT Manager action (checkable toggle) ----
        self._orbat_action = self._make_action(
            icon_path=plugin_path("icons", "orbat_editor.svg"),
            text=self.tr("ORBAT Manager"),
            tooltip=self.tr("Open / close the ORBAT manager"),
            checkable=True,
            callback=self._toggle_orbat_dock,
        )

        # ---- Layer Manager action (checkable toggle) ----
        self._layer_mgr_action = self._make_action(
            icon_path=plugin_path("icons", "map.svg"),
            text=self.tr("Layer Manager"),
            tooltip=self.tr("Manage symbol layers and export"),
            checkable=True,
            callback=self._toggle_layer_manager_dock,
        )

        # ---- Settings action (checkable toggle) ----
        self._settings_action = self._make_action(
            icon_path=plugin_path("icons", "settings.svg"),
            text=self.tr("Settings"),
            tooltip=self.tr("Open / close plugin settings"),
            checkable=True,
            callback=self._toggle_settings_dock,
        )

        # ---- About action ----
        self._about_action = self._make_action(
            icon_path=plugin_path("icons", "about.svg"),
            text=self.tr("About…"),
            tooltip=self.tr("Plugin information"),
            checkable=False,
            callback=self.show_about,
        )

        # ---- Log file action ----
        self._log_action = self._make_action(
            icon_path=plugin_path("icons", "log.svg"),
            text=self.tr("Open log file"),
            tooltip=self.tr("Open the plugin log file"),
            checkable=False,
            callback=self.open_log_file,
        )

        # ---- Build a dedicated plugin toolbar ----
        self._toolbar = self.iface.mainWindow().addToolBar(
            self.tr("APP-6(D) Toolbar")
        )
        self._toolbar.setObjectName("QgisApp6Toolbar")
        self._toolbar.addAction(self._catalog_action)
        self._toolbar.addAction(self._editor_action)
        self._toolbar.addAction(self._orbat_action)
        self._toolbar.addAction(self._layer_mgr_action)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._settings_action)

        # ---- Register entries under Plugins > APP-6(D) ----
        _MENU = self.tr("APP-6(&D)")
        for act in (
            self._catalog_action,
            self._editor_action,
            self._orbat_action,
            self._layer_mgr_action,
        ):
            self.iface.addPluginToMenu(_MENU, act)
        # Secondary entries
        self.iface.addPluginToMenu(_MENU, self._settings_action)
        self.iface.addPluginToMenu(_MENU, self._about_action)
        self.iface.addPluginToMenu(_MENU, self._log_action)

        # Start the built-in symbol rendering server
        self._start_symbol_server()

        # Initialise the symbol layer manager (QgsVectorLayer-backed)
        self._init_layer_manager()

        # Trigger creation of all vector layers
        if self._layer_manager is not None:
            self._layer_manager.ensure_layers()

        # Install canvas interaction filter (drag&drop + double-click +
        # right-click context menu)
        self._init_canvas_interactions()

        # Initialise temporal manager
        self._init_temporal_manager()

        # Initialise project I/O (auto save/load with QGIS project)
        self._init_project_io()

        LOG.debug(
            "QgisApp6Plugin.initGui() – %d actions registered",
            len(self._actions),
        )

    def unload(self) -> None:
        """Remove all UI elements and stop background services."""
        # Disconnect project I/O signals
        if self._project_io is not None:
            self._project_io.disconnect_signals()
            self._project_io = None

        # Disconnect temporal manager
        if self._temporal_manager is not None:
            self._temporal_manager.disconnect_temporal_controller()
            self._temporal_manager = None

        # Stop the symbol server
        self._stop_symbol_server()

        # Remove canvas interaction filter
        if self._canvas_filter is not None:
            try:
                self.iface.mapCanvas().viewport().removeEventFilter(
                    self._canvas_filter
                )
            except Exception:
                pass
            self._canvas_filter = None

        # Close docks gracefully
        for dock in (self._catalog_dock, self._orbat_dock,
                     self._settings_dock, self._layer_manager_dock):
            if dock is not None:
                dock.close()

        # Close floating editor dialog
        if self._editor_dock is not None:
            self._editor_dock.close()
            self._editor_dock = None

        self._catalog_dock = None
        self._orbat_dock = None
        self._settings_dock = None
        self._layer_manager_dock = None
        self._layer_manager = None

        # Remove toolbar
        if self._toolbar is not None:
            self._toolbar.clear()
            self.iface.mainWindow().removeToolBar(self._toolbar)
            self._toolbar = None

        # Remove Plugins menu entries
        _MENU = self.tr("APP-6(&D)")
        for act in self._actions:
            self.iface.removePluginMenu(_MENU, act)

        self._actions.clear()
        LOG.info("%s plugin unloaded", _PLUGIN_NAME)

    # ------------------------------------------------------------------
    # Layer manager
    # ------------------------------------------------------------------

    def _init_layer_manager(self) -> None:
        """Create the SymbolLayerManager (backed by QgsVectorLayer)."""
        try:
            from .gui.symbol_layer import SymbolLayerManager

            self._layer_manager = SymbolLayerManager(
                project_data=self._project_data,
                parent=self.iface.mainWindow(),
            )
            # Trigger layer creation immediately
            self._layer_manager.layer()
            LOG.info("SymbolLayerManager initialised")
        except Exception as exc:
            LOG.error("Failed to initialise layer manager: %s", exc)

    # ------------------------------------------------------------------
    # Right-click → open Symbol Editor
    # ------------------------------------------------------------------

    def _on_canvas_context_menu_at_point(
        self, map_point, global_pos
    ) -> bool:
        """Called by CanvasInteractionFilter on right-click.

        Searches for a MilSymb feature near *map_point* and shows the
        symbol context menu when found.  Returns ``True`` if a symbol
        was found (event consumed), ``False`` otherwise.
        """
        if self._layer_manager is None:
            return False
        canvas = self.iface.mapCanvas()
        sym_id = self._layer_manager.find_symbol_at_point(
            map_point, canvas.mapSettings()
        )
        if sym_id is not None:
            sym = self._layer_manager.get_symbol(sym_id)
            if sym is not None:
                self._show_symbol_context_menu(sym, global_pos)
                return True
        return False

    def _show_symbol_context_menu(self, sym, global_pos) -> None:
        """Show a context menu for a symbol on the map canvas."""
        from qgis.PyQt.QtWidgets import QMenu, QAction as _QAction

        menu = QMenu(self.iface.mainWindow())

        act_label = _QAction(f"Symbol: {sym.designation or sym.sidc[:10]}", menu)
        act_label.setEnabled(False)
        menu.addAction(act_label)
        menu.addSeparator()

        act_edit = _QAction("Open in Editor…", menu)
        act_edit.triggered.connect(lambda: self._open_editor_for(sym))
        menu.addAction(act_edit)

        act_move = _QAction("Move Symbol", menu)
        act_move.triggered.connect(lambda: self._on_move_symbol(sym))
        menu.addAction(act_move)

        menu.addSeparator()

        act_delete = _QAction("Delete Symbol", menu)
        act_delete.triggered.connect(lambda: self._delete_symbol_from_canvas(sym))
        menu.addAction(act_delete)

        menu.exec_(global_pos)

    def _delete_symbol_from_canvas(self, sym) -> None:
        """Delete *sym* directly from canvas context menu (with confirmation)."""
        from qgis.PyQt.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            "Delete Symbol",
            f"Delete symbol '{sym.designation or sym.sidc}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self._layer_manager is not None:
            self._layer_manager.remove_symbol(sym.id)
            LOG.info("Symbol %s deleted from canvas context menu", sym.id[:8])

    def _on_show_text_modifiers_changed(self, show: bool) -> None:
        if self._editor_dock is not None:
            self._editor_dock.set_show_text_modifiers(show)

    def _toggle_editor_dock(self, checked: bool) -> None:
        """Show or hide the Symbol Editor dock."""
        if self._editor_dock is None:
            self._ensure_editor_dock()
            self._editor_dock.reset_to_new_symbol_mode()
        if checked:
            self._show_editor_dock()
        else:
            self._editor_dock.hide()

    def _on_orbat_edit_unit_requested(self, unit) -> None:
        """Open the Symbol Editor dock to edit an ORBAT unit."""
        self._ensure_editor_dock()

        if unit.map_symbol_id and self._layer_manager is not None:
            sym = self._layer_manager.get_symbol(unit.map_symbol_id)
            if sym is not None:
                self._editor_dock.edit_symbol(sym)
                self._editor_dock._orbat_unit = unit
                self._show_editor_dock()
                self._editor_action.setChecked(True)
                return

        self._editor_dock.edit_orbat_unit(unit)
        self._show_editor_dock()
        self._editor_action.setChecked(True)

    def _on_orbat_unit_updated(self, unit) -> None:
        """Sync the ORBAT tree after the Symbol Editor applied changes to a unit."""
        if self._orbat_dock is not None:
            self._orbat_dock.refresh_after_edit(unit)

    def _open_editor_for(self, sym) -> None:
        """Open the Symbol Editor dock and load *sym* for editing."""
        self._ensure_editor_dock()
        self._editor_dock.edit_symbol(sym)
        self._show_editor_dock()
        self._editor_action.setChecked(True)

    def _on_catalog_edit_requested(self, payload) -> None:
        """Open the editor dock pre-populated with a catalog entry."""
        self._ensure_editor_dock()
        entry = payload["entry"]
        identity = payload.get("identity")
        echelon = payload.get("echelon")
        self._editor_dock.load_from_catalog(entry, identity=identity, echelon=echelon)
        self._show_editor_dock()

    def _ensure_editor_dock(self) -> None:
        """Create the floating editor dock if it does not exist yet."""
        import sip
        if self._editor_dock is not None and not sip.isdeleted(self._editor_dock):
            return
        from .gui.symbol_editor_dock import SymbolEditorDockWidget

        self._editor_dock = SymbolEditorDockWidget(
            iface=self.iface,
            action=self._editor_action,
            parent=self.iface.mainWindow(),
        )
        self._editor_dock.set_layer_manager(self._layer_manager)
        if self._settings_dock is not None:
            self._editor_dock.set_show_text_modifiers(
                self._settings_dock.show_text_modifiers
            )
        self._editor_dock.setObjectName("QgisApp6SymbolEditorDock")
        self._editor_dock.orbat_unit_updated.connect(self._on_orbat_unit_updated)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self._editor_dock)
        self._tabify_dock(self._editor_dock)

    def _show_editor_dock(self) -> None:
        """Ensure the editor dock is docked (not floating), visible and raised."""
        if self._editor_dock is None:
            return
        # Re-dock if the user detached it or if it ended up floating
        if self._editor_dock.isFloating():
            self._editor_dock.setFloating(False)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self._editor_dock)
            self._tabify_dock(self._editor_dock)
        self._editor_dock.show()
        self._editor_dock.raise_()

    # ------------------------------------------------------------------
    # Canvas interaction filter
    # ------------------------------------------------------------------

    def _init_canvas_interactions(self) -> None:
        """Install the canvas event filter for drag&drop and double-click."""
        try:
            from .gui.canvas_drop_filter import CanvasInteractionFilter

            canvas = self.iface.mapCanvas()
            self._canvas_filter = CanvasInteractionFilter(
                canvas=canvas,
                place_cb=self._on_drop_place_symbol,
                open_editor_cb=self._open_editor_at_point,
                context_menu_cb=self._on_canvas_context_menu_at_point,
                parent=canvas,
            )
            canvas.viewport().installEventFilter(self._canvas_filter)
            canvas.setAcceptDrops(True)
            canvas.viewport().setAcceptDrops(True)
            LOG.info("Canvas interaction filter installed")
        except Exception as exc:
            LOG.error("Failed to install canvas interaction filter: %s", exc)

    def _on_drop_place_symbol(
        self,
        sidc: str,
        designation: str,
        higher_formation: str,
        longitude: float,
        latitude: float,
    ) -> None:
        """Called by CanvasInteractionFilter when a symbol is dropped on the canvas."""
        if self._layer_manager is None:
            return
        from .core.models import MilSymbol

        sym = MilSymbol(
            sidc=sidc,
            designation=designation,
            higher_formation=higher_formation,
            longitude=longitude,
            latitude=latitude,
        )
        self._layer_manager.add_symbol(sym)
        LOG.info("Symbol added via drag&drop: %s SIDC=%s", sym.id[:8], sidc[:10])

    def _open_editor_at_point(self, map_point) -> None:
        """Called by CanvasInteractionFilter on double-click."""
        if self._layer_manager is None:
            return
        canvas = self.iface.mapCanvas()
        sym_id = self._layer_manager.find_symbol_at_point(
            map_point, canvas.mapSettings()
        )
        if sym_id is not None:
            sym = self._layer_manager.get_symbol(sym_id)
            if sym is not None:
                self._open_editor_for(sym)

    def _on_move_symbol(self, sym) -> None:
        """Activate SymbolMoveTool for *sym* (QGIS-native click-to-reposition).

        """
        if self._layer_manager is None:
            return
        canvas = self.iface.mapCanvas()
        try:
            from .gui.symbol_move_tool import SymbolMoveTool
            tool = SymbolMoveTool(canvas, self._layer_manager, sym.id)
            tool.symbol_moved.connect(
                lambda sid: LOG.info("Symbol %s moved via SymbolMoveTool", sid[:8])
            )
            canvas.setMapTool(tool)
            LOG.info("SymbolMoveTool activated for sym_id=%s", sym.id[:8])
        except Exception as exc:
            LOG.error("SymbolMoveTool activation failed: %s", exc)

    # ------------------------------------------------------------------
    # Temporal manager
    # ------------------------------------------------------------------

    def _init_temporal_manager(self) -> None:
        """Create the TemporalManager and hook into QGIS Temporal Controller."""
        try:
            from .gui.temporal import TemporalManager

            if self._layer_manager is None:
                LOG.warning("Cannot init TemporalManager – layer manager not ready")
                return
            self._temporal_manager = TemporalManager(
                layer_manager=self._layer_manager,
                parent=self.iface.mainWindow(),
            )
            self._temporal_manager.connect_temporal_controller()
            LOG.info("TemporalManager initialised")
        except Exception as exc:
            LOG.error("Failed to initialise TemporalManager: %s", exc)

    # ------------------------------------------------------------------
    # Project I/O
    # ------------------------------------------------------------------

    def _init_project_io(self) -> None:
        """Set up automatic project save/load tied to QGIS project signals."""
        try:
            from .gui.project_io import ProjectIO

            self._project_io = ProjectIO(
                project_data=self._project_data,
                parent=self.iface.mainWindow(),
            )
            self._project_io.project_loaded.connect(self._on_project_loaded)
            self._project_io.connect_signals()
            LOG.info("ProjectIO initialised")
        except Exception as exc:
            LOG.error("Failed to initialise ProjectIO: %s", exc)

    def _on_project_loaded(self, project_data) -> None:
        """Refresh layer and docks after MilSymb data is loaded from disk."""
        LOG.info("Refreshing plugin after project load (%d symbols, %d orbats)",
                 len(project_data.symbols), len(project_data.orbats))

        self._project_data = project_data

        if self._project_io is not None:
            self._project_io.set_project_data(project_data)

        if self._layer_manager is not None:
            self._layer_manager.rebuild_from_project(project_data)

        if self._catalog_dock is not None:
            self._catalog_dock.set_project_data(project_data)
        if self._orbat_dock is not None:
            self._orbat_dock.set_project_data(project_data)
        if self._settings_dock is not None:
            self._settings_dock.set_project_data(project_data)
        if self._layer_manager_dock is not None:
            self._layer_manager_dock.set_project_data(project_data)
        if self._editor_dock is not None:
            self._editor_dock.close()

    # ------------------------------------------------------------------
    # Symbol rendering server
    # ------------------------------------------------------------------

    def _start_symbol_server(self) -> None:
        """Start the built-in HTTP symbol server on a free port."""
        try:
            from .server.symbol_server import SymbolServer

            self._symbol_server = SymbolServer()
            self._symbol_server.start()
            LOG.info("Symbol server started on port %d", self._symbol_server.port)
        except Exception as exc:
            LOG.error("Failed to start symbol server: %s", exc)

    def _stop_symbol_server(self) -> None:
        """Stop the built-in symbol server."""
        if self._symbol_server is not None:
            self._symbol_server.stop()
            self._symbol_server = None
            LOG.info("Symbol server stopped")

    # ------------------------------------------------------------------
    # Dock toggling
    # ------------------------------------------------------------------

    def _tabify_dock(self, new_dock) -> None:
        """Tabify *new_dock* with first existing plugin dock."""
        from qgis.PyQt.QtWidgets import QMainWindow, QTabWidget
        mw = self.iface.mainWindow()
        mw.setDockOptions(
            mw.dockOptions()
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
        )
        for area in (
            Qt.RightDockWidgetArea,
            Qt.LeftDockWidgetArea,
            Qt.BottomDockWidgetArea,
            Qt.TopDockWidgetArea,
        ):
            mw.setTabPosition(area, QTabWidget.South)
        for existing in (self._catalog_dock, self._orbat_dock,
                         self._settings_dock, self._layer_manager_dock,
                         self._editor_dock):
            if existing is not None and existing is not new_dock:
                mw.tabifyDockWidget(existing, new_dock)
                new_dock.show()
                new_dock.raise_()
                return

    def _toggle_catalog_dock(self, checked: bool) -> None:
        """Show or hide the symbol catalog dock widget."""
        if self._catalog_dock is None:
            try:
                from .gui.catalog_dock import CatalogDockWidget

                self._catalog_dock = CatalogDockWidget(
                    iface=self.iface,
                    symbol_server=self._symbol_server,
                    action=self._catalog_action,
                    parent=self.iface.mainWindow(),
                )
                self._catalog_dock.set_layer_manager(self._layer_manager)
                self._catalog_dock.set_project_data(self._project_data)
                self._catalog_dock.setObjectName("QgisApp6CatalogDock")
                self._catalog_dock.edit_in_editor_requested.connect(
                    self._on_catalog_edit_requested
                )
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._catalog_dock
                )
                self._tabify_dock(self._catalog_dock)
                LOG.info("CatalogDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the symbol catalog:\n{exc}",
                )
                self._catalog_action.setChecked(False)
                return

        if checked:
            self._catalog_dock.show()
            self._catalog_dock.raise_()
        else:
            self._catalog_dock.hide()

    def _toggle_orbat_dock(self, checked: bool) -> None:
        """Show or hide the ORBAT manager dock widget."""
        if self._orbat_dock is None:
            try:
                from .gui.orbat_dock import OrbatDockWidget

                self._orbat_dock = OrbatDockWidget(
                    iface=self.iface,
                    symbol_server=self._symbol_server,
                    action=self._orbat_action,
                    parent=self.iface.mainWindow(),
                )
                self._orbat_dock.set_project_data(self._project_data)
                self._orbat_dock.set_layer_manager(self._layer_manager)
                self._orbat_dock.edit_unit_requested.connect(
                    self._on_orbat_edit_unit_requested
                )
                self._orbat_dock.setObjectName("QgisApp6OrbatDock")
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._orbat_dock
                )
                self._tabify_dock(self._orbat_dock)
                LOG.info("OrbatDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the ORBAT manager:\n{exc}",
                )
                self._orbat_action.setChecked(False)
                return

        if checked:
            self._orbat_dock.show()
            self._orbat_dock.raise_()
        else:
            self._orbat_dock.hide()

    def _toggle_settings_dock(self, checked: bool) -> None:
        """Show or hide the settings dock widget."""
        if self._settings_dock is None:
            try:
                from .gui.settings_dock import SettingsDockWidget

                self._settings_dock = SettingsDockWidget(
                    iface=self.iface,
                    action=self._settings_action,
                    parent=self.iface.mainWindow(),
                )
                self._settings_dock.set_project_data(self._project_data)
                self._settings_dock.set_symbol_server(self._symbol_server)
                self._settings_dock.set_layer_manager(self._layer_manager)
                self._settings_dock.project_loaded.connect(self._on_project_loaded)
                if self._layer_manager is not None:
                    self._settings_dock.symbol_size_changed.connect(
                        self._layer_manager.set_symbol_size
                    )
                    self._settings_dock.show_text_modifiers_changed.connect(
                        self._layer_manager.set_show_text_modifiers
                    )
                    self._settings_dock.show_text_modifiers_changed.connect(
                        self._on_show_text_modifiers_changed
                    )
                self._settings_dock.setObjectName("QgisApp6SettingsDock")
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._settings_dock
                )
                self._tabify_dock(self._settings_dock)
                LOG.info("SettingsDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open settings:\n{exc}",
                )
                self._settings_action.setChecked(False)
                return

        if checked:
            self._settings_dock.show()
            self._settings_dock.raise_()
        else:
            self._settings_dock.hide()

    def _toggle_layer_manager_dock(self, checked: bool) -> None:
        """Show or hide the layer manager dock widget."""
        if self._layer_manager_dock is None:
            try:
                from .gui.layer_manager_dock import LayerManagerDockWidget

                self._layer_manager_dock = LayerManagerDockWidget(
                    iface=self.iface,
                    action=self._layer_mgr_action,
                    parent=self.iface.mainWindow(),
                )
                self._layer_manager_dock.set_project_data(self._project_data)
                self._layer_manager_dock.set_layer_manager(self._layer_manager)
                self._layer_manager_dock.setObjectName("QgisApp6LayerManagerDock")
                self.iface.mainWindow().addDockWidget(
                    Qt.RightDockWidgetArea, self._layer_manager_dock
                )
                self._tabify_dock(self._layer_manager_dock)
                LOG.info("LayerManagerDockWidget added to right dock area")
            except Exception as exc:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Error",
                    f"Failed to open the layer manager:\n{exc}",
                )
                self._layer_mgr_action.setChecked(False)
                return

        if checked:
            self._layer_manager_dock.show()
            self._layer_manager_dock.raise_()
        else:
            self._layer_manager_dock.hide()

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------

    def show_about(self) -> None:
        """Show the About dialog."""
        text = f"""
<h3>{_PLUGIN_NAME}</h3>
<p><b>Version {_PLUGIN_VERSION}</b></p>
<p>
  Military symbol library (APP-6D) with ORBAT management<br>
  and temporal control for QGIS 3.16+.
</p>
<p>
  Features:<br>
  &bull; APP-6(D) symbol catalog with 20-char SIDC<br>
  &bull; Built-in SVG/PNG rendering server<br>
  &bull; ORBAT hierarchical manager<br>
  &bull; QGIS Temporal Controller integration
</p>
<p>
  Author: {_PLUGIN_AUTHOR}<br>
  Repository: <a href="{_PLUGIN_URL}">{_PLUGIN_URL}</a>
</p>
<p style="font-size:10px; color:gray;">
  Compatible with QGIS 3.16+ &middot; GPL-2.0 licence
</p>
"""
        QMessageBox.about(
            self.iface.mainWindow(),
            f"About {_PLUGIN_NAME}",
            text,
        )

    # ------------------------------------------------------------------
    # Log file
    # ------------------------------------------------------------------

    def open_log_file(self) -> None:
        """Open the plugin log file with the default system viewer."""
        log_path = os.environ.get(
            "QGIS_MILSYMB_LOG",
            os.path.join(milsymb_data_dir(), "qgis_milsymb.log"),
        )
        if not os.path.exists(log_path):
            QMessageBox.information(
                self.iface.mainWindow(),
                "Log file not found",
                f"No log file exists yet at:\n{log_path}",
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(log_path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", log_path])
            else:
                subprocess.Popen(["xdg-open", log_path])
        except Exception as exc:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Cannot open log",
                f"Failed to open the log file:\n{exc}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_action(
        self,
        icon_path: str,
        text: str,
        tooltip: str,
        checkable: bool,
        callback,
    ) -> QAction:
        """Create a QAction, connect it and add it to _actions."""
        action = QAction(QIcon(icon_path), text)
        action.setToolTip(tooltip)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(callback)
        else:
            action.triggered.connect(callback)
        self._actions.append(action)
        return action

    def tr(self, message: str) -> str:
        """Translate *message* using Qt's translation mechanism."""
        return QCoreApplication.translate("QgisApp6Plugin", message)

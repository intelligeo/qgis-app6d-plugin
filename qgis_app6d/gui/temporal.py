# -*- coding: utf-8 -*-
"""
Temporal controller integration.

Listens to the QGIS Temporal Controller and delegates filtering to
``SymbolLayerManager.apply_temporal_filter()``, which shows/hides
``SymbolItem``s based on their temporal extent.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.temporal")


class TemporalManager(QObject):
    """Bridges the QGIS Temporal Controller with the MilSymb layer manager.

    Parameters
    ----------
    layer_manager : SymbolLayerManager
        The managed symbol layer manager.
    parent : QObject or None
        Qt parent.
    """

    filter_changed = pyqtSignal(str)

    def __init__(self, *, layer_manager=None, parent: QObject | None = None):
        super().__init__(parent)
        self._layer_manager = layer_manager
        self._connected = False
        self._nav_object = None

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    def connect_temporal_controller(self) -> None:
        if self._connected:
            return
        try:
            canvas = self._get_map_canvas()
            if canvas is None:
                LOG.warning("No map canvas found - temporal controller unavailable")
                return
            controller = canvas.temporalController()
            if controller is None:
                LOG.warning("Temporal controller not available on canvas")
                return
            self._nav_object = controller
            controller.updateTemporalRange.connect(self._on_temporal_range_changed)
            self._connected = True
            LOG.info("Connected to QGIS Temporal Controller")
            self._on_temporal_range_changed(controller.temporalRange())
        except Exception as exc:
            LOG.error("Failed to connect temporal controller: %s", exc)

    def disconnect_temporal_controller(self) -> None:
        if not self._connected or self._nav_object is None:
            return
        try:
            self._nav_object.updateTemporalRange.disconnect(self._on_temporal_range_changed)
        except (TypeError, RuntimeError):
            pass
        self._connected = False
        self._nav_object = None
        self._clear_filter()
        LOG.info("Disconnected from QGIS Temporal Controller")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Temporal range handler
    # ------------------------------------------------------------------

    def _on_temporal_range_changed(self, temporal_range) -> None:
        if temporal_range is None or temporal_range.isEmpty():
            self._clear_filter()
            return
        begin = temporal_range.begin()
        end = temporal_range.end()
        if not begin.isValid() or not end.isValid():
            self._clear_filter()
            return
        begin_iso = begin.toString("yyyy-MM-ddTHH:mm:ss")
        end_iso = end.toString("yyyy-MM-ddTHH:mm:ss")
        self._apply_filter(begin_iso, end_iso)

    # ------------------------------------------------------------------
    # Manual API
    # ------------------------------------------------------------------

    def filter_to_time(self, iso_time: str) -> None:
        """Filter symbols visible at a specific instant."""
        self._apply_filter(iso_time, iso_time)

    def show_all(self) -> None:
        """Remove temporal filter - show all symbols."""
        self._clear_filter()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_filter(self, begin_iso: str, end_iso: str) -> None:
        if self._layer_manager is not None:
            self._layer_manager.apply_temporal_filter(begin_iso, end_iso)
        label = f"{begin_iso} / {end_iso}"
        self.filter_changed.emit(label)
        LOG.debug("Temporal filter applied: %s", label)

    def _clear_filter(self) -> None:
        if self._layer_manager is not None:
            self._layer_manager.apply_temporal_filter(None, None)
        self.filter_changed.emit("")
        LOG.debug("Temporal filter cleared")

    @staticmethod
    def _get_map_canvas():
        try:
            from qgis.utils import iface
            if iface is not None:
                return iface.mapCanvas()
        except (ImportError, AttributeError):
            pass
        return None


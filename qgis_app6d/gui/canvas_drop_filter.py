# -*- coding: utf-8 -*-
"""
Canvas interaction event filter.

Installed on the map canvas viewport during plugin init; handles:

1. **Drag and Drop** from the Symbol Catalog:
   ``DragEnter`` / ``Drop`` events carrying MIME type
   ``application/x-qgis-app6`` (JSON payload with SIDC and text
   amplifiers).  The pixel position is converted to WGS-84 and the
   ``place_cb`` callback creates the new ``MilSymbol``.

2. **Double-click** (left button) to open the Symbol Editor for the
   feature under the cursor.  Delegates to ``open_editor_cb`` with the
   map-unit ``QgsPointXY`` so the caller can do the feature search.

3. **Right-click / context menu** to show the symbol context menu.
   Uses both ``QEvent.MouseButtonRelease`` (RightButton) and
   ``QEvent.ContextMenu`` for broad Qt5/Qt6 compatibility.
"""

from __future__ import annotations

import json
from typing import Callable

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QEvent, QObject, Qt

from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.canvas_drop_filter")

MILSYMB_MIME_TYPE = "application/x-qgis-app6"


class CanvasInteractionFilter(QObject):
    """Event filter installed on ``QgsMapCanvas.viewport()``.

    Parameters
    ----------
    canvas : QgsMapCanvas
    place_cb : Callable
        Called on drop with ``(sidc, designation, higher_formation,
        longitude_wgs84, latitude_wgs84)``.
    open_editor_cb : Callable
        Called on double-click with a ``QgsPointXY`` in map CRS.
    context_menu_cb : Callable or None
        Called on right-click with ``(QgsPointXY in map CRS,
        QPoint global screen position)``.  Should return ``True`` if a
        context menu was shown (so the event is consumed), ``False``
        to fall through to the default QGIS canvas context menu.
    parent : QObject or None
    """

    def __init__(
        self,
        canvas: QgsMapCanvas,
        place_cb: Callable,
        open_editor_cb: Callable,
        context_menu_cb: Callable | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._place_cb = place_cb
        self._open_editor_cb = open_editor_cb
        self._context_menu_cb = context_menu_cb

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:  # noqa: N802
        evt_type = ev.type()

        # ---- Drag enter --------------------------------------------------
        if evt_type == QEvent.DragEnter:
            if ev.mimeData().hasFormat(MILSYMB_MIME_TYPE):
                ev.acceptProposedAction()
                return True

        # ---- Drag move – must accept to keep the drop cursor active ------
        elif evt_type == QEvent.DragMove:
            if ev.mimeData().hasFormat(MILSYMB_MIME_TYPE):
                ev.acceptProposedAction()
                return True

        # ---- Drop --------------------------------------------------------
        elif evt_type == QEvent.Drop:
            if ev.mimeData().hasFormat(MILSYMB_MIME_TYPE):
                raw = bytes(ev.mimeData().data(MILSYMB_MIME_TYPE)).decode("utf-8")
                try:
                    payload = json.loads(raw)
                except Exception as exc:
                    LOG.warning("Failed to decode drop payload: %s", exc)
                    return False

                if hasattr(ev, "position"):
                    pos = ev.position().toPoint()
                else:
                    pos = ev.pos()
                map_pt = self._canvas.getCoordinateTransform().toMapCoordinates(
                    pos.x(), pos.y()
                )

                map_crs = self._canvas.mapSettings().destinationCrs()
                wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
                if map_crs != wgs84:
                    xform = QgsCoordinateTransform(
                        map_crs, wgs84, QgsProject.instance()
                    )
                    map_pt = xform.transform(QgsPointXY(map_pt))

                self._place_cb(
                    payload.get("sidc", "10031000000000000000"),
                    payload.get("designation", ""),
                    payload.get("higher_formation", ""),
                    float(map_pt.x()),
                    float(map_pt.y()),
                )
                ev.acceptProposedAction()
                LOG.info(
                    "Symbol dropped at (%.6f, %.6f) SIDC=%s",
                    map_pt.x(), map_pt.y(),
                    payload.get("sidc", "?")[:10],
                )
                return True

        # ---- Double-click (left) -> open editor --------------------------
        elif evt_type == QEvent.MouseButtonDblClick:
            if ev.button() == Qt.LeftButton:
                pos = ev.pos()
                map_pt = self._canvas.getCoordinateTransform().toMapCoordinates(
                    pos.x(), pos.y()
                )
                self._open_editor_cb(QgsPointXY(map_pt))
                return True

        # ---- Right-click / context menu -> symbol context menu -----------
        # We intercept MouseButtonRelease with RightButton for reliability
        # across Qt5 and Qt6, then also handle QEvent.ContextMenu as fallback.
        elif evt_type == QEvent.MouseButtonRelease and self._context_menu_cb is not None:
            if ev.button() == Qt.RightButton:
                pos = ev.pos()
                map_pt = self._canvas.getCoordinateTransform().toMapCoordinates(
                    pos.x(), pos.y()
                )
                consumed = self._context_menu_cb(
                    QgsPointXY(map_pt),
                    ev.globalPos() if hasattr(ev, 'globalPos') else
                    self._canvas.viewport().mapToGlobal(pos),
                )
                if consumed:
                    return True

        # ---- QEvent.ContextMenu as fallback (standard Qt) ----------------
        elif evt_type == QEvent.ContextMenu and self._context_menu_cb is not None:
            pos = ev.pos()
            map_pt = self._canvas.getCoordinateTransform().toMapCoordinates(
                pos.x(), pos.y()
            )
            consumed = self._context_menu_cb(
                QgsPointXY(map_pt), ev.globalPos()
            )
            if consumed:
                return True  # swallow event; default canvas menu suppressed

        return False

# -*- coding: utf-8 -*-
"""
Symbol layer manager – maintains a ``QgsVectorLayer`` (memory, Point) per
:class:`~qgis_app6d.core.models.SymbolLayer` and a QgsFeature for every
:class:`~qgis_app6d.core.models.MilSymbol`.

Architecture (QGIS-native)
--------------------------
* One in-memory ``QgsVectorLayer`` per ``SymbolLayer`` (named group).
* One ``QgsFeature`` (point) per ``MilSymbol``, carrying a ``sym_id``
  attribute used as the stable cross-reference key.
* A per-session SVG cache directory stores rendered icon files.
* A ``QgsSvgMarkerSymbolLayer`` with data-defined ``name`` (= SVG path)
  drives rendering; the path stored in the ``svg_path`` feature field is
  resolved by the QGIS SVG engine at paint time.
* ``_fid_map``  – maps ``sym_id -> (QgsVectorLayer, QgsFeatureId)``
* ``_hidden_fids`` – features hidden by the temporal filter
  ``sym_id -> (QgsVectorLayer, QgsFeatureId, QgsFeature snapshot)``

Public API
----------
QGIS-native API. Compatible with QGIS 3.16+.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from qgis.PyQt.QtCore import QObject, QVariant, pyqtSignal
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMapSettings,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsRectangle,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbol,
    QgsVectorLayer,
    QgsWkbTypes,
)

from ..core.models import MilSymbol, MilSymbProject, SymbolLayer
from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.symbol_layer")

_LAYER_PREFIX = "MilSymb - "
_CRS_WGS84 = "EPSG:4326"
_SYMBOL_SIZE_MM = 10.0   # rendered size in mm
_SYMBOL_SIZE_PX = 64     # raster size for SVG cache files
_ANCHOR = 0.5

# Field indices (must match URI field order)
_FLD_SYM_ID = 0
_FLD_SVG_PATH = 1
_FLD_DESIGNATION = 2
_FLD_COMMENT = 3

# ---------------------------------------------------------------------------
# SIDC helpers (unchanged from original version)
# ---------------------------------------------------------------------------

_MILX_SIDC_RE = __import__('re').compile(r'^[A-Z\-\*]{15}$')


def _normalize_mss_sidc(sidc15: str) -> str:
    """Swap modifier positions to make a 15-char MSS SIDC milsymbol.js-compatible."""
    chars = list(sidc15)
    chars[10], chars[11] = chars[11], chars[10]
    return "".join(chars)


def _effective_sidc(sym: MilSymbol) -> tuple:
    """Return ``(sidc_for_rendering, addinfo_text)``."""
    sidc20 = sym.sidc or ""
    if len(sidc20) == 20 and sidc20[10:16] != "000000":
        orig = (sym.additional_information or "").strip().upper()
        addinfo_text = "" if (len(orig) == 15 and _MILX_SIDC_RE.match(orig)) else (sym.additional_information or "")
        return sidc20, addinfo_text
    orig = (sym.additional_information or "").strip().upper()
    if len(orig) == 15 and _MILX_SIDC_RE.match(orig):
        return _normalize_mss_sidc(orig), ""
    return sidc20, sym.additional_information or ""


# ---------------------------------------------------------------------------
# SVG cache
# ---------------------------------------------------------------------------

_svg_dir: Optional[str] = None
_svg_cache: dict = {}


def _ensure_svg_dir() -> str:
    global _svg_dir
    if _svg_dir is None or not os.path.isdir(_svg_dir):
        _svg_dir = tempfile.mkdtemp(prefix="qgis_app6d_svg_")
    return _svg_dir


def _get_svg_path(sym: MilSymbol, size: int = _SYMBOL_SIZE_PX, show_text: bool = False) -> Optional[str]:
    sidc, addinfo = _effective_sidc(sym)
    if show_text:
        desig = getattr(sym, 'designation', "")
        hf = getattr(sym, 'higher_formation', "")
        quant = getattr(sym, 'quantity', "")
        staff = getattr(sym, 'staff_comments', "")
        evalrat = getattr(sym, 'evaluation_rating', "")
        combeff = getattr(sym, 'combat_effectiveness', "")
        dtg = getattr(sym, 'dtg', "")
        typestr = getattr(sym, 'type_str', "")
        speed = getattr(sym, 'speed', "")
        alt = getattr(sym, 'altitude_depth', "")
        dr = getattr(sym, 'direction', None)
        cache_key = f"{sidc}_{size}|{desig}|{hf}|{quant}|{staff}|{addinfo}|{evalrat}|{combeff}|{dtg}|{typestr}|{speed}|{alt}|{dr}"
    else:
        desig = hf = quant = staff = evalrat = combeff = dtg = typestr = speed = alt = dr = ""
        cache_key = f"{sidc}_{size}"

    if cache_key in _svg_cache:
        return _svg_cache[cache_key]

    try:
        from ..symbology.renderer import cached_svg
        if show_text:
            svg_str = cached_svg(
                sidc, desig, hf,
                quantity=quant, staff_comments=staff,
                additional_information=addinfo, evaluation_rating=evalrat,
                combat_effectiveness=combeff, dtg=dtg, type_str=typestr,
                speed=speed, altitude_depth=alt, direction=dr,
            )
        else:
            svg_str = cached_svg(sidc, "", "")
    except Exception as exc:
        LOG.warning("SVG render failed for SIDC %s: %s", sidc, exc)
        return None

    svg_dir = _ensure_svg_dir()
    safe_name = str(hash(cache_key) & 0xFFFFFFFF)
    fpath = os.path.join(svg_dir, f"{safe_name}.svg")
    try:
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(svg_str)
        _svg_cache[cache_key] = fpath
        return fpath
    except OSError as exc:
        LOG.error("Cannot write SVG cache file %s: %s", fpath, exc)
        return None


# ---------------------------------------------------------------------------
# QgsVectorLayer factory helpers
# ---------------------------------------------------------------------------

def _build_renderer(size_mm: float = _SYMBOL_SIZE_MM) -> QgsSingleSymbolRenderer:
    """Return a QgsSingleSymbolRenderer with a data-defined SVG marker.

    The ``name`` (SVG path) property is bound to the ``svg_path`` feature
    field so each feature is rendered with its own pre-rendered SVG icon.
    """
    svg_sl = QgsSvgMarkerSymbolLayer("")
    svg_sl.setSize(size_mm)
    svg_sl.setDataDefinedProperty(
        QgsSvgMarkerSymbolLayer.PropertyName,
        QgsProperty.fromField("svg_path"),
    )
    marker = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
    marker.changeSymbolLayer(0, svg_sl)
    return QgsSingleSymbolRenderer(marker)


def _make_vl(name: str) -> QgsVectorLayer:
    """Create a named in-memory Point layer with the plugin attribute schema."""
    uri = (
        f"Point?crs={_CRS_WGS84}"
        f"&field=sym_id:string(36)"
        f"&field=svg_path:string(512)"
        f"&field=designation:string(255)"
        f"&field=comment:string(512)"
    )
    vl = QgsVectorLayer(uri, name, "memory")
    if not vl.isValid():
        LOG.error("Failed to create memory layer '%s'", name)
        return vl
    vl.setRenderer(_build_renderer())
    return vl


def _feature_for_sym(sym: MilSymbol, svg_path: str) -> QgsFeature:
    """Build a QgsFeature from a MilSymbol."""
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(sym.longitude, sym.latitude)))
    feat.setAttributes([
        sym.id,
        svg_path or "",
        sym.designation or "",
        sym.comment or "",
    ])
    return feat


# ======================================================================
# SymbolLayerManager
# ======================================================================

class SymbolLayerManager(QObject):
    """Manages one QgsVectorLayer (memory) per SymbolLayer.

    QGIS-native manager: one QgsVectorLayer per SymbolLayer.
    Same public signal/method surface throughout the plugin.  Works on QGIS 3.16+.
    """

    symbol_added = pyqtSignal(str)
    symbol_removed = pyqtSignal(str)
    symbol_updated = pyqtSignal(str)
    layer_added = pyqtSignal(str)
    layer_removed = pyqtSignal(str)
    layer_renamed = pyqtSignal(str, str)
    active_layer_changed = pyqtSignal(str)

    def __init__(self, project_data: MilSymbProject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project = project_data
        # sym_layer.id -> QgsVectorLayer
        self._vl_map: dict = {}
        # sym_id -> (QgsVectorLayer, feature_id)
        self._fid_map: dict = {}
        # sym_id -> (QgsVectorLayer, feature_id, QgsFeature snapshot)
        self._hidden_map: dict = {}
        self._sym_size: int = _SYMBOL_SIZE_PX
        self._sym_size_mm: float = _SYMBOL_SIZE_MM
        self._show_text_modifiers: bool = False
        self._active_layer_id: str = project_data.default_layer().id

    def set_show_text_modifiers(self, enabled: bool) -> None:
        if self._show_text_modifiers != enabled:
            self._show_text_modifiers = enabled
            self._refresh_all_symbols()

    # ------------------------------------------------------------------
    # Active layer
    # ------------------------------------------------------------------

    @property
    def active_layer_id(self) -> str:
        return self._active_layer_id

    def set_active_layer(self, layer_id: str) -> None:
        if layer_id != self._active_layer_id:
            self._active_layer_id = layer_id
            self.active_layer_changed.emit(layer_id)

    def active_symbol_layer(self) -> SymbolLayer:
        lyr = self._project.layer_by_id(self._active_layer_id)
        if lyr is None:
            lyr = self._project.default_layer()
            self._active_layer_id = lyr.id
        return lyr

    # ------------------------------------------------------------------
    # QgsVectorLayer access
    # ------------------------------------------------------------------

    def vector_layer(self, layer_id: str) -> Optional[QgsVectorLayer]:
        """Return (or lazily create) the QgsVectorLayer for *layer_id*."""
        existing = self._vl_map.get(layer_id)
        if existing is not None and existing.isValid():
            return existing
        sym_layer = self._project.layer_by_id(layer_id)
        if sym_layer is None:
            sym_layer = self._project.default_layer()
        return self._create_vl(sym_layer)

    def layer(self) -> Optional[QgsVectorLayer]:
        """Return the active QgsVectorLayer."""
        return self.vector_layer(self._active_layer_id)

    def all_vector_layers(self) -> list:
        """Return a list of all QgsVectorLayers, one per SymbolLayer."""
        return [self.vector_layer(sl.id) for sl in self._project.layers]

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def ensure_layers(self) -> None:
        for sl in self._project.layers:
            self.vector_layer(sl.id)

    def _create_vl(self, sym_layer: SymbolLayer) -> Optional[QgsVectorLayer]:
        name = _LAYER_PREFIX + sym_layer.name
        vl = _make_vl(name)
        if not vl.isValid():
            return None
        QgsProject.instance().addMapLayer(vl)
        self._vl_map[sym_layer.id] = vl
        for sym in sym_layer.symbols:
            self._add_feature(vl, sym)
        LOG.info("Created VectorLayer '%s' with %d features", name, len(sym_layer.symbols))
        return vl

    # ------------------------------------------------------------------
    # Layer CRUD
    # ------------------------------------------------------------------

    def add_layer(self, name: str = "New Layer") -> SymbolLayer:
        sl = self._project.add_layer(name)
        self._create_vl(sl)
        self.layer_added.emit(sl.id)
        LOG.info("Symbol layer added: %s (%s)", name, sl.id)
        return sl

    def remove_layer(self, layer_id: str) -> bool:
        if len(self._project.layers) <= 1:
            LOG.warning("Cannot remove the last symbol layer")
            return False
        target_vl = self._vl_map.get(layer_id)
        to_remove = [sid for sid, (vl, _fid) in self._fid_map.items() if vl is target_vl]
        for sid in to_remove:
            del self._fid_map[sid]
        vl = self._vl_map.pop(layer_id, None)
        if vl is not None:
            try:
                QgsProject.instance().removeMapLayer(vl.id())
            except Exception:
                pass
        removed = self._project.remove_layer(layer_id)
        if removed:
            if self._active_layer_id == layer_id:
                self.set_active_layer(self._project.layers[0].id)
            self.layer_removed.emit(layer_id)
            LOG.info("Symbol layer removed: %s", layer_id)
        return removed

    def rename_layer(self, layer_id: str, new_name: str) -> bool:
        ok = self._project.rename_layer(layer_id, new_name)
        if ok:
            vl = self._vl_map.get(layer_id)
            if vl is not None:
                vl.setName(_LAYER_PREFIX + new_name)
            self.layer_renamed.emit(layer_id, new_name)
            LOG.info("Symbol layer renamed to '%s'", new_name)
        return ok

    def symbol_layers(self) -> list:
        return self._project.layers

    # ------------------------------------------------------------------
    # Symbol CRUD
    # ------------------------------------------------------------------

    def add_symbol(self, sym: MilSymbol, layer_id: str | None = None) -> None:
        lid = layer_id or self._active_layer_id
        sl = self._project.layer_by_id(lid)
        if sl is None:
            sl = self._project.default_layer()
            lid = sl.id
        sl.symbols.append(sym)
        vl = self.vector_layer(lid)
        if vl is not None:
            self._add_feature(vl, sym)
        self.symbol_added.emit(sym.id)
        LOG.info("Symbol added: %s (%s) -> layer %s", sym.designation or sym.sidc, sym.id, sl.name)

    def remove_symbol(self, sym_id: str) -> None:
        sl = self._project.layer_of_symbol(sym_id)
        if sl is None:
            return
        sl.symbols = [s for s in sl.symbols if s.id != sym_id]
        self._hidden_map.pop(sym_id, None)
        entry = self._fid_map.pop(sym_id, None)
        if entry is not None:
            vl, fid = entry
            try:
                vl.dataProvider().deleteFeatures([fid])
                vl.triggerRepaint()
            except Exception as exc:
                LOG.warning("Error removing feature for sym %s: %s", sym_id[:8], exc)
        self.symbol_removed.emit(sym_id)
        LOG.info("Symbol removed: %s", sym_id)

    def update_symbol(self, sym: MilSymbol) -> None:
        sl = self._project.layer_of_symbol(sym.id)
        if sl is None:
            return
        for i, s in enumerate(sl.symbols):
            if s.id == sym.id:
                sl.symbols[i] = sym
                break

        entry = self._fid_map.get(sym.id)
        hidden = self._hidden_map.get(sym.id)
        target_vl = None
        target_fid = None
        if entry is not None:
            target_vl, target_fid = entry
        elif hidden is not None:
            target_vl, target_fid, _ = hidden

        if target_vl is not None and target_fid is not None:
            svg_path = _get_svg_path(sym, self._sym_size, self._show_text_modifiers) or ""
            geom = QgsGeometry.fromPointXY(QgsPointXY(sym.longitude, sym.latitude))
            prov = target_vl.dataProvider()
            prov.changeGeometryValues({target_fid: geom})
            prov.changeAttributeValues({target_fid: {
                _FLD_SVG_PATH: svg_path,
                _FLD_DESIGNATION: sym.designation or "",
                _FLD_COMMENT: sym.comment or "",
            }})
            target_vl.triggerRepaint()

        self.symbol_updated.emit(sym.id)

    def get_symbol(self, sym_id: str) -> Optional[MilSymbol]:
        return self._project.symbol_by_id(sym_id)

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def find_symbol_at_point(
        self, map_point: QgsPointXY, map_settings: QgsMapSettings
    ) -> Optional[str]:
        """Return the sym_id of the symbol nearest to *map_point*, or None.

        Uses a tolerance rectangle query on the underlying QgsVectorLayers;
        pure QGIS API, no external dependencies.
        """
        try:
            mupp = map_settings.mapUnitsPerPixel()
        except Exception:
            mupp = 0.00001
        tol = mupp * 10
        rect = QgsRectangle(
            map_point.x() - tol, map_point.y() - tol,
            map_point.x() + tol, map_point.y() + tol,
        )
        map_crs = map_settings.destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem(_CRS_WGS84)
        if map_crs != wgs84:
            xform = QgsCoordinateTransform(map_crs, wgs84, QgsProject.instance())
            rect = xform.transformBoundingBox(rect)

        best_sym_id: Optional[str] = None
        best_dist = float("inf")
        click_pt = QgsPointXY(
            (rect.xMinimum() + rect.xMaximum()) / 2,
            (rect.yMinimum() + rect.yMaximum()) / 2,
        )
        for vl in self._vl_map.values():
            if vl is None or not vl.isValid():
                continue
            req = QgsFeatureRequest().setFilterRect(rect).setFlags(
                QgsFeatureRequest.ExactIntersect
            )
            for feat in vl.getFeatures(req):
                sym_id = feat.attribute("sym_id")
                if sym_id:
                    pt = feat.geometry().asPoint()
                    dist = pt.distance(click_pt)
                    if dist < best_dist:
                        best_dist = dist
                        best_sym_id = sym_id
        return best_sym_id

    # ------------------------------------------------------------------
    # Temporal filtering
    # ------------------------------------------------------------------

    def apply_temporal_filter(self, begin_iso: Optional[str], end_iso: Optional[str]) -> None:
        """Show only symbols whose temporal extent overlaps [begin, end].
        Pass ``begin_iso=None`` to restore all symbols.
        """
        if begin_iso is None:
            self._restore_all_hidden()
            return
        for sl in self._project.layers:
            vl = self._vl_map.get(sl.id)
            if vl is None:
                continue
            for sym in sl.symbols:
                in_range = self._sym_in_range(sym, begin_iso, end_iso)
                vis = sym.id in self._fid_map
                hid = sym.id in self._hidden_map
                if not in_range and vis:
                    vl2, fid = self._fid_map.pop(sym.id)
                    snap = next(vl2.getFeatures(QgsFeatureRequest(fid)), None)
                    try:
                        vl2.dataProvider().deleteFeatures([fid])
                        vl2.triggerRepaint()
                    except Exception:
                        pass
                    self._hidden_map[sym.id] = (vl2, fid, snap)
                elif in_range and hid:
                    vl2, _old_fid, snap = self._hidden_map.pop(sym.id)
                    if snap is not None:
                        snap.setId(-1)
                        ok, new_feats = vl2.dataProvider().addFeatures([snap])
                        if ok and new_feats:
                            self._fid_map[sym.id] = (vl2, new_feats[0].id())
                    vl2.triggerRepaint()

    def _restore_all_hidden(self) -> None:
        groups: dict = {}
        for sym_id, (vl, _fid, snap) in list(self._hidden_map.items()):
            if snap is not None:
                snap.setId(-1)
                groups.setdefault(id(vl), (vl, []))[1].append((sym_id, snap))
        for _key, (vl, items) in groups.items():
            snaps = [snap for _, snap in items]
            ok, new_feats = vl.dataProvider().addFeatures(snaps)
            if ok:
                for (sym_id, _), feat in zip(items, new_feats):
                    self._fid_map[sym_id] = (vl, feat.id())
            vl.triggerRepaint()
        self._hidden_map.clear()

    @staticmethod
    def _sym_in_range(sym: MilSymbol, begin_iso: str, end_iso: Optional[str]) -> bool:
        t = sym.temporal
        if not t.start:
            return True
        if end_iso and t.start > end_iso:
            return False
        if t.end and t.end < begin_iso:
            return False
        return True

    # ------------------------------------------------------------------
    # Symbol size & renderer update
    # ------------------------------------------------------------------

    def set_symbol_size(self, size_px: int) -> None:
        self._sym_size = size_px
        self._sym_size_mm = size_px * 0.264583  # px → mm at 96 dpi
        self._refresh_all_symbols()

    def _refresh_all_symbols(self) -> None:
        """Regenerate SVG paths and repaint all visible layers."""
        for sym_id, (vl, fid) in list(self._fid_map.items()):
            sym = self._project.symbol_by_id(sym_id)
            if sym is None:
                continue
            svg_path = _get_svg_path(sym, self._sym_size, self._show_text_modifiers) or ""
            try:
                vl.dataProvider().changeAttributeValues({fid: {
                    _FLD_SVG_PATH: svg_path,
                    _FLD_DESIGNATION: sym.designation or "",
                }})
            except Exception:
                pass
        for vl in self._vl_map.values():
            if vl and vl.isValid():
                rend = vl.renderer()
                if rend and hasattr(rend, 'symbol'):
                    sym_obj = rend.symbol()
                    if sym_obj and sym_obj.symbolLayerCount() > 0:
                        sl_obj = sym_obj.symbolLayer(0)
                        if hasattr(sl_obj, 'setSize'):
                            sl_obj.setSize(self._sym_size_mm)
                vl.triggerRepaint()

    # ------------------------------------------------------------------
    # Rebuild from project data
    # ------------------------------------------------------------------

    def rebuild_from_project(self, project: MilSymbProject) -> None:
        self._project = project
        self._fid_map.clear()
        self._hidden_map.clear()
        for vl in list(self._vl_map.values()):
            try:
                if vl and vl.isValid():
                    QgsProject.instance().removeMapLayer(vl.id())
            except Exception:
                pass
        self._vl_map.clear()
        self.ensure_layers()
        self._active_layer_id = project.default_layer().id
        LOG.info(
            "Layers rebuilt from project data – %d layers, %d symbols",
            len(project.layers), len(project.symbols),
        )

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def feature_count(self) -> int:
        return sum(len(sl.symbols) for sl in self._project.layers)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_feature(self, vl: QgsVectorLayer, sym: MilSymbol) -> None:
        svg_path = _get_svg_path(sym, self._sym_size, self._show_text_modifiers) or ""
        feat = _feature_for_sym(sym, svg_path)
        ok, added = vl.dataProvider().addFeatures([feat])
        if ok and added:
            self._fid_map[sym.id] = (vl, added[0].id())
        else:
            LOG.error("Failed to add feature for sym %s", sym.id[:8])

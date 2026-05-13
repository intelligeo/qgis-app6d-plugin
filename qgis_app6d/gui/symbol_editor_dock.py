# -*- coding: utf-8 -*-
"""
Symbol Editor floating dialog – popup editor for military symbols.

Opened from the symbol catalog (right-click → "Edit…") or from
right-clicking a symbol feature on the map canvas.  Allows editing all
SIDC components, text amplifiers and temporal attributes; changes are
applied live to the layer.

Layout (top → bottom)
---------------------
1. **Designation / Comment** text fields
2. **Symbology combos** (Identity, Symbol Set, Entity, Echelon, …)
3. **Preview** – live SVG preview
4. **Temporal** – optional start / end
5. **Place on Map / Apply / Delete** buttons
"""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt, QByteArray, pyqtSignal, QDateTime
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.models import MilSymbol
from ..core.sidc import (
    SIDC as SIDCClass,
    Echelon,
    HqTfDummy,
    STANDARD_IDENTITY_LABELS,
    StandardIdentity,
    Status,
    SymbolSet,
)
from . import DARK_THEME_SS
from ..symbology.catalog_data import (
    SYMBOL_SET_NAMES,
    CatalogEntry,
    entries_by_symbol_set,
)
from ..symbology.renderer import cached_svg
from ..logger import get_logger

LOG = get_logger("qgis_milsymb.gui.symbol_editor_dock")

_PREVIEW_SIZE = 96

# Dictionary of some common APP-6D Modifiers for UI
_COMMON_MOD1 = {
    "00": "None",
    "01": "Air Assault",
    "02": "Airborne",
    "03": "Airborne and Air Assault",
    "04": "Amphibious",
    "05": "Airmobile",
    "06": "Bicycle Equipped",
    "07": "Hovercraft",
    "08": "Light",
    "09": "Mechanized",
    "10": "Motorized",
    "11": "Mountain",
    "12": "Ski",
    "13": "Stryker / Medium",
    "14": "Dismounted / Towed",
    "15": "Aviation",
    "16": "Pack Animal",
    "17": "Autonomous Control",
    "18": "Remotely Piloted",
    "31": "Close Range",
    "32": "Short Range",
    "33": "Medium Range",
    "34": "Long Range",
    "35": "Intercontinental",
    "41": "Multiple Rocket Launcher",
    "42": "Single Rocket Launcher",
    "43": "Ground to Air",
    "44": "Ground to Ground",
    "45": "Air to Air",
    "46": "Air to Ground",
    "47": "Air to Subsurface",
    "48": "Anti-Tank",
    "49": "Anti-Ship",
    "51": "Attack / Strike",
    "52": "Bomb",
    "53": "Heavy",
    "54": "Medium",
    "55": "Light",
    "61": "Ballistic",
    "62": "Cruise",
    "63": "Interceptor",
    "71": "Cyber",
    "72": "Electronic Warfare",
    "73": "Signals Intelligence",
    "74": "Unmanned Aerial System",
}

_COMMON_MOD2 = {
    "00": "None",
    "01": "Airborne",
    "02": "Arctic",
    "04": "Bicycle Equipped",
    "07": "Close Range",
    "09": "Decontamination",
    "11": "Dismounted",
    "14": "Electronic Warfare",
    "15": "Explosive Ordnance Disposal",
    "16": "Heavy",
    "19": "Light",
    "20": "Long Range",
    "22": "Medium",
    "24": "Medium Range",
    "26": "Motorized",
    "27": "Mountain",
    "33": "Short Range",
    "35": "Tracked",
    "36": "Wheeled",
    "37": "Towed",
    "38": "Railway",
}


# ======================================================================
# Helpers
# ======================================================================

def _svg_to_pixmap(svg_str: str, size: int) -> QPixmap | None:
    """Convert an SVG string to a QPixmap preserving SVG aspect ratio.

    The rendered image fits inside a ``size × size`` bounding box,
    so rectangular frames (e.g. APP-6 Friend) look proportionally correct.
    """
    try:
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    if not renderer.isValid():
        return None
    natural = renderer.defaultSize()
    if natural.width() > 0 and natural.height() > 0:
        ratio = natural.width() / natural.height()
    else:
        ratio = 1.0
    if ratio >= 1.0:
        w = size
        h = max(1, round(size / ratio))
    else:
        h = size
        w = max(1, round(size * ratio))
    image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(image)


# ======================================================================
# SymbolEditorDockWidget
# ======================================================================

class SymbolEditorDockWidget(QDockWidget):
    """Dock widget editor for a single :class:`MilSymbol` or catalogue entry.

    Signals
    -------
    symbol_updated(str)
        Emitted with the symbol id after the user applies changes.
    symbol_deleted(str)
        Emitted with the symbol id after the user deletes the symbol.
    symbol_placed(object)
        Emitted when the user places a new symbol on the map.
    """

    symbol_updated = pyqtSignal(str)
    symbol_deleted = pyqtSignal(str)
    symbol_placed = pyqtSignal(object)
    # Emitted after the user applies changes to an ORBAT unit (not a map symbol)
    orbat_unit_updated = pyqtSignal(object)  # OrbatUnit

    def __init__(self, iface, action=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Symbol Editor")
        self.setMinimumWidth(340)
        self._iface = iface
        self._action = action

        # Container widget wrapped in a scroll area so content is
        # always accessible even when the dock is shorter than its contents.
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._container)
        self.setWidget(self._scroll)

        # External bindings
        self._layer_manager = None

        # Currently edited symbol (None = nothing selected)
        self._symbol: MilSymbol | None = None

        # If editing an ORBAT unit (no map symbol yet), keep a reference here
        self._orbat_unit = None

        # Map tool reference for placement
        self._map_tool = None

        self._build_ui()
        self._set_editing_enabled(False)
        LOG.debug("SymbolEditorDockWidget created")

    def closeEvent(self, event):  # noqa: N802
        """Uncheck the ribbon action when the dock is closed by the user."""
        if self._action is not None:
            self._action.setChecked(False)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # External bindings / lifecycle helpers
    # ------------------------------------------------------------------

    def reset_to_new_symbol_mode(self) -> None:
        """Switch the editor to 'new symbol' mode (Place button visible, no current symbol)."""
        self._symbol = None
        self._orbat_unit = None
        self.setWindowTitle("Symbol Editor")
        self._set_editing_enabled(True)
        self._place_btn.setVisible(True)
        self._apply_btn.setVisible(False)
        self._delete_btn.setVisible(False)

    def set_layer_manager(self, mgr) -> None:
        self._layer_manager = mgr

    # ------------------------------------------------------------------
    # Public – load a symbol for editing
    # ------------------------------------------------------------------

    def edit_orbat_unit(self, unit) -> None:
        """Open the editor to edit an :class:`OrbatUnit` that has no map symbol.

        Builds a temporary :class:`MilSymbol` from the unit's data so the
        full APP-6(D) editor is reused.  On Apply the changes are written
        back to *unit* and the :pyqtSignal:`orbat_unit_updated` signal is emitted.
        """
        from ..core.models import MilSymbol

        # Build a transient MilSymbol that mirrors the unit
        tmp = MilSymbol(
            id=unit.id,  # same id so update_symbol is a no-op (not in layer)
            sidc=unit.sidc,
            designation=unit.name,
            higher_formation=unit.short_name,
            temporal=unit.temporal,
        )
        self.edit_symbol(tmp)
        # Re-set after edit_symbol (which resets _orbat_unit to None)
        self._orbat_unit = unit
        # Hide place/delete buttons – we only allow Apply for ORBAT units
        self._delete_btn.setVisible(False)
        self.setWindowTitle(f"Symbol Editor  –  {unit.name or 'Unit'}")

    def edit_symbol(self, sym: MilSymbol) -> None:
        """Populate all fields from *sym* and enable editing."""
        self._orbat_unit = None  # entering normal map-symbol edit mode
        self._symbol = sym
        self._populate_from_symbol(sym)
        self._set_editing_enabled(True)
        # In editing mode the Place button is hidden (symbol already on map)
        self._place_btn.setVisible(False)
        self._apply_btn.setVisible(True)
        self._delete_btn.setVisible(True)
        self.adjustSize()
        LOG.debug("Editing symbol %s (SIDC=%s)", sym.id[:8], sym.sidc)

    def load_from_catalog(self, entry: CatalogEntry,
                          identity: StandardIdentity | None = None,
                          echelon: Echelon | None = None) -> None:
        """Initialise the editor from a catalog entry (new symbol mode).

        Parameters
        ----------
        entry : CatalogEntry
            The catalog entry to load.
        identity : StandardIdentity or None
            If given, set the Identity combo to this value.
        echelon : Echelon or None
            If given, set the Echelon combo to this value.

        In this mode the *Apply / Delete* buttons are hidden and the
        *Place on Map* button is shown instead.
        """
        self._symbol = None  # not editing an existing symbol

        self._block_combos(True)

        #  clear text fields
        self._designation_edit.clear()
        self._higher_edit.clear()
        self._comment_edit.clear()
        self._quantity_edit.clear()
        self._staff_comments_edit.clear()
        self._additional_info_edit.clear()
        self._eval_rating_edit.clear()
        self._combat_eff_edit.clear()
        self._dtg_edit.clear()
        self._type_edit.clear()
        self._speed_edit.clear()
        self._altitude_edit.clear()
        self._direction_edit.clear()

        # Identity – carry over from catalog dock
        if identity is not None:
            self._select_combo_data(self._identity_combo, identity)

        # Echelon – carry over from catalog dock
        if echelon is not None:
            self._select_combo_data(self._echelon_combo, echelon)

        # Symbol set
        for i in range(self._symbol_set_combo.count()):
            if self._symbol_set_combo.itemData(i).value == entry.symbol_set:
                self._symbol_set_combo.setCurrentIndex(i)
                break

        # Refresh entity list for the chosen symbol set
        self._refresh_entity_combo()

        # Select the matching entity (match by code + modifiers)
        for i in range(self._entity_combo.count()):
            data = self._entity_combo.itemData(i)
            if data and data.entity_code == entry.entity_code \
               and data.modifier_1 == entry.modifier_1 \
               and data.modifier_2 == entry.modifier_2:
                self._entity_combo.setCurrentIndex(i)
                break

        self._t_start_check.setChecked(False)
        self._t_end_check.setChecked(False)
        self._coord_label.setText("")

        self._block_combos(False)

        # Switch UI mode: show Place, hide Apply/Delete
        self._set_editing_enabled(True)
        self._place_btn.setVisible(True)
        self._apply_btn.setVisible(False)
        self._delete_btn.setVisible(False)

        self._update_preview()
        self.adjustSize()
        LOG.info("Editor loaded from catalog: %s", entry.name)

    def clear_editor(self) -> None:
        """Clear all fields and disable editing."""
        self._symbol = None
        self._designation_edit.clear()
        self._higher_edit.clear()
        self._comment_edit.clear()
        self._quantity_edit.clear()
        self._staff_comments_edit.clear()
        self._additional_info_edit.clear()
        self._eval_rating_edit.clear()
        self._combat_eff_edit.clear()
        self._dtg_edit.clear()
        self._type_edit.clear()
        self._speed_edit.clear()
        self._altitude_edit.clear()
        self._direction_edit.clear()
        self._sidc_label.setText("")
        self._preview_label.clear()
        self._preview_label.setText("No symbol selected")
        self._set_editing_enabled(False)
        self._place_btn.setVisible(False)
        self._apply_btn.setVisible(True)
        self._delete_btn.setVisible(True)

    def set_show_text_modifiers(self, show: bool) -> None:
        pass  # Disabilitato: la visibilità è gestita dal collapse interno.

    def _toggle_text_modifiers(self, checked: bool) -> None:
        """Toggle inner widgets of the modifier group to expand/collapse."""
        layout = self._mod_group.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(checked)
        self.adjustSize()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = self._container_layout
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        container = QWidget()
        container.setStyleSheet(DARK_THEME_SS)
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- Text fields ----
        txt_group = QGroupBox("Core Text")
        txt_layout = QFormLayout(txt_group)

        self._designation_edit = QLineEdit()
        self._designation_edit.setPlaceholderText("Unique Designation (T)")
        txt_layout.addRow("Designation:", self._designation_edit)

        self._higher_edit = QLineEdit()
        self._higher_edit.setPlaceholderText("Higher Formation (M)")
        txt_layout.addRow("Higher form.:", self._higher_edit)

        self._comment_edit = QLineEdit()
        self._comment_edit.setPlaceholderText("General Comment")
        txt_layout.addRow("Comment:", self._comment_edit)

        layout.addWidget(txt_group)

        # ---- Extended Text Modifiers ----
        self._mod_group = QGroupBox("Text Modifiers")
        self._mod_group.setCheckable(True)
        self._mod_group.setChecked(False)
        self._mod_group.toggled.connect(self._toggle_text_modifiers)
        mod_layout = QFormLayout(self._mod_group)

        self._quantity_edit = QLineEdit()
        self._quantity_edit.setPlaceholderText("Quantity (C)")
        mod_layout.addRow("Quantity:", self._quantity_edit)

        self._staff_comments_edit = QLineEdit()
        self._staff_comments_edit.setPlaceholderText("Staff Comments (G)")
        mod_layout.addRow("Staff Cmds:", self._staff_comments_edit)

        self._additional_info_edit = QLineEdit()
        self._additional_info_edit.setPlaceholderText("Additional Info (H)")
        mod_layout.addRow("Add. Info:", self._additional_info_edit)

        self._eval_rating_edit = QLineEdit()
        self._eval_rating_edit.setPlaceholderText("Eval Rating (J)")
        mod_layout.addRow("Eval Rating:", self._eval_rating_edit)

        self._combat_eff_edit = QLineEdit()
        self._combat_eff_edit.setPlaceholderText("Combat Effectiveness (K)")
        mod_layout.addRow("Combat Eff:", self._combat_eff_edit)

        self._dtg_edit = QLineEdit()
        self._dtg_edit.setPlaceholderText("Date-Time Group (W)")
        mod_layout.addRow("DTG:", self._dtg_edit)

        self._type_edit = QLineEdit()
        self._type_edit.setPlaceholderText("Type (V)")
        mod_layout.addRow("Type:", self._type_edit)

        self._speed_edit = QLineEdit()
        self._speed_edit.setPlaceholderText("Speed/Velocity (Z)")
        mod_layout.addRow("Speed:", self._speed_edit)

        self._altitude_edit = QLineEdit()
        self._altitude_edit.setPlaceholderText("Altitude/Depth (X)")
        mod_layout.addRow("Alt/Depth:", self._altitude_edit)

        self._direction_edit = QLineEdit()
        self._direction_edit.setPlaceholderText("Direction in degrees (Q)")
        mod_layout.addRow("Direction:", self._direction_edit)

        # Connect text changes to preview
        self._designation_edit.textChanged.connect(self._on_sym_changed)
        self._higher_edit.textChanged.connect(self._on_sym_changed)
        self._comment_edit.textChanged.connect(self._on_sym_changed)
        self._quantity_edit.textChanged.connect(self._on_sym_changed)
        self._staff_comments_edit.textChanged.connect(self._on_sym_changed)
        self._additional_info_edit.textChanged.connect(self._on_sym_changed)
        self._eval_rating_edit.textChanged.connect(self._on_sym_changed)
        self._combat_eff_edit.textChanged.connect(self._on_sym_changed)
        self._dtg_edit.textChanged.connect(self._on_sym_changed)
        self._type_edit.textChanged.connect(self._on_sym_changed)
        self._speed_edit.textChanged.connect(self._on_sym_changed)
        self._altitude_edit.textChanged.connect(self._on_sym_changed)
        self._direction_edit.textChanged.connect(self._on_sym_changed)

        # ---- Symbology combos ----
        sym_group = QGroupBox("Symbology (APP-6D)")
        sym_layout = QFormLayout(sym_group)

        self._frame_combo = QComboBox()
        self._frame_combo.addItem("Reality (Solid)", "0")
        self._frame_combo.addItem("Exercise (Dashed)", "1")
        self._frame_combo.addItem("Simulation (Dotted)", "2")
        self._frame_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Context/Frame:", self._frame_combo)

        self._identity_combo = QComboBox()
        for si in StandardIdentity:
            label = STANDARD_IDENTITY_LABELS.get(
                si, si.name.replace("_", " ").title()
            )
            self._identity_combo.addItem(label, si)
        self._identity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Identity:", self._identity_combo)

        self._symbol_set_combo = QComboBox()
        for ss in SymbolSet:
            label = SYMBOL_SET_NAMES.get(ss.value, ss.name)
            self._symbol_set_combo.addItem(label, ss)
        self._symbol_set_combo.currentIndexChanged.connect(
            self._on_symbol_set_changed
        )
        sym_layout.addRow("Symbol Set:", self._symbol_set_combo)

        self._entity_combo = QComboBox()
        self._entity_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Entity:", self._entity_combo)

        self._mod1_combo = QComboBox()
        for i in range(0, 100):
            code = f"{i:02d}"
            label = _COMMON_MOD1.get(code, f"Modifier {code}")
            self._mod1_combo.addItem(f"{code} - {label}", code)
        self._mod1_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 1:", self._mod1_combo)

        self._mod2_combo = QComboBox()
        for i in range(0, 100):
            code = f"{i:02d}"
            label = _COMMON_MOD2.get(code, f"Modifier {code}")
            self._mod2_combo.addItem(f"{code} - {label}", code)
        self._mod2_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Modifier 2:", self._mod2_combo)

        self._echelon_combo = QComboBox()
        for ech in Echelon:
            self._echelon_combo.addItem(
                ech.name.replace("_", " ").title(), ech
            )
        self._echelon_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Echelon:", self._echelon_combo)

        self._hqtf_combo = QComboBox()
        for h in HqTfDummy:
            self._hqtf_combo.addItem(
                h.name.replace("_", " ").title(), h
            )
        self._hqtf_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("HQ/TF/Dummy:", self._hqtf_combo)

        self._status_combo = QComboBox()
        for st in Status:
            self._status_combo.addItem(st.name.replace("_", " ").title(), st)
        self._status_combo.currentIndexChanged.connect(self._on_sym_changed)
        sym_layout.addRow("Status:", self._status_combo)

        # Preview
        preview_row = QHBoxLayout()
        self._preview_label = QLabel("No symbol selected")
        self._preview_label.setFixedSize(_PREVIEW_SIZE, _PREVIEW_SIZE)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "QLabel { background: white; border: 1px solid #ccc; }"
        )
        preview_row.addStretch()
        preview_row.addWidget(self._preview_label)
        preview_row.addStretch()
        sym_layout.addRow(preview_row)

        self._sidc_label = QLabel("")
        self._sidc_label.setAlignment(Qt.AlignCenter)
        self._sidc_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; color: #666;"
        )
        sym_layout.addRow(self._sidc_label)

        layout.addWidget(sym_group)
        layout.addWidget(self._mod_group)

        # ---- Temporal ----
        temp_group = QGroupBox("Temporal Validity (optional)")
        temp_layout = QFormLayout(temp_group)

        self._t_start_edit = QDateTimeEdit()
        self._t_start_edit.setCalendarPopup(True)
        self._t_start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._t_start_edit.setDateTime(
            QDateTime(QDateTime.currentDateTime().date().year(), 1, 1, 0, 0, 0)
        )
        self._t_start_check = self._make_optional_datetime(
            self._t_start_edit, temp_layout, "Start:"
        )

        self._t_end_edit = QDateTimeEdit()
        self._t_end_edit.setCalendarPopup(True)
        self._t_end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        _now = QDateTime.currentDateTime()
        _end_month = _now.date().month() + 6
        _end_year = _now.date().year() + (_end_month - 1) // 12
        _end_month = (_end_month - 1) % 12 + 1
        self._t_end_edit.setDateTime(
            QDateTime(_end_year, _end_month, _now.date().day(), 23, 59, 59)
        )
        self._t_end_check = self._make_optional_datetime(
            self._t_end_edit, temp_layout, "End:"
        )

        layout.addWidget(temp_group)

        # ---- Buttons ----
        btn_row = QHBoxLayout()

        self._place_btn = QPushButton("Place on Map")
        self._place_btn.setToolTip("Place this symbol on the map")
        self._place_btn.setStyleSheet(
            "QPushButton { font-weight: bold; }"
        )
        self._place_btn.clicked.connect(self._on_place_on_map)
        self._place_btn.setVisible(False)
        btn_row.addWidget(self._place_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setToolTip("Save changes to this symbol")
        self._apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self._apply_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setToolTip("Remove this symbol from the map")
        self._delete_btn.setStyleSheet("QPushButton { color: #ffffff; background: #cc3333; }")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        layout.addLayout(btn_row)

        # ---- Coordinate info ----
        self._coord_label = QLabel("")
        self._coord_label.setStyleSheet(
            "font-size: 10px; color: #666; padding: 2px;"
        )
        layout.addWidget(self._coord_label)

        layout.addStretch()

        outer.addWidget(container)

    @staticmethod
    def _make_optional_datetime(dt_edit, form_layout, label):
        cb = QCheckBox()
        cb.setChecked(False)
        dt_edit.setEnabled(False)
        cb.toggled.connect(dt_edit.setEnabled)
        row = QHBoxLayout()
        row.addWidget(cb)
        row.addWidget(dt_edit, 1)
        form_layout.addRow(label, row)
        return cb

    # ------------------------------------------------------------------
    # Enable / disable all fields
    # ------------------------------------------------------------------

    def _set_editing_enabled(self, enabled: bool) -> None:
        for w in (
            self._designation_edit,
            self._higher_edit,
            self._comment_edit,
            self._quantity_edit,
            self._staff_comments_edit,
            self._additional_info_edit,
            self._eval_rating_edit,
            self._combat_eff_edit,
            self._dtg_edit,
            self._type_edit,
            self._speed_edit,
            self._altitude_edit,
            self._direction_edit,
            self._identity_combo,
            self._symbol_set_combo,
            self._entity_combo,
            self._echelon_combo,
            self._hqtf_combo,
            self._status_combo,
            self._t_start_check,
            self._t_start_edit,
            self._t_end_check,
            self._t_end_edit,
            self._place_btn,
            self._apply_btn,
            self._delete_btn,
        ):
            w.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Populate from MilSymbol
    # ------------------------------------------------------------------

    def _populate_from_symbol(self, sym: MilSymbol) -> None:
        # Block signals to avoid recursive updates during population
        self._block_combos(True)

        self._designation_edit.setText(sym.designation)
        self._higher_edit.setText(sym.higher_formation)
        self._comment_edit.setText(sym.comment)
        self._quantity_edit.setText(getattr(sym, 'quantity', ''))
        self._staff_comments_edit.setText(getattr(sym, 'staff_comments', ''))
        self._additional_info_edit.setText(getattr(sym, 'additional_information', ''))
        self._eval_rating_edit.setText(getattr(sym, 'evaluation_rating', ''))
        self._combat_eff_edit.setText(getattr(sym, 'combat_effectiveness', ''))
        self._dtg_edit.setText(getattr(sym, 'dtg', ''))
        self._type_edit.setText(getattr(sym, 'type_str', ''))
        self._speed_edit.setText(getattr(sym, 'speed', ''))
        self._altitude_edit.setText(getattr(sym, 'altitude_depth', ''))

        dr = getattr(sym, 'direction', None)
        self._direction_edit.setText(str(dr) if dr is not None else '')

        # Parse SIDC
        try:
            sidc = SIDCClass.parse(sym.sidc)
        except ValueError:
            sidc = SIDCClass()

        # Identity
        self._select_combo_data(self._identity_combo, sidc.standard_identity)

        # Context/Frame string matching
        for i in range(self._frame_combo.count()):
            if self._frame_combo.itemData(i) == sidc.context.value:
                self._frame_combo.setCurrentIndex(i)
                break

        # SIDC modifier combos
        for i in range(self._mod1_combo.count()):
            if self._mod1_combo.itemData(i) == sidc.modifier1:
                self._mod1_combo.setCurrentIndex(i)
                break
        for i in range(self._mod2_combo.count()):
            if self._mod2_combo.itemData(i) == sidc.modifier2:
                self._mod2_combo.setCurrentIndex(i)
                break

        # Symbol set
        self._select_combo_data(self._symbol_set_combo, sidc.symbol_set)

        # Populate entities then select
        self._refresh_entity_combo()
        entity_code = sidc.entity
        for i in range(self._entity_combo.count()):
            data = self._entity_combo.itemData(i)
            if data and data.entity_code == entity_code:
                self._entity_combo.setCurrentIndex(i)
                break

        # Echelon – compare .value strings
        for i in range(self._echelon_combo.count()):
            if self._echelon_combo.itemData(i).value == sidc.amplifier:
                self._echelon_combo.setCurrentIndex(i)
                break

        # HQ/TF/Dummy
        self._select_combo_data(self._hqtf_combo, sidc.hq_tf_dummy)

        # Status
        self._select_combo_data(self._status_combo, sidc.status)

        # Temporal
        self._t_start_check.setChecked(False)
        self._t_end_check.setChecked(False)
        if sym.temporal.start:
            from qgis.PyQt.QtCore import QDateTime
            self._t_start_check.setChecked(True)
            self._t_start_edit.setDateTime(
                QDateTime.fromString(sym.temporal.start, Qt.ISODate)
            )
        if sym.temporal.end:
            from qgis.PyQt.QtCore import QDateTime
            self._t_end_check.setChecked(True)
            self._t_end_edit.setDateTime(
                QDateTime.fromString(sym.temporal.end, Qt.ISODate)
            )

        # Coordinate info
        self._coord_label.setText(
            f"Location: {sym.longitude:.6f}, {sym.latitude:.6f}"
        )

        self._block_combos(False)
        self._update_preview()

    @staticmethod
    def _select_combo_data(combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _block_combos(self, block: bool) -> None:
        for w in (
            self._identity_combo,
            self._symbol_set_combo,
            self._entity_combo,
            self._echelon_combo,
            self._hqtf_combo,
            self._status_combo,
        ):
            w.blockSignals(block)

    # ------------------------------------------------------------------
    # Entity combo refresh
    # ------------------------------------------------------------------

    def _on_symbol_set_changed(self, _idx: int = 0) -> None:
        self._refresh_entity_combo()
        self._on_sym_changed()

    def _refresh_entity_combo(self) -> None:
        ss: SymbolSet = self._symbol_set_combo.currentData()
        self._entity_combo.blockSignals(True)
        self._entity_combo.clear()
        self._entity_combo.addItem("(generic)", None)

        entries = entries_by_symbol_set(ss.value)
        for entry in entries:
            self._entity_combo.addItem(entry.name, entry)

        self._entity_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # SIDC builder & preview
    # ------------------------------------------------------------------

    def _build_sidc(self) -> str:
        identity: StandardIdentity = self._identity_combo.currentData()
        ss: SymbolSet = self._symbol_set_combo.currentData()
        echelon: Echelon = self._echelon_combo.currentData()
        hqtf: HqTfDummy = self._hqtf_combo.currentData()
        status: Status = self._status_combo.currentData()

        entry: CatalogEntry | None = self._entity_combo.currentData()
        entity_code = entry.entity_code if entry else "000000"

        ctx = self._frame_combo.currentData() or "0"
        m1 = self._mod1_combo.currentData() or "00"
        m2 = self._mod2_combo.currentData() or "00"

        return (
            f"10"
            f"{ctx}"
            f"{identity.value}"
            f"{ss.value}"
            f"{status.value}"
            f"{hqtf.value}"
            f"{echelon.value}"
            f"{entity_code}"
            f"{m1}"
            f"{m2}"
        )

    def _on_sym_changed(self, _idx: int = 0) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        sidc = self._build_sidc()
        self._sidc_label.setText(sidc)
        try:
            val_dir = self._direction_edit.text().strip()
            direction_float = float(val_dir) if val_dir else None
        except ValueError:
            direction_float = None

        try:
            svg = cached_svg(
                sidc_code=sidc,
                designation=self._designation_edit.text().strip(),
                higher_formation=self._higher_edit.text().strip(),
                quantity=self._quantity_edit.text().strip(),
                staff_comments=self._staff_comments_edit.text().strip(),
                additional_information=self._additional_info_edit.text().strip(),
                evaluation_rating=self._eval_rating_edit.text().strip(),
                combat_effectiveness=self._combat_eff_edit.text().strip(),
                dtg=self._dtg_edit.text().strip(),
                type_str=self._type_edit.text().strip(),
                speed=self._speed_edit.text().strip(),
                altitude_depth=self._altitude_edit.text().strip(),
                direction=direction_float
            )
            pm = _svg_to_pixmap(svg, _PREVIEW_SIZE)
            if pm:
                self._preview_label.setPixmap(pm)
            else:
                self._preview_label.setText("?")
        except ValueError:
            self._preview_label.setText("?")

    # ------------------------------------------------------------------
    # Apply changes
    # ------------------------------------------------------------------

    def _on_apply(self) -> None:
        sym = self._symbol
        if sym is None:
            return

        sym.sidc = self._build_sidc()
        sym.designation = self._designation_edit.text().strip()
        sym.higher_formation = self._higher_edit.text().strip()
        sym.comment = self._comment_edit.text().strip()
        sym.quantity = self._quantity_edit.text().strip()
        sym.staff_comments = self._staff_comments_edit.text().strip()
        sym.additional_information = self._additional_info_edit.text().strip()
        sym.evaluation_rating = self._eval_rating_edit.text().strip()
        sym.combat_effectiveness = self._combat_eff_edit.text().strip()
        sym.dtg = self._dtg_edit.text().strip()
        sym.type_str = self._type_edit.text().strip()
        sym.speed = self._speed_edit.text().strip()
        sym.altitude_depth = self._altitude_edit.text().strip()

        try:
            val_dir = self._direction_edit.text().strip()
            sym.direction = float(val_dir) if val_dir else None
        except ValueError:
            sym.direction = None

        # Temporal
        if self._t_start_check.isChecked():
            sym.temporal.start = (
                self._t_start_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            sym.temporal.start = ""
        if self._t_end_check.isChecked():
            sym.temporal.end = (
                self._t_end_edit.dateTime().toString(Qt.ISODate)
            )
        else:
            sym.temporal.end = None

        # If this is an ORBAT unit edit, write back to the unit and signal
        if self._orbat_unit is not None:
            unit = self._orbat_unit
            unit.sidc = sym.sidc
            unit.name = sym.designation or unit.name
            unit.short_name = sym.higher_formation or unit.short_name
            unit.temporal = sym.temporal
            # If the unit also has a live map symbol, update the layer too
            if self._layer_manager is not None:
                self._layer_manager.update_symbol(sym)
                self.symbol_updated.emit(sym.id)
            self._update_preview()
            self.orbat_unit_updated.emit(unit)
            self.setWindowTitle("Symbol Editor")
            LOG.info("ORBAT unit %s updated via editor (SIDC=%s)", unit.name, unit.sidc)
            return

        # Persist to layer (symbol without ORBAT link)
        if self._layer_manager is not None:
            self._layer_manager.update_symbol(sym)

        self._update_preview()
        self.symbol_updated.emit(sym.id)
        LOG.info("Symbol %s updated (SIDC=%s)", sym.id[:8], sym.sidc)

    # ------------------------------------------------------------------
    # Delete symbol
    # ------------------------------------------------------------------

    def _on_delete(self) -> None:
        sym = self._symbol
        if sym is None:
            return

        reply = QMessageBox.question(
            self,
            "Delete Symbol",
            f"Delete symbol '{sym.designation or sym.sidc}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        sym_id = sym.id
        if self._layer_manager is not None:
            self._layer_manager.remove_symbol(sym_id)

        self.clear_editor()
        self.symbol_deleted.emit(sym_id)
        LOG.info("Symbol %s deleted", sym_id[:8])

    # ------------------------------------------------------------------
    # Place on Map (new symbol from editor)
    # ------------------------------------------------------------------

    def _on_place_on_map(self) -> None:
        """Activate the placement map tool with the current editor SIDC."""
        sidc = self._build_sidc()
        designation = self._designation_edit.text().strip()
        higher_formation = self._higher_edit.text().strip()

        from .map_tool import SymbolPlacementTool

        canvas = self._iface.mapCanvas()
        self._map_tool = SymbolPlacementTool(
            canvas=canvas,
            sidc=sidc,
            designation=designation,
            higher_formation=higher_formation,
        )
        self._map_tool.symbol_placed.connect(self._on_symbol_placed)
        canvas.setMapTool(self._map_tool)
        LOG.info("Editor placement tool activated for SIDC=%s", sidc)

    def _on_symbol_placed(self, sym: MilSymbol) -> None:
        """Handle the symbol_placed signal from the map tool."""
        # Apply extra data from the editor to the new symbol
        if self._t_start_check.isChecked():
            sym.temporal.start = (
                self._t_start_edit.dateTime().toString(Qt.ISODate)
            )
        if self._t_end_check.isChecked():
            sym.temporal.end = (
                self._t_end_edit.dateTime().toString(Qt.ISODate)
            )

        sym.comment = self._comment_edit.text().strip()
        sym.quantity = self._quantity_edit.text().strip()
        sym.staff_comments = self._staff_comments_edit.text().strip()
        sym.additional_information = self._additional_info_edit.text().strip()
        sym.evaluation_rating = self._eval_rating_edit.text().strip()
        sym.combat_effectiveness = self._combat_eff_edit.text().strip()
        sym.dtg = self._dtg_edit.text().strip()
        sym.type_str = self._type_edit.text().strip()
        sym.speed = self._speed_edit.text().strip()
        sym.altitude_depth = self._altitude_edit.text().strip()

        try:
            val_dir = self._direction_edit.text().strip()
            sym.direction = float(val_dir) if val_dir else None
        except ValueError:
            sym.direction = None

        if self._layer_manager is not None:
            self._layer_manager.add_symbol(sym)

        # Keep the new symbol loaded in the editor for further edits
        self._symbol = sym
        self._set_editing_enabled(True)
        self._place_btn.setVisible(False)
        self._delete_btn.setVisible(True)
        self._coord_label.setText(
            f"Location: {sym.longitude:.6f}, {sym.latitude:.6f}"
        )

        self.symbol_placed.emit(sym)
        LOG.info("Symbol placed from editor: %s", sym.id)

# -*- coding: utf-8 -*-
"""GUI components – catalog dock, map tool, symbol layer, settings."""

# ======================================================================
# Shared stylesheet (compatible with both light and dark QGIS themes)
# ======================================================================
# Qt widgets default to black text in light mode; this stylesheet ensures
# the panel container always has a light background so text is legible.

DARK_THEME_SS = """
    QWidget {
        background: #f0f0f0;
        color: #1a1a1a;
    }
    QGroupBox {
        font-weight: bold;
    }
    QTreeWidget::item:selected {
        background: #3399ff;
        color: #ffffff;
    }
"""

# -*- coding: utf-8 -*-
"""Utility functions for the QGIS APP-6(D) plugin."""

import os


def plugin_path(*paths: str) -> str:
    """Return an absolute path relative to the plugin's root directory.

    Example::

        icon = plugin_path("icons", "milsymb.svg")
    """
    root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(root, *paths)


def milsymb_data_dir() -> str:
    """Return (and create) the user data directory for QGIS APP-6(D).

    Uses ``QgsApplication.qgisSettingsDirPath()`` when QGIS is available
    so the directory follows the standard QGIS profile location.
    Falls back to ``~/.qgis_milsymb`` for headless / test environments.
    """
    try:
        from qgis.core import QgsApplication  # noqa: PLC0415
        base = os.path.join(QgsApplication.qgisSettingsDirPath(), "qgis_milsymb")
    except Exception:
        base = os.path.expanduser("~/.qgis_milsymb")
    os.makedirs(base, exist_ok=True)
    return base

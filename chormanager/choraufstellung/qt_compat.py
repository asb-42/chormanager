"""
Qt Compatibility Layer
=======================

Allows the code to work with both PyQt5 and PyQt6.

In addition to ``exec_qt`` (which handles ``exec()`` vs ``exec_()``),
this module also re-exports every Qt class that the choraufstellung
subapp needs and assigns the enum aliases (``QFrame.Panel`` etc.)
that PyQt6 no longer exposes for backward compatibility.

Fallback classes (``FallbackSinger``, ``FallbackOptimizerDialog``,
``FallbackGridEngine``) are provided so that ``main.py`` does not
need a ``try/except`` block at import time. They are only used when
the corresponding module (e.g. ``singer_model``, ``core.grid_engine``)
fails to import, which in practice never happens — but the import
isolation makes the code easier to read.
"""

try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtPrintSupport import *
    QT_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtPrintSupport import *
    QT_VERSION = 5


# --- PyQt5/PyQt6 enum compatibility aliases -------------------------
# PyQt6 split monolithic enums (e.g. Qt.AlignCenter) into scoped
# enums (Qt.AlignmentFlag.AlignCenter). The choraufstellung codebase
# uses the PyQt5 names everywhere, so we re-create the aliases on the
# module/class level here so callers can keep using ``Qt.AlignCenter``
# and ``QFrame.Panel`` regardless of the Qt version.
if QT_VERSION >= 6:
    QFrame.Panel = QFrame.Shape.Panel
    QFrame.Raised = QFrame.Shadow.Raised
    QFrame.Sunken = QFrame.Shadow.Sunken
    QFrame.HLine = QFrame.Shape.HLine
    QFrame.VLine = QFrame.Shape.VLine
    QFrame.StyledPanel = QFrame.Shape.StyledPanel
    QFrame.NoFrame = QFrame.Shape.NoFrame

    Qt.Horizontal = Qt.Orientation.Horizontal
    Qt.Vertical = Qt.Orientation.Vertical
    Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt.AlignRight = Qt.AlignmentFlag.AlignRight
    Qt.AlignTop = Qt.AlignmentFlag.AlignTop
    Qt.LeftButton = Qt.MouseButton.LeftButton
    Qt.RightButton = Qt.MouseButton.RightButton
    Qt.ControlModifier = Qt.KeyboardModifier.ControlModifier


# --- exec_qt compatibility helper -----------------------------------
def exec_qt(obj, action=None):
    """Handle exec() vs exec_() difference between Qt versions.

    Works for QDialog.exec(), QMenu.exec(), QDrag.exec(), etc.

    Args:
        obj: The Qt object to call exec on (QDialog, QMenu, QDrag, etc.)
        action: Optional drag action (Qt.CopyAction, Qt.MoveAction, etc.)
    """
    if action is None:
        if QT_VERSION >= 6:
            return obj.exec()
        else:
            return obj.exec_()
    else:
        if QT_VERSION >= 6:
            return obj.exec(action)
        else:
            return obj.exec_(action)


# --- Fallback classes (used when domain modules fail to import) -----
# These are intentionally tiny and only carry the attributes/methods
# the choraufstellung subapp actually touches. They live here so
# ``main.py`` does not need a ``try/except`` around its imports.
class FallbackSinger:
    """Minimal stand-in for ``singer_model.Singer``."""

    def __init__(self, name, voice_group, height=0, singer_id="1"):
        self.name = name
        self.voice_group = voice_group
        self.height = height
        self.singer_id = singer_id


class FallbackOptimizerDialog(QDialog):
    """Minimal stand-in for ``ui.optimizer_dialog.OptimizerDialog``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Optimierung nicht verfügbar")


class FallbackGridEngine:
    """Minimal stand-in for ``core.grid_engine.GridEngine``."""

    def __init__(self, *args, **kwargs):
        pass

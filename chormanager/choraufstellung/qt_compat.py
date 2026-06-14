"""
Qt Compatibility Layer (A2-FIX-A: PyQt6-only).

Re-exports every Qt class that the choraufstellung subapp needs and
assigns the enum aliases (``QFrame.Panel`` etc.) that PyQt6 no longer
exposes for backward compatibility. Also provides the ``exec_qt``
helper for the ``exec()`` vs ``exec_()`` difference.

A2-FIX-A: PyQt5 is no longer supported. The ``FallbackSinger``,
``FallbackOptimizerDialog`` and ``FallbackGridEngine`` classes that
used to live here have been removed (they were dead code — the
corresponding domain modules always import cleanly on PyQt6). All
importers can now safely do ``from PyQt6.QtWidgets import ...``
directly; ``qt_compat`` remains as a thin compatibility shim for the
``exec_qt`` helper and the enum aliases.
"""

from PyQt6.QtWidgets import *  # noqa: F401,F403
from PyQt6.QtCore import *  # noqa: F401,F403
from PyQt6.QtGui import *  # noqa: F401,F403
from PyQt6.QtPrintSupport import *  # noqa: F401,F403
QT_VERSION = 6


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


# A2-FIX-A: Fallback classes have been removed. The corresponding
# domain modules (singer_model, optimizer_dialog, grid_engine) import
# cleanly on PyQt6 and the previous "in case of import error" stand-ins
# were dead code. Use the real classes directly.

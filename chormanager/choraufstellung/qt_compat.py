"""
Qt Compatibility Layer

Allows the code to work with both PyQt5 and PyQt6.
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
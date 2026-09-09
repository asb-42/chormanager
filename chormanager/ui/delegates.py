"""Shared Qt delegates for ChorManager."""

from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import QSize


class PaddedDelegate(QStyledItemDelegate):
    """Custom delegate with padding for better text display."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height() + 10)

    def paint(self, painter, option, index):
        option.rect = option.rect.adjusted(0, 5, 0, -5)
        super().paint(painter, option, index)

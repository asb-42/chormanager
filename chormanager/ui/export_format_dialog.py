"""Export-Format dialog for the project-wide availability export.

Asks the user to pick a target format (PDF or ODT) and optionally
a destination file via QFileDialog. Kept deliberately small: the heavy
lifting (matrix building, rendering) happens in ``core/``.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


#: Supported export formats. Keys are the canonical name used in the
#: renderer module imports; values are a human label and a default
#: file extension.
SUPPORTED_FORMATS = {
    "pdf": {"label": "PDF-Datei (.pdf)", "ext": ".pdf"},
    "odt": {"label": "LibreOffice Writer (.odt)", "ext": ".odt"},
}


class ExportFormatDialog(QDialog):
    """Dialog that lets the user choose the export format.

    The dialog has a radio group for the format and the standard
    OK/Cancel buttons. When OK is pressed, the chosen format is
    available via :attr:`selected_format`. The dialog does NOT open
    a file dialog — the caller (main_window) does that with
    :meth:`get_save_path` after the user clicks OK.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        default_format: str = "pdf",
        title: str = "Zusagen/Absagen-Liste exportieren",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.setModal(True)

        self._button_group = QButtonGroup(self)
        self._radios: dict[str, QRadioButton] = {}
        self.selected_format: str = default_format

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Bitte wählen Sie das gewünschte Ausgabeformat für die "
            "Zusagen- und Absagen-Liste:"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for fmt_key, fmt_def in SUPPORTED_FORMATS.items():
            radio = QRadioButton(fmt_def["label"])
            self._button_group.addButton(radio)
            self._radios[fmt_key] = radio
            radio.toggled.connect(
                lambda checked, k=fmt_key: self._on_radio_toggled(k, checked)
            )
            if fmt_key == self.selected_format:
                radio.setChecked(True)
            layout.addWidget(radio)

        # Spacer + standard button box
        layout.addStretch(1)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_radio_toggled(self, fmt_key: str, checked: bool) -> None:
        if checked:
            self.selected_format = fmt_key

    @classmethod
    def get_save_path(
        cls,
        parent: QWidget | None,
        fmt_key: str,
        default_filename: str,
    ) -> Path | None:
        """Open a QFileDialog and return the chosen path (or None)."""
        ext = SUPPORTED_FORMATS[fmt_key]["ext"]
        filt = f"{'PDF' if fmt_key == 'pdf' else 'LibreOffice/ODT'} (*{ext})"
        path_str, _ = QFileDialog.getSaveFileName(
            parent,
            "Zusagen/Absagen-Liste speichern",
            default_filename,
            filt,
        )
        if not path_str:
            return None
        path = Path(path_str)
        # Auto-append the extension if the user didn't add it
        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        return path

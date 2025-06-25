# ui/log_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title = QLabel("Log Output")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)

        # Log output area
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 10))

        layout.addWidget(title)
        layout.addWidget(self.log_output)

    def append_log(self, message: str):
        """Append a new line to the log output."""
        self.log_output.appendPlainText(message)

    def clear_log(self):
        """Clear the log display."""
        self.log_output.clear()

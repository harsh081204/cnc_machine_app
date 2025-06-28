from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import os
import json

class MacroTab(QWidget):
    macro_executed = Signal(str)  # Emitted when a macro is played
    MACRO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'macros.json')

    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self.serial_manager = serial_manager
        self.macros = []
        self.init_ui()
        self.load_macros()

    def init_ui(self):
        layout = QHBoxLayout(self)
        # Macro list
        self.macro_list = QListWidget()
        self.macro_list.setFixedWidth(180)
        self.macro_list.itemClicked.connect(self.display_macro)
        layout.addWidget(self.macro_list)
        # Macro editor and controls
        editor_layout = QVBoxLayout()
        self.macro_name = QLineEdit()
        self.macro_name.setPlaceholderText("Macro Name")
        self.macro_editor = QTextEdit()
        self.macro_editor.setPlaceholderText("Write G-code here...")
        btn_row = QHBoxLayout()
        self.save_macro_btn = QPushButton(QIcon.fromTheme("document-save"), "Save")
        self.save_macro_btn.clicked.connect(self.save_macro)
        self.delete_macro_btn = QPushButton(QIcon.fromTheme("edit-delete"), "Delete")
        self.delete_macro_btn.clicked.connect(self.delete_macro)
        self.play_macro_btn = QPushButton(QIcon.fromTheme("media-playback-start"), "Play")
        self.play_macro_btn.clicked.connect(self.play_macro)
        self.load_gcode_btn = QPushButton(QIcon.fromTheme("document-open"), "Load G-Code")
        self.load_gcode_btn.clicked.connect(self.load_gcode_file)
        btn_row.addWidget(self.save_macro_btn)
        btn_row.addWidget(self.delete_macro_btn)
        btn_row.addWidget(self.play_macro_btn)
        btn_row.addWidget(self.load_gcode_btn)
        editor_layout.addWidget(self.macro_name)
        editor_layout.addWidget(self.macro_editor)
        editor_layout.addLayout(btn_row)
        layout.addLayout(editor_layout)

    def load_macros(self):
        # Try to load from file, else use defaults
        try:
            if os.path.exists(self.MACRO_FILE):
                with open(self.MACRO_FILE, 'r', encoding='utf-8') as f:
                    self.macros = json.load(f)
            else:
                self.macros = [
                    {"name": "Home All", "gcode": "G28"},
                    {"name": "Unlock", "gcode": "$X"},
                ]
        except Exception as e:
            QMessageBox.warning(self, "Macro Load Error", f"Could not load macros: {e}")
            self.macros = [
                {"name": "Home All", "gcode": "G28"},
                {"name": "Unlock", "gcode": "$X"},
            ]
        self.refresh_macro_list()

    def refresh_macro_list(self):
        self.macro_list.clear()
        for macro in self.macros:
            self.macro_list.addItem(macro["name"])

    def display_macro(self, item):
        idx = self.macro_list.row(item)
        macro = self.macros[idx]
        self.macro_name.setText(macro["name"])
        self.macro_editor.setText(macro["gcode"])

    def save_macros_to_file(self):
        try:
            os.makedirs(os.path.dirname(self.MACRO_FILE), exist_ok=True)
            with open(self.MACRO_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.macros, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Macro Save Error", f"Could not save macros: {e}")

    def save_macro(self):
        name = self.macro_name.text().strip()
        gcode = self.macro_editor.toPlainText().strip()
        if not name or not gcode:
            QMessageBox.warning(self, "Error", "Macro name and G-code required.")
            return
        # Check if editing existing
        for macro in self.macros:
            if macro["name"] == name:
                macro["gcode"] = gcode
                break
        else:
            self.macros.append({"name": name, "gcode": gcode})
        self.refresh_macro_list()
        self.save_macros_to_file()

    def delete_macro(self):
        idx = self.macro_list.currentRow()
        if idx >= 0:
            self.macros.pop(idx)
            self.refresh_macro_list()
            self.macro_name.clear()
            self.macro_editor.clear()
            self.save_macros_to_file()

    def play_macro(self):
        gcode = self.macro_editor.toPlainText()
        for line in gcode.splitlines():
            line = line.strip()
            if line:
                self.serial_manager.send_command(line)
        self.macro_executed.emit(gcode)

    def load_gcode_file(self):
        """Load a G-code file from the file system"""
        # Get the user's desktop path
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # Open file dialog starting from desktop
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load G-Code File",
            desktop_path,
            "G-Code Files (*.gcode *.nc *.g *.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Read the G-code file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    gcode_content = f.read()
                
                # Extract filename without extension for macro name
                filename = os.path.splitext(os.path.basename(file_path))[0]
                
                # Set the macro name and content
                self.macro_name.setText(filename)
                self.macro_editor.setText(gcode_content)
                
                # Show success message
                QMessageBox.information(
                    self, 
                    "G-Code Loaded", 
                    f"Successfully loaded G-code from:\n{os.path.basename(file_path)}\n\nLines loaded: {len(gcode_content.splitlines())}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Load Error", 
                    f"Could not load G-code file:\n{str(e)}"
                ) 
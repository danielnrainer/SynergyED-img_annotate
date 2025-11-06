"""
Preset management module for TEM Image Editor.
Handles preset storage, loading, and the preset management dialog.
"""

import json
from pathlib import Path
from typing import Dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialogButtonBox
)


class PresetManager(QDialog):
    """Dialog for managing imaging mode presets."""
    
    def __init__(self, presets: Dict[str, float], parent=None):
        super().__init__(parent)
        self.presets = presets.copy()
        self.setWindowTitle("Manage Presets")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Table for presets
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Mode Name", "nm per pixel"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.populate_table()
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Preset")
        add_btn.clicked.connect(self.add_preset)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_preset)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.resize(400, 300)
        
    def populate_table(self):
        self.table.setRowCount(len(self.presets))
        for row, (name, value) in enumerate(sorted(self.presets.items())):
            name_item = QTableWidgetItem(name)
            value_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, value_item)
            
    def add_preset(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("New Mode"))
        self.table.setItem(row, 1, QTableWidgetItem("1.0"))
        
    def remove_preset(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            
    def get_presets(self) -> Dict[str, float]:
        """Get the updated presets from the table."""
        presets = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            if name_item and value_item:
                try:
                    name = name_item.text().strip()
                    value = float(value_item.text())
                    if name and value > 0:
                        presets[name] = value
                except ValueError:
                    pass
        return presets


class PresetStorage:
    """Handles loading and saving presets to disk."""
    
    @staticmethod
    def get_preset_file() -> Path:
        """Get the path to the preset file."""
        return Path(__file__).parent / "tem_presets.json"
    
    @staticmethod
    def load_presets() -> Dict[str, float]:
        """Load presets from JSON file."""
        preset_file = PresetStorage.get_preset_file()
        
        # Default presets
        presets = {
            "Standard": 35.6,
            "Local Map": 80.5,
            "Reference": 16.0,
            "In focus": 32.9,
            "High Res": 5.3,
            "Custom": 1.0
        }
        
        if preset_file.exists():
            try:
                with open(preset_file, 'r') as f:
                    loaded_presets = json.load(f)
                    presets.update(loaded_presets)
            except Exception as e:
                print(f"Error loading presets: {e}")
        
        return presets
    
    @staticmethod
    def save_presets(presets: Dict[str, float]):
        """Save presets to JSON file."""
        preset_file = PresetStorage.get_preset_file()
        try:
            with open(preset_file, 'w') as f:
                json.dump(presets, f, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")

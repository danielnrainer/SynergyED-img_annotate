from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

class QCollapsibleBox(QWidget):
    """A custom collapsible box widget"""
    
    def __init__(self, title="", parent=None, expanded=True):
        super().__init__(parent)
        
        self.title = title
        # Set initial arrow based on expanded state
        arrow = "▼" if expanded else "▶"
        self.toggleButton = QPushButton(f"{arrow} {title}")
        self.toggleButton.setStyleSheet("text-align: left; padding: 5px;")
        self.toggleButton.setCheckable(True)
        self.toggleButton.setChecked(expanded)
        self.toggleButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.contentWidget = QWidget()
        self.contentWidget.setVisible(expanded)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggleButton)
        lay.addWidget(self.contentWidget)
        
        self.toggleButton.toggled.connect(self.toggle)
    
    def toggle(self, checked):
        self.contentWidget.setVisible(checked)
        # Update the arrow icon based on expanded/collapsed state
        if checked:
            self.toggleButton.setText(f"▼ {self.title}")
        else:
            self.toggleButton.setText(f"▶ {self.title}")
        
    def setContentLayout(self, layout):
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        self.contentWidget.setLayout(layout)
        
        self.toggleButton.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 6px 8px;
                margin: 0px;
                border: 1px solid #d0d0d0;
                background-color: #f5f5f5;
                border-radius: 3px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border: 1px solid #b0b0b0;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
            }
        """)

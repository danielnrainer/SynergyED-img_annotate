"""
SynergyED Image Annotating - Main GUI application.
A PyQt6 application for processing TEM images with scalebar addition,
brightness/contrast adjustment, and export capabilities.
"""

import sys
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QComboBox, QDoubleSpinBox,
    QGroupBox, QCheckBox, QMessageBox, QSpinBox, QDialog, QListWidget,
    QProgressDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QAction, QColor, QFont
from PyQt6.QtWidgets import QColorDialog, QFontDialog

# Helpers
class SmartDoubleSpinBox(QDoubleSpinBox):
    """A QDoubleSpinBox that displays integers without decimals and
    non-integers with up to 2 decimals (without trailing zeros)."""
    def textFromValue(self, value: float) -> str:  # type: ignore[override]
        try:
            if abs(value - round(value)) < 1e-9:
                return str(int(round(value)))
            # Show up to 2 decimals without trailing zeros
            return (f"{value:.2f}").rstrip('0').rstrip('.')
        except Exception:
            return super().textFromValue(value)

# Import our modules
from core.image_processor import ImageProcessor
from core.overlay_renderer import OverlayRenderer
from utils.preset_manager import PresetManager, PresetStorage
from gui.collapsible_box import QCollapsibleBox


class TEMImageEditor(QMainWindow):
    """Main application window for TEM image editing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SynergyED Image Annotate")
        self.setGeometry(100, 100, 1100, 700)
        
        # Initialize modules
        self.image_processor = ImageProcessor()
        self.overlay_renderer = OverlayRenderer()
        
        # Current file and calibration
        self.current_file: Optional[str] = None
        self.nm_per_pixel = 1.0
        self.pixel_size_unit = "nm"
        
        # Load presets
        self.presets = PresetStorage.load_presets()
        
        # Setup UI
        self.setup_ui()
        self.setup_menu()
        
    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_image)
        file_menu.addAction(open_action)
        
        save_action = QAction("Export Image...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.export_image)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        batch_action = QAction("Batch Annotate...", self)
        batch_action.setShortcut("Ctrl+B")
        batch_action.triggered.connect(self.batch_annotate)
        file_menu.addAction(batch_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Presets menu
        presets_menu = menubar.addMenu("Presets")
        manage_presets_action = QAction("Manage Presets...", self)
        manage_presets_action.triggered.connect(self.manage_presets)
        presets_menu.addAction(manage_presets_action)
        
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Left side - Image display
        image_layout = QVBoxLayout()
        
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("QLabel { background-color: #2b2b2b; border: 2px solid #555; }")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("No image loaded")
        
        image_layout.addWidget(self.image_label)
        
        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setStyleSheet("QLabel { color: #888; padding: 5px; }")
        image_layout.addWidget(self.file_info_label)
        
        main_layout.addLayout(image_layout, stretch=3)
        
        # Right side - Controls in a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumWidth(350)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout()
        controls_widget.setLayout(controls_layout)
        
        # Load button
        load_btn = QPushButton("Load Image")
        load_btn.setMinimumHeight(40)
        load_btn.clicked.connect(self.load_image)
        controls_layout.addWidget(load_btn)
        
        # Imaging mode preset
        self._setup_preset_controls(controls_layout)
        
        # Brightness/Contrast controls
        self._setup_brightness_contrast_controls(controls_layout)
        
        # Transform controls
        self._setup_transform_controls(controls_layout)
        
        # Scalebar controls
        self._setup_scalebar_controls(controls_layout)
        
        # Aperture controls
        self._setup_aperture_controls(controls_layout)
        
        # Export button
        export_btn = QPushButton("Export Image")
        export_btn.setMinimumHeight(40)
        export_btn.clicked.connect(self.export_image)
        controls_layout.addWidget(export_btn)
        
        controls_layout.addStretch()
        
        # Set the scroll area's widget and add to main layout
        scroll_area.setWidget(controls_widget)
        main_layout.addWidget(scroll_area, stretch=1)
        central_widget.setLayout(main_layout)
        
    def _setup_preset_controls(self, parent_layout):
        """Setup imaging mode preset controls."""
        preset_box = QCollapsibleBox("Imaging Mode", expanded=True)
        preset_layout = QVBoxLayout()
        
        self.preset_combo = QComboBox()
        self._update_preset_combo()
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(QLabel("Select Preset:"))
        preset_layout.addWidget(self.preset_combo)
        
        # Pixel size input
        pixel_size_layout = QHBoxLayout()
        pixel_size_layout.addWidget(QLabel("Pixel size:"))
        
        self.pixel_size_spinbox = QDoubleSpinBox()
        self.pixel_size_spinbox.setRange(0.00001, 100000.0)
        self.pixel_size_spinbox.setDecimals(3)
        self.pixel_size_spinbox.setValue(1.0)
        self.pixel_size_spinbox.valueChanged.connect(self.on_pixel_size_changed)
        pixel_size_layout.addWidget(self.pixel_size_spinbox)
        
        self.pixel_size_unit_combo = QComboBox()
        self.pixel_size_unit_combo.addItems(["nm", "µm"])
        self.pixel_size_unit_combo.currentTextChanged.connect(self.on_pixel_size_unit_changed)
        pixel_size_layout.addWidget(self.pixel_size_unit_combo)
        
        preset_layout.addLayout(pixel_size_layout)
        
        # Set default preset
        if "Standard" in self.presets:
            self.preset_combo.setCurrentText("Standard")
            # Apply preset-specific scalebar defaults for Standard
            QTimer.singleShot(0, self._apply_initial_scalebar_defaults)
        
        preset_box.setContentLayout(preset_layout)
        parent_layout.addWidget(preset_box)
        
    def _setup_brightness_contrast_controls(self, parent_layout):
        """Setup brightness/contrast controls."""
        bc_box = QCollapsibleBox("Brightness/Contrast", expanded=True)
        bc_layout = QVBoxLayout()
        
        auto_btn = QPushButton("Auto Adjust")
        auto_btn.clicked.connect(self.auto_adjust)
        bc_layout.addWidget(auto_btn)
        
        # Min slider
        bc_layout.addWidget(QLabel("Min Value:"))
        min_layout = QHBoxLayout()
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setRange(0, 255)
        self.min_slider.setValue(0)
        self.min_slider.valueChanged.connect(self.on_brightness_contrast_changed)
        self.min_value_label = QLabel("0")
        min_layout.addWidget(self.min_slider)
        min_layout.addWidget(self.min_value_label)
        bc_layout.addLayout(min_layout)
        
        # Max slider
        bc_layout.addWidget(QLabel("Max Value:"))
        max_layout = QHBoxLayout()
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setRange(0, 255)
        self.max_slider.setValue(255)
        self.max_slider.valueChanged.connect(self.on_brightness_contrast_changed)
        self.max_value_label = QLabel("255")
        max_layout.addWidget(self.max_slider)
        max_layout.addWidget(self.max_value_label)
        bc_layout.addLayout(max_layout)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_brightness_contrast)
        bc_layout.addWidget(reset_btn)
        
        bc_box.setContentLayout(bc_layout)
        parent_layout.addWidget(bc_box)
        
    def _setup_transform_controls(self, parent_layout):
        """Setup image transform controls."""
        transform_box = QCollapsibleBox("Image Transform", expanded=False)
        transform_layout = QHBoxLayout()
        
        flip_h_btn = QPushButton("Flip Horizontal")
        flip_h_btn.clicked.connect(self.flip_horizontal)
        transform_layout.addWidget(flip_h_btn)
        
        flip_v_btn = QPushButton("Flip Vertical")
        flip_v_btn.clicked.connect(self.flip_vertical)
        transform_layout.addWidget(flip_v_btn)
        
        transform_box.setContentLayout(transform_layout)
        parent_layout.addWidget(transform_box)
        
    def _setup_scalebar_controls(self, parent_layout):
        """Setup scalebar controls."""
        scalebar_box = QCollapsibleBox("Scalebar", expanded=True)
        scalebar_layout = QVBoxLayout()
        
        self.scalebar_checkbox = QCheckBox("Show Scalebar")
        self.scalebar_checkbox.setChecked(True)
        self.scalebar_checkbox.stateChanged.connect(self.on_scalebar_toggled)
        scalebar_layout.addWidget(self.scalebar_checkbox)
        
        # Length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:"))
        self.scalebar_length_spinbox = SmartDoubleSpinBox()
        self.scalebar_length_spinbox.setDecimals(2)
        self.scalebar_length_spinbox.setSingleStep(0.1)
        self.scalebar_length_spinbox.setRange(0.01, 10000.0)
        self.scalebar_length_spinbox.setValue(100.0)
        self.scalebar_length_spinbox.valueChanged.connect(self.on_scalebar_changed)
        # Track raw user text to preserve trailing zeros if provided
        try:
            self.scalebar_length_spinbox.lineEdit().textEdited.connect(self.on_scalebar_length_text_edited)
        except Exception:
            pass
        length_layout.addWidget(self.scalebar_length_spinbox)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["nm", "µm"])
        self.unit_combo.currentTextChanged.connect(self.on_scalebar_unit_changed)
        length_layout.addWidget(self.unit_combo)
        scalebar_layout.addLayout(length_layout)
        
        # Thickness
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Thickness (px):"))
        self.scalebar_thickness_spinbox = QSpinBox()
        self.scalebar_thickness_spinbox.setRange(5, 100)
        self.scalebar_thickness_spinbox.setValue(15)
        self.scalebar_thickness_spinbox.valueChanged.connect(self.on_scalebar_changed)
        thickness_layout.addWidget(self.scalebar_thickness_spinbox)
        scalebar_layout.addLayout(thickness_layout)
        
        # Position
        scalebar_layout.addWidget(QLabel("Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["bottom-right", "bottom-left", "top-right", "top-left"])
        self.position_combo.currentTextChanged.connect(self.on_scalebar_changed)
        scalebar_layout.addWidget(self.position_combo)
        
        # Bar color
        bar_color_layout = QHBoxLayout()
        bar_color_layout.addWidget(QLabel("Bar Color:"))
        self.bar_color_combo = QComboBox()
        self.bar_color_combo.addItems(["white", "black"])
        self.bar_color_combo.currentTextChanged.connect(self.on_bar_color_preset_changed)
        bar_color_layout.addWidget(self.bar_color_combo)
        self.bar_color_btn = QPushButton("Choose Color…")
        self.bar_color_btn.clicked.connect(self.choose_bar_color)
        bar_color_layout.addWidget(self.bar_color_btn)
        scalebar_layout.addLayout(bar_color_layout)
        
        # Text color
        text_color_layout = QHBoxLayout()
        text_color_layout.addWidget(QLabel("Text Color:"))
        self.text_color_combo = QComboBox()
        self.text_color_combo.addItems(["white", "black"])
        self.text_color_combo.currentTextChanged.connect(self.on_text_color_preset_changed)
        text_color_layout.addWidget(self.text_color_combo)
        self.text_color_btn = QPushButton("Choose Color…")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        text_color_layout.addWidget(self.text_color_btn)
        scalebar_layout.addLayout(text_color_layout)
        
        # Font
        font_layout = QHBoxLayout()
        self.font_label = QLabel("Font: Arial, 20pt")
        choose_font_btn = QPushButton("Choose Font…")
        choose_font_btn.clicked.connect(self.choose_font)
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(choose_font_btn)
        scalebar_layout.addLayout(font_layout)
        
        # Background box
        bg_inner_box = QCollapsibleBox("Background Box", expanded=False)
        bg_layout = QVBoxLayout()
        self.bg_checkbox = QCheckBox("Enable background box for legibility")
        self.bg_checkbox.stateChanged.connect(self.on_bg_toggled)
        bg_layout.addWidget(self.bg_checkbox)
        
        bg_controls_layout = QHBoxLayout()
        self.bg_color_btn = QPushButton("Choose Color…")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        bg_controls_layout.addWidget(self.bg_color_btn)
        
        bg_controls_layout.addWidget(QLabel("Opacity:"))
        self.bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_opacity_slider.setRange(0, 255)
        self.bg_opacity_slider.setValue(255)
        self.bg_opacity_slider.valueChanged.connect(self.on_bg_opacity_changed)
        bg_controls_layout.addWidget(self.bg_opacity_slider)
        
        bg_layout.addLayout(bg_controls_layout)
        self.bg_checkbox.setChecked(True)
        bg_inner_box.setContentLayout(bg_layout)
        scalebar_layout.addWidget(bg_inner_box)
        
        scalebar_box.setContentLayout(scalebar_layout)
        parent_layout.addWidget(scalebar_box)
        
    def _setup_aperture_controls(self, parent_layout):
        """Setup aperture overlay controls."""
        aperture_box = QCollapsibleBox("Aperture Overlay", expanded=False)
        aperture_layout = QVBoxLayout()
        
        self.aperture_checkbox = QCheckBox("Show Aperture")
        self.aperture_checkbox.setChecked(False)
        self.aperture_checkbox.stateChanged.connect(self.on_aperture_toggled)
        aperture_layout.addWidget(self.aperture_checkbox)
        
        # Size selector
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Nominal diameter (µm):"))
        self.aperture_size_combo = QComboBox()
        self.aperture_size_combo.addItems(["300", "200", "100", "50"])
        self.aperture_size_combo.setCurrentText("100")
        self.aperture_size_combo.currentTextChanged.connect(self.on_aperture_size_changed)
        size_layout.addWidget(self.aperture_size_combo)
        aperture_layout.addLayout(size_layout)
        
        self.aperture_info_label = QLabel("Apparent diameter: 2.0 µm")
        self.aperture_info_label.setStyleSheet("QLabel { color: #888; font-size: 10pt; }")
        aperture_layout.addWidget(self.aperture_info_label)
        
        # Color
        aperture_color_layout = QHBoxLayout()
        aperture_color_layout.addWidget(QLabel("Circle color:"))
        self.aperture_color_btn = QPushButton("Choose Color...")
        self.aperture_color_btn.clicked.connect(self.choose_aperture_color)
        aperture_color_layout.addWidget(self.aperture_color_btn)
        aperture_layout.addLayout(aperture_color_layout)
        
        aperture_box.setContentLayout(aperture_layout)
        parent_layout.addWidget(aperture_box)
        
    # Event handlers
    def load_image(self):
        """Load an image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Image Files (*.rodhypix *.tif *.tiff *.png *.jpg *.jpeg *.bmp);;RODHyPix Files (*.rodhypix);;TIFF Files (*.tif *.tiff);;All Files (*.*)"
        )
        
        if file_path:
            success, error, dimensions, pixel_metadata = self.image_processor.load_image(file_path)
            
            if success:
                self.current_file = file_path
                width, height = dimensions
                filename = Path(file_path).name
                self.file_info_label.setText(f"File: {filename} | Size: {width}x{height}px")
                
                # If we got pixel metadata from rodhypix file, automatically set the calibration
                if pixel_metadata and 'pixel_size_nm' in pixel_metadata:
                    # Set the pixel size calibration automatically
                    nm_per_pixel = pixel_metadata['pixel_size_nm']
                    um_per_pixel = pixel_metadata['pixel_size_um']
                    
                    # Determine which unit is more appropriate (prefer nm for < 1 µm, µm for >= 1 µm)
                    if um_per_pixel >= 1.0:
                        self.nm_per_pixel = um_per_pixel
                        self.pixel_size_unit = "µm"
                        self.pixel_size_unit_combo.setCurrentText("µm")
                    else:
                        self.nm_per_pixel = nm_per_pixel
                        self.pixel_size_unit = "nm"
                        self.pixel_size_unit_combo.setCurrentText("nm")
                    
                    self._update_pixel_size_display()
                    
                    # Show a message to the user
                    info_text = f"Pixel size from file header: {nm_per_pixel:.1f} nm ({um_per_pixel:.3f} µm)"
                    print(info_text)
                    self.file_info_label.setText(f"File: {filename} | Size: {width}x{height}px | {info_text}")
                
                # Auto adjust and display
                self.image_processor.auto_adjust_contrast()
                self._update_brightness_sliders()
                self.update_display()
            else:
                QMessageBox.critical(self, "Error", f"Failed to load image:\n{error}")
    
    def on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if preset_name in self.presets:
            try:
                npp = float(self.presets[preset_name])
                if npp <= 0:
                    npp = 1.0
            except Exception:
                npp = 1.0
            
            self.nm_per_pixel = npp
            self._update_pixel_size_display()
            
            # Set preset-specific scalebar defaults (only if UI is fully initialized)
            if hasattr(self, 'unit_combo') and hasattr(self, 'scalebar_length_spinbox'):
                if preset_name == "Standard":
                    self.unit_combo.setCurrentText("µm")
                    self.scalebar_length_spinbox.setValue(5.0)
                    self.scalebar_length_text_raw = "5"
                elif preset_name == "High Res":
                    self.unit_combo.setCurrentText("nm")
                    self.scalebar_length_spinbox.setValue(500.0)
                    self.scalebar_length_text_raw = "500"
            
            self.update_display()
    
    def _update_pixel_size_display(self):
        """Update pixel size spinbox display."""
        display_value = self.nm_per_pixel / 1000.0 if self.pixel_size_unit == "µm" else self.nm_per_pixel
        self.pixel_size_spinbox.blockSignals(True)
        self.pixel_size_spinbox.setValue(display_value)
        self.pixel_size_spinbox.blockSignals(False)
    
    def on_pixel_size_changed(self, value: float):
        """Handle manual pixel size change."""
        npp = value * 1000.0 if self.pixel_size_unit == "µm" else value
        if npp <= 0:
            npp = 1.0
        self.nm_per_pixel = npp
        self.presets["Custom"] = npp
        self.update_display()
    
    def on_pixel_size_unit_changed(self, unit: str):
        """Handle pixel size unit change."""
        old_unit = self.pixel_size_unit
        self.pixel_size_unit = unit
        
        current_val = self.pixel_size_spinbox.value()
        self.pixel_size_spinbox.blockSignals(True)
        if old_unit == "nm" and unit == "µm":
            self.pixel_size_spinbox.setValue(current_val / 1000.0)
        elif old_unit == "µm" and unit == "nm":
            self.pixel_size_spinbox.setValue(current_val * 1000.0)
        self.pixel_size_spinbox.blockSignals(False)
        self.update_display()
    
    def on_brightness_contrast_changed(self):
        """Handle brightness/contrast slider changes."""
        min_val = self.min_slider.value()
        max_val = self.max_slider.value()
        
        if min_val >= max_val:
            if self.sender() == self.min_slider:
                min_val = max_val - 1
                self.min_slider.setValue(min_val)
            else:
                max_val = min_val + 1
                self.max_slider.setValue(max_val)
        
        self.min_value_label.setText(str(min_val))
        self.max_value_label.setText(str(max_val))
        
        self.image_processor.set_brightness_contrast(min_val, max_val)
        self.update_display()
    
    def reset_brightness_contrast(self):
        """Reset brightness/contrast."""
        self.image_processor.reset_brightness_contrast()
        self._update_brightness_sliders()
        self.update_display()
    
    def auto_adjust(self):
        """Auto-adjust brightness/contrast."""
        self.image_processor.auto_adjust_contrast()
        self._update_brightness_sliders()
        self.update_display()
    
    def _update_brightness_sliders(self):
        """Update brightness/contrast sliders from processor."""
        self.min_slider.setValue(self.image_processor.min_val)
        self.max_slider.setValue(self.image_processor.max_val)
        self.min_value_label.setText(str(self.image_processor.min_val))
        self.max_value_label.setText(str(self.image_processor.max_val))
    
    def flip_horizontal(self):
        """Flip image horizontally."""
        self.image_processor.flip_horizontal()
        self.update_display()
    
    def flip_vertical(self):
        """Flip image vertically."""
        self.image_processor.flip_vertical()
        self.update_display()
    
    def on_scalebar_toggled(self, state):
        """Handle scalebar checkbox toggle."""
        self.overlay_renderer.scalebar_enabled = (state == Qt.CheckState.Checked.value)
        self.update_display()
    
    def on_scalebar_changed(self):
        """Handle scalebar parameter changes."""
        # numeric value for pixel conversion
        self.overlay_renderer.scalebar_length_value = float(self.scalebar_length_spinbox.value())
        self.overlay_renderer.scalebar_thickness = self.scalebar_thickness_spinbox.value()
        self.overlay_renderer.scalebar_position = self.position_combo.currentText()
        # Preserve label decimals as typed, if available and valid
        override = getattr(self, 'scalebar_length_text_raw', None)
        if isinstance(override, str) and override.strip() != "":
            try:
                float(override)
                self.overlay_renderer.scalebar_label_override = override.strip()
            except ValueError:
                self.overlay_renderer.scalebar_label_override = None
        else:
            self.overlay_renderer.scalebar_label_override = None
        self.update_display()
    
    def on_scalebar_unit_changed(self, unit: str):
        """Handle scalebar unit change."""
        self.overlay_renderer.scalebar_unit = unit
        # Update renderer label consistency
        self.on_scalebar_changed()
        self.update_display()

    def on_scalebar_length_text_edited(self, text: str):
        """Capture raw text as typed in the length spinbox to preserve trailing zeros in label."""
        self.scalebar_length_text_raw = text
        self.on_scalebar_changed()
    
    def on_bar_color_preset_changed(self, name: str):
        """Handle bar color preset change."""
        self.overlay_renderer.bar_color = QColor(255, 255, 255) if name == "white" else QColor(0, 0, 0)
        self.update_display()
    
    def choose_bar_color(self):
        """Choose custom bar color."""
        color = QColorDialog.getColor(self.overlay_renderer.bar_color, self, "Choose Scalebar Bar Color")
        if color.isValid():
            self.overlay_renderer.bar_color = color
            self.update_display()
    
    def on_text_color_preset_changed(self, name: str):
        """Handle text color preset change."""
        self.overlay_renderer.text_color = QColor(255, 255, 255) if name == "white" else QColor(0, 0, 0)
        self.update_display()
    
    def choose_text_color(self):
        """Choose custom text color."""
        color = QColorDialog.getColor(self.overlay_renderer.text_color, self, "Choose Scalebar Text Color")
        if color.isValid():
            self.overlay_renderer.text_color = color
            self.update_display()
    
    def choose_font(self):
        """Choose scalebar font."""
        options = QFontDialog.FontDialogOption.ScalableFonts | QFontDialog.FontDialogOption.DontUseNativeDialog
        font, ok = QFontDialog.getFont(self.overlay_renderer.scalebar_font, self, "Choose Scalebar Font", options=options)
        if ok:
            try:
                self.overlay_renderer.scalebar_font = QFont(font)
                pt = font.pointSize()
                px = font.pixelSize()
                size_text = f"{pt}pt" if pt > 0 else f"{px}px" if px > 0 else ""
                label_text = f"Font: {font.family()}" + (f", {size_text}" if size_text else "")
                self.font_label.setText(label_text)
            except Exception as e:
                QMessageBox.warning(self, "Font Error", f"Selected font could not be applied.\n{e}")
                self.overlay_renderer.scalebar_font = QFont("Arial", 20)
                self.font_label.setText("Font: Arial, 20pt")
            self.update_display()
    
    def on_bg_toggled(self, state):
        """Handle background box toggle."""
        enabled = (state == Qt.CheckState.Checked.value)
        self.bg_color_btn.setEnabled(enabled)
        self.bg_opacity_slider.setEnabled(enabled)
        self.overlay_renderer.scalebar_bg_enabled = enabled
        self.update_display()
    
    def choose_bg_color(self):
        """Choose background color."""
        color = QColorDialog.getColor(self.overlay_renderer.scalebar_bg_color, self, "Choose Background Color")
        if color.isValid():
            self.overlay_renderer.scalebar_bg_color = color
            self.update_display()
    
    def on_bg_opacity_changed(self, value: int):
        """Handle background opacity change."""
        self.overlay_renderer.scalebar_bg_opacity = value
        self.update_display()
    
    def on_aperture_toggled(self, state):
        """Handle aperture checkbox toggle."""
        self.overlay_renderer.aperture_enabled = (state == Qt.CheckState.Checked.value)
        self.update_display()
    
    def on_aperture_size_changed(self, size_str: str):
        """Handle aperture size change."""
        try:
            nominal_size = int(size_str)
            self.overlay_renderer.aperture_nominal_size = nominal_size
            apparent_diameter = nominal_size / 50.0
            self.aperture_info_label.setText(f"Apparent diameter: {apparent_diameter:.1f} µm")
            self.update_display()
        except ValueError:
            pass
    
    def choose_aperture_color(self):
        """Choose aperture color."""
        color = QColorDialog.getColor(self.overlay_renderer.aperture_color, self, "Choose Aperture Color")
        if color.isValid():
            self.overlay_renderer.aperture_color = color
            self.update_display()
    
    def update_display(self):
        """Update the displayed image."""
        if not self.image_processor.has_image():
            return
        
        # Get current image with overlays
        q_image = self.overlay_renderer.render_image_with_overlays(
            self.image_processor.get_current_image(),
            self.nm_per_pixel
        )
        
        if q_image is None:
            return
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
    
    def export_image(self):
        """Export the current image."""
        if not self.image_processor.has_image():
            QMessageBox.warning(self, "Warning", "No image loaded to export.")
            return
        
        suggested_name = Path(self.current_file).stem + "_processed.png" if self.current_file else "tem_image.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", suggested_name,
            "PNG Image (*.png);;TIFF Image (*.tif *.tiff);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)"
        )
        
        if file_path:
            try:
                q_image = self.overlay_renderer.render_image_with_overlays(
                    self.image_processor.get_current_image(),
                    self.nm_per_pixel
                )
                
                if q_image is None:
                    QMessageBox.warning(self, "Warning", "No image to export.")
                    return
                
                # Convert to RGBA8888
                q_rgba = q_image.convertToFormat(QImage.Format.Format_RGBA8888)
                width = q_rgba.width()
                height = q_rgba.height()
                ptr = q_rgba.bits()
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                export_rgba = arr.copy()
                
                # Determine DPI
                input_dpi = self.image_processor.get_dpi()
                if input_dpi and all(v > 0 for v in input_dpi):
                    xdpi = min(input_dpi[0], 300.0)
                    ydpi = min(input_dpi[1], 300.0)
                else:
                    xdpi = ydpi = 300.0
                
                # Save
                ext = Path(file_path).suffix.lower()
                if ext in [".jpg", ".jpeg", ".bmp"]:
                    export_rgb = export_rgba[:, :, :3]
                    pil_image = Image.fromarray(export_rgb, mode='RGB')
                    pil_image.save(file_path, dpi=(xdpi, ydpi))
                else:
                    pil_image = Image.fromarray(export_rgba, mode='RGBA')
                    pil_image.save(file_path, dpi=(xdpi, ydpi))
                
                QMessageBox.information(self, "Success", f"Image exported successfully to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export image:\n{str(e)}")
    
    def manage_presets(self):
        """Open preset manager dialog."""
        dialog = PresetManager(self.presets, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.presets = dialog.get_presets()
            PresetStorage.save_presets(self.presets)
            self._update_preset_combo()
    
    def _update_preset_combo(self):
        """Update preset combo box."""
        current = self.preset_combo.currentText() if self.preset_combo.count() > 0 else None
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.presets.keys()))
        if current and current in self.presets:
            self.preset_combo.setCurrentText(current)
    
    def _apply_initial_scalebar_defaults(self):
        """Apply initial scalebar defaults for the default preset."""
        current_preset = self.preset_combo.currentText()
        if current_preset == "Standard":
            self.unit_combo.setCurrentText("µm")
            self.scalebar_length_spinbox.setValue(5)
        elif current_preset == "High Res":
            self.unit_combo.setCurrentText("nm")
            self.scalebar_length_spinbox.setValue(500)
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        if self.image_processor.has_image():
            QTimer.singleShot(100, self.update_display)
    
    def batch_annotate(self):
        """Open batch annotation dialog."""
        dialog = BatchAnnotationDialog(self.presets, self.overlay_renderer, self)
        dialog.exec()


class BatchAnnotationDialog(QDialog):
    """Dialog for batch annotation of multiple images."""
    
    def __init__(self, presets: dict, renderer: OverlayRenderer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Annotate Images")
        self.setModal(True)
        self.resize(900, 700)
        
        self.presets = presets
        self.renderer = renderer
        self.files = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the batch dialog UI."""
        layout = QVBoxLayout()
        
        # File selection section
        file_group = QGroupBox("Select Files")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._add_files)
        btn_layout.addWidget(add_files_btn)
        
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(remove_files_btn)
        
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self._clear_files)
        btn_layout.addWidget(clear_files_btn)
        
        file_layout.addLayout(btn_layout)
        
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Parameters section
        params_group = QGroupBox("Annotation Parameters")
        params_layout = QVBoxLayout()
        
        # Preset selection
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(sorted(self.presets.keys()))
        self.preset_combo.setCurrentText("Standard")
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        params_layout.addLayout(preset_layout)
        
        # Pixel size
        pixel_layout = QHBoxLayout()
        pixel_layout.addWidget(QLabel("Pixel size:"))
        self.pixel_size_spinbox = QDoubleSpinBox()
        self.pixel_size_spinbox.setRange(0.00001, 100000.0)
        self.pixel_size_spinbox.setDecimals(3)
        self.pixel_size_spinbox.setValue(35.6)
        pixel_layout.addWidget(self.pixel_size_spinbox)
        
        self.pixel_unit_combo = QComboBox()
        self.pixel_unit_combo.addItems(["nm", "µm"])
        pixel_layout.addWidget(self.pixel_unit_combo)
        params_layout.addLayout(pixel_layout)
        
        # Auto brightness/contrast
        self.auto_bc_checkbox = QCheckBox("Auto-adjust brightness/contrast")
        self.auto_bc_checkbox.setChecked(True)
        params_layout.addWidget(self.auto_bc_checkbox)
        
        # Scalebar section
        scalebar_group = QGroupBox("Scalebar")
        scalebar_layout = QVBoxLayout()
        
        self.scalebar_checkbox = QCheckBox("Add scalebar")
        self.scalebar_checkbox.setChecked(True)
        scalebar_layout.addWidget(self.scalebar_checkbox)
        
        # Scalebar length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:"))
        self.scalebar_length_spinbox = SmartDoubleSpinBox()
        self.scalebar_length_spinbox.setDecimals(2)
        self.scalebar_length_spinbox.setSingleStep(0.1)
        self.scalebar_length_spinbox.setRange(0.01, 10000.0)
        self.scalebar_length_spinbox.setValue(5.0)
        try:
            self.scalebar_length_spinbox.lineEdit().textEdited.connect(self._on_batch_scalebar_length_text_edited)
        except Exception:
            pass
        length_layout.addWidget(self.scalebar_length_spinbox)
        
        self.scalebar_unit_combo = QComboBox()
        self.scalebar_unit_combo.addItems(["nm", "µm"])
        self.scalebar_unit_combo.setCurrentText("µm")
        length_layout.addWidget(self.scalebar_unit_combo)
        scalebar_layout.addLayout(length_layout)
        
        # Scalebar thickness
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Thickness (px):"))
        self.scalebar_thickness_spinbox = QSpinBox()
        self.scalebar_thickness_spinbox.setRange(5, 100)
        self.scalebar_thickness_spinbox.setValue(self.renderer.scalebar_thickness)
        thickness_layout.addWidget(self.scalebar_thickness_spinbox)
        scalebar_layout.addLayout(thickness_layout)
        
        # Scalebar position
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["bottom-right", "bottom-left", "top-right", "top-left"])
        self.position_combo.setCurrentText(self.renderer.scalebar_position)
        position_layout.addWidget(self.position_combo)
        scalebar_layout.addLayout(position_layout)
        
        # Colors
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Bar color:"))
        self.bar_color_btn = QPushButton("Choose...")
        self.bar_color = QColor(self.renderer.bar_color)
        self.bar_color_btn.clicked.connect(self._choose_bar_color)
        color_layout.addWidget(self.bar_color_btn)
        
        color_layout.addWidget(QLabel("Text color:"))
        self.text_color_btn = QPushButton("Choose...")
        self.text_color = QColor(self.renderer.text_color)
        self.text_color_btn.clicked.connect(self._choose_text_color)
        color_layout.addWidget(self.text_color_btn)
        scalebar_layout.addLayout(color_layout)
        
        # Background box
        self.bg_checkbox = QCheckBox("Background box")
        self.bg_checkbox.setChecked(self.renderer.scalebar_bg_enabled)
        scalebar_layout.addWidget(self.bg_checkbox)
        
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("BG color:"))
        self.bg_color_btn = QPushButton("Choose...")
        self.bg_color = QColor(self.renderer.scalebar_bg_color)
        self.bg_color_btn.clicked.connect(self._choose_bg_color)
        bg_layout.addWidget(self.bg_color_btn)
        
        bg_layout.addWidget(QLabel("Opacity:"))
        self.bg_opacity_spinbox = QSpinBox()
        self.bg_opacity_spinbox.setRange(0, 255)
        self.bg_opacity_spinbox.setValue(self.renderer.scalebar_bg_opacity)
        bg_layout.addWidget(self.bg_opacity_spinbox)
        scalebar_layout.addLayout(bg_layout)
        
        scalebar_group.setLayout(scalebar_layout)
        params_layout.addWidget(scalebar_group)
        
        # Aperture section
        aperture_group = QGroupBox("Aperture Overlay")
        aperture_layout = QVBoxLayout()
        
        self.aperture_checkbox = QCheckBox("Add aperture overlay")
        self.aperture_checkbox.setChecked(False)
        aperture_layout.addWidget(self.aperture_checkbox)
        
        ap_layout = QHBoxLayout()
        ap_layout.addWidget(QLabel("Nominal diameter (µm):"))
        self.aperture_size_combo = QComboBox()
        self.aperture_size_combo.addItems(["300", "200", "100", "50"])
        self.aperture_size_combo.setCurrentText("100")
        ap_layout.addWidget(self.aperture_size_combo)
        aperture_layout.addLayout(ap_layout)
        
        ap_color_layout = QHBoxLayout()
        ap_color_layout.addWidget(QLabel("Circle color:"))
        self.aperture_color_btn = QPushButton("Choose...")
        self.aperture_color = QColor(self.renderer.aperture_color)
        self.aperture_color_btn.clicked.connect(self._choose_aperture_color)
        ap_color_layout.addWidget(self.aperture_color_btn)
        aperture_layout.addLayout(ap_color_layout)
        
        aperture_group.setLayout(aperture_layout)
        params_layout.addWidget(aperture_group)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Output section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Output folder:"))
        self.output_folder_edit = QLabel("(same as input)")
        self.output_folder_edit.setStyleSheet("QLabel { border: 1px solid #555; padding: 3px; }")
        folder_layout.addWidget(self.output_folder_edit, stretch=1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._choose_output_folder)
        folder_layout.addWidget(browse_btn)
        output_layout.addLayout(folder_layout)
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("Filename suffix:"))
        self.suffix_edit = QComboBox()
        self.suffix_edit.setEditable(True)
        self.suffix_edit.addItems(["_processed", "_annotated", "_scaled", ""])
        self.suffix_edit.setCurrentText("_processed")
        suffix_layout.addWidget(self.suffix_edit)
        output_layout.addLayout(suffix_layout)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "TIFF", "JPEG"])
        self.format_combo.setCurrentText("PNG")
        format_layout.addWidget(self.format_combo)
        output_layout.addLayout(format_layout)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        process_btn = QPushButton("Process All")
        process_btn.setMinimumHeight(40)
        process_btn.clicked.connect(self._process_all)
        button_layout.addWidget(process_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Initialize preset
        self._on_preset_changed("Standard")
    
    def _add_files(self):
        """Add files to the batch list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Image Files (*.rodhypix *.tif *.tiff *.png *.jpg *.jpeg *.bmp);;RODHyPix Files (*.rodhypix);;TIFF Files (*.tif *.tiff);;All Files (*.*)"
        )
        if files:
            for file in files:
                if file not in self.files:
                    self.files.append(file)
                    self.file_list.addItem(Path(file).name)
    
    def _remove_selected(self):
        """Remove selected files from the list."""
        selected = self.file_list.selectedItems()
        if not selected:
            return
        for item in selected:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            self.files.pop(row)
    
    def _clear_files(self):
        """Clear all files from the list."""
        self.files.clear()
        self.file_list.clear()
    
    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if preset_name in self.presets:
            try:
                npp = float(self.presets[preset_name])
                if npp <= 0:
                    npp = 1.0
            except Exception:
                npp = 1.0
            
            self.pixel_size_spinbox.setValue(npp)
            self.pixel_unit_combo.setCurrentText("nm")
            
            # Set preset-specific scalebar defaults
            if preset_name == "Standard":
                self.scalebar_unit_combo.setCurrentText("µm")
                self.scalebar_length_spinbox.setValue(5.0)
                self._batch_scalebar_length_text_raw = "5"
            elif preset_name == "High Res":
                self.scalebar_unit_combo.setCurrentText("nm")
                self.scalebar_length_spinbox.setValue(500.0)
                self._batch_scalebar_length_text_raw = "500"
    
    def _choose_bar_color(self):
        """Choose bar color."""
        color = QColorDialog.getColor(self.bar_color, self, "Choose Scalebar Bar Color")
        if color.isValid():
            self.bar_color = color
    
    def _choose_text_color(self):
        """Choose text color."""
        color = QColorDialog.getColor(self.text_color, self, "Choose Scalebar Text Color")
        if color.isValid():
            self.text_color = color
    
    def _choose_bg_color(self):
        """Choose background color."""
        color = QColorDialog.getColor(self.bg_color, self, "Choose Background Color")
        if color.isValid():
            self.bg_color = color
    
    def _choose_aperture_color(self):
        """Choose aperture color."""
        color = QColorDialog.getColor(self.aperture_color, self, "Choose Aperture Color")
        if color.isValid():
            self.aperture_color = color
    
    def _choose_output_folder(self):
        """Choose output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder_edit.setText(folder)

    def _on_batch_scalebar_length_text_edited(self, text: str):
        """Capture raw text for batch scalebar length to preserve trailing zeros in label."""
        self._batch_scalebar_length_text_raw = text
    
    def _process_all(self):
        """Process all files in the batch."""
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add files to process.")
            return
        
        # Get output folder
        output_folder_text = self.output_folder_edit.text()
        if output_folder_text == "(same as input)":
            output_folder = None
        else:
            output_folder = Path(output_folder_text)
            if not output_folder.exists():
                QMessageBox.warning(self, "Invalid Folder", "Output folder does not exist.")
                return
        
        # Get parameters
        pixel_size = self.pixel_size_spinbox.value()
        pixel_unit = self.pixel_unit_combo.currentText()
        nm_per_pixel = pixel_size * 1000.0 if pixel_unit == "µm" else pixel_size
        if nm_per_pixel <= 0:
            nm_per_pixel = 1.0
        
        auto_bc = self.auto_bc_checkbox.isChecked()
        
        # Scalebar settings
        scalebar_enabled = self.scalebar_checkbox.isChecked()
        scalebar_length = self.scalebar_length_spinbox.value()
        scalebar_unit = self.scalebar_unit_combo.currentText()
        scalebar_thickness = self.scalebar_thickness_spinbox.value()
        scalebar_position = self.position_combo.currentText()
        
        # Aperture settings
        aperture_enabled = self.aperture_checkbox.isChecked()
        aperture_size = int(self.aperture_size_combo.currentText())
        
        # Output settings
        suffix = self.suffix_edit.currentText()
        output_format = self.format_combo.currentText().lower()
        
        # Create progress dialog
        progress = QProgressDialog("Processing images...", "Cancel", 0, len(self.files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        
        # Process each file
        processor = ImageProcessor()
        renderer = OverlayRenderer()
        
        # Configure renderer
        renderer.scalebar_enabled = scalebar_enabled
        renderer.scalebar_length_value = float(scalebar_length)
        renderer.scalebar_unit = scalebar_unit
        renderer.scalebar_thickness = scalebar_thickness
        renderer.scalebar_position = scalebar_position
        renderer.bar_color = QColor(self.bar_color)
        renderer.text_color = QColor(self.text_color)
        renderer.scalebar_bg_enabled = self.bg_checkbox.isChecked()
        renderer.scalebar_bg_color = QColor(self.bg_color)
        renderer.scalebar_bg_opacity = self.bg_opacity_spinbox.value()
        renderer.aperture_enabled = aperture_enabled
        renderer.aperture_nominal_size = aperture_size
        renderer.aperture_color = QColor(self.aperture_color)
        # Preserve label decimals in batch if provided
        override = getattr(self, '_batch_scalebar_length_text_raw', None)
        if isinstance(override, str) and override.strip() != "":
            try:
                float(override)
                renderer.scalebar_label_override = override.strip()
            except ValueError:
                renderer.scalebar_label_override = None
        
        successful = 0
        failed = []
        
        for i, file_path in enumerate(self.files):
            if progress.wasCanceled():
                break
            
            progress.setValue(i)
            progress.setLabelText(f"Processing {Path(file_path).name}...")
            QApplication.processEvents()
            
            try:
                # Load image
                success, error, _, pixel_metadata = processor.load_image(file_path)
                if not success:
                    failed.append((file_path, error))
                    continue
                
                # Use pixel metadata from rodhypix file if available, otherwise use provided value
                file_nm_per_pixel = nm_per_pixel
                if pixel_metadata and 'pixel_size_nm' in pixel_metadata:
                    # Use pixel size from file header
                    if pixel_size_unit == "µm":
                        file_nm_per_pixel = pixel_metadata['pixel_size_um']
                    else:
                        file_nm_per_pixel = pixel_metadata['pixel_size_nm']
                    print(f"Using pixel size from {Path(file_path).name}: {file_nm_per_pixel:.3f} {pixel_size_unit}")
                
                # Auto adjust if requested
                if auto_bc:
                    processor.auto_adjust_contrast()
                
                # Render with overlays
                q_image = renderer.render_image_with_overlays(
                    processor.get_current_image(),
                    file_nm_per_pixel
                )
                
                if q_image is None:
                    failed.append((file_path, "Failed to render image"))
                    continue
                
                # Determine output path
                input_path = Path(file_path)
                if output_folder:
                    output_dir = output_folder
                else:
                    output_dir = input_path.parent
                
                output_name = input_path.stem + suffix + "." + output_format
                output_path = output_dir / output_name
                
                # Convert and export
                q_rgba = q_image.convertToFormat(QImage.Format.Format_RGBA8888)
                width = q_rgba.width()
                height = q_rgba.height()
                ptr = q_rgba.bits()
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                export_rgba = arr.copy()
                
                # Get DPI
                input_dpi = processor.get_dpi()
                if input_dpi and all(v > 0 for v in input_dpi):
                    xdpi = min(input_dpi[0], 300.0)
                    ydpi = min(input_dpi[1], 300.0)
                else:
                    xdpi = ydpi = 300.0
                
                # Save
                if output_format in ["jpg", "jpeg", "bmp"]:
                    export_rgb = export_rgba[:, :, :3]
                    pil_image = Image.fromarray(export_rgb, mode='RGB')
                    pil_image.save(str(output_path), dpi=(xdpi, ydpi))
                else:
                    pil_image = Image.fromarray(export_rgba, mode='RGBA')
                    pil_image.save(str(output_path), dpi=(xdpi, ydpi))
                
                successful += 1
                
            except Exception as e:
                failed.append((file_path, str(e)))
        
        progress.setValue(len(self.files))
        
        # Show summary
        if failed:
            failed_list = "\n".join([f"{Path(f).name}: {e}" for f, e in failed[:10]])
            if len(failed) > 10:
                failed_list += f"\n... and {len(failed) - 10} more"
            QMessageBox.warning(
                self, "Batch Processing Complete",
                f"Successfully processed: {successful}/{len(self.files)}\n\n"
                f"Failed files:\n{failed_list}"
            )
        else:
            QMessageBox.information(
                self, "Batch Processing Complete",
                f"Successfully processed all {successful} images!"
            )
        
        self.accept()


def main():
    """Main entry point."""
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false;qt.qpa.fonts.warning=false")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = TEMImageEditor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

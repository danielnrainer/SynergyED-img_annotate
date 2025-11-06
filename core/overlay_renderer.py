"""
Overlay rendering module for TEM Image Editor.
Handles drawing scalebar and aperture overlays on images.
"""

from typing import Optional
import numpy as np
from PyQt6.QtGui import QImage, QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt, QRectF


class OverlayRenderer:
    """Handles rendering of scalebar and aperture overlays."""
    
    def __init__(self):
        # Scalebar parameters
        self.scalebar_enabled = True
        self.scalebar_length_value = 100.0  # numeric value (in selected unit)
        self.scalebar_unit = "nm"
        self.scalebar_thickness = 15
        self.scalebar_position = "bottom-right"
        self.bar_color = QColor(255, 255, 255)
        self.text_color = QColor(255, 255, 255)
        self.scalebar_font = QFont("Arial", 20, QFont.Weight.Black)
        self.scalebar_bg_enabled = True
        self.scalebar_bg_color = QColor(0, 0, 0)
        self.scalebar_bg_opacity = 255
        # Optional label override (numeric text only, without unit). If set, we'll display it verbatim.
        self.scalebar_label_override: Optional[str] = None
        
        # Aperture parameters
        self.aperture_enabled = False
        self.aperture_nominal_size = 100  # diameter in µm
        self.aperture_color = QColor(255, 255, 0)
    
    def render_image_with_overlays(self, 
                                   image: np.ndarray, 
                                   nm_per_pixel: float) -> Optional[QImage]:
        """
        Render image with scalebar and aperture overlays.
        
        Args:
            image: The numpy array image to render
            nm_per_pixel: Calibration in nanometers per pixel
            
        Returns:
            QImage with overlays drawn, or None if image is invalid
        """
        if image is None:
            return None
        
        # Prepare RGB image for painting
        if len(image.shape) == 2:
            # Convert grayscale to RGB using NumPy
            rgb = np.stack([image, image, image], axis=-1)
        else:
            # Already RGB/color
            rgb = image
        
        # Ensure contiguous memory layout
        rgb = np.ascontiguousarray(rgb)
        height, width = rgb.shape[:2]
        bytes_per_line = rgb.strides[0]
        
        # Create QImage
        qimg = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        qimg = qimg.copy().convertToFormat(QImage.Format.Format_ARGB32)
        
        if not self.scalebar_enabled:
            return qimg
        
        # Guard against invalid calibration
        if nm_per_pixel is None or nm_per_pixel <= 0:
            return qimg
        
        # Draw scalebar
        self._draw_scalebar(qimg, width, height, nm_per_pixel)
        
        # Draw aperture if enabled
        if self.aperture_enabled:
            self._draw_aperture(qimg, width, height, nm_per_pixel)
        
        return qimg
    
    def _draw_scalebar(self, qimg: QImage, width: int, height: int, nm_per_pixel: float):
        """Draw scalebar on the image."""
        # Compute scalebar length in pixels
        if self.scalebar_unit == "µm":
            length_nm = self.scalebar_length_value * 1000.0
        else:
            length_nm = float(self.scalebar_length_value)
        
        desired_px = int(round(length_nm / nm_per_pixel))
        
        # Cap scalebar length to fit within margins
        margin = 30
        max_px = max(1, width - 2 * margin)
        scalebar_length_px = min(desired_px, max_px)
        
        # Determine colors
        bar_qcolor = QColor(self.bar_color)
        text_qcolor = QColor(self.text_color)
        
        # Compute outline color for text contrast
        r, g, b, *_ = text_qcolor.getRgb()
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        outline_qcolor = QColor(0, 0, 0) if luminance > 0.5 else QColor(255, 255, 255)
        
        # Determine position
        if "bottom" in self.scalebar_position:
            y = height - margin - self.scalebar_thickness
        else:
            y = margin
        
        if "right" in self.scalebar_position:
            x = width - margin - scalebar_length_px
        else:
            x = margin
        
        # Build label
        if self.scalebar_label_override is not None and str(self.scalebar_label_override).strip() != "":
            label_value_text = str(self.scalebar_label_override).strip()
        else:
            # Default formatting if no override provided
            if self.scalebar_unit == "µm":
                value = length_nm / 1000.0
            else:
                value = length_nm
            # Show integer if it's effectively an integer; otherwise, show up to 2 decimals without trailing zeros
            if abs(value - round(value)) < 1e-9:
                label_value_text = f"{int(round(value))}"
            else:
                label_value_text = f"{value:.2f}".rstrip('0').rstrip('.')
        unit_text = "µm" if self.scalebar_unit == "µm" else "nm"
        label = f"{label_value_text} {unit_text}"
        
        # Start painting
        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # Font setup
        try:
            if isinstance(self.scalebar_font, QFont):
                painter.setFont(self.scalebar_font)
            else:
                painter.setFont(QFont("Arial", 20))
        except Exception:
            painter.setFont(QFont("Arial", 20))
        
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(label)
        text_height = fm.height()
        ascent = fm.ascent()
        descent = fm.descent()
        
        # Text position
        if "bottom" in self.scalebar_position:
            text_baseline_y = y - 12  # 12px gap
            text_top = text_baseline_y - ascent
            text_bottom = text_baseline_y + descent
        else:
            text_baseline_y = y + self.scalebar_thickness + ascent + 12
            text_top = y + self.scalebar_thickness + 12
            text_bottom = text_baseline_y + descent
        
        # Center label horizontally over the bar
        text_x = x + (scalebar_length_px - text_width) // 2
        text_x = max(0, min(text_x, width - text_width))
        
        # Optional background box
        if self.scalebar_bg_enabled:
            pad = 6
            rect_left = min(x, text_x) - pad
            rect_right = max(x + scalebar_length_px, text_x + text_width) + pad
            rect_top = min(y, text_top)
            rect_bottom = max(y + self.scalebar_thickness, text_bottom) + pad
            rect_left = max(0, rect_left)
            rect_top = max(0, rect_top)
            rect_right = min(width - 1, rect_right)
            rect_bottom = min(height - 1, rect_bottom)
            
            bg = QColor(self.scalebar_bg_color)
            bg.setAlpha(self.scalebar_bg_opacity)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg))
            painter.drawRect(int(rect_left), int(rect_top), 
                           int(rect_right - rect_left), int(rect_bottom - rect_top))
        
        # Draw scalebar rectangle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bar_qcolor))
        painter.drawRect(x, y, scalebar_length_px, self.scalebar_thickness)
        
        # Draw text with outline
        pen = QPen(outline_qcolor)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(text_x, text_baseline_y, label)
        
        # Foreground text
        painter.setPen(QPen(text_qcolor))
        painter.drawText(text_x, text_baseline_y, label)
        
        painter.end()
    
    def _draw_aperture(self, qimg: QImage, width: int, height: int, nm_per_pixel: float):
        """Draw aperture overlay on the image."""
        if nm_per_pixel is None or nm_per_pixel <= 0:
            return
        
        # Calculate apparent diameter and radius
        apparent_diameter_um = self.aperture_nominal_size / 50.0
        apparent_radius_um = apparent_diameter_um / 2.0
        apparent_radius_nm = apparent_radius_um * 1000.0
        # Target INNER radius in pixels (physical clear aperture)
        target_inner_radius_px = float(apparent_radius_nm) / float(nm_per_pixel)
        
        # Center of image
        center_x = width // 2
        center_y = height // 2
        
        # Draw circle
        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Use a consistent pen width and ensure INNER diameter stays correct.
        # Qt strokes are centered on the ellipse path, so half the pen width
        # is inside the path and half is outside. To keep the INNER diameter
        # equal to the requested apparent diameter, expand the ellipse radius
        # by pen_width/2.
        pen_width_px = 5.0
        pen = QPen(self.aperture_color)
        try:
            pen.setWidthF(pen_width_px)
        except Exception:
            # Fallback for environments without setWidthF
            pen.setWidth(int(round(pen_width_px)))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Adjusted (outer) radius so that inner radius matches target
        adjusted_radius_px = target_inner_radius_px + (pen_width_px / 2.0)
        rect = QRectF(
            center_x - adjusted_radius_px,
            center_y - adjusted_radius_px,
            2.0 * adjusted_radius_px,
            2.0 * adjusted_radius_px,
        )
        painter.drawEllipse(rect)
        
        painter.end()

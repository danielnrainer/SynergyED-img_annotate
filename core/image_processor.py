"""
Image processing module for TEM Image Editor.
Handles image loading, transformations, and brightness/contrast adjustments.
"""

from typing import Optional, Tuple
import numpy as np
from PIL import Image


class ImageProcessor:
    """Handles all image processing operations."""
    
    def __init__(self):
        self.original_image: Optional[np.ndarray] = None
        self.current_image: Optional[np.ndarray] = None
        self.input_dpi: Optional[Tuple[float, float]] = None
        self.min_val = 0
        self.max_val = 255
        
    def load_image(self, file_path: str) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
        """
        Load an image from file.
        
        Returns:
            (success, error_message, (width, height))
        """
        try:
            # Load image using PIL
            pil_image = Image.open(file_path)
            
            # Try to capture source DPI metadata
            self.input_dpi = None
            try:
                dpi = pil_image.info.get('dpi')
                if dpi and isinstance(dpi, (tuple, list)) and len(dpi) == 2:
                    self.input_dpi = (float(dpi[0]), float(dpi[1]))
                else:
                    # Some TIFFs store resolution differently
                    res = pil_image.info.get('resolution')
                    unit = pil_image.info.get('resolution_unit', 2)  # 2=inches, 3=cm
                    if res and isinstance(res, (tuple, list)) and len(res) == 2:
                        xres, yres = float(res[0]), float(res[1])
                        if unit == 3:  # cm -> inch
                            xres *= 2.54
                            yres *= 2.54
                        self.input_dpi = (xres, yres)
                    else:
                        # Fallback to TIFF tags if available
                        tag = getattr(pil_image, 'tag_v2', None)
                        if tag is not None:
                            xres = tag.get(282)  # XResolution
                            yres = tag.get(283)  # YResolution
                            unit_tag = tag.get(296)  # ResolutionUnit (2=in, 3=cm)
                            if xres and yres:
                                xval = float(xres[0] / xres[1]) if isinstance(xres, (tuple, list)) else float(xres)
                                yval = float(yres[0] / yres[1]) if isinstance(yres, (tuple, list)) else float(yres)
                                if unit_tag == 3:  # cm
                                    xval *= 2.54
                                    yval *= 2.54
                                self.input_dpi = (xval, yval)
            except Exception:
                self.input_dpi = None
            
            # Convert to grayscale if needed
            if pil_image.mode != 'L' and pil_image.mode != 'I;16':
                pil_image = pil_image.convert('L')
            
            self.original_image = np.array(pil_image)
            
            # Handle 16-bit images
            if self.original_image.dtype == np.uint16:
                # Normalize to 8-bit for display
                self.original_image = (self.original_image / 256).astype(np.uint8)
            
            self.current_image = self.original_image.copy()
            
            # Get dimensions
            height, width = self.original_image.shape
            
            return True, None, (width, height)
            
        except Exception as e:
            return False, str(e), None
    
    def auto_adjust_contrast(self):
        """Automatically adjust brightness/contrast based on image histogram."""
        if self.original_image is None:
            return
        
        # Calculate percentiles for auto-adjustment
        p_low = np.percentile(self.original_image, 2)
        p_high = np.percentile(self.original_image, 98)
        
        self.min_val = int(p_low)
        self.max_val = int(p_high)
        
        self.apply_brightness_contrast()
    
    def set_brightness_contrast(self, min_val: int, max_val: int):
        """Set brightness/contrast values and apply."""
        self.min_val = min_val
        self.max_val = max_val
        self.apply_brightness_contrast()
    
    def apply_brightness_contrast(self):
        """Apply brightness/contrast adjustment to the image."""
        if self.original_image is None:
            return
        
        # Apply contrast stretching
        img = self.original_image.astype(np.float32)
        
        # Clip and normalize
        img = np.clip(img, self.min_val, self.max_val)
        if self.max_val > self.min_val:
            img = (img - self.min_val) / (self.max_val - self.min_val) * 255
        
        self.current_image = img.astype(np.uint8)
    
    def reset_brightness_contrast(self):
        """Reset brightness/contrast to default."""
        self.min_val = 0
        self.max_val = 255
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
    
    def flip_horizontal(self):
        """Flip the image horizontally (left-right)."""
        if self.original_image is None:
            return
        
        self.original_image = np.fliplr(self.original_image)
        self.apply_brightness_contrast()
    
    def flip_vertical(self):
        """Flip the image vertically (top-bottom)."""
        if self.original_image is None:
            return
        
        self.original_image = np.flipud(self.original_image)
        self.apply_brightness_contrast()
    
    def get_current_image(self) -> Optional[np.ndarray]:
        """Get the current processed image."""
        return self.current_image
    
    def get_original_image(self) -> Optional[np.ndarray]:
        """Get the original image."""
        return self.original_image
    
    def has_image(self) -> bool:
        """Check if an image is loaded."""
        return self.current_image is not None
    
    def get_dpi(self) -> Optional[Tuple[float, float]]:
        """Get the input DPI if available."""
        return self.input_dpi

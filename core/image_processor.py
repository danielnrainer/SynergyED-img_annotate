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
        self.raw_image: Optional[np.ndarray] = None  # Store raw data before normalization
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
            if pil_image.mode not in ['L', 'I', 'I;16', 'F']:
                pil_image = pil_image.convert('L')
            
            self.original_image = np.array(pil_image)
            self.raw_image = self.original_image.copy()  # Store raw data before normalization
            
            # Print diagnostic info
            print(f"Loaded image dtype: {self.original_image.dtype}")
            print(f"Image range: min={np.min(self.original_image):.2f}, max={np.max(self.original_image):.2f}")
            print(f"Image mean: {np.mean(self.original_image):.2f}")
            
            # Handle different bit depths and normalize to 8-bit
            if self.original_image.dtype == np.uint16:
                # 16-bit unsigned integer
                img_min = np.min(self.original_image)
                img_max = np.max(self.original_image)
                print(f"16-bit image detected, normalizing range [{img_min}, {img_max}] to [0, 255]")
                
                if img_max > img_min:
                    normalized = (self.original_image.astype(np.float32) - img_min) / (img_max - img_min) * 255
                    self.original_image = normalized.astype(np.uint8)
                else:
                    self.original_image = np.zeros_like(self.original_image, dtype=np.uint8)
                    
            elif self.original_image.dtype in [np.float32, np.float64]:
                # 32-bit or 64-bit float
                img_min = np.min(self.original_image)
                img_max = np.max(self.original_image)
                print(f"Float image detected, normalizing range [{img_min:.4f}, {img_max:.4f}] to [0, 255]")
                
                if img_max > img_min:
                    normalized = (self.original_image - img_min) / (img_max - img_min) * 255
                    self.original_image = normalized.astype(np.uint8)
                else:
                    self.original_image = np.zeros((self.original_image.shape), dtype=np.uint8)
                    
            elif self.original_image.dtype == np.uint32 or self.original_image.dtype == np.int32:
                # 32-bit integer
                img_min = np.min(self.original_image)
                img_max = np.max(self.original_image)
                print(f"32-bit integer image detected, normalizing range [{img_min}, {img_max}] to [0, 255]")
                
                if img_max > img_min:
                    normalized = (self.original_image.astype(np.float64) - img_min) / (img_max - img_min) * 255
                    self.original_image = normalized.astype(np.uint8)
                else:
                    self.original_image = np.zeros((self.original_image.shape), dtype=np.uint8)
            
            # If already 8-bit, use as-is
            elif self.original_image.dtype != np.uint8:
                # Fallback for any other type
                print(f"Unknown dtype {self.original_image.dtype}, converting to uint8")
                img_min = np.min(self.original_image)
                img_max = np.max(self.original_image)
                if img_max > img_min:
                    normalized = (self.original_image.astype(np.float64) - img_min) / (img_max - img_min) * 255
                    self.original_image = normalized.astype(np.uint8)
                else:
                    self.original_image = np.zeros((self.original_image.shape), dtype=np.uint8)
            
            print(f"After normalization: dtype={self.original_image.dtype}, range=[{np.min(self.original_image)}, {np.max(self.original_image)}]")
            
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
        # Use more aggressive percentiles (0.1% and 99.9%) to better handle the normalized 8-bit data
        p_low = np.percentile(self.original_image, 0.1)
        p_high = np.percentile(self.original_image, 99.9)
        
        # Ensure min and max are different
        if p_high <= p_low:
            p_low = np.min(self.original_image)
            p_high = np.max(self.original_image)
        
        # Add some margin if the range is still too narrow
        range_val = p_high - p_low
        if range_val < 10:  # If range is very narrow
            mid = (p_high + p_low) / 2
            p_low = max(0, mid - 25)
            p_high = min(255, mid + 25)
        
        self.min_val = int(p_low)
        self.max_val = int(p_high)
        
        print(f"Auto-adjust: min={self.min_val}, max={self.max_val} (range={self.max_val - self.min_val})")
        
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
        
        # Apply contrast stretching with proper input->output mapping
        # min_val and max_val define the INPUT range that gets mapped to 0-255 OUTPUT
        img = self.original_image.astype(np.float32)
        
        if self.max_val > self.min_val:
            # Map [min_val, max_val] input range to [0, 255] output range
            # Values below min_val -> black (0)
            # Values above max_val -> white (255)
            img = (img - self.min_val) / (self.max_val - self.min_val) * 255
            img = np.clip(img, 0, 255)
        
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

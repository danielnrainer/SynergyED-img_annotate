# SynergyED Image Annotate

A PyQt6-based desktop application for processing (mainly) Synergy-ED images with scalebars, aperture overlays, and batch processing capabilities.

## Features

- **Image Processing**: Load TIF/TIFF images with automatic brightness/contrast adjustment
- **Smart Scalebars**: Calibrated scalebars with customizable appearance (length, thickness, position, colors, font)
- **Aperture Overlay**: Visualize SAED aperture sizes on images
- **Batch Processing**: Process multiple images with consistent settings
- **Imaging Presets**: Store and manage pixel size calibrations for different imaging modes
- **Compact UI**: Laptop-friendly interface with collapsible sections and scrollable controls
- **Multiple Export Formats**: PNG, TIFF, JPEG

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/danielnrainer/SynergyED-img_annotate.git
cd SynergyED-img_annotate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

Run the application:
```bash
python SynergyED-img_annotate.py
```

**Basic Workflow:**
1. Load an image (Ctrl+O)
2. Select imaging mode preset or enter pixel size manually
3. Adjust brightness/contrast (Auto Adjust recommended)
4. Configure scalebar settings (length, position, colors)
5. Export image (Ctrl+S)

**Batch Processing:**
- File → Batch Annotate (Ctrl+B)
- Add images, configure settings, and process all at once

## Project Structure

```
SynergyED-img_annotate/
├── core/                       # Core processing modules
│   ├── image_processor.py     # Image loading and adjustments
│   └── overlay_renderer.py    # Scalebar and aperture rendering
├── gui/                       # GUI components
│   └── collapsible_box.py    # Collapsible section widget
├── utils/                     # Utility modules
│   └── preset_manager.py     # Preset storage and management
├── SynergyED-img_annotate.py # Main application entry point
├── requirements.txt           # Python dependencies
└── pixelsize_presets.json    # Pixel size presets
```

## Requirements

- Python 3.8+
- PyQt6 >= 6.10.0
- NumPy >= 2.3.4
- Pillow >= 12.0.0

## Technical Details

- **Image Processing**: 8-bit grayscale (16-bit images auto-normalized)
- **Scalebar Calculation**: Accounts for nm/pixel calibration
- **Architecture**: Modular design with separate core, GUI, and utility modules
- **UI**: Collapsible sections for efficient screen space management

## Building Executable

Create a standalone executable with PyInstaller:
```bash
pyinstaller SynergyED-img_annotate.spec
```

## License

BSD 3-Clause License - see [LICENSE](LICENSE) file for details.

## Author

Daniel N. Rainer (ORCID: 0000-0002-3272-3161)

Project Link: [https://github.com/danielnrainer/SynergyED-img_annotate](https://github.com/danielnrainer/SynergyED-img_annotate)

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# Collect all PyQt6 submodules to avoid missing plugin issues on some systems
hidden_pyqt6 = collect_submodules('PyQt6')

block_cipher = None


a = Analysis(
    ['SynergyED-img_annotate.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include data files as (source, dest) tuples
        ('pixelsize_presets.json', '.'),
        # Include all module directories
        ('core', 'core'),
        ('gui', 'gui'),
        ('utils', 'utils'),
    ],
    hiddenimports=hidden_pyqt6 + [
        'PyQt6.QtCore', 
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'core.image_processor',
        'core.overlay_renderer',
        'gui.collapsible_box',
        'utils.preset_manager',
        'numpy',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SynergyED-img_annotate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app (no console window)
    icon=None,      # Set to a .ico path if you have an app icon
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

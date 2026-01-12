# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for MoIP Manager."""

import sys
from pathlib import Path

# Determine the project root (one level up from packaging/)
project_root = Path(SPECPATH).parent

block_cipher = None

# Icon paths (use None if icons don't exist yet)
mac_icon_path = project_root / 'packaging' / 'icons' / 'icon.icns'
win_icon_path = project_root / 'packaging' / 'icons' / 'icon.ico'
mac_icon = str(mac_icon_path) if mac_icon_path.exists() else None
win_icon = str(win_icon_path) if win_icon_path.exists() else None

# Collect all data files (static assets, templates, etc.)
datas = [
    (str(project_root / 'app' / 'static'), 'app/static'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # System tray support
    'pystray',
    'pystray._darwin',
    'pystray._win32',
    'PIL',
    'PIL.Image',
]

a = Analysis(
    [str(project_root / 'run.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='MoIP Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=mac_icon if sys.platform == 'darwin' else win_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MoIP Manager',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='MoIP Manager.app',
        icon=mac_icon,
        bundle_identifier='com.moip.manager',
        info_plist={
            'CFBundleName': 'MoIP Manager',
            'CFBundleDisplayName': 'MoIP Manager',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSBackgroundOnly': False,
        },
    )

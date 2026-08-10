# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH).resolve().parent

soundfile_datas, soundfile_bins, soundfile_hidden = collect_all('soundfile')
sounddevice_datas, sounddevice_bins, sounddevice_hidden = collect_all('sounddevice')

analysis = Analysis(
    [str(project_root / 'app.py')],
    pathex=[str(project_root)],
    binaries=soundfile_bins + sounddevice_bins,
    datas=soundfile_datas + sounddevice_datas + [
        (str(project_root / 'assets' / 'icon.ico'), 'assets'),
        (str(project_root / 'assets' / 'icon.png'), 'assets'),
        (str(project_root / 'assets' / 'icon.svg'), 'assets'),
        (str(project_root / 'assets' / 'icon.icns'), 'assets'),
    ],
    hiddenimports=soundfile_hidden + sounddevice_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='FilmSetRecorder',
    icon=str(project_root / 'assets' / 'icon.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FilmSetRecorder',
)

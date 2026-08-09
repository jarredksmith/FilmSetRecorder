# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

soundfile_datas, soundfile_bins, soundfile_hidden = collect_all('soundfile')
sounddevice_datas, sounddevice_bins, sounddevice_hidden = collect_all('sounddevice')

block_cipher = None

analysis = Analysis(
    ['app.py'],
    pathex=[],
    binaries=soundfile_bins + sounddevice_bins,
    datas=soundfile_datas + sounddevice_datas,
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='FilmSetRecorder',
)

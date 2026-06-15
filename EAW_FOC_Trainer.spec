# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules('pymem') + collect_submodules('keyboard') + [
    'shared', 'shared.paths', 'shared.process', 'shared.xml_store', 'shared.bootstrap',
    'trainer', 'trainer.app', 'trainer.cheats', 'trainer.scanner', 'trainer.hotkeys', 'trainer.hotkey_store', 'trainer.file_logger',
]

a = Analysis(
    ['trainer_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EAW_FOC_Trainer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

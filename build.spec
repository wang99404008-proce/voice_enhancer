# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 若有 models/ 或 icon.ico 存在則動態加入 datas
datas = []
if os.path.exists('models'):
    datas.append(('models', 'models'))
if os.path.exists('icon.ico'):
    datas.append(('icon.ico', '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'soundfile',
        'pedalboard',
        'scipy.signal',
        'scipy.special',
        'scipy.special.cython_special',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'tensorflow',
        'matplotlib',
        'IPython',
        'pytest',
    ],
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
    name='VoiceEnhancer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 設為 False 可大幅降低 Windows Defender 誤殺機率
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不顯示黑底 CMD 視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

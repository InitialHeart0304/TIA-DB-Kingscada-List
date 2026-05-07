# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

VERSION_INFO = VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904b0',
        [StringStruct('CompanyName', 'ZHONGCANXIAO'),
        StringStruct('FileDescription', 'DB-Kingscada List'),
        StringStruct('FileVersion', '1.0.0.0'),
        StringStruct('InternalName', 'Python model testing'),
        StringStruct('LegalCopyright', 'Copyright (C) 2026 ZHONGCANXIAO'),
        StringStruct('OriginalFilename', 'DB-Kingscada List.exe'),
        StringStruct('ProductName', 'S7点表生成'),
        StringStruct('ProductVersion', '1.0.0.0'),
        StringStruct('Comments', '作者：ZHONGCANXIAO')])
      ]),
    VarFileInfo([VarStruct('Translation', [0x409, 1200])])
  ]
)

a = Analysis(
    ['DB-KingscadaV6.2.py'],
    pathex=[],
    binaries=[],
    datas=[('hat_star_icon.ico', '.')],
    hiddenimports=[],
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
    name='DB-KingscadaV6.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['hat_star_icon.ico'],
    version=VERSION_INFO,
)

# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\core', 'core'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\agents', 'agents'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\vm', 'vm'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\android', 'android'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\plugins', 'plugins'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\dashboard\\templates', 'dashboard/templates'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\dashboard\\static', 'dashboard/static'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\config.yaml', '.'), ('C:\\Users\\evosp\\Downloads\\angeticbackup\\agent_zero\\logs', 'logs')],
    hiddenimports=['asyncio', 'sqlite3', 'yaml', 'tenacity', 'bs4', 'flask', 'jinja2', 'werkzeug', 'cryptography', 'aiohttp', 'queue', 'threading', 'uuid', 'json', 're', 'ast', 'shutil', 'subprocess', 'concurrent', 'concurrent.futures', 'pkg_resources', 'pkgutil', 'importlib', 'inspect', 'ctypes', 'pathlib', 'http.client', 'urllib.request', 'urllib.error', 'socket', 'ssl', 'email', 'email.mime', 'email.mime.text', 'email.mime.multipart', 'xml', 'xml.etree', 'xml.etree.ElementTree', 'html.parser', 'winsound', 'win32com', 'win32com.client', 'pythoncom', 'PIL', 'PIL.ImageGrab', 'pyautogui', 'requests', 'stripe', 'docker', 'flask_socketio', 'eventlet', 'engineio', 'werkzeug.security', 'cryptography.hazmat.primitives', 'cryptography.hazmat.primitives.asymmetric', 'cryptography.hazmat.backends', 'cryptography.hazmat.primitives.hashes', 'cryptography.hazmat.primitives.serialization', 'dashboard', 'dashboard.app'],
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
    name='AngeticEssence',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

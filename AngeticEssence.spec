# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

BASE = r'C:\Users\evosp\Downloads\angeticbackup\agent_zero'

# Collect every file inside the dashboard package so PyInstaller
# bundles dashboard/__init__.py, dashboard/app.py, etc. as importable modules
dashboard_datas, dashboard_binaries, dashboard_hiddenimports = collect_all('dashboard')

# Collect flask and werkzeug fully (they use dynamic plugin loading)
flask_datas, flask_binaries, flask_hiddenimports = collect_all('flask')
werkzeug_datas, werkzeug_binaries, werkzeug_hiddenimports = collect_all('werkzeug')
jinja2_datas, jinja2_binaries, jinja2_hiddenimports = collect_all('jinja2')

all_datas = (
    dashboard_datas
    + flask_datas
    + werkzeug_datas
    + jinja2_datas
    + [
        (os.path.join(BASE, 'core'),                          'core'),
        (os.path.join(BASE, 'agents'),                        'agents'),
        (os.path.join(BASE, 'vm'),                            'vm'),
        (os.path.join(BASE, 'android'),                       'android'),
        (os.path.join(BASE, 'plugins'),                       'plugins'),
        (os.path.join(BASE, 'dashboard', 'templates'),        'dashboard/templates'),
        (os.path.join(BASE, 'dashboard', 'static'),           'dashboard/static'),
        (os.path.join(BASE, 'config.yaml'),                   '.'),
    ]
)

all_binaries  = dashboard_binaries + flask_binaries + werkzeug_binaries + jinja2_binaries
all_hiddenimports = (
    dashboard_hiddenimports
    + flask_hiddenimports
    + werkzeug_hiddenimports
    + jinja2_hiddenimports
    + collect_submodules('dashboard')
    + collect_submodules('core')
    + collect_submodules('agents')
    + collect_submodules('plugins')
    + collect_submodules('vm')
    + collect_submodules('android')
    + [
        'dashboard', 'dashboard.app',
        'asyncio', 'sqlite3', 'yaml', 'tenacity', 'bs4',
        'flask', 'jinja2', 'werkzeug', 'cryptography', 'aiohttp',
        'queue', 'threading', 'uuid', 'json', 're', 'ast',
        'shutil', 'subprocess', 'concurrent', 'concurrent.futures',
        'pkg_resources', 'pkgutil', 'importlib', 'inspect',
        'ctypes', 'pathlib', 'http.client', 'urllib.request', 'urllib.error',
        'socket', 'ssl', 'email', 'email.mime', 'email.mime.text',
        'email.mime.multipart', 'xml', 'xml.etree', 'xml.etree.ElementTree',
        'html.parser', 'winsound', 'win32com', 'win32com.client',
        'pythoncom', 'PIL', 'PIL.ImageGrab', 'pyautogui',
        'requests', 'stripe', 'docker', 'flask_socketio',
        'eventlet', 'engineio',
        'werkzeug.security',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.serialization',
    ]
)

a = Analysis(
    [os.path.join(BASE, 'main.py')],
    pathex=[BASE],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
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

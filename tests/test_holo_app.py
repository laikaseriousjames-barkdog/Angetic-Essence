import os
import re
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
HOLO_DIR = os.path.join(REPO_DIR, "holo-app")

def test_holo_manifest_and_resources():
    manifest_path = os.path.join(HOLO_DIR, "AndroidManifest.xml")
    assert os.path.isfile(manifest_path), "holo-app/AndroidManifest.xml missing"
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "package=\"org.antigravity.agenticholo\"" in content
    assert "android.permission.RECORD_AUDIO" in content
    assert "android.permission.INTERNET" in content
    assert "MainActivity" in content

def test_holo_web_assets_integrity():
    assets_dir = os.path.join(HOLO_DIR, "assets/www")
    assert os.path.isdir(assets_dir), "assets/www directory missing in holo-app"

    index_html = os.path.join(assets_dir, "index.html")
    styles_css = os.path.join(assets_dir, "styles.css")
    renderer_js = os.path.join(assets_dir, "holo-renderer.js")
    voice_js = os.path.join(assets_dir, "voice-engine.js")
    spatial_js = os.path.join(assets_dir, "spatial-tasks.js")
    app_js = os.path.join(assets_dir, "app.js")

    for p in [index_html, styles_css, renderer_js, voice_js, spatial_js, app_js]:
        assert os.path.isfile(p), f"Missing holo-app asset: {p}"

    with open(index_html, "r", encoding="utf-8") as f:
        html = f.read()
    # Confirm NO chat boxes / input forms
    assert "type=\"text\"" not in html.lower() or "id=\"modelinput\"" not in html.lower()
    assert "holo-stage-canvas" in html
    assert "spatial-task-viewport" in html
    assert "voice-orb-container" in html

def test_holo_renderer_personas():
    renderer_js = os.path.join(HOLO_DIR, "assets/www/holo-renderer.js")
    with open(renderer_js, "r", encoding="utf-8") as f:
        js = f.read()

    assert "drawSwarm" in js
    assert "drawTuring" in js
    assert "drawKnuth" in js
    assert "drawLovelace" in js
    assert "FRAME_INTERVAL" in js

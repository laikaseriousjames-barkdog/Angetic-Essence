#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/holo-app"
SDK_DIR="/root/android-sdk"
if [ ! -f "$SDK_DIR/android.jar" ] && [ -f "/root/android_tools/android.jar" ]; then
    SDK_DIR="/root/android_tools"
fi

KEYSTORE="/root/debug.keystore"
if [ ! -f "$KEYSTORE" ] && [ -f "/root/android_tools/debug.keystore" ]; then
    KEYSTORE="/root/android_tools/debug.keystore"
fi

OUT_APK="$APP_DIR/bin/AgenticHolo-Android.apk"

echo "=== Building Agentic Hologram Android Holodeck APK ==="

mkdir -p "$APP_DIR/bin" "$APP_DIR/obj" "$APP_DIR/assets/www"

# Verify asset existence
test -f "$APP_DIR/assets/www/index.html" || { echo "Error: holo-app/assets/www/index.html missing"; exit 1; }
test -f "$APP_DIR/assets/www/styles.css" || { echo "Error: holo-app/assets/www/styles.css missing"; exit 1; }
test -f "$APP_DIR/assets/www/holo-renderer.js" || { echo "Error: holo-app/assets/www/holo-renderer.js missing"; exit 1; }
test -f "$APP_DIR/assets/www/spatial-tasks.js" || { echo "Error: holo-app/assets/www/spatial-tasks.js missing"; exit 1; }
test -f "$APP_DIR/assets/www/voice-engine.js" || { echo "Error: holo-app/assets/www/voice-engine.js missing"; exit 1; }
test -f "$APP_DIR/assets/www/app.js" || { echo "Error: holo-app/assets/www/app.js missing"; exit 1; }

# Step 1: Generate R.java
echo "Step 1: Generating R.java with aapt..."
aapt package -f -m -J "$APP_DIR/src" \
    -M "$APP_DIR/AndroidManifest.xml" \
    -S "$APP_DIR/res" \
    -I "$SDK_DIR/android.jar"

# Step 2: Compile Java sources
echo "Step 2: Compiling Java source files with javac..."
javac -d "$APP_DIR/obj" \
    -cp "$SDK_DIR/android.jar" \
    "$APP_DIR/src/org/antigravity/agenticholo/"*.java \
    --release 8

# Step 3: Compile classes to DEX using D8
echo "Step 3: Compiling classes to DEX with D8..."
java -cp "$SDK_DIR/r8.jar" com.android.tools.r8.D8 \
    --output "$APP_DIR/bin" \
    --lib "$SDK_DIR/android.jar" \
    --min-api 21 \
    "$APP_DIR/obj/org/antigravity/agenticholo/"*.class

# Step 4: Package resources and assets into APK
echo "Step 4: Packaging assets and manifest into initial APK..."
aapt package -f \
    -M "$APP_DIR/AndroidManifest.xml" \
    -S "$APP_DIR/res" \
    -A "$APP_DIR/assets" \
    -I "$SDK_DIR/android.jar" \
    -F "$APP_DIR/bin/unaligned.apk"

# Step 5: Add classes.dex into APK
echo "Step 5: Adding classes.dex to APK package..."
cd "$APP_DIR/bin"
aapt add unaligned.apk classes.dex
cd "$SCRIPT_DIR"

# Step 6: Zipalign APK
echo "Step 6: Zipaligning APK package..."
zipalign -f -p 4 "$APP_DIR/bin/unaligned.apk" "$APP_DIR/bin/unsigned.apk"

# Step 7: Sign APK with debug keystore
echo "Step 7: Signing APK package with apksigner..."
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkey -v -keystore "$KEYSTORE" \
        -alias androiddebugkey -keypass android -storepass android \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Agentic Holo, OU=Swarm, O=Agentic, L=Global, ST=Earth, C=US"
fi

apksigner sign --ks "$KEYSTORE" \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --out "$OUT_APK" \
    "$APP_DIR/bin/unsigned.apk"

# Step 8: Verify signature
echo "Step 8: Verifying APK signature..."
apksigner verify "$OUT_APK"

# Step 9: Distribute locally and to downloads
if [ -d "$SCRIPT_DIR/downloads" ]; then
    cp "$OUT_APK" "$SCRIPT_DIR/downloads/AgenticHolo-Android.apk"
fi
if [ -w "/root" ]; then
    mkdir -p /root/Downloads
    cp "$OUT_APK" /root/Downloads/AgenticHolo-Android.apk 2>/dev/null || true
    cp "$OUT_APK" /root/AgenticHolo-Android.apk 2>/dev/null || true
fi
if [ -d "/sdcard/Download" ] && [ -w "/sdcard/Download" ]; then
    cp "$OUT_APK" /sdcard/Download/AgenticHolo-Android.apk 2>/dev/null || true
fi

echo "=== SUCCESS! Agentic Hologram APK built and verified at $OUT_APK ==="
ls -lh "$OUT_APK"

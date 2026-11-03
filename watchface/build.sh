#!/usr/bin/env bash
# Gera o projeto, valida o XML e empacota o APK assinado (sem Gradle).
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-$LOCALAPPDATA/Android/Sdk}"
BT="$SDK/build-tools/36.0.0"
JAR="$SDK/platforms/android-37.0/android.jar"
OUT=out
mkdir -p "$OUT"

python gen.py
java ../build/Validate.java ../build/v4x/watchface.xsd src/res/raw/watchface.xml

rm -f "$OUT/compiled.zip" "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$BT/aapt2.exe" compile --dir src/res -o "$OUT/compiled.zip"
"$BT/aapt2.exe" link -o "$OUT/unsigned.apk" -I "$JAR" --manifest src/AndroidManifest.xml \
  --min-sdk-version 36 --target-sdk-version 36 --version-code 1 --version-name 1.0 "$OUT/compiled.zip"
"$BT/zipalign.exe" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"

# Chave local só para instalar no seu relógio (não serve para publicar na Play Store)
KS="$OUT/horizonte.keystore"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias horizonte \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Horizonte Watch Face"
fi
"$BT/apksigner.bat" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android --out "$OUT/horizonte.apk" "$OUT/aligned.apk"
"$BT/apksigner.bat" verify "$OUT/horizonte.apk" && echo "APK pronto: $OUT/horizonte.apk"
ls -l "$OUT/horizonte.apk"

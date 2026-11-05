#!/usr/bin/env bash
# Uso: bash shared/build.sh <face> [--bump]
# Gera o projeto da face, valida o XML e empacota o APK assinado (sem Gradle).
# versionCode vem de faces/<face>/version (um inteiro). --bump incrementa antes do build.
set -euo pipefail

FACE="${1:?uso: build.sh <face> [--bump]}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FACE_DIR="$ROOT/faces/$FACE"
TOOLS="$ROOT/shared/tools"
[ -d "$FACE_DIR" ] || { echo "Face não encontrada: $FACE_DIR"; exit 1; }
cd "$FACE_DIR"

VFILE=version
[ -f "$VFILE" ] || echo 1 > "$VFILE"
if [ "${2:-}" = "--bump" ]; then echo $(( $(cat "$VFILE") + 1 )) > "$VFILE"; fi
VCODE="$(cat "$VFILE")"
VNAME="1.$((VCODE - 1))"

SDK="${ANDROID_HOME:-$LOCALAPPDATA/Android/Sdk}"
BT="$SDK/build-tools/36.0.0"
JAR="$SDK/platforms/android-37.0/android.jar"
OUT=out
mkdir -p "$OUT" "$ROOT/dist"

python gen.py
python -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('src/res/raw/watchface.xml'); print('XML bem formado')"
# O schema oficial v4x quebra no Xerces do Java (cos-all-limited); vale só como aviso.
java "$TOOLS/Validate.java" "$TOOLS/v4x/watchface.xsd" src/res/raw/watchface.xml 2>/dev/null   || echo "aviso: validação XSD indisponível (schema v4x incompatível com Xerces)"

rm -f "$OUT/compiled.zip" "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$BT/aapt2.exe" compile --dir src/res -o "$OUT/compiled.zip"
"$BT/aapt2.exe" link -o "$OUT/unsigned.apk" -I "$JAR" --manifest src/AndroidManifest.xml \
  --min-sdk-version 36 --target-sdk-version 36 --version-code "$VCODE" --version-name "$VNAME" "$OUT/compiled.zip"
"$BT/zipalign.exe" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"

# Chave local só para instalar no seu relógio (NÃO serve para publicar na Play Store).
# Para publicar use a chave de upload guardada fora do repositório.
KS="$OUT/$FACE.keystore"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias "$FACE" \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=$FACE Watch Face"
fi
"$BT/apksigner.bat" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android --out "$OUT/$FACE.apk" "$OUT/aligned.apk"
"$BT/apksigner.bat" verify "$OUT/$FACE.apk" && echo "APK pronto: $OUT/$FACE.apk (versionCode $VCODE)"
cp "$OUT/$FACE.apk" "$ROOT/dist/$FACE.apk"

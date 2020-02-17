#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-STM32CubeMX.exe>"
    exit 1
fi

OUTDIR=stm1337cubemx
INEXE=$1
OUTJAR=$(dirname $INEXE)/STM1337CubeMX.jar

if [ ! -f "$INEXE" ]; then
    echo "File \"$INEXE\" not found"
    exit 1
fi
if [ -d "$OUTDIR" ]; then
    echo "Temp directory \"$OUTDIR\" already exists, please remove it"
    exit 1
fi
if [ -f "$OUTJAR" ]; then
    echo "JAR $OUTJAR already exists, please remove it"
    exit 1
fi

echo "[1] Creating temporary directory..."
mkdir "$OUTDIR"
cp "$INEXE" "$OUTDIR/"
cd "$OUTDIR"
echo "[2] Unpacking $INEXE..."
unzip -q "$INEXE" || echo "Unzip exited with warnings or errors"
rm "$(basename $INEXE)"

echo "[3] Patching class file..."
python3 "$DIR/patch-cubemx-class.py"

echo "[4] Recreating JAR file..."
jar cmf META-INF/MANIFEST.MF "$OUTJAR" *

echo "[5] Done! Run \"java -jar $(basename $OUTJAR)\" to start STM1337CubeMX."

#!/bin/bash
set -e
set -o pipefail
JLISA_BIN_DIR="jlisa-0.1"
VENV_DIR=".sv-comp_venv"

usage() {
    echo "Usage: $0 --jlisa-dir PATH_TO_JLISA"
    exit 1
}

JLISA_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --jlisa-dir)
            JLISA_DIR="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            ;;
    esac
done

if [[ -z "$JLISA_DIR" ]]; then
    echo "Error: --jlisa-dir is required."
    usage
fi

echo ">>> JLISA_DIR=$JLISA_DIR"
SV_COMP_DIR="."
SVCOMP_BENCHMARK_DIR="$(pwd)/SVCOMP/sv-benchmarks"

PYTHON=${PYTHON:-python3}
echo "Creating venv in $VENV_DIR using $($PYTHON --version)"
$PYTHON -m venv "$VENV_DIR"
VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
$VENV_PIP install --upgrade pip
echo "Installing pyinstaller..."
$VENV_PIP install pyinstaller
echo "Running vendoryze..."
$VENV_PY ./vendor/vendorize.py



TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTDIR="$(pwd)/outputs/$TIMESTAMP"

mkdir -p "$OUTDIR"

if [ -d "$JLISA_DIR/build" ]; then
    echo "Removing existing jlisa build folder..."
    rm -rf "$JLISA_DIR/build"
fi

echo "Building jlisa..."
(cd "$JLISA_DIR" && ./gradlew clean build --refresh-dependencies -x test -x spotlessApply -x spotlessCheck --no-configuration-cache)

if [ -d "$SV_COMP_DIR/$JLISA_BIN_DIR" ]; then
    echo "Removing existing $SV_COMP_DIR/$JLISA_BIN_DIR folder..."
    rm -rf "$SV_COMP_DIR/$JLISA_BIN_DIR"
fi

echo "Unzipping jlisa distribution into $SV_COMP_DIR..."
JLISA_ZIP=$(ls $JLISA_DIR/build/distributions/*.zip | head -n1)
if [ -z "$JLISA_ZIP" ]; then
    echo "Error: No jlisa zip found in build/distributions"
    exit 1
fi
unzip -o "$JLISA_ZIP" -d "$SV_COMP_DIR/"


JLISA_DIR_UNZIPPED="$JLISA_BIN_DIR"
CONFIG_JSON="$SV_COMP_DIR/config.json"

echo "Creating config.json..."
cat > "$CONFIG_JSON" << EOF
{
    "path_to_sv_comp_benchmark_dir": "$SVCOMP_BENCHMARK_DIR",
    "path_to_lisa_instance": "\"${JLISA_DIR_UNZIPPED}/lib/*\"",
    "path_to_output_dir": "$OUTDIR"
}
EOF

if [ -f "$SV_COMP_DIR/smoketest.sh" ]; then
    echo "Running smoketest..."
    (cd "$SV_COMP_DIR" && bash smoketest.sh)
else
    echo "Warning: smoketest.sh not found in $SV_COMP_DIR"
fi

echo "Generating jlisa executable."


APP_NAME="jlisa"
MAIN_SCRIPT="main.py"
PYVER=$($VENV_PY -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
VENDOR_PATH="vendor/lib/python$PYVER/site-packages"
INCLUDE_ITEMS=(
  "$JLISA_BIN_DIR:$JLISA_BIN_DIR"
  "./config.json:."
  "./pyproject.toml:."
)

ADD_DATA_FLAGS=()
for item in "${INCLUDE_ITEMS[@]}"; do
  ADD_DATA_FLAGS+=(--add-data "$item")
done

echo "===================================="
echo " Building project"
echo "  • Main script: $MAIN_SCRIPT"
echo "  • Output name: $APP_NAME"
echo "===================================="


$VENV_PY -m PyInstaller "$MAIN_SCRIPT" \
  --onefile \
  --clean --strip \
  --name "$APP_NAME" \
  --paths "$VENDOR_PATH" \
  "${ADD_DATA_FLAGS[@]}"

echo ""
echo "Build complete!"
echo "Executable created at: dist/$APP_NAME"
echo ""

JLISA_EXEC="dist/$APP_NAME"
DIST_TEMPLATE="dist-template"
MAIN_FOLDER="$(pwd)"
TEMP_DIR="$(mktemp -d "$MAIN_FOLDER/tmp_dist_XXXX")"
JLISA_FOLDER="$TEMP_DIR/$JLISA_BIN_DIR"
ZIP_FILE="$MAIN_FOLDER/jlisa.zip"

if [ -f "$ZIP_FILE" ]; then
    echo "Removing existing $ZIP_FILE in main folder..."
    rm -f "$ZIP_FILE"
fi

echo "Creating temporary folder at $JLISA_FOLDER..."

mkdir -p "$JLISA_FOLDER"

cp -r "$DIST_TEMPLATE/." "$JLISA_FOLDER/"

cp "$JLISA_EXEC" "$JLISA_FOLDER/"
chmod +x "$JLISA_FOLDER/$(basename "$JLISA_EXEC")"
chmod +x "$JLISA_FOLDER/smoketest.sh"

echo "Creating zip file $ZIP_FILE..."
(cd "$TEMP_DIR" && zip -r "$ZIP_FILE" "$JLISA_BIN_DIR")

echo "Cleaning up temporary folder..."
rm -rf "$TEMP_DIR"

echo "Zip package created successfully: $ZIP_FILE"

TEST_DIR="$(mktemp -d "$MAIN_FOLDER/tmp_test_XXXX")"
echo "Unzipping $ZIP_FILE into $TEST_DIR..."
unzip -q "$ZIP_FILE" -d "$TEST_DIR"
echo "Test smoketest.sh of zip"
SMOKETEST="$TEST_DIR/$JLISA_BIN_DIR/smoketest.sh"
if [ -f "$SMOKETEST" ]; then
    echo "Running smoketest.sh..."
    (cd "$TEST_DIR/$JLISA_BIN_DIR" && bash smoketest.sh)
else
    echo "Warning: smoketest.sh not found in the zip"
fi

rm -rf "$TEST_DIR"
echo "Temporary test folder cleaned up."

echo "jlisa.zip successfully create in $(pwd)"
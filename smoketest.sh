#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

MAIN_PY="$SCRIPT_DIR/main.py"

# Prepend SCRIPT_DIR to all input paths
INPUT_1=(
  "$SCRIPT_DIR/test/01/Main.java"
)

INPUT_2=(
  "$SCRIPT_DIR/test/02/Main.java"
)

PROPERTY="$SCRIPT_DIR/test/valid-assert.prp"

# Run the command
python "$MAIN_PY" check --inputs "${INPUT_1[@]}" --property "$PROPERTY"
python "$MAIN_PY" check --inputs "${INPUT_2[@]}" --property "$PROPERTY"
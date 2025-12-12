#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

JLISA="$SCRIPT_DIR/jlisa"

# Prepend SCRIPT_DIR to all input paths
INPUT_1=(
  "$SCRIPT_DIR/test/01/Main.java"
)

INPUT_2=(
  "$SCRIPT_DIR/test/02/Main.java"
)

PROPERTY="$SCRIPT_DIR/test/valid-assert.prp"

# Run the command
$JLISA version
$JLISA check --inputs "${INPUT_1[@]}" --property "$PROPERTY"
$JLISA check --inputs "${INPUT_2[@]}" --property "$PROPERTY"
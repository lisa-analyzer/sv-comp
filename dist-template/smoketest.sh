#!/usr/bin/env bash
# Smoke test of the jlisa archive: `jlisa check` (if jlisa is included) and `jlisa validate`
# (if jlisa-wit is included). Set JLISA to test another command, e.g. JLISA="python3 main.py".
set -euo pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TEST="$SCRIPT_DIR/test"

JLISA="${JLISA:-$SCRIPT_DIR/jlisa}"

version="$($JLISA version)"
echo "version: $version"
[ -n "$version" ]

components="$($JLISA components)"
if [ -z "$components" ]; then
  echo "error: neither jlisa nor jlisa-wit is included"
  exit 1
fi

# expect NAME ACTUAL EXPECTED
expect() {
  echo "$1: $2"
  if [ "$2" != "$3" ]; then
    echo "error: expected $3"
    exit 1
  fi
}

# check PROPERTY EXPECTED INPUT...
check() {
  local property="$1" expected="$2"
  shift 2
  expect "check $property $*" "$($JLISA check --inputs "$*" --property "$TEST/$property" | tail -n 1)" "$expected"
}

# validate WITNESS PROPERTY PROGRAM EXPECTED
validate() {
  local witness="$1" property="$2" program="$3" expected="$4"
  expect "validate $witness $property $program" \
    "$($JLISA validate --witness "$TEST/$witness" --property "$TEST/$property" --inputs "$TEST/common/ $TEST/$program/" | tail -n 1)" \
    "$expected"
}

if grep -qx jlisa <<< "$components"; then
  check valid-assert.prp TRUE "$TEST/01/Main.java"
  check valid-assert.prp TRUE "$TEST/02/Main.java"
  check valid-assert.prp UNKNOWN "$TEST/common/" "$TEST/nondet-assert/"
else
  echo "skipped: jlisa not included"
fi

if grep -qx jlisa-wit <<< "$components"; then
  # FALSE: witness confirmed, TRUE: witness rejected, UNKNOWN: could not validate
  validate witness-correct.graphml valid-assert.prp nondet-assert FALSE
  validate witness-spurious.graphml valid-assert.prp nondet-assert TRUE
  validate witness-novalue.graphml valid-assert.prp nondet-assert UNKNOWN
  validate witness-correct.graphml no-runtime-exception.prp nondet-rte FALSE
  validate witness-correct.graphml no-runtime-exception.prp nondet-assert UNKNOWN
else
  echo "skipped: jlisa-wit not included"
fi

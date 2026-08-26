#!/bin/sh
# The mandated way to invoke any gate suite. Closes the exit-code-masking
# class: a pipe (`suite | tail`) returns the pipe tail's status, and a
# compound wrapper (`echo done; suite; echo ok`) returns the LAST command's
# status - both shapes reported a C5 smoke failure as green. This runner
# never pipes the suite and demands BOTH proofs of health:
#
#   1. the suite process exits 0, AND
#   2. its output ends with the success sentinel (default "ALL PASS";
#      override with GATE_SENTINEL for suites with a different final line,
#      e.g. GATE_SENTINEL="MATH DIFF PROOF: EMPTY" for mathdiff).
#
# Any mismatch - nonzero exit, missing sentinel, or a FAILURES line beside
# exit 0 - fails loudly with a GATE FAIL line and a nonzero exit. Even if a
# careless caller pipes THIS script, the GATE FAIL line survives in output.
#
# Usage: sh tests/run_gate.sh <command...>
#   sh tests/run_gate.sh python3 tests/test_vor.py
#   GATE_SENTINEL="MATH DIFF PROOF: EMPTY" sh tests/run_gate.sh python3 tests/mathdiff.py
# Self-test: python3 tests/test_run_gate.py (deliberately failing fixtures).
set -u
[ $# -ge 1 ] || { echo "GATE FAIL: no command given"; exit 2; }
SENTINEL="${GATE_SENTINEL:-ALL PASS}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

"$@" >"$TMP" 2>&1
CODE=$?
cat "$TMP"

if [ "$CODE" -ne 0 ]; then
    echo "GATE FAIL: suite exited $CODE ($*)"
    exit "$CODE"
fi
if ! tail -5 "$TMP" | grep -qF "$SENTINEL"; then
    echo "GATE FAIL: exit 0 but the sentinel '$SENTINEL' is absent from the output tail ($*)"
    exit 1
fi
if grep -qE "^[0-9]+ FAILURES" "$TMP"; then
    echo "GATE FAIL: exit 0 but the output reports a failure count ($*)"
    exit 1
fi
echo "GATE OK: $*"
exit 0

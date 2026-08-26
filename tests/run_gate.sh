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
#   3. no guard SKIPPED itself (override with GATE_ALLOW_SKIP=1).
#
# Any mismatch - nonzero exit, missing sentinel, a FAILURES line beside exit 0,
# or an unexpected SKIP - fails loudly with a GATE FAIL line and a nonzero exit.
# Even if a careless caller pipes THIS script, the GATE FAIL line survives.
#
# THE SKIP RULE, and why it exists. run_gate originally proved only that the
# ENVELOPE was healthy - the process exited 0 and said ALL PASS. It could not
# see whether the guards inside had actually run. tests/test_analysis.py
# cache-gates five determinism reruns behind `if os.path.exists(...)`, so on any
# runner without the HISTORY cache it printed five SKIP lines and then ALL PASS,
# and the gate called that green. That is the same class as the exit-code
# masking this runner was written to close, one level up: a check that cannot
# fail. A skipped guard is now a failure unless the caller says otherwise, and
# every run reports RAN n GUARDS so coverage is a number, not an assumption.
#
# The count is taken here rather than inside each suite deliberately: one
# implementation cannot drift out of sync with fifteen suites, and it counts
# what the gate actually observed rather than what a suite claims.
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

# coverage: how many guards actually ran, and did any decline to run?
RAN=$(grep -cE "^(PASS|FAIL) " "$TMP" || true)
SKIPPED=$(grep -cE "^SKIP" "$TMP" || true)
echo "RAN $RAN GUARDS"
if [ "$SKIPPED" -gt 0 ]; then
    if [ "${GATE_ALLOW_SKIP:-0}" = "1" ]; then
        echo "GATE NOTE: $SKIPPED guard(s) skipped, allowed by GATE_ALLOW_SKIP=1"
    else
        echo "GATE FAIL: $SKIPPED guard(s) SKIPPED - a skipped guard is not a passing"
        echo "           guard. Set GATE_ALLOW_SKIP=1 only when the skip is expected"
        echo "           and its coverage loss is recorded ($*)"
        grep -E "^SKIP" "$TMP" | sed "s/^/           /"
        exit 1
    fi
fi
echo "GATE OK: $*"
exit 0

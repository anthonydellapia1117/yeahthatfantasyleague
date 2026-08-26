#!/usr/bin/env python3
"""Self-test for tests/run_gate.sh with deliberately failing fixtures.

The gate must catch every shape of the exit-code-masking class:
  liar      exits 0 while its output reports failures  -> gate nonzero
  crasher   exits nonzero mid-run                       -> gate nonzero
  mute      exits 0 with no success sentinel            -> gate nonzero
  honest    exits 0 and prints the sentinel             -> gate zero
  skipper   exits 0, prints the sentinel, but a guard SKIPPED itself
            -> gate nonzero by default, zero under GATE_ALLOW_SKIP=1.
            This is the class one level up: run_gate originally proved
            the envelope was healthy and could not see whether the
            guards inside had run at all.
  masked    the historical shape itself: the crasher run through
            `sh -c '...; suite; echo done'` and `suite | tail` both
            return 0 raw (proving the mask is real), while the gate
            wrapping the same suite returns nonzero.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "tests", "run_gate.sh")
FAILS = []


def ok(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


def fixture(body):
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    f.write(body)
    f.close()
    return f.name


LIAR = fixture('print("FAIL  something broke")\nprint("1 FAILURES")\n')
CRASHER = fixture('print("PASS  one thing")\nraise SystemExit(3)\n')
MUTE = fixture('print("did some work, said nothing conclusive")\n')
HONEST = fixture('print("PASS  the only check")\nprint("ALL PASS")\n')
SKIPPER = fixture('print("PASS  one real check")\n'
                  'print("SKIP  the determinism rerun - cache absent")\n'
                  'print("ALL PASS")\n')


def gate(*cmd, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(["sh", GATE] + list(cmd), capture_output=True,
                          text=True, env=e)


r = gate(sys.executable, LIAR)
ok(r.returncode != 0, "liar (exit 0 + FAILURES in output) is caught")
ok("GATE FAIL" in r.stdout, "liar: the gate says so loudly")

r = gate(sys.executable, CRASHER)
ok(r.returncode == 3, "crasher: the inner exit code propagates untouched")
ok("GATE FAIL" in r.stdout, "crasher: the gate says so loudly")

r = gate(sys.executable, MUTE)
ok(r.returncode != 0, "mute (exit 0, no sentinel) is caught")

r = gate(sys.executable, HONEST)
ok(r.returncode == 0, "honest suite passes the gate")
ok("GATE OK" in r.stdout, "honest suite gets the GATE OK line")

r = gate(sys.executable, MUTE,
         env={"GATE_SENTINEL": "did some work"})
ok(r.returncode == 0, "GATE_SENTINEL override works for non-ALL-PASS suites")

# prove the historical mask is real, then prove the gate closes it
raw_compound = subprocess.run(
    ["sh", "-c", f"echo pre; {sys.executable} {CRASHER}; echo post"],
    capture_output=True, text=True)
ok(raw_compound.returncode == 0,
   "control: a compound wrapper really does mask the crash (returns 0)")
raw_pipe = subprocess.run(
    ["sh", "-c", f"{sys.executable} {CRASHER} | tail -1"],
    capture_output=True, text=True)
ok(raw_pipe.returncode == 0,
   "control: a tail pipe really does mask the crash (returns 0)")
gated = subprocess.run(
    ["sh", "-c", f"sh {GATE} {sys.executable} {CRASHER} | tail -2"],
    capture_output=True, text=True)
ok("GATE FAIL" in gated.stdout,
   "even piped, the gate's loud failure line survives in output")

# the SKIP rule: a guard that declines to run is not a guard that passed.
# This is the masking class one level up - run_gate originally proved only
# that the ENVELOPE was healthy (exit 0 plus sentinel) and could not see
# whether the guards inside had run at all.
r = gate(sys.executable, SKIPPER)
ok(r.returncode != 0, "skipper: a SKIP line fails the gate despite exit 0 + sentinel")
ok("GATE FAIL" in r.stdout and "SKIPPED" in r.stdout,
   "skipper: the gate names the skip as the reason")
r = gate(sys.executable, SKIPPER, env={"GATE_ALLOW_SKIP": "1"})
ok(r.returncode == 0, "skipper: GATE_ALLOW_SKIP=1 permits an expected skip")
ok("GATE NOTE" in r.stdout,
   "skipper: an allowed skip is still reported, never silent")
# and the coverage count is emitted on every healthy run
r = gate(sys.executable, HONEST)
ok("RAN 1 GUARDS" in r.stdout,
   "honest: the gate reports how many guards actually ran")

for p in (LIAR, CRASHER, MUTE, HONEST, SKIPPER):
    os.unlink(p)

if FAILS:
    print(f"{len(FAILS)} FAILURES")
    sys.exit(1)
print("ALL PASS")

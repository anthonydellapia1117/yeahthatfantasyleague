#!/usr/bin/env python3
"""The frozen-math byte proof, run at every merge and on draft morning.

The five survival functions are law: byte-identical to origin/main in
BOTH surfaces - the Python originals in src/engine_2026.py and the JS
mirrors in out/draft_room.html. This script extracts each function body
from the working tree and from origin/main and compares bytes. Any
difference is a failure; there is no tolerance.

Run from the repo root after `git fetch origin main`:
    python3 tests/mathdiff.py
"""
import re
import subprocess
import sys

PY_FUNCS = ["fit_sd_curve", "sd_for", "_raw_survival", "survival",
            "cond_survival"]
JS_FUNCS = ["sdFor", "erfc", "rawSurvival", "survival", "condSurvival"]


def extract_js(src, name):
    m = re.search(r"function %s\(" % re.escape(name), src)
    if not m:
        return None
    i = src.index("{", m.start())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    return None


def extract_py(src, name):
    m = re.search(r"^def %s\(" % re.escape(name), src, re.M)
    if not m:
        return None
    end = re.search(r"^\S", src[m.end():], re.M)
    return src[m.start():m.end() + (end.start() if end else len(src))].rstrip()


def show(path):
    return subprocess.run(["git", "show", f"origin/main:{path}"],
                          capture_output=True, text=True, check=True).stdout


def main():
    ok = True
    for path, funcs, extract in (
            ("src/engine_2026.py", PY_FUNCS, extract_py),
            ("out/draft_room.html", JS_FUNCS, extract_js)):
        cur = open(path, encoding="utf-8").read()
        old = show(path)
        for f in funcs:
            a, b = extract(old, f), extract(cur, f)
            if a is None or b is None:
                print(f"MISSING {path}:{f} main={'yes' if a else 'NO'} "
                      f"current={'yes' if b else 'NO'}")
                ok = False
            elif a == b:
                print(f"IDENTICAL {path}:{f} ({len(a)} bytes)")
            else:
                print(f"DIFFERS {path}:{f}")
                ok = False
    print("MATH DIFF PROOF:",
          "EMPTY (all ten function bodies byte-identical to origin/main)"
          if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

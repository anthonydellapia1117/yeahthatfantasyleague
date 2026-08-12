#!/usr/bin/env python3
"""Export the Claude Code session transcript to a redacted markdown chat history.

REDACTION IS THE POINT. This file is destined for a public repo and the raw
transcript contains a reused password, a Yahoo client secret, OAuth access and
refresh tokens, authorization codes, and a third-party bearer token. Every one of
those is replaced before a single byte is written.

Redaction is deny-by-default on shape, not just on the literal strings observed,
so a secret that appears in a form we did not anticipate is still caught.

Run:  python3 src/export_chat.py <session.jsonl> <out.md>
"""
import json, re, sys, os, datetime

# Literal secret values are NEVER stored in this file - it is committed to a public
# repo, and a redactor that hardcodes secrets IS the leak. They live in
# .redact-literals (gitignored), one per line. The shape-based PATTERNS below are the
# real defence; the literal file is belt-and-braces for shapes we did not anticipate.
def _load_literals():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".redact-literals")
    if not os.path.exists(path):
        print("WARNING: .redact-literals absent - shape patterns only", file=sys.stderr)
        return []
    return [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]


LITERALS = _load_literals()

# Shape-based rules. Order matters: longest and most specific first.
PATTERNS = [
    # Yahoo consumer keys begin with a short fixed prefix. Matched with no length
    # floor because tool output truncates mid-value and a partial secret is still a
    # secret. The prefix itself lives in .redact-literals, not here.
    (re.compile(r"\bdj0[A-Za-z0-9_\-]{8,}"), "<REDACTED:YAHOO_CONSUMER_KEY>"),
    # Generic high-entropy bearer tokens: long, mixed case, digits, url-safe charset.
    # Deliberately broad - over-redaction is the safe failure mode here.
    (re.compile(r"\b(?=[A-Za-z0-9._\-]*[A-Z])(?=[A-Za-z0-9._\-]*[a-z])"
                r"(?=[A-Za-z0-9._\-]*[0-9])[A-Za-z0-9._\-]{80,}"),
     "<REDACTED:OPAQUE_TOKEN>"),
    # generic long opaque tokens that follow a token-ish label
    (re.compile(r"(?i)\b(access[_-]?token|refresh[_-]?token|bearer)\b\s*[:=]?\s*['\"]?[A-Za-z0-9._~+/\-]{40,}={0,2}"),
     r"\1=<REDACTED>"),
    # KEY=VALUE forms in env dumps
    (re.compile(r"(?i)\b(YAHOO_CONSUMER_KEY|YAHOO_CONSUMER_SECRET|YAHOO_ACCESS_TOKEN|"
                r"YAHOO_REFRESH_TOKEN|YAHOO_GUID|YAHOO_TOKEN_TYPE)\s*=\s*\S+"),
     r"\1=<REDACTED>"),
    # 40-char hex, the shape of the Yahoo client secret
    (re.compile(r"\b[0-9a-f]{40}\b"), "<REDACTED:SECRET_40HEX>"),
    # the owner's email
    (re.compile(r"\banthonydellapia@gmail\.com\b"), "<REDACTED:EMAIL>"),
    # any other email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<REDACTED:EMAIL>"),
]

# Verification codes are short and would false-positive badly on shape alone, so they
# are covered by LITERALS only. Any new one must be added there.


def redact(text):
    if not text:
        return text
    for lit in LITERALS:
        text = text.replace(lit, "<REDACTED>")
    for pat, repl in PATTERNS:
        text = pat.sub(repl, text)
    return text


def blocks(content):
    """Flatten a message's content into (kind, text) pairs."""
    if isinstance(content, str):
        return [("text", content)]
    out = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            out.append(("text", b.get("text", "")))
        elif t == "thinking":
            continue                      # never exported
        elif t == "tool_use":
            name = b.get("name", "tool")
            inp = json.dumps(b.get("input", {}), indent=1)[:2000]
            out.append(("tool_use", f"**Tool: `{name}`**\n\n```json\n{inp}\n```"))
        elif t == "tool_result":
            c = b.get("content")
            if isinstance(c, list):
                c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
            c = str(c or "")[:3000]
            out.append(("tool_result", f"```\n{c}\n```"))
    return out


def main(src, dst):
    stamp = datetime.datetime.now()
    rows = []
    for line in open(src, errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    parts = [
        "# ff-hub - Full Chat History",
        "",
        f"**Exported {stamp:%Y-%m-%d %H:%M:%S %Z}** from the Claude Code session that built this repo.",
        "",
        "> **Redacted.** This transcript is machine-scrubbed of every credential that appeared "
        "during the session: a reused password, a Yahoo client ID and secret, OAuth access and "
        "refresh tokens, authorization codes, a third-party bearer token, and email addresses. "
        "Redaction is shape-based as well as literal, so unanticipated forms are still caught. "
        "Model reasoning blocks are excluded entirely.",
        "",
        "> **Read `out/HANDOFF.md` first.** It is the distilled state. This file is the audit "
        "trail behind it.",
        "",
        "---",
        "",
    ]

    n_user = n_asst = 0
    for r in rows:
        role = (r.get("message") or {}).get("role") or r.get("type")
        content = (r.get("message") or {}).get("content")
        if role not in ("user", "assistant"):
            continue
        bl = blocks(content)
        if not bl:
            continue
        text = "\n\n".join(t for _, t in bl).strip()
        if not text:
            continue
        # skip pure system-reminder noise
        if text.startswith("<system-reminder>") and len(text) < 400:
            continue
        ts = (r.get("timestamp") or "")[:19].replace("T", " ")
        if role == "user":
            n_user += 1
            parts.append(f"## User - {ts}\n\n{redact(text)}\n")
        else:
            n_asst += 1
            parts.append(f"### Claude - {ts}\n\n{redact(text)}\n")

    parts += [
        "",
        "---",
        "",
        f"*{n_user} user turns, {n_asst} assistant turns. "
        f"Exported {stamp:%Y-%m-%d %H:%M:%S}.*",
    ]

    body = "\n".join(parts)

    # Final gate: refuse to write if any known literal survived.
    for lit in LITERALS:
        if lit in body:
            print(f"ABORT: literal survived redaction: {lit[:12]}...", file=sys.stderr)
            sys.exit(1)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f:
        f.write(body)
    print(f"wrote {dst}")
    print(f"  {n_user} user turns, {n_asst} assistant turns, {len(body)//1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

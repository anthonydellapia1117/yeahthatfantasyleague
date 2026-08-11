#!/usr/bin/env python3
"""Yahoo OAuth2 handshake using the app's REGISTERED redirect URI.

yahoo_oauth defaults to callback_uri 'oob', which Yahoo has deprecated. This uses
https://localhost:8080 to match the app, then writes the resulting tokens into .env
where yfpy picks them up via env_var_fallback. Credentials are never printed.

  python3 src/oauth_exchange.py url          -> print the authorize URL
  python3 src/oauth_exchange.py code <CODE>  -> exchange and save tokens
"""
import base64, json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
REDIRECT = "https://localhost:8080"


def env():
    v = {}
    for line in open(ENV):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, val = line.split("=", 1)
            v[k.strip()] = val.strip()
    return v


def save(tokens):
    v = env()
    v.update(tokens)
    with open(ENV, "w") as f:
        for k, val in v.items():
            f.write(f"{k}={val}\n")
    os.chmod(ENV, 0o600)


def main():
    v = env()
    key, sec = v["YAHOO_CONSUMER_KEY"], v["YAHOO_CONSUMER_SECRET"]

    if sys.argv[1] == "url":
        q = urllib.parse.urlencode({
            "client_id": key, "redirect_uri": REDIRECT,
            "response_type": "code", "language": "en-us",
        })
        print("https://api.login.yahoo.com/oauth2/request_auth?" + q)
        return

    code = sys.argv[2].strip()
    data = urllib.parse.urlencode({
        "code": code, "redirect_uri": REDIRECT, "grant_type": "authorization_code",
    }).encode()
    auth = base64.b64encode(f"{key}:{sec}".encode()).decode()
    req = urllib.request.Request(
        "https://api.login.yahoo.com/oauth2/get_token", data=data,
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        body = json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
    except urllib.error.HTTPError as e:
        print("EXCHANGE FAILED:", e.code, e.read().decode()[:300], file=sys.stderr)
        sys.exit(1)

    save({
        "YAHOO_ACCESS_TOKEN": body["access_token"],
        "YAHOO_REFRESH_TOKEN": body["refresh_token"],
        "YAHOO_TOKEN_TYPE": body.get("token_type", "bearer"),
        "YAHOO_GUID": body.get("xoauth_yahoo_guid", ""),
        "YAHOO_TOKEN_TIME": str(time.time()),
    })
    print(f"OK. tokens saved to .env (expires_in={body.get('expires_in')}s). "
          f"access_token {len(body['access_token'])} chars, "
          f"refresh_token {len(body['refresh_token'])} chars.")


if __name__ == "__main__":
    main()

"""Post to LinkedIn via the official API (stdlib only).

Setup:  fill .env (see .env.example), then
  python linkedin_post.py login            # one-time browser OAuth, saves token.json
  python linkedin_post.py post "Your text" # asks for confirmation before publishing
  python linkedin_post.py post --file post.txt
"""
import json, os, sys, secrets, threading, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
TOKEN_FILE = HERE / "token.json"
SCOPES = "openid profile w_member_social"


def load_env():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    for k in ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI"):
        if not os.environ.get(k):
            sys.exit(f"Missing {k} in .env")


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            return r.status, json.loads(body) if body else {}, r.headers
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()}")


def login():
    redirect = os.environ["LINKEDIN_REDIRECT_URI"]
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "response_type": "code", "client_id": os.environ["LINKEDIN_CLIENT_ID"],
        "redirect_uri": redirect, "state": state, "scope": SCOPES})
    result = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.end_headers()
            self.wfile.write(b"Done. You can close this tab.")
        def log_message(self, *a): pass

    u = urllib.parse.urlparse(redirect)
    srv = HTTPServer((u.hostname, u.port or 80), H)
    webbrowser.open("https://www.linkedin.com/oauth/v2/authorization?" + params)
    print("Waiting for LinkedIn approval in your browser...")
    srv.handle_request()
    if result.get("state") != state or "code" not in result:
        sys.exit(f"Login failed: {result}")
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": result["code"],
        "redirect_uri": redirect, "client_id": os.environ["LINKEDIN_CLIENT_ID"],
        "client_secret": os.environ["LINKEDIN_CLIENT_SECRET"]}).encode()
    _, tok, _ = http("https://www.linkedin.com/oauth/v2/accessToken", body,
                     {"Content-Type": "application/x-www-form-urlencoded"})
    TOKEN_FILE.write_text(json.dumps(tok))
    print("Saved token.json (valid ~60 days).")


def post(text):
    if not TOKEN_FILE.exists():
        sys.exit("Run `login` first.")
    token = json.loads(TOKEN_FILE.read_text())["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    _, info, _ = http("https://api.linkedin.com/v2/userinfo", headers=auth)
    print(f"\nWill post as {info.get('name')}:\n{'-'*40}\n{text}\n{'-'*40}")
    if input("Publish? (yes/no): ").strip().lower() != "yes":
        sys.exit("Cancelled.")
    payload = {
        "author": f"urn:li:person:{info['sub']}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED",
                         "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    status, _, hdr = http("https://api.linkedin.com/rest/posts",
                          json.dumps(payload).encode(),
                          {**auth, "Content-Type": "application/json",
                           "LinkedIn-Version": "202601",
                           "X-Restli-Protocol-Version": "2.0.0"}, "POST")
    print("Published!" if status == 201 else status, hdr.get("x-restli-id", ""))


if __name__ == "__main__":
    load_env()
    a = sys.argv[1:]
    if a[:1] == ["login"]:
        login()
    elif a[:1] == ["post"] and len(a) >= 2:
        post(Path(a[2]).read_text(encoding="utf-8") if a[1] == "--file" else a[1])
    else:
        print(__doc__)

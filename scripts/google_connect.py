#!/usr/bin/env python3
"""Run this ON YOUR LAPTOP once per YouTube channel to connect your analytics.

  python3 google_connect.py

Uses Google's "desktop app" sign-in: it opens your browser, you pick the
channel, and it prints a refresh token. Paste it into GitHub as
YT_REFRESH_TOKEN_1 (first channel) or YT_REFRESH_TOKEN_2 (second).
"""
import json, getpass, http.server, secrets, threading, urllib.parse, urllib.request, webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly"
cid = input("Google OAuth Client ID: ").strip()
csec = getpass.getpass("Google OAuth Client Secret (hidden while typing): ").strip()
state = secrets.token_urlsafe(16)
got = {}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state", [""])[0] == state:
            got["code"] = q.get("code", [""])[0]; got["error"] = q.get("error", [""])[0]
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab and go back to the terminal.</h2>")
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("127.0.0.1", 0), H)
redirect = f"http://127.0.0.1:{srv.server_port}/"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
    "access_type": "offline", "prompt": "consent select_account", "state": state})
print("\nOpening Google sign-in. Pick the YouTube CHANNEL you want to connect.\nIf no browser opens, go to:\n" + url + "\n")
webbrowser.open(url)
while "code" not in got and "error" not in got:
    srv.handle_request()
if not got.get("code"):
    raise SystemExit("Sign-in was cancelled or failed: " + got.get("error", "unknown"))
data = urllib.parse.urlencode({"code": got["code"], "client_id": cid, "client_secret": csec,
                               "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
res = json.loads(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)).read().decode())
if "refresh_token" not in res:
    raise SystemExit("No refresh token came back: " + json.dumps(res)[:300])
print("\nConnected. Your refresh token (copy the next line into the GitHub secret):\n")
print(res["refresh_token"])
print("\nDo not share it or post it anywhere.")

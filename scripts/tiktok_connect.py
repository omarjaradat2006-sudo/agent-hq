#!/usr/bin/env python3
"""Run this ON YOUR LAPTOP once to connect your TikTok account.

  python3 tiktok_connect.py

It opens TikTok's login page, you approve, then paste the code shown on the
Agent HQ page. It prints a refresh token: paste that into GitHub as the
TT_REFRESH_TOKEN secret. Nothing is saved anywhere else.
"""
import json, secrets, urllib.parse, urllib.request, webbrowser, getpass

REDIRECT = "https://omarjaradat2006-sudo.github.io/agent-hq/auth/tiktok.html"
SCOPES = "user.info.basic,user.info.stats,video.list"

key = input("TikTok Client Key: ").strip()
secret = getpass.getpass("TikTok Client Secret (hidden while typing): ").strip()
state = secrets.token_urlsafe(16)
url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(
    {"client_key": key, "scope": SCOPES, "response_type": "code", "redirect_uri": REDIRECT, "state": state})
print("\nOpening TikTok. Log in and press Authorize.\nIf no browser opens, go to:\n" + url + "\n")
webbrowser.open(url)
code = input("Paste the code from the Agent HQ page: ").strip()
code = urllib.parse.unquote(code)
data = urllib.parse.urlencode({"client_key": key, "client_secret": secret, "code": code,
                               "grant_type": "authorization_code", "redirect_uri": REDIRECT}).encode()
req = urllib.request.Request("https://open.tiktokapis.com/v2/oauth/token/", data=data,
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
try:
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
except urllib.error.HTTPError as e:
    res = {"error": e.code, "detail": e.read().decode()[:400]}
if "refresh_token" in res:
    print("\nConnected. Scopes granted:", res.get("scope"))
    print("\nYour TT_REFRESH_TOKEN (copy everything on the next line into the GitHub secret):\n")
    print(res["refresh_token"])
    print("\nIt lasts about a year. Do not share it or post it anywhere.")
else:
    print("\nThat didn't work:", res)

"""Create an original cartoon image for the next post in social/bank.json and publish it to LinkedIn and X
through their OFFICIAL APIs. Standard library plus Pillow (installed in the workflow).

Secrets (add in Settings > Secrets and variables > Actions; skip any channel you do not want):
  LinkedIn:  LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR_URN   (urn:li:person:XXXX or urn:li:organization:XXXX)
  X:         X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
Optional variable LINKEDIN_VERSION (default 202510) if LinkedIn retires an API version.

Behaviour: one new post per run, never repeats until the bank is used up, caps of 1 LinkedIn and 2 X posts a day,
the LinkedIn link goes in a first comment (better reach), X carries the link in the tweet.
With no secrets it only creates the image (social/out/<id>.png) so you or Claude can post it by hand.
No follows, likes, replies or messages are ever sent. DRY_RUN=1 creates the image and prints what would be posted.
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from cartoon import make_cartoon
from common import UA, load_state, save_state, with_utm

STATE = "state/social.json"
OUT = "social/out"
dry = os.environ.get("DRY_RUN") == "1"
only = [c.strip() for c in os.environ.get("CHANNELS", "linkedin,x").split(",") if c.strip()]

bank = json.load(open("social/bank.json", encoding="utf-8"))
state = load_state(STATE, {"used": [], "day": "", "counts": {"linkedin": 0, "x": 0}, "log": []})
today = datetime.date.today().isoformat()
if state.get("day") != today:
    state["day"], state["counts"] = today, {"linkedin": 0, "x": 0}
if len(state["used"]) >= len(bank):
    state["used"] = []
nxt = next((b for b in bank if b["id"] not in state["used"]), None)
if nxt is None:
    print("bank empty")
    sys.exit(0)

os.makedirs(OUT, exist_ok=True)
img = os.path.join(OUT, nxt["id"] + ".png")
make_cartoon(img, nxt["speech"], nxt.get("scene", "inbox"), nxt.get("style", "sweater1"))
print("image:", img)


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


# ---------------- LinkedIn ----------------
def post_linkedin():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    if not token or not author:
        return "skipped (no LinkedIn secrets)"
    if state["counts"]["linkedin"] >= 1:
        return "skipped (daily cap)"
    ver = os.environ.get("LINKEDIN_VERSION", "202510") or "202510"
    base = {"Authorization": "Bearer " + token, "LinkedIn-Version": ver, "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json", "User-Agent": UA}
    code, _, body = http("https://api.linkedin.com/rest/images?action=initializeUpload",
                         json.dumps({"initializeUploadRequest": {"owner": author}}).encode(), base, "POST")
    if code not in (200, 201):
        return "image init failed %s %s" % (code, body[:200])
    val = json.loads(body)["value"]
    with open(img, "rb") as f:
        code, _, body = http(val["uploadUrl"], f.read(), {"Authorization": "Bearer " + token, "Content-Type": "application/octet-stream"}, "PUT")
    if code not in (200, 201):
        return "image upload failed %s %s" % (code, body[:200])
    post = {
        "author": author,
        "commentary": nxt["li"],
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"altText": nxt["speech"][:200], "id": val["image"]}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    code, hdr, body = http("https://api.linkedin.com/rest/posts", json.dumps(post).encode(), base, "POST")
    if code not in (200, 201):
        return "post failed %s %s" % (code, body[:300])
    urn = hdr.get("x-restli-id") or hdr.get("X-RestLi-Id") or ""
    msg = "posted " + urn
    if urn:  # first comment with the link
        link = with_utm(nxt["link"], "linkedin", nxt["id"])
        cm = {"actor": author, "message": {"text": "Full guide: " + link}}
        code, _, body = http("https://api.linkedin.com/rest/socialActions/%s/comments" % urllib.parse.quote(urn, safe=""),
                             json.dumps(cm).encode(), base, "POST")
        msg += "; link comment %s" % code
    state["counts"]["linkedin"] += 1
    return msg


# ---------------- X ----------------
def oauth1_header(method, url, extra_params=None):
    ck, cs = os.environ["X_API_KEY"], os.environ["X_API_SECRET"]
    tk, ts = os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"]
    p = {"oauth_consumer_key": ck, "oauth_nonce": uuid.uuid4().hex, "oauth_signature_method": "HMAC-SHA1",
         "oauth_timestamp": str(int(time.time())), "oauth_token": tk, "oauth_version": "1.0"}
    allp = dict(p)
    allp.update(extra_params or {})
    enc = lambda s: urllib.parse.quote(str(s), safe="~")
    norm = "&".join("%s=%s" % (enc(k), enc(v)) for k, v in sorted(allp.items()))
    base = "&".join([method.upper(), enc(url), enc(norm)])
    key = enc(cs) + "&" + enc(ts)
    p["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join('%s="%s"' % (enc(k), enc(v)) for k, v in sorted(p.items()))


def multipart(fields, fname, data):
    b = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode()
    out += ("--%s\r\nContent-Disposition: form-data; name=\"media\"; filename=\"%s\"\r\nContent-Type: image/png\r\n\r\n" % (b, fname)).encode()
    out += data + ("\r\n--%s--\r\n" % b).encode()
    return out, "multipart/form-data; boundary=" + b


def post_x():
    need = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    if not all(os.environ.get(k, "").strip() for k in need):
        return "skipped (no X secrets)"
    if state["counts"]["x"] >= 2:
        return "skipped (daily cap)"
    data = open(img, "rb").read()
    media_id = None
    for url, fields in (("https://api.x.com/2/media/upload", {"media_category": "tweet_image"}),
                        ("https://upload.twitter.com/1.1/media/upload.json", {})):
        body, ctype = multipart(fields, os.path.basename(img), data)
        code, _, resp = http(url, body, {"Authorization": oauth1_header("POST", url), "Content-Type": ctype, "User-Agent": UA}, "POST")
        if code in (200, 201):
            j = json.loads(resp)
            media_id = (j.get("data") or {}).get("id") or j.get("media_id_string")
            if media_id:
                break
        print("X media upload via %s failed: %s %s" % (url, code, resp[:160]))
    if not media_id:
        return "media upload failed"
    link = with_utm(nxt["link"], "x", nxt["id"])
    text = nxt["x"]
    if len(text) > 240:
        text = text[:237] + "..."
    url = "https://api.x.com/2/tweets"
    payload = json.dumps({"text": "%s\n\n%s" % (text, link), "media": {"media_ids": [str(media_id)]}}).encode()
    code, _, resp = http(url, payload, {"Authorization": oauth1_header("POST", url), "Content-Type": "application/json", "User-Agent": UA}, "POST")
    if code not in (200, 201):
        return "tweet failed %s %s" % (code, resp[:250])
    state["counts"]["x"] += 1
    return "tweeted " + resp[:120]


results = {}
if dry:
    print("DRY RUN: LinkedIn text:\n", nxt["li"], "\nX text:\n", nxt["x"], "\nlink:", nxt["link"])
else:
    if "linkedin" in only:
        results["linkedin"] = post_linkedin()
    if "x" in only:
        results["x"] = post_x()
    for k, v in results.items():
        print(k + ":", v)

posted = any(v.startswith(("posted", "tweeted")) for v in results.values())
no_creds = all(v.startswith("skipped (no") for v in results.values()) if results else False
if not dry and (posted or no_creds):
    state["used"].append(nxt["id"])
    state["log"] = (state.get("log", []) + [{"day": today, "id": nxt["id"], "results": results}])[-60:]
save_state(STATE, state)
failed = [k for k, v in results.items() if "failed" in v]
sys.exit(1 if failed else 0)

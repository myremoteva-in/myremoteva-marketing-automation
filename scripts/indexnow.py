"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver and others) about new or changed pages.

Reads the live sitemap and submits every URL whose lastmod is within DAYS days.
Set ALL=1 to submit every URL. IndexNow needs no secret: the key is public and the
key file is served from the site root.
"""
import datetime
import json
import os
import sys
import urllib.request

from common import HOST, INDEXNOW_KEY, SITE, UA, sitemap_entries

days = int(os.environ.get("DAYS", "3"))
submit_all = os.environ.get("ALL") == "1"
cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()

entries = sitemap_entries()
urls = [u for u, lm in entries if submit_all or (lm and lm >= cutoff)]
print("sitemap urls: %d, to submit: %d (cutoff %s)" % (len(entries), len(urls), cutoff))
if not urls:
    print("nothing new, done")
    sys.exit(0)

urls = urls[:10000]
body = json.dumps({
    "host": HOST,
    "key": INDEXNOW_KEY,
    "keyLocation": "%s/%s.txt" % (SITE, INDEXNOW_KEY),
    "urlList": urls,
}).encode("utf-8")
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print("IndexNow HTTP", r.status)
        sys.exit(0 if r.status in (200, 202) else 1)
except urllib.error.HTTPError as e:
    print("IndexNow HTTP", e.code, e.read()[:200])
    sys.exit(0 if e.code in (200, 202) else 1)

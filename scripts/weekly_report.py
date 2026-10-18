"""Weekly site report: checks every URL in the sitemap, lists problems, and opens a GitHub Issue with the summary.

Needs no secret beyond the built-in GITHUB_TOKEN. If a broken page is found the issue is labelled as needing action.
"""
import concurrent.futures
import datetime
import json
import os
import urllib.request

from common import UA, sitemap_entries

entries = sitemap_entries()
today = datetime.date.today()
week_ago = (today - datetime.timedelta(days=7)).isoformat()


def check(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(200000).decode("utf-8", "replace").lower()
            noindex = 'name="robots"' in body and "noindex" in body.split('name="robots"')[1][:80]
            return url, r.status, noindex
    except urllib.error.HTTPError as e:
        return url, e.code, False
    except Exception:
        return url, 0, False


with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(lambda e: check(e[0]), entries))

bad = [(u, c) for u, c, n in results if c != 200]
noindexed = [u for u, c, n in results if n]
new = [u for u, lm in entries if lm and lm >= week_ago]

lines = [
    "## Weekly site report, %s" % today.isoformat(),
    "",
    "- URLs in the sitemap: **%d**" % len(entries),
    "- New or updated in the last 7 days: **%d**" % len(new),
    "- URLs not returning 200: **%d**" % len(bad),
    "- URLs with a noindex tag: **%d**" % len(noindexed),
    "",
]
if bad:
    lines += ["### Problems to fix", ""] + ["- %s (HTTP %s)" % (u, c) for u, c in bad[:60]] + [""]
if noindexed:
    lines += ["### noindex pages (check these are intended)", ""] + ["- " + u for u in noindexed[:30]] + [""]
if new:
    lines += ["### Updated this week", ""] + ["- " + u for u in new[:40]] + [""]
lines += [
    "### Do this week",
    "",
    "- Ask Google to index the newest pages (Search Console > URL inspection).",
    "- Check Search Console clicks and impressions, and the Bing AI Performance report.",
    "- Look at the Ahrefs free authority checker: https://ahrefs.com/website-authority-checker?input=myremoteva.com",
]
body = "\n".join(lines)
print(body)

repo = os.environ.get("GITHUB_REPOSITORY")
token = os.environ.get("GITHUB_TOKEN")
if repo and token:
    payload = {"title": "Weekly site report %s%s" % (today.isoformat(), " (action needed)" if bad else ""), "body": body}
    req = urllib.request.Request("https://api.github.com/repos/%s/issues" % repo, data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                                          "User-Agent": UA, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        print("issue created, HTTP", r.status)

"""Cross-post NEW blog guides to DEV (dev.to) as a short excerpt with a canonical link back to the original.
Needs one repository secret: DEVTO_API_KEY (created in your DEV account under Settings > Extensions).

Safety: articles are created as DRAFTS by default, so you read each one and press Publish yourself.
Set the repository variable DEVTO_PUBLISH=true to publish automatically. The canonical_url points to
myremoteva.com so search engines treat our page as the original.
Max 1 new article per run. First run only records what exists.

Failures are explained in the run summary (annotations). A guide that DEV rejects for its own content is recorded
as skipped so it cannot block the queue; temporary network or DEV problems end the run quietly and the next run retries.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

from common import UA, feed_items, load_state, save_state, with_utm

STATE = "state/devto.json"
key = os.environ.get("DEVTO_API_KEY", "").strip()
if not key:
    print("DEVTO_API_KEY secret missing: nothing posted.")
    sys.exit(0)
publish = os.environ.get("DEVTO_PUBLISH", "false").lower() == "true"


def note(level, title, msg):
    """Print a GitHub annotation so the reason shows on the run page without opening the log."""
    print("::%s title=%s::%s" % (level, title, " ".join(str(msg).split())[:400]))


try:
    items = feed_items()
except Exception as e:  # temporary network trouble reaching our own site
    note("warning", "DEV: feed unavailable", "Could not read feed.xml (%s). The next run will retry." % e)
    sys.exit(0)

state = load_state(STATE, {"posted": []})
if not state["posted"]:
    state["posted"] = [i["link"] for i in items]
    save_state(STATE, state)
    print("first run: recorded %d existing guides, nothing posted" % len(items))
    sys.exit(0)

todo = [i for i in items if i["link"] not in state["posted"]][:1]
if not todo:
    print("no new guides")
    sys.exit(0)

it = todo[0]
paras = re.findall(r"<p>(.*?)</p>", it["html"], re.S)
text = []
for p in paras[:4]:
    t = re.sub(r"<[^>]+>", "", p).strip()
    if t:
        text.append(t)
excerpt = "\n\n".join(text)
body = "%s\n\n**Read the full guide, with the tables and checklists:** [%s](%s)\n\n_Published by [MyRemoteVA](https://myremoteva.com), a managed service for admin, bookkeeping, customer support, ecommerce and website work._" % (
    excerpt, it["title"], with_utm(it["link"], "devto", "crosspost"))
payload = {"article": {
    "title": it["title"][:128],
    "published": publish,
    "body_markdown": body,
    "canonical_url": it["link"],
    "description": it["desc"][:250],
    "tags": ["virtualassistant", "smallbusiness", "productivity", "remotework"],
}}
req = urllib.request.Request("https://dev.to/api/articles", data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json", "api-key": key, "User-Agent": UA}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode())
        print("created (%s):" % ("published" if publish else "draft"), res.get("url") or res.get("id"))
        state["posted"].append(it["link"])
        save_state(STATE, state)
except urllib.error.HTTPError as e:
    detail = e.read()[:400].decode("utf-8", "replace")
    print("DEV API error", e.code, detail)
    if e.code == 429 or e.code >= 500:
        note("notice", "DEV busy", "DEV returned %d. The next scheduled run will retry." % e.code)
        sys.exit(0)
    if e.code in (401, 403):
        # A rejected key is an owner task, not a code bug. Show it as a warning instead of emailing every 6 hours.
        note("warning", "DEV key rejected", "DEV returned %d. Create a new key at https://dev.to/settings/extensions and save it as the repository secret DEVTO_API_KEY." % e.code)
        sys.exit(0)
    # Any other 4xx means DEV refused THIS article (for example a duplicate canonical URL or a field it dislikes).
    # Record it as skipped so it cannot block every later guide.
    note("warning", "DEV skipped a guide", "DEV returned %d for %s: %s" % (e.code, it["link"], detail))
    state["posted"].append(it["link"])
    state.setdefault("skipped", []).append({"link": it["link"], "code": e.code, "detail": detail[:200]})
    save_state(STATE, state)
    sys.exit(0)
except Exception as e:  # timeouts and other network errors are temporary
    note("notice", "DEV unreachable", "%s. The next scheduled run will retry." % e)
    sys.exit(0)
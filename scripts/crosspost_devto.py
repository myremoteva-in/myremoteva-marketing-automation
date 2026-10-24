"""Cross-post NEW blog guides to DEV (dev.to) as a short excerpt with a canonical link back to the original.
Needs one repository secret: DEVTO_API_KEY (created in your DEV account under Settings > Extensions).

Safety: articles are created as DRAFTS by default, so you read each one and press Publish yourself.
Set the repository variable DEVTO_PUBLISH=true to publish automatically. The canonical_url points to
myremoteva.com so search engines treat our page as the original.
Max 1 new article per run. First run only records what exists.
"""
import json
import os
import re
import sys
import urllib.request

from common import UA, feed_items, load_state, save_state, with_utm

STATE = "state/devto.json"
key = os.environ.get("DEVTO_API_KEY", "").strip()
if not key:
    print("DEVTO_API_KEY secret missing: nothing posted.")
    sys.exit(0)
publish = os.environ.get("DEVTO_PUBLISH", "false").lower() == "true"

items = feed_items()
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
body = "%s\n\n**Read the full guide, with the tables and checklists:** [%s](%s)\n\n_Published by [MyRemoteVA](https://myremoteva.com), a managed virtual assistant and bookkeeping support service._" % (
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
    print("DEV API error", e.code, e.read()[:300])
    if e.code == 429 or e.code >= 500:
        print("Temporary DEV limit or outage; the next scheduled run will retry.")
        sys.exit(0)
    if e.code in (401, 403):
        # A rejected key is an owner task, not a code bug. Show it as a warning instead of emailing every 6 hours.
        print("::warning title=DEV key rejected::DEV returned %d. Create a new key at https://dev.to/settings/extensions and save it as the repository secret DEVTO_API_KEY." % e.code)
        sys.exit(0)
    sys.exit(1)

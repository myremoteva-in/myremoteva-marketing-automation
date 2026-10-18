"""Post each NEW blog guide to Bluesky once, with a UTM link. Needs two repository secrets:
BLUESKY_HANDLE (for example myremoteva.bsky.social) and BLUESKY_APP_PASSWORD (a Bluesky APP password, not the login password).

Rules built in: only our own new guides, max 2 per run and 3 per day, never follows, likes, replies or messages anyone.
First run only records what already exists (set BACKFILL=3 to post the newest 3 on the first run).
"""
import datetime
import json
import os
import sys
import urllib.request

from common import feed_items, load_state, save_state, with_utm

STATE = "state/bluesky.json"
handle = os.environ.get("BLUESKY_HANDLE", "").strip()
password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
if not handle or not password:
    print("BLUESKY_HANDLE or BLUESKY_APP_PASSWORD secret missing: nothing posted (add both in Settings > Secrets > Actions).")
    sys.exit(0)

items = feed_items()
state = load_state(STATE, {"posted": [], "day": "", "count": 0})
today = datetime.date.today().isoformat()
if state.get("day") != today:
    state["day"], state["count"] = today, 0

first_run = not state["posted"]
if first_run:
    backfill = int(os.environ.get("BACKFILL", "0"))
    seed = [i["link"] for i in items[backfill:]]
    state["posted"] = seed
    print("first run: recorded %d existing guides, backfill %d" % (len(seed), backfill))

todo = [i for i in items if i["link"] not in state["posted"]][:2]
todo = list(reversed(todo))  # oldest first


def api(path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://bsky.social/xrpc/" + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


if todo:
    session = api("com.atproto.server.createSession", {"identifier": handle, "password": password})
    for it in todo:
        if state["count"] >= 3:
            print("daily limit of 3 reached")
            break
        link = with_utm(it["link"], "bluesky")
        title = it["title"][:150]
        text = "%s\n\n%s" % (title, link)
        if len(text) > 300:
            title = title[: 300 - len(link) - 5] + "..."
            text = "%s\n\n%s" % (title, link)
        start = len(text[: text.rfind(link)].encode("utf-8"))
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "langs": ["en"],
            "facets": [{
                "index": {"byteStart": start, "byteEnd": start + len(link.encode("utf-8"))},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
            }],
            "embed": {"$type": "app.bsky.embed.external", "external": {
                "uri": link, "title": it["title"][:300], "description": it["desc"][:300]}},
        }
        res = api("com.atproto.repo.createRecord", {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record}, session["accessJwt"])
        print("posted:", it["title"], res.get("uri"))
        state["posted"].append(it["link"])
        state["count"] += 1
else:
    print("no new guides to post")

save_state(STATE, state)

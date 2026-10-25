"""Post each NEW blog guide to Bluesky once, with a UTM link. Needs two repository secrets:
BLUESKY_HANDLE (for example myremoteva.bsky.social) and BLUESKY_APP_PASSWORD (a Bluesky APP password, not the login password).

Rules built in: only our own new guides, max 2 per run and 3 per day, never follows, likes, replies or messages anyone.
First run only records what already exists (set BACKFILL=3 to post the newest 3 on the first run).
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

from common import feed_items, load_state, save_state, with_utm

STATE = "state/bluesky.json"
handle = os.environ.get("BLUESKY_HANDLE", "").strip()
password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
if not handle or not password:
    print("BLUESKY_HANDLE or BLUESKY_APP_PASSWORD secret missing: nothing posted (add both in Settings > Secrets > Actions).")
    sys.exit(0)

# Forgive common typing slips in the two secrets.
handle = handle.lstrip("@").strip().lower()
if "." not in handle:
    handle += ".bsky.social"
compact = password.replace("-", "").replace(" ", "")
if len(compact) == 16:
    password = "-".join(compact[i:i + 4] for i in range(0, 16, 4))

def note(level, title, msg):
    """Print a GitHub annotation so the reason shows on the run page without opening the log."""
    print("::%s title=%s::%s" % (level, title, " ".join(str(msg).split())[:400]))


try:
    items = feed_items()
except Exception as e:  # temporary network trouble reaching our own site
    note("warning", "Bluesky: feed unavailable", "Could not read feed.xml (%s). The next run will retry." % e)
    sys.exit(0)
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


class Skip(Exception):
    """Bluesky refused this one post; skip the guide so it cannot block the queue."""


class Stop(Exception):
    """Temporary problem: end quietly, the next run retries."""


def api(path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://bsky.social/xrpc/" + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        print("Bluesky API error %s on %s: %s" % (e.code, path, detail))
        if path.endswith("createSession"):
            if e.code in (400, 401):
                note("error", "Bluesky login rejected", "Check that BLUESKY_HANDLE is exactly the handle (myremoteva.bsky.social) and BLUESKY_APP_PASSWORD is a current app password. %s" % detail)
                sys.exit(1)
            raise Stop("login returned %d" % e.code)
        if e.code == 429 or e.code >= 500:
            raise Stop("Bluesky returned %d" % e.code)
        raise Skip("Bluesky returned %d: %s" % (e.code, detail))
    except Exception as e:  # timeouts and network errors
        raise Stop(str(e))

if todo:
    try:
        session = api("com.atproto.server.createSession", {"identifier": handle, "password": password})
    except Stop as e:
        note("notice", "Bluesky busy", "%s. The next scheduled run will retry." % e)
        sys.exit(0)
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
        try:
            res = api("com.atproto.repo.createRecord", {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record}, session["accessJwt"])
        except Skip as e:
            note("warning", "Bluesky skipped a guide", "%s: %s" % (it["link"], e))
            state["posted"].append(it["link"])
            state.setdefault("skipped", []).append({"link": it["link"], "detail": str(e)[:200]})
            continue
        except Stop as e:
            note("notice", "Bluesky busy", "%s. The next scheduled run will retry." % e)
            break
        print("posted:", it["title"], res.get("uri"))
        state["posted"].append(it["link"])
        state["count"] += 1
else:
    print("no new guides to post")

save_state(STATE, state)

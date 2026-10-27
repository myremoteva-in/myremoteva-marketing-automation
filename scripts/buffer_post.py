"""Step 3: send state/plan.json to Buffer's GraphQL API (addToQueue). Needs one repository secret: BUFFER_API_KEY
(Buffer dashboard > Settings > API > create a key). No LinkedIn or X keys are needed: Buffer holds those connections.

Images are served from this public repo (raw.githubusercontent.com), which Buffer fetches when the post goes out.
If Buffer says a channel queue is full, we stop for that channel and try again next run (the post is not marked used).
Set up your Buffer posting schedule with at least as many daily slots as PER_CHANNEL so the queue keeps draining.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

from common import UA, load_state, save_state

KEY = os.environ.get("BUFFER_API_KEY", "").strip()
if not KEY:
    print("BUFFER_API_KEY secret missing: nothing sent. The images and plan are still saved in the repo.")
    sys.exit(0)

REPO = os.environ.get("GITHUB_REPOSITORY", "myremoteva-in/myremoteva-marketing-automation")
RAW = "https://raw.githubusercontent.com/%s/main/social/out/" % REPO
plan = load_state("state/plan.json", {"posts": []})["posts"]
state = load_state("state/buffer.json", {"used": {"linkedin": [], "twitter": [], "facebook": []}})
state["used"].setdefault("facebook", [])


def gql(query):
    req = urllib.request.Request("https://api.buffer.com", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": "HTTP %s %s" % (e.code, e.read()[:200].decode("utf-8", "replace"))}]}


orgs = gql("query { account { organizations { id name } } }")
if "errors" in orgs or not orgs.get("data"):
    print("Could not read the Buffer account:", orgs)
    sys.exit(1)
channels = {}
for o in orgs["data"]["account"]["organizations"]:
    r = gql('query { channels(input: { organizationId: "%s" }) { id name service } }' % o["id"])
    for c in (r.get("data") or {}).get("channels", []):
        channels.setdefault(c["service"].lower(), []).append(c)
print("Buffer channels:", {k: [c["name"] for c in v] for k, v in channels.items()})

wanted = {"linkedin": "linkedin", "twitter": "twitter", "facebook": "facebook"}
full = set()
sent = 0
for p in plan:
    svc = wanted[p["channel"]]
    if svc not in channels:
        print("no %s channel connected in Buffer, skipping" % svc)
        continue
    if p["channel"] in full:
        continue
    if p["id"] in state["used"][p["channel"]]:
        continue
    text = json.dumps(p["text"])
    q = ('mutation { createPost(input: { text: %s, channelId: "%s", schedulingType: automatic, mode: addToQueue, '
         'assets: [{ image: { url: "%s" } }] }) { ... on PostActionSuccess { post { id dueAt } } ... on MutationError { message } } }'
         % (text, channels[svc][0]["id"], RAW + p["image"]))
    res = gql(q)
    out = (res.get("data") or {}).get("createPost") or {}
    if out.get("post"):
        print("queued", p["channel"], p["id"], out["post"].get("dueAt"))
        state["used"][p["channel"]].append(p["id"])
        sent += 1
    else:
        msg = out.get("message") or json.dumps(res.get("errors") or res)[:300]
        print("not queued", p["channel"], p["id"], "-", msg)
        full.add(p["channel"])  # likely queue full or a channel problem: stop this channel for today
    time.sleep(1.5)

save_state("state/buffer.json", state)
print("queued %d post(s)" % sent)
if sent == 0 and full:
    print("NOTHING WAS QUEUED. Check: the Buffer queue may be full (add posting slots), a channel may be disconnected, or the key may have expired.")
    sys.exit(1)  # a red run makes GitHub email the repo owner

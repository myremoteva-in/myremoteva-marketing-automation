"""Step 1 of the Buffer automation (v2, 28 Oct 2026): choose the next hand-written post for each channel.
Only social/bank3.json (image posts, each with image_file in social/out) is used: hand-written, fact-checked posts. There is NO fallback to feed summaries and NO repeats:
when a channel runs out, the run says so and queues nothing (add posts to the bank).
Rules (UTC weekday, Monday = 0): LinkedIn is queued on Mon, Tue, Wed (Buffer sends Tue, Wed, Thu at 13:30 UTC);
X is queued Mon to Fri (one a day); Facebook every day (one a day).
Posts carry no link by default (links reduce reach). Optional keys: "scene"/"speech"/"style" draw a cartoon image; "url" adds a link.
Env: FORCE_WEEKDAY (testing), DRY_RUN=1 (no state changes).
"""
import datetime
import json
import os
import sys

from common import load_state, save_state

STATE = "state/buffer.json"
OUT = "social/out"
CHANNELS = ["linkedin", "twitter", "facebook"]

bank = json.load(open("social/bank3.json", encoding="utf-8"))
state = load_state(STATE, {"used": {"linkedin": [], "twitter": [], "facebook": []}})
for c in CHANNELS:
    state["used"].setdefault(c, [])

wd = int(os.environ.get("FORCE_WEEKDAY", datetime.datetime.utcnow().weekday()))
today = {"linkedin": wd in (0, 1, 2), "twitter": wd <= 4, "facebook": True}

detail = []
for ch in CHANNELS:
    if not today[ch]:
        print(ch, "-> not queued on this weekday")
        continue
    nxt = [p for p in bank if p["id"] not in state["used"][ch]]
    if not nxt:
        print("::warning::%s: the post bank is empty. Add new posts to social/bank2.json. Nothing queued." % ch)
        continue
    p = nxt[0]
    text = p["x"] if ch == "twitter" else p["li"]
    if p.get("url"):
        text += "\n\n" + p["url"]
    image = p.get("image_file")
    if not image and p.get("scene"):
        from cartoon import make_cartoon
        os.makedirs(OUT, exist_ok=True)
        image = p["id"] + ".png"
        path = os.path.join(OUT, image)
        if not os.path.exists(path):
            make_cartoon(path, p.get("speech", ""), p["scene"], p.get("style", "sweater1"))
    detail.append({"channel": ch, "id": p["id"], "text": text, "image": image})
    print(ch, "->", p["id"], "(%d left after this)" % (len(nxt) - 1))

if os.environ.get("DRY_RUN") == "1":
    print(json.dumps(detail, indent=1, ensure_ascii=False)[:1500])
    sys.exit(0)
save_state("state/plan.json", {"posts": detail})
print("plan written with %d posts" % len(detail))
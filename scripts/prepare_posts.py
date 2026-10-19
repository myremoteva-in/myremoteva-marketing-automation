"""Step 1 of the daily Buffer automation: choose the next posts, draw their cartoons, write state/plan.json.
No AI is involved. Content comes from social/bank.json (hand-written, checked posts) and, once those are used up,
from our own published guides (title and summary from the site's RSS feed), so every claim is already on our site.

Env: PER_CHANNEL (posts per channel per run, default 3), DRY_RUN=1 (no state changes).
Each channel (linkedin, twitter) keeps its own list of used ids, so the plan never repeats a post on a channel.
"""
import hashlib
import json
import os
import re
import sys

from cartoon import make_cartoon, STYLES
from common import feed_items, load_state, save_state, with_utm

PER = int(os.environ.get("PER_CHANNEL", "3"))
CHANNELS = ["linkedin", "twitter"]
STATE = "state/buffer.json"
OUT = "social/out"
SCENES = ["inbox", "sheet", "calendar", "mail", "invoice", "chart", "clock", "robot"]

bank = json.load(open("social/bank.json", encoding="utf-8"))
state = load_state(STATE, {"used": {"linkedin": [], "twitter": []}})
for c in CHANNELS:
    state["used"].setdefault(c, [])


def short(s, n):
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "..."


def items():
    out = list(bank)
    try:
        for it in feed_items()[:60]:
            slug = it["link"].rstrip("/").split("/")[-1]
            h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
            desc = short(it["desc"], 420)
            out.append({
                "id": "g-" + slug,
                "scene": SCENES[h % len(SCENES)],
                "style": list(STYLES)[h % len(STYLES)],
                "speech": short(it["title"], 95),
                "li": desc,
                "x": short("New guide: " + it["title"], 200),
                "link": it["link"],
            })
    except Exception as e:  # feed down: bank only
        print("feed unavailable:", e)
    return out


pool = items()
plan = []
for ch in CHANNELS:
    picked = [p for p in pool if p["id"] not in state["used"][ch]][:PER]
    if not picked:
        state["used"][ch] = []  # everything used once: start over
        picked = pool[:PER]
    for p in picked:
        plan.append({"channel": ch, "id": p["id"]})
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, p["id"] + ".png")
        if not os.path.exists(path):
            make_cartoon(path, p["speech"], p.get("scene", "inbox"), p.get("style", "sweater1"))
        p["_path"] = path
    print(ch, "->", [p["id"] for p in picked])

lookup = {p["id"]: p for p in pool}
detail = []
for e in plan:
    p = lookup[e["id"]]
    link = with_utm(p["link"], "linkedin" if e["channel"] == "linkedin" else "x", p["id"])
    text = (p["li"] + "\n\n" + link) if e["channel"] == "linkedin" else (short(p["x"], 220) + "\n\n" + link)
    detail.append({"channel": e["channel"], "id": e["id"], "text": text, "image": e["id"] + ".png"})

if os.environ.get("DRY_RUN") == "1":
    print(json.dumps(detail[:2], indent=1))
    sys.exit(0)
save_state("state/plan.json", {"posts": detail})
print("plan written with %d posts" % len(detail))

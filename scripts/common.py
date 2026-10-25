"""Shared helpers for the MyRemoteVA marketing automation. Standard library only."""
import json
import os
import re
import time
import urllib.request

HOST = "myremoteva.com"
SITE = "https://" + HOST
SITEMAP = SITE + "/sitemap.xml"
FEED = SITE + "/feed.xml"
INDEXNOW_KEY = "a1f6fdb61f592053b634548f20510f2"  # public key, also served at /<key>.txt
UA = "myremoteva-marketing-automation/1.0 (+https://myremoteva.com)"


def get(url, timeout=60, tries=3):
    """Fetch a URL with short retries. GitHub runners sometimes lose their route for a moment ("Network is unreachable"),
    so wait and try again before giving up; callers decide what a final failure means."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=min(timeout, 45)) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network errors and HTTP errors alike
            last = e
            if attempt < tries - 1:
                time.sleep(8 * (attempt + 1))
    raise last


def sitemap_entries():
    """Return a list of (url, lastmod or '') from the live sitemap."""
    xml = get(SITEMAP)
    out = []
    for m in re.finditer(r"<url>(.*?)</url>", xml, re.S):
        block = m.group(1)
        loc = re.search(r"<loc>(.*?)</loc>", block)
        lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if loc:
            out.append((loc.group(1).strip(), lm.group(1).strip()[:10] if lm else ""))
    return out


def feed_items():
    """Return feed items newest first: dicts with title, link, desc, date, html."""
    xml = get(FEED, timeout=120)
    items = []
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
        b = m.group(1)

        def tag(name):
            t = re.search(r"<%s>(.*?)</%s>" % (name, name), b, re.S)
            if not t:
                return ""
            v = t.group(1).strip()
            cd = re.match(r"<!\[CDATA\[(.*)\]\]>$", v, re.S)
            return cd.group(1) if cd else v

        items.append({
            "title": unescape(tag("title")),
            "link": tag("link"),
            "desc": unescape(re.sub(r"<[^>]+>", " ", tag("description"))).strip(),
            "date": tag("pubDate"),
            "html": tag("content:encoded"),
        })
    return items


def unescape(s):
    import html
    return html.unescape(s)


def with_utm(url, source, campaign="autopost"):
    sep = "&" if "?" in url else "?"
    return "%s%sutm_source=%s&utm_medium=social&utm_campaign=%s" % (url, sep, source, campaign)


def load_state(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_state(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")

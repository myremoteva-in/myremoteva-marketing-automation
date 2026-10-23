"""Uptime and quality check for myremoteva.com. Exits 1 on any failure, so GitHub emails the repo owner.

Checks: key pages return 200 and contain their key facts, no accidental noindex,
sitemap and robots.txt healthy, llms.txt present, TLS certificate not close to expiry,
sign-up and free-trial links work.
"""
import datetime
import socket
import ssl
import sys
import urllib.request

from common import HOST, SITE, UA, get

failures = []


def status(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # network error
        return 0, str(e)


def expect(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (" - " + detail if detail else ""))
    if not ok:
        failures.append(label)


PAGES = {
    "/": ["$5.62"],
    "/pricing": ["$899", "$5.62"],
    "/services": ["virtual assistant"],
    "/blog/virtual-assistant-cost-per-task": ["cost per task"],
    "/blog/dedicated-virtual-assistant": ["dedicated virtual assistant"],
    "/best-virtual-assistant-services": ["virtual assistant"],
    "/cost-calculator": ["calculator"],
    "/terms-of-service": ["India"],
    "/privacy-policy": ["privacy"],
}
for path, needles in PAGES.items():
    code, body = status(SITE + path)
    expect("%s returns 200" % path, code == 200, str(code))
    if code == 200:
        low = body.lower()
        for n in needles:
            expect("%s contains %r" % (path, n), n.lower() in low)
        if 'name="robots"' in low and "noindex" in low.split('name="robots"')[1][:80]:
            expect("%s has no noindex" % path, False)

code, body = status(SITE + "/sitemap.xml")
expect("sitemap.xml has more than 250 URLs", code == 200 and body.count("<loc>") > 250, "%d urls" % body.count("<loc>"))
code, body = status(SITE + "/robots.txt")
expect("robots.txt lists the sitemap", code == 200 and "sitemap" in body.lower())
code, _ = status(SITE + "/llms.txt")
expect("llms.txt present", code == 200, str(code))
code, _ = status("https://dash.myremoteva.com/register")
expect("sign-up page returns 200", code == 200, str(code))
code, body = status("https://dash.myremoteva.com/register?plan=39")
expect("free-trial link returns 200", code == 200, str(code))
if code == 200:
    expect("free trial is offered on the sign-up page", "free trial" in body.lower())

try:
    ctx = ssl.create_default_context()
    with socket.create_connection((HOST, 443), timeout=20) as s:
        with ctx.wrap_socket(s, server_hostname=HOST) as t:
            cert = t.getpeercert()
    exp = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days_left = (exp - datetime.datetime.utcnow()).days
    expect("TLS certificate valid for more than 14 days", days_left > 14, "%d days left" % days_left)
except Exception as e:
    expect("TLS certificate readable", False, str(e))

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)

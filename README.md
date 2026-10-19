# MyRemoteVA marketing automation (100% free)

Free GitHub Actions that keep [myremoteva.com](https://myremoteva.com) healthy, indexed and visible. Everything here runs on GitHub's free tier (public repositories have unlimited Actions minutes) and uses only the Python standard library. No paid tools, no ads, no purchased links, no fake accounts.

## What runs

| Workflow | When | What it does | Secret needed |
|---|---|---|---|
| IndexNow ping | daily | Sends new and changed sitemap URLs to Bing, Yandex and other IndexNow search engines, so new guides are crawled in hours instead of weeks | none |
| Site health check | every 6 hours | Checks key pages, key facts, noindex tags, sitemap, robots.txt, llms.txt, the sign-up and free-trial links and the TLS certificate. A failure emails the repo owner | none |
| Post new guides to Bluesky | every 2 hours | Posts each new guide once, with a UTM link (max 3 a day). Never follows, likes, replies or messages anyone | BLUESKY_HANDLE, BLUESKY_APP_PASSWORD |
| Cross-post to DEV | every 6 hours | Creates a DEV article from each new guide as a draft, with a canonical link to the original on myremoteva.com | DEVTO_API_KEY |
| Weekly site report | Mondays | Checks every sitemap URL, lists errors and noindex pages, opens an Issue with the week's to-do list, pings IndexNow | none |
| Daily posts to Buffer (LinkedIn and X) | daily | Chooses the next 3 posts per channel from social/bank.json and then from our own guides, draws an original cartoon for each (Pillow, no AI), publishes the images in this repo and adds the posts to your Buffer queue through Buffer's API. Nothing is posted by GitHub itself: Buffer holds your LinkedIn and X connections | BUFFER_API_KEY |
| (Optional) Direct LinkedIn and X posting | manual | The earlier version that talks to LinkedIn and X directly. Not used | LinkedIn and X keys |

The repository also publishes the free [virtual assistant task brief templates](templates/virtual-assistant-task-brief-templates.md) so people and AI assistants can find and reuse them.

## Setup (10 minutes, once)

1. Make sure Actions are enabled (Actions tab, "I understand my workflows, go ahead and enable them").
2. Settings, Secrets and variables, Actions, add the secrets you want. Use a Bluesky APP PASSWORD (Bluesky Settings, Privacy and security, App passwords) and never your login password. Workflows with a missing secret simply skip.
3. Optional variable `DEVTO_PUBLISH` = `true` to publish DEV articles automatically. Leave it unset to review drafts first.
4. Run each workflow once from the Actions tab (Run workflow) to confirm it is green.

## Buffer setup (free, 10 minutes)

1. Sign up at buffer.com (free plan: 3 channels, a queue of up to 10 posts per channel at a time). Connect your LinkedIn and X accounts.
2. In Buffer set a posting schedule with at least 3 slots a day for each channel, so the queue empties as the workflow fills it.
3. In Buffer, open Settings, then API, and create a key. Add it here as the secret BUFFER_API_KEY. Never paste it in a chat.
4. Run the workflow once from the Actions tab. The log shows which channels it found and what it queued.
5. Change PER_CHANNEL (default 3) in the workflow if you want fewer posts. For a small LinkedIn audience, 1 or 2 a day is often better.

## Getting the LinkedIn and X keys (free, one time)

For LinkedIn, create an app at developer.linkedin.com, add the product Share on LinkedIn, generate an access token with the w_member_social scope, and note your author URN (urn:li:person:... for a profile). Tokens expire after about 60 days, so renew when the workflow reports a 401. Company-page posting needs LinkedIn's Community Management access and a urn:li:organization:... value.

For X, create a project and app at developer.x.com with Read and Write permission, then generate the API key, API secret, access token and access token secret. The free tier allows a limited number of posts a month, which is enough for 2 a day.

Add them as repository secrets. Never paste them in a chat or a file. Use only the official APIs: browser or cookie bots break LinkedIn's and X's rules and can get the account restricted.

## Honest expectations

These automations save time and remove delays. They do not buy rankings. Traffic grows from good pages, real links and being found quickly; this repo handles the "found quickly" and "stays healthy" parts for free. Judge results in Search Console, Bing Webmaster Tools and GA4, not by post counts.

## Rules baked in

- Our own content only, with UTM links so visits can be measured.
- No automated follows, likes, replies, direct messages or connection requests anywhere.
- No bought links, link exchanges, private blog networks or spam tools.
- We do not serve clients in India, Pakistan or Bangladesh and the automation never targets them.

## License

Code: MIT. Templates: CC BY 4.0 (keep a link to https://myremoteva.com/templates).
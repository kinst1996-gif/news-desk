"""Telegram news-to-LinkedIn bot (stdlib only).

Flow: /news -> list of latest instrumentation + AI stories -> tap "Draft" ->
bot writes a LinkedIn post + hashtags and finds the article image ->
you tap Approve -> it publishes to LinkedIn. Nothing posts without Approve.

Needs in .env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (yours), plus the LinkedIn
vars from linkedin_post.py (run `python linkedin_post.py login` first).
Optional: ANTHROPIC_API_KEY for better drafts (otherwise a simple template is used).
"""
import hashlib, json, os, re, sys, time, html, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
for _s in (sys.stdout, sys.stderr):   # a stray character in a feed error must never crash the bot on Windows consoles
    try: _s.reconfigure(errors="replace")
    except Exception: pass
FEEDS = {
    "Instrumentation": [
        "https://www.engineering.com/feed/",
        "https://www.chemengonline.com/feed/",
        "https://www.rtinsights.com/feed/",
        "https://instrumentation.co.uk/category/news/feed/",
        "https://www.controldesign.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.flowcontrolnetwork.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.plantservices.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.chemicalprocessing.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.processingmagazine.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.machinedesign.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.smartindustry.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.iiot-world.com/feed/",
        "https://www.automationmag.com/feed/",
        "https://www.designworldonline.com/feed/",
        "https://www.automation-mag.com/news/feed",
        "https://www.emersonautomationexperts.com/feed/",
        "https://drivesncontrols.com/feed/",
        "https://processandcontrolmag.co.uk/feed/",
        "https://www.iaasiaonline.com/feed/",
        "https://valvemagazine.com/feed/",
        "https://www.pumpsandsystems.com/feed/",
        "https://www.industrialcyber.co/feed/",
        "https://www.offshore-mag.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D",
        "https://www.yokogawa.com/rss/news/pr/",
        "https://ir.emerson.com/news-events/press-releases/rss",
        "https://www.engineeringnews.co.za/page/instrumentation-control/feed",
        # Vendor news (their own sites block bots), via Google News search feeds
        *[("https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
           + urllib.parse.quote(q + " when:3d")) for q in (
            "Rosemount OR Emerson process automation", "KROHNE flow measurement", "WIKA pressure temperature",
            "Endress+Hauser", "Yokogawa process automation", "ABB measurement analytics",
            "Siemens process instrumentation", "VEGA level measurement", "JUMO sensors", "Baumer sensors")],
    ],
    "AI": [
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        "https://www.unite.ai/feed/",
        "https://siliconangle.com/category/ai/feed/",
        "https://blogs.nvidia.com/feed/",
        "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "https://www.marktechpost.com/feed/",
        "https://news.microsoft.com/source/feed/",
        "https://www.engadget.com/category/ai/feed/",
        "https://thenextweb.com/feed",
        "https://huggingface.co/blog/feed.xml",
        "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "https://mistral.ai/news/rss",
        "https://blog.google/technology/ai/rss/",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "https://arstechnica.com/ai/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://the-decoder.com/feed/",
        "https://openai.com/news/rss.xml",
        "https://deepmind.google/blog/rss.xml",
    ],
    "Robotics": [
        "https://www.therobotreport.com/feed/",
        "https://www.roboticsbusinessreview.com/feed/",
        "https://www.humanoidsdaily.com/feed.xml",
        "https://interestingengineering.com/feed",
        "https://robohub.org/feed/",
        "https://spectrum.ieee.org/feeds/topic/robotics.rss",
    ],
    "UAE": [
        "https://www.khaleejtimes.com/api/v1/collections/uae.rss",
        "https://www.khaleejtimes.com/api/v1/collections/business.rss",
        "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://www.emirates247.com/rss/mobile/v2/flash-news.rss",
        "https://www.economymiddleeast.com/feed/",
        "https://www.wamda.com/feed",
        "https://www.tahawultech.com/feed/",
        "https://www.intelligentcio.com/me/feed/",
        "https://www.forbesmiddleeast.com/feed",
        # Big UAE outlets that block bots, through Google News (dated headlines, title-card images)
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Agulfnews.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Aarabianbusiness.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Awam.ae%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Azawya.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Agulfbusiness.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Aagbi.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=site%3Aoilandgasmiddleeast.com%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=%28ADNOC%20OR%20Masdar%20OR%20DEWA%20OR%20%22Abu%20Dhabi%22%20OR%20Dubai%29%20%28industry%20OR%20energy%20OR%20technology%20OR%20AI%29%20when%3A2d",
    ],
    "UAE AI": [
        "https://www.middleeastainews.com/feed",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=UAE%20%28%22artificial%20intelligence%22%20OR%20AI%29%20when%3A2d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=%28G42%20OR%20MBZUAI%20OR%20%22Technology%20Innovation%20Institute%22%20OR%20%22Falcon%20LLM%22%20OR%20Core42%20OR%20Khazna%20OR%20%22Stargate%20UAE%22%29%20when%3A3d",
        "https://news.google.com/rss/search?hl=en-AE&gl=AE&ceid=AE:en&q=%28Dubai%20OR%20%22Abu%20Dhabi%22%29%20AI%20when%3A2d",
    ],
    "Smart Sensors": [
        "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=%22smart%20sensor%22%20OR%20%22smart%20sensors%22%20%28industrial%20OR%20process%20OR%20factory%29%20when%3A3d",
        "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=%28%22IIoT%20sensor%22%20OR%20%22industrial%20IoT%20sensor%22%20OR%20%22wireless%20sensor%22%20OR%20%22IO-Link%22%20OR%20%22Ethernet-APL%22%29%20when%3A3d",
        "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=%28launches%20OR%20introduces%20OR%20unveils%29%20%28sensor%20OR%20transmitter%29%20%28pressure%20OR%20flow%20OR%20level%20OR%20temperature%20OR%20gas%20OR%20vibration%29%20when%3A3d",
        "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=%28%22condition%20monitoring%22%20OR%20%22predictive%20maintenance%22%29%20sensor%20when%3A3d",
    ],
    "IoT": [
        "https://iot-now.com/feed/",
        "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=site%3Aiotforall.com%20when%3A3d",   # IoT For All has no feed
    ],
}
# Normal websites without RSS: the bot scrapes headline links from these pages.
SITES = {
    "IoT": [
        "https://iottechnews.com/news/",
    ],
    "Instrumentation": [
        "https://www.controleng.com/",
        "https://www.automationworld.com/",
        "https://www.processonline.com.au/",
        "https://processonline.com.au/magazine",
        "https://www.controlglobal.com/",
        "https://www.automation.com/",
        "https://www.industrial-production.de/",
        "https://www.computer-automation.de/",
    ],
    "AI": [
        "https://www.anthropic.com/news",
    ],
}
PER_FEED = 5
WATCH_MINUTES = 10   # local mode: how often to look for breaking news
MAX_ALERTS = 4       # max new-story alerts per check
BASE_TAGS = ["#AI", "#Instrumentation", "#IndustrialAutomation", "#ProcessControl", "#Industry40"]
UA = {"User-Agent": "Mozilla/5.0 (news-bot)"}

items, drafts, seen = [], {}, []
STATE = HERE / "state.json"
CARDS = HERE / "cards"   # images prepared for drafts, uploaded to LinkedIn on approval
offset = 0


STATE_FLAGS = {"has_seen": False}


def uid(it):
    return hashlib.md5(it["link"].encode()).hexdigest()[:10]


def load_state():
    global offset
    if STATE.exists():
        d = json.loads(STATE.read_text(encoding="utf-8"))
        items[:] = d.get("items", [])
        drafts.update(d.get("drafts", {}))
        offset = d.get("offset", 0)
        seen[:] = d.get("seen", [])
        STATE_FLAGS["has_seen"] = "seen" in d


def save_state():
    STATE.write_text(json.dumps({"offset": offset, "items": items[-60:], "drafts": drafts, "seen": seen[-3000:]}), encoding="utf-8")


def load_env():
    f = HERE / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if not os.environ.get(k):
            if os.environ.get("GITHUB_ACTIONS"):   # secrets not added yet: wait quietly instead of failing every 5 minutes
                print(f"{k} is not set in the repository Secrets yet; skipping this run.")
                sys.exit(0)
            sys.exit(f"Missing {k} in .env")


def req(url, data=None, headers=None, method=None, raw=False, timeout=60):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read()
            if raw:
                return resp.status, body, resp.headers
            return resp.status, (json.loads(body) if body else {}), resp.headers
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {url}: {e.read().decode(errors='replace')[:300]}")


# ---------- news ----------
def strip(s):
    t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())
    return re.sub(r"\s*The post .*? appeared first on .*$", "", t).strip()


def parse_ts(t):
    """Publish time as unix seconds (0 if unknown)."""
    try:
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone
        t = (t or "").strip()
        try:
            d = parsedate_to_datetime(t)
        except Exception:
            d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int(d.timestamp())
    except Exception:
        return 0


def page_ts(url):
    """Publish time read from the article page itself (meta tag or JSON-LD)."""
    try:
        _, body, _ = req(url, headers=UA, raw=True, timeout=20)
    except Exception:
        return 0
    page = body.decode("utf-8", "replace")
    for pat in (r"""article:published_time["'][^>]*content=["']([^"']+)""",
                r"""content=["']([^"']+)["'][^>]*article:published_time""",
                r""""datePublished"\s*:\s*"([^"]+)""",
                r"""<time[^>]*datetime=["']([^"']+)"""):
        m = re.search(pat, page)
        if m and parse_ts(m.group(1)):
            return parse_ts(m.group(1))
    return 0


def fmt_ts(ts):
    from datetime import datetime
    return datetime.fromtimestamp(ts).astimezone().strftime("%d %b %Y, %I:%M %p %Z") if ts else "date unknown"


def feed_image(entry):
    """Picture a feed entry carries itself: media:content/thumbnail, an image enclosure, or an <img> in its HTML."""
    for c in entry.iter():
        name = c.tag.split("}")[-1]
        u = c.get("url") or ""
        if name in ("content", "thumbnail") and u and (c.get("medium") == "image" or (c.get("type") or "").startswith("image") or re.search(r"[.](jpe?g|png|webp)([?]|$)", u, re.I)):
            return u
        if name == "enclosure" and u and (c.get("type") or "").startswith("image"):
            return u
    for c in entry.iter():
        if c.tag.split("}")[-1] in ("description", "encoded", "summary", "content") and c.text:
            m = re.search(r"""<img[^>]+src=["']([^"']+)""", c.text)
            if m:
                return html.unescape(m.group(1))
    return None


def fetch_feed(url, limit=None):
    try:
        _, body, _ = req(url, headers=UA, raw=True, timeout=20)
        try:
            root = ET.fromstring(body)
        except ET.ParseError:   # sloppy feeds: escape stray ampersands / drop control chars and retry
            t = body.decode("utf-8", "replace")
            t = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", t)
            t = "".join(ch for ch in t if ch.isprintable() or ch.isspace())
            root = ET.fromstring(t.encode("utf-8"))
    except Exception as e:
        print("feed failed", url, e)
        return []
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        g = lambda n: next((c for c in it if c.tag.split("}")[-1] == n), None)
        t, l, d = g("title"), g("link"), (g("description") if g("description") is not None else g("summary"))
        link = (l.text or l.get("href")) if l is not None else ""
        if t is not None and link:
            dt = g("pubDate") if g("pubDate") is not None else (g("published") if g("published") is not None else g("updated"))
            out.append({"title": strip(t.text), "link": link.strip(), "summary": strip(d.text if d is not None else "")[:500],
                        "ts": parse_ts(dt.text if dt is not None else ""), "feed_img": feed_image(it)})
    return out[:limit or PER_FEED]


def fetch_site(url):
    """Generic headline scraper: longest-text same-site links that look like articles."""
    body = None
    for attempt in range(2):                 # one retry: some sites drop a request now and then
        try:
            _, body, _ = req(url, headers=UA, raw=True, timeout=20)
            break
        except Exception as e:
            print("site failed", url, e)
            time.sleep(3)
    if body is None:
        return []
    page = body.decode("utf-8", "replace")
    host = urllib.parse.urlparse(url).netloc
    out, seen = [], set()
    for m in re.finditer(r"""<a\s[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""", page, re.S | re.I):
        link = urllib.parse.urljoin(url, html.unescape(m.group(1))).split("#")[0]
        title = " ".join(strip(m.group(2)).split())
        path = urllib.parse.urlparse(link).path.strip("/")
        if (urllib.parse.urlparse(link).netloc != host or len(title) < 35 or len(title.split()) < 5
                or (path.count("/") < 1 and path.count("-") < 4) or re.search(r"/(category|tag|author|about|podcasts?|videos?|events?|webinars?|topics?)(/|-)", "/" + path + "/")
                or link in seen or link.rstrip("/") == url.rstrip("/")):
            continue
        seen.add(link)
        out.append({"title": title, "link": link, "summary": ""})
    return out[:PER_FEED]


JUNK = re.compile(r"(stock|shares|stake|price target|target price|wealth|investment management|NYSE|NASDAQ|dividend|analyst|ETF)|[$][A-Z]{2,5}", re.I)


def fetch_batch():
    """The Batch (DeepLearning.AI) has no feed; its issue pages are static, numbered and weekly."""
    out = []
    for k in range(395, 340, -1):
        u = f"https://www.deeplearning.ai/the-batch/issue-{k}/"
        try:
            _, body, _ = req(u, headers=UA, raw=True, timeout=15)
        except Exception:
            continue
        t = body.decode("utf-8", "replace")
        m = re.search(r"""<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)""", t)
        d = re.search(r"""<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)""", t)
        if m:
            out.append({"title": "The Batch: " + strip(m.group(1)), "link": u, "summary": strip(d.group(1)) if d else "", "ts": page_ts(u), "cat": "AI"})
        if len(out) >= 2:
            break
    return out


def collect():
    items = []
    items.extend(fetch_batch())
    for cat, urls in FEEDS.items():
        for u in urls:
            for it in fetch_feed(u):
                it["cat"] = cat
                items.append(it)
    for cat, urls in SITES.items():
        for u in urls:
            for it in fetch_site(u):
                it["cat"] = cat
                items.append(it)
    return [x for x in items if not JUNK.search(x["title"])]


def refresh_news():
    items[:] = collect()


def og_desc(url):
    if "news.google.com" in url:
        return ""
    try:
        _, body, _ = req(url, headers=UA, raw=True, timeout=20)
        m = re.search(rb"""<meta[^>]+(?:property|name)=["']og:description["'][^>]+content=["']([^"']+)""", body)
        return strip(m.group(1).decode("utf-8", "replace")) if m else ""
    except Exception:
        return ""


def og_image(url):
    if "news.google.com" in url:   # redirect page, its image would be the Google logo
        return None
    try:
        _, body, _ = req(url, headers=UA, raw=True, timeout=20)
        m = re.search(rb'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', body) or \
            re.search(rb'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', body)
        return html.unescape(m.group(1).decode()) if m else None
    except Exception:
        return None


# ---------- drafting ----------
def write_draft(item):
    key = os.environ.get("ANTHROPIC_API_KEY")
    gkey = os.environ.get("GEMINI_API_KEY")
    if key or gkey:
        prompt = (
            "Write a LinkedIn post for an instrumentation/process-automation professional about this news. "
            "Max 1100 characters. Strong first line, 2-3 short paragraphs, one practical takeaway, "
            "no em dashes, no hype words, no emojis overload. End with 5-6 hashtags on their own line, starting from these suggestions: " + " ".join(__import__("hashtags").tags_for(item["title"], item.get("summary", ""), item.get("cat", "AI"), __import__("hashtags").google_trends())[0]) + ". "
            "Do not include the link, it is added automatically. Output only the post.\n\n"
            f"Title: {item['title']}\nSummary: {item['summary']}\nSource: {item['link']}")
        try:
            if gkey:
                _, r, _ = req("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + gkey,
                              json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode(),
                              {"Content-Type": "application/json"})
                return r["candidates"][0]["content"]["parts"][0]["text"].strip()
            _, r, _ = req("https://api.anthropic.com/v1/messages",
                          json.dumps({"model": "claude-sonnet-5-5", "max_tokens": 800,
                                      "messages": [{"role": "user", "content": prompt}]}).encode(),
                          {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            return r["content"][0]["text"].strip()
        except Exception as e:
            print("LLM draft failed, using template:", e)
    return f"{item['title']}\n\n{item['summary'][:400]}\n\nWhat does this mean for your plant or project?\n\n" + " ".join(__import__("hashtags").tags_for(item['title'], item.get('summary', ''), item.get('cat', 'AI'), __import__("hashtags").google_trends())[0])


# ---------- telegram ----------
def tg(method, **p):
    _, r, _ = req(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
                  json.dumps(p).encode(), {"Content-Type": "application/json"}, timeout=70)
    return r


def tg_photo(jpeg):
    """Send image bytes (multipart upload), for pictures that have no public URL such as title cards."""
    bnd = "----newsbot" + hashlib.md5(jpeg[:256]).hexdigest()
    head = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{os.environ['TELEGRAM_CHAT_ID']}\r\n"
            f"--{bnd}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"card.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n")
    body = head.encode() + jpeg + f"\r\n--{bnd}--\r\n".encode()
    req(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto", body,
        {"Content-Type": f"multipart/form-data; boundary={bnd}"}, timeout=70)


def say(text, buttons=None):
    p = {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000], "disable_web_page_preview": True}
    if buttons:
        p["reply_markup"] = {"inline_keyboard": buttons}
    return tg("sendMessage", **p)


def show_news():
    say("Fetching latest news...")
    refresh_news()
    if not items:
        return say("No news fetched. Check feeds / internet.")
    for it in items:
        say(f"[{it['cat']}] {it['title']}\n{it['link']}", [[{"text": "Draft post", "callback_data": f"d:{uid(it)}"}]])


def show_top(n=4):
    """n ready-to-approve posts (image + draft + buttons), half instrumentation, half AI."""
    say(f"Preparing {n} posts...")
    refresh_news()
    picked, per = [], {"Instrumentation": 0, "AI": 0, "Robotics": 0, "UAE": 0, "UAE AI": 0}
    for it in items:
        if len(picked) >= n or per[it["cat"]] >= n // 2:
            continue
        if og_image(it["link"]):
            per[it["cat"]] += 1
            picked.append(it)
    for it in picked:
        make_draft(it)


def make_draft(it, header="DRAFT"):
    k = uid(it)
    if not it["summary"]:
        it["summary"] = og_desc(it["link"])
    text = write_draft(it)
    lines = text.rstrip().splitlines()
    src = f"Source: {it['link']}"
    if lines[-1].lstrip().startswith("#"):
        lines[-1:] = [src, "", lines[-1]]
    else:
        lines += ["", src]
    text = chr(10).join(lines)
    import images   # article picture shrunk to 1200px, or a generated title card when the story has none
    img_file, kind = None, "none"
    try:
        jpeg, kind = images.story_image(it)
        CARDS.mkdir(exist_ok=True)
        img_file = CARDS / f"{k}.jpg"
        img_file.write_bytes(jpeg)
        tg_photo(jpeg)
    except Exception as e:
        print("image failed", e)
    drafts[k] = {"text": text, "img_file": str(img_file) if img_file else None, "link": it["link"], "topic": it.get("cat", "")}
    label = {"article": "article photo", "card": "title card"}.get(kind, "none")
    say(f"{header} (image: {label}):\n\n{text}",
        [[{"text": "Approve & post", "callback_data": f"a:{k}"},
          {"text": "Reject", "callback_data": f"r:{k}"}]])


# ---------- linkedin ----------
def li_post(d):
    tok = os.environ.get("LINKEDIN_ACCESS_TOKEN") or json.loads((HERE / "token.json").read_text())["access_token"]
    auth = {"Authorization": f"Bearer {tok}", "LinkedIn-Version": "202601", "X-Restli-Protocol-Version": "2.0.0"}
    _, info, _ = req("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {tok}"})
    owner = f"urn:li:person:{info['sub']}"
    payload = {"author": owner, "commentary": d["text"], "visibility": "PUBLIC",
               "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
               "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    f = d.get("img_file")
    if f and not Path(f).exists():          # on GitHub each run starts clean: make the picture again
        try:
            import images
            first = next((ln for ln in d["text"].splitlines() if ln.strip()), "News")
            jpeg, _ = images.story_image({"title": first, "link": d["link"], "cat": d.get("topic", "AI"), "topic": d.get("topic", "AI")})
            Path(f).parent.mkdir(exist_ok=True); Path(f).write_bytes(jpeg)
        except Exception as e:
            print("picture rebuild failed", e)
    if f and Path(f).exists():
        try:
            b = Path(f).read_bytes()
            _, up, _ = req("https://api.linkedin.com/rest/images?action=initializeUpload",
                           json.dumps({"initializeUploadRequest": {"owner": owner}}).encode(),
                           {**auth, "Content-Type": "application/json"})
            req(up["value"]["uploadUrl"], b, {"Authorization": f"Bearer {tok}"}, "PUT", raw=True)
            payload["content"] = {"media": {"id": up["value"]["image"], "altText": "Article image"}}
        except Exception as e:
            say(f"Image upload failed ({e}); posting text only.")
    status, _, h = req("https://api.linkedin.com/rest/posts", json.dumps(payload).encode(),
                       {**auth, "Content-Type": "application/json"}, "POST")
    return status, h.get("x-restli-id", "")


ROBO_WORDS = re.compile(r"robot|humanoid|cobot|drone|autonomous|exoskeleton", re.I)
INST_WORDS = re.compile(r"sensor|flow ?meter|transmitter|measurement|instrument|calibrat|PLC|SCADA|DCS|process control|analy[sz]er|valve|pump|automation", re.I)


def item_from_link(url):
    """Build a news item from any article URL: title, summary, date and image from the page's own tags."""
    _, body, _ = req(url, headers=UA, raw=True, timeout=25)
    page = body.decode("utf-8", "replace")

    def meta(prop):
        m = (re.search(r"""<meta[^>]+(?:property|name)=["']%s["'][^>]+content=["']([^"']+)""" % prop, page, re.I)
             or re.search(r"""<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']%s["']""" % prop, page, re.I))
        return strip(m.group(1)) if m else ""

    title = meta("og:title") or meta("twitter:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
        title = strip(m.group(1)) if m else url
    title = re.sub(r"\s+[-|–]\s+[^-|–]{2,40}$", "", title)   # drop " - Site Name" endings
    summary = meta("og:description") or meta("description") or meta("twitter:description")
    text = title + " " + summary
    cat = "Robotics" if ROBO_WORDS.search(text) else ("Instrumentation" if INST_WORDS.search(text) else "AI")
    return {"title": title, "link": url, "summary": summary[:500], "ts": page_ts(url) or int(time.time()), "cat": cat}


def log_post(d, post_id):
    """Remember what went to LinkedIn, for the dashboard's Posted tracker."""
    f = HERE / "posted.json"
    try:
        log = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except Exception:
        log = []
    first = next((ln for ln in d["text"].splitlines() if ln.strip()), d["link"])
    log.insert(0, {"title": first[:200], "link": d["link"], "at": int(time.time()), "topic": d.get("topic", ""), "post_id": post_id})
    f.write_text(json.dumps(log[:200], ensure_ascii=False), encoding="utf-8")


def handle(u):
    chat = os.environ["TELEGRAM_CHAT_ID"]
    if "message" in u:
        m = u["message"]
        if str(m["chat"]["id"]) != chat:
            return
        t = m.get("text") or ""
        link = re.search(r"https?://\S+", t)
        if link and not t.startswith("/"):
            say("Reading the link and writing a post...")
            try:
                it = item_from_link(link.group(0).rstrip(").,"))
                make_draft(it, header=f"FROM YOUR LINK [{it['cat']}]")
            except Exception as e:
                say(f"Could not read that page ({e}). The site may block bots; try another link to the same story.")
        elif t.startswith("/news"):
            show_news()
        elif t.startswith(("/top", "/start")):
            show_top()
    elif "callback_query" in u:
        c = u["callback_query"]
        if str(c["message"]["chat"]["id"]) != chat:
            return
        tg("answerCallbackQuery", callback_query_id=c["id"])
        act, k = c["data"].split(":")
        if act == "d":
            it = next((x for x in items if uid(x) == k), None)
            make_draft(it) if it else say("That story expired. Send /news again.")
        elif act == "r":
            drafts.pop(k, None)
            say("Rejected.")
        elif act == "a" and k in drafts:
            try:
                d = drafts.pop(k)
                s, pid = li_post(d)
                log_post(d, pid)
                say(f"Published to LinkedIn ({s}) {pid}")
            except Exception as e:
                say(f"LinkedIn error: {e}")


def check_new():
    """Look at every feed/site; push any story not seen before as a ready-to-approve draft."""
    found = collect()
    new = [x for x in found if uid(x) not in seen]
    if not STATE_FLAGS["has_seen"]:          # first ever run: just remember what exists
        seen.extend(uid(x) for x in found)
        STATE_FLAGS["has_seen"] = True
        print("baseline saved:", len(found))
        return
    for it in new[:MAX_ALERTS]:
        seen.append(uid(it))
        try:
            make_draft(it, header=f"NEW [{it['cat']}] {fmt_ts(it.get('ts', 0))}")
        except Exception as e:
            print("alert failed", e)
    if len(new) > MAX_ALERTS:
        say(f"{len(new) - MAX_ALERTS} more new stories will arrive in the next check.")


def main():
    """python news_bot.py            -> run forever (local PC)
    python news_bot.py --once 270    -> poll ~270s then exit (GitHub Actions)
    python news_bot.py --digest      -> send the news list now, then exit"""
    global offset
    load_env()
    load_state()
    if "--digest" in sys.argv:
        show_top()
        return save_state()
    once = "--once" in sys.argv
    last_check = 0
    end = time.time() + (int(sys.argv[sys.argv.index("--once") + 1]) if once else 10**9)
    while time.time() < end:
        if time.time() - last_check > (0 if not last_check else WATCH_MINUTES * 60):
            last_check = time.time()
            try:
                check_new()
                save_state()
            except Exception as e:
                print("check failed", e)
        try:
            wait = max(1, min(50, int(end - time.time()))) if once else 50
            for u in tg("getUpdates", offset=offset, timeout=wait).get("result", []):
                offset = u["update_id"] + 1
                try:
                    handle(u)
                except Exception as e:
                    say(f"Error: {e}")
                save_state()
        except Exception as e:
            print("poll error", e)
            time.sleep(3)
    save_state()


if __name__ == "__main__":
    main()

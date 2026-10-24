"""Live trends for the dashboard, written to dash/trends.json (fast: headlines only, no images).

Two kinds of rows:
  kind="news"   keywords rising in AI / instrumentation / robotics news: stories in the last 6 hours
                compared with the 24 hours before
  kind="google" Google Trends top searches (several countries) that are about tech, AI or industry
"""
import json, re, time, urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import news_bot as n
import hashtags as h
import os
if hasattr(time, "tzset"):            # Linux (GitHub runners use UTC); Windows already uses local time
    os.environ.setdefault("TZ", "Asia/Dubai")
    time.tzset()                     # GitHub runners use UTC: stamp times in UAE time

NOW = time.time()
RECENT, BASE = 6 * 3600, 24 * 3600
GEOS = ["US", "GB", "IN", "AE", "SA", "DE", "SG", "AU", "CA", "JP"]
TECH = re.compile(r"\bai\b|artificial intelligence|gpt|openai|chatgpt|gemini|claude|anthropic|nvidia|\bchips?\b|semiconductor|robot|"
                  r"quantum|ionq|tesla|spacex|starlink|apple|iphone|samsung|google|microsoft|meta|amazon|\baws\b|software|cyber|hack|"
                  r"data ?cent|cloud|sensor|automation|siemens|\babb\b|honeywell|emerson|yokogawa|schneider|aramco|adnoc|g42|"
                  r"hydrogen|solar|battery|\bev\b|drone|satellite|5g|6g|intel|\bamd\b|tsmc|qualcomm|oppo|xiaomi|huawei|pixel|android", re.I)

AIHEAD = re.compile(r"\bAI\b|[Aa]rtificial intelligence|OpenAI|NVIDIA|[Rr]obot|[Ss]emiconductor|[Aa]utomation")

# 1. rising keywords in our own news feeds
feeds = [(cat, u) for cat in ("AI", "Instrumentation", "Robotics", "UAE AI", "Smart Sensors", "IoT") for u in n.FEEDS.get(cat, [])]
with ThreadPoolExecutor(12) as pool:
    lists = list(pool.map(lambda cu: [dict(x, cat=cu[0]) for x in n.fetch_feed(cu[1], limit=30)], feeds))
seen, stories = set(), []
for lst in lists:
    for x in lst:
        if x["link"] not in seen and x["ts"] >= NOW - RECENT - BASE:
            seen.add(x["link"]); stories.append(x)

stat = {}
for x in stories:
    text = x["title"] + " " + x.get("summary", "")
    tags = {t for p, t in h.COMPANIES if re.search(p, text)} | {t for rx, t in h.TOPICS if rx.search(text)}
    tags -= {"#UAE", "#India", "#SaudiArabia"}   # places are not topics
    recent = x["ts"] >= NOW - RECENT
    host = urllib.parse.urlparse(x["link"]).netloc.replace("www.", "")
    for t in tags:
        s = stat.setdefault(t, {"now": 0, "before": 0, "cats": {}, "hours": [0] * 30, "first": None, "with": {}, "stories": []})
        s["now" if recent else "before"] += 1
        s["cats"][x["cat"]] = s["cats"].get(x["cat"], 0) + 1
        age_h = int((NOW - x["ts"]) // 3600)
        if 0 <= age_h < 30:
            s["hours"][29 - age_h] += 1            # oldest hour first, current hour last
        if recent:
            s["first"] = x["ts"] if s["first"] is None else min(s["first"], x["ts"])
            for o in tags - {t}:
                s["with"][o] = s["with"].get(o, 0) + 1
        s["stories"].append({"title": x["title"], "link": x["link"], "ts": x["ts"], "source": host})

stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
rows = []
for t, s in stat.items():
    if s["now"] < 2:
        continue
    rate_now, rate_before = s["now"] / 6, (s["before"] + 1) / 24       # stories per hour, smoothed
    change = round(100 * (rate_now / rate_before - 1))
    related = [k for k, _ in sorted(s["with"].items(), key=lambda kv: -kv[1])][:8]
    st = sorted(s["stories"], key=lambda y: -y["ts"])[:8]
    rows.append({"kind": "news", "term": t.lstrip("#"), "hashtag": t, "beat": max(s["cats"], key=s["cats"].get),
                 "count": s["now"], "before": s["before"], "change": change, "score": round(s["now"] * rate_now / rate_before, 2),
                 "geo": "", "traffic": "", "started": int(s["first"] or NOW), "active": "Yes" if s["hours"][-1] or s["hours"][-2] else "No",
                 "series": json.dumps(s["hours"]), "related": json.dumps(related), "stories": json.dumps(st),
                 "headline": st[0]["title"] if st else "", "link": st[0]["link"] if st else "",
                 "explore": "https://trends.google.com/trends/explore?date=now%207-d&q=" + urllib.parse.quote(t.lstrip("#")),
                 "updated": stamp})
rows.sort(key=lambda r: -r["score"])
rows = rows[:15]

# 2. Google Trends: top searches per country, kept when they are about tech / AI / industry
for geo in GEOS:
    try:
        _, body, _ = n.req(f"https://trends.google.com/trending/rss?geo={geo}", headers=n.UA, raw=True, timeout=20)
    except Exception as e:
        print("trends failed", geo, e)
        continue
    for item in re.findall(r"<item>(.*?)</item>", body.decode("utf-8", "replace"), re.S):
        term = re.search(r"<title>([^<]+)</title>", item)
        if not term:
            continue
        term = n.strip(term.group(1))
        titles = [n.strip(v) for v in re.findall(r"<ht:news_item_title>([^<]+)<", item)]
        urls = [n.strip(v) for v in re.findall(r"<ht:news_item_url>([^<]+)<", item)]
        sources = [n.strip(v) for v in re.findall(r"<ht:news_item_source>([^<]+)<", item)]
        about = term + " " + " ".join(titles)
        if not (TECH.search(term) or AIHEAD.search(about)):
            continue
        traffic = re.search(r"<ht:approx_traffic>([^<]+)<", item)
        pub = re.search(r"<pubDate>([^<]+)</pubDate>", item)
        st = [{"title": a, "link": b, "ts": 0, "source": c} for a, b, c in zip(titles, urls, sources + [""] * len(titles))]
        rows.append({"kind": "google", "term": term, "hashtag": h.camel(term),
                     "beat": "AI" if re.search(r"\bai\b|gpt|openai|gemini|claude|nvidia", about, re.I) else "Tech",
                     "count": 0, "before": 0, "change": 0, "score": 0, "geo": geo, "traffic": traffic.group(1) if traffic else "",
                     "started": n.parse_ts(pub.group(1)) if pub else int(NOW), "active": "Yes", "series": "[]", "related": "[]",
                     "stories": json.dumps(st), "headline": titles[0] if titles else "", "link": urls[0] if urls else "",
                     "explore": f"https://trends.google.com/trends/explore?date=now%201-d&geo={geo}&q=" + urllib.parse.quote(term),
                     "updated": stamp})

# 3. what was posted to LinkedIn (logged by the Telegram bot on Approve)
try:
    for p in json.load(open("posted.json", encoding="utf-8"))[:30]:
        rows.append({"kind": "posted", "term": p["title"], "hashtag": "", "beat": p.get("topic", ""), "count": 0, "before": 0, "change": 0, "score": 0,
                     "geo": "", "traffic": "", "started": p["at"], "active": "", "series": "[]", "related": "[]", "stories": "[]",
                     "headline": p["title"], "link": p["link"], "explore": "", "updated": stamp})
except FileNotFoundError:
    pass

json.dump(rows, open("data/trends.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len([r for r in rows if r["kind"] == "news"]), "rising news keywords,", len([r for r in rows if r["kind"] == "google"]), "Google trends,", len(stories), "stories read")

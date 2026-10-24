"""Build the website's news data: data/today_news.json plus one picture per story in img/.

Pictures are cached by story: a story that already has img/<id>.jpg is not downloaded again,
and pictures of stories that dropped out of the list are deleted, so the repository stays small.
"""
import json, os, re, time, collections
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import news_bot as n
import images, hashtags

HERE = Path(__file__).parent
DATA, IMG = HERE / "data", HERE / "img"
DATA.mkdir(exist_ok=True); IMG.mkdir(exist_ok=True)
if hasattr(time, "tzset"):            # Linux (GitHub runners use UTC); Windows already uses local time
    os.environ.setdefault("TZ", "Asia/Dubai")
    time.tzset()                     # GitHub runners use UTC: show times in UAE time

KEEP_DAYS = 7                      # stories (and their pictures) older than this are dropped on every refresh
now = time.time(); cut = now - KEEP_DAYS * 86400
FETCHED = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")

found = {}
for cat, urls in n.FEEDS.items():
    for u in urls:
        for it in n.fetch_feed(u, limit=40):
            if it["ts"] >= cut:
                it["cat"] = cat; found[it["link"]] = it
for cat, urls in n.SITES.items():
    for u in urls:
        for it in n.fetch_site(u):
            it["cat"] = cat; it["ts"] = n.page_ts(it["link"])
            if it["ts"] >= cut:
                found[it["link"]] = it
for x in n.fetch_batch():
    if x["ts"] >= cut:
        found[x["link"]] = x

MARKET = re.compile(r"\bmarket (size|share|report|forecast|outlook|analysis|to 20\d\d)|\bCAGR\b|market will (reach|grow)|market is (expected|projected)", re.I)
items = [x for x in found.values() if not n.JUNK.search(x["title"]) and not MARKET.search(x["title"])]
items.sort(key=lambda x: -x["ts"])
CAPS = {"Instrumentation": 100, "AI": 90, "Robotics": 50, "UAE": 80, "UAE AI": 70, "Smart Sensors": 60}   # balance the beats
cnt, sel = {}, []
for x in items:
    cnt[x["cat"]] = cnt.get(x["cat"], 0) + 1
    if cnt[x["cat"]] <= CAPS.get(x["cat"], 50):
        sel.append(x)
items = sel

ROBO = re.compile(r"robot|humanoid|cobot|drone|autonomous|exoskeleton", re.I)
INST = re.compile(r"sensor|flow ?meter|transmitter|measurement|instrument|calibrat|PLC|SCADA|\bDCS\b|process control|analyzer|valve", re.I)
SENSOR = re.compile(r"\bsensors?\b|\btransmitters?\b|IO-Link|\bMEMS\b|Ethernet-APL|\bsensing\b", re.I)
UAE_AI = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|artificial intelligence|machine learning|LLM|generative|chatbot|data cent|G42|MBZUAI|Falcon|Core42", re.I)


def topic(x):
    t = x["title"] + " " + x.get("summary", "")
    if x["cat"] == "Smart Sensors": return "Smart Sensors"
    if x["cat"] in ("Instrumentation", "Robotics") and SENSOR.search(x["title"]): return "Smart Sensors"
    if x["cat"] == "Robotics": return "Robotics"
    if x["cat"] == "UAE AI": return "UAE AI"
    if x["cat"] == "UAE": return "UAE AI" if UAE_AI.search(t) else "UAE"
    if ROBO.search(t): return "Robotics"
    if x["cat"] == "Instrumentation" or INST.search(x["title"]): return "Instrumentation"
    return "AI"


TRENDS = hashtags.google_trends()
old = {}
try:
    old = {r["link"]: r for r in json.load(open(DATA / "today_news.json", encoding="utf-8"))}
except Exception:
    pass


def make_row(x):
    prev = old.get(x["link"])
    desc = x.get("summary") or (prev or {}).get("summary") or n.og_desc(x["link"])
    tp = topic({**x, "summary": desc})
    uid = n.uid(x)
    path = IMG / f"{uid}.jpg"
    kind = (prev or {}).get("image", "No")
    if not path.exists():
        try:
            b, k = images.story_image({**x, "topic": tp}, width=640, quality=68)
            path.write_bytes(b)
            kind = {"article": "Article", "card": "Title card"}.get(k, "No")
        except Exception:
            kind = "No"
    tg, trd = hashtags.tags_for(x["title"], desc, tp, TRENDS)
    d = datetime.fromtimestamp(x["ts"]).astimezone()
    return {"date": d.strftime("%Y-%m-%d"), "time": d.strftime("%H:%M"), "group": x["cat"], "topic": tp,
            "title": x["title"], "summary": desc[:200], "link": x["link"],
            "image": kind, "img": f"img/{uid}.jpg" if path.exists() else "", "fetched": FETCHED,
            "tags": " ".join(tg), "trending": ", ".join(trd)}


with ThreadPoolExecutor(8) as pool:
    rows = list(pool.map(make_row, items))

keep = {Path(r["img"]).name for r in rows if r["img"]}
removed = 0
for f in IMG.glob("*.jpg"):
    if f.name not in keep:
        f.unlink(); removed += 1

json.dump(rows, open(DATA / "today_news.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(rows), "stories,", len(keep), "pictures kept,", removed, "old pictures removed,",
      os.path.getsize(DATA / "today_news.json") // 1024, "KB of data")
print(collections.Counter(r["topic"] for r in rows), collections.Counter(r["image"] for r in rows))

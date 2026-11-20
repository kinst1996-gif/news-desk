"""Key facts from an article's own text, so a post can say what actually happened.

key_facts(url, title, summary) -> up to 3 short sentences (no AI: picks the most informative
sentences from the article's opening paragraphs: numbers, names, places, dates).
"""
import html, re
import news_bot as n

BOILER = re.compile(r"cookie|subscribe|newsletter|sign up|sign in|log in|advertis|all rights reserved|©|copyright|read more|follow us|"
                    r"click here|javascript|privacy policy|terms of use|share this|related articles|whatsapp channel|download our app|"
                    r"photo:|image:|credit:|getty|reuters/|afp/|^also read|recommended for you", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'‘(])")


def _paragraphs(page):
    body = page
    m = re.search(r"<article\b.*?</article>", page, re.S | re.I)
    if m and len(m.group(0)) > 1500:
        body = m.group(0)
    body = re.sub(r"(?is)<(script|style|noscript|figure|figcaption|aside|nav|footer|header|form)\b.*?</\1>", " ", body)
    out = []
    for p in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", body):
        t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", p)).split())
        if len(t) >= 60 and not BOILER.search(t):
            out.append(t)
    return out


def key_facts(url, title="", summary="", limit=3):
    if "news.google.com" in url:
        return []
    try:
        _, body, _ = n.req(url, headers=n.UA, raw=True, timeout=20)
    except Exception:
        return []
    paras = _paragraphs(body.decode("utf-8", "replace"))[:10]
    seen = {re.sub(r"\W+", "", title.lower())[:60], re.sub(r"\W+", "", summary.lower())[:60]}
    cands = []
    for pi, p in enumerate(paras):
        for s in SENT.split(p):
            s = s.strip()
            key = re.sub(r"\W+", "", s.lower())[:60]
            if not (50 <= len(s) <= 240) or key in seen or BOILER.search(s):
                continue
            seen.add(key)
            score = 2 * bool(re.search(r"\d", s)) + bool(re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", s[1:])) + (2 if pi < 3 else 0) - 0.1 * len(cands)
            if s.endswith("?") or s.startswith(("“", '"')) and s.count("“") + s.count('"') > 2:
                score -= 1
            if (s.count('"') % 2) or (s.count("“") != s.count("”")) or re.search(r"[\"”]\s*(he|she|they) (said|added)\.?$", s):
                score -= 3                                  # half a quote or a "...," he said fragment
            cands.append((score, len(cands), s))
    best = sorted(cands, key=lambda c: -c[0])[:limit]
    return [s for _, _, s in sorted(best, key=lambda c: c[1])]   # keep the article's own order


if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        print(u)
        for f in key_facts(u):
            print("  -", f)

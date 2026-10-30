"""Images for news items: the article's own picture, shrunk, or a generated title card.

story_image(item)            -> (jpeg_bytes, "article" | "card")
title_card(title, topic, source, width) -> jpeg_bytes
"""
import io, os, textwrap, urllib.parse
from PIL import Image, ImageDraw, ImageFont

import news_bot as n

# Card colours per topic: (background, accent)
PALETTE = {
    "Instrumentation": ((18, 52, 77), (88, 196, 220)),
    "AI": ((38, 30, 72), (170, 150, 255)),
    "Robotics": ((24, 60, 46), (120, 220, 160)),
    "UAE": ((92, 26, 34), (232, 196, 120)),
    "UAE AI": ((70, 22, 60), (240, 170, 210)),
    "Smart Sensors": ((60, 34, 12), (255, 160, 80)),
    "IoT": ((10, 56, 56), (94, 234, 212)),
}
FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation"]
BOLD = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
REGULAR = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]


def _font(names, size):
    for d in FONT_DIRS:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _jpeg(img, width, quality):
    img = img.convert("RGB")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    return out.getvalue()


def title_card(title, topic="AI", source="", width=1200, quality=82):
    """LinkedIn-shaped (1.91:1) card: topic label, headline, source."""
    W, H = 1200, 628
    bg, accent = PALETTE.get(topic, PALETTE["AI"])
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, H], fill=accent)
    d.text((80, 70), (topic or "News").upper(), font=_font(BOLD, 34), fill=accent)
    # Fit the headline: shrink the font until it fits in 5 lines.
    for size in (72, 64, 56, 50, 44):
        f = _font(BOLD, size)
        chars = max(14, int(1040 / (size * 0.52)))
        lines = textwrap.wrap(title.strip(), width=chars)
        if len(lines) <= 5:
            break
    lines = lines[:5]
    y = 150
    for line in lines:
        d.text((80, y), line, font=f, fill=(255, 255, 255))
        y += int(size * 1.22)
    if source:
        d.text((80, H - 90), source, font=_font(REGULAR, 30), fill=(210, 220, 230))
    return _jpeg(img, width, quality)


def _download(url):
    _, body, h = n.req(url, headers=n.UA, raw=True, timeout=25)
    if not (h.get_content_type() or "").startswith("image/") or len(body) > 15_000_000:
        raise ValueError("not an image")
    img = Image.open(io.BytesIO(body))
    img.load()
    if img.width < 200 or img.height < 120:   # icons and tracking pixels
        raise ValueError("too small")
    return img


def story_image(item, width=1200, quality=82):
    """Best picture for a story as JPEG bytes. Falls back to a title card, never None."""
    host = urllib.parse.urlparse(item.get("link", "")).netloc.replace("www.", "")
    for url in (item.get("feed_img"), None if "news.google.com" in item.get("link", "") else n.og_image(item["link"])):
        if not url:
            continue
        try:
            return _jpeg(_download(url), width, quality), "article"
        except Exception:
            continue
    return title_card(item["title"], item.get("topic") or item.get("cat", "AI"), host, width, quality), "card"

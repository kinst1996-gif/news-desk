"""Assemble index.html (the website) from the dashboard page in page.html. Run after editing page.html."""
from pathlib import Path
HERE = Path(__file__).parent
page = (HERE / "page.html").read_text(encoding="utf-8")
head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>News Desk</title>
<meta name="description" content="Live instrumentation, AI, robotics and UAE news, ready to post on LinkedIn.">
<meta name="theme-color" content="#060b14">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-192.png">
<style>
  :root { --font-anthropic-sans: "Segoe UI", system-ui, -apple-system, Roboto, sans-serif; --font-anthropic-serif: Georgia, serif; --cds-ease-out: cubic-bezier(.2,.8,.2,1); --cds-dur-slow: .4s; color-scheme: dark; }
  html, body { margin: 0; background: #060b14; min-height: 100%; }
  #dash-root { min-height: 100vh; }
  .dash-skeleton:empty { min-height: 120px; border-radius: 10px; background: linear-gradient(90deg, rgba(255,255,255,.03), rgba(255,255,255,.07), rgba(255,255,255,.03)); background-size: 200% 100%; animation: sk 1.4s linear infinite; }
  @keyframes sk { from { background-position: 100% 0; } to { background-position: -100% 0; } }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="shim.js"></script>
</head>
<body>
<div id="dash-root">
"""
(HERE / "index.html").write_text(head + page + "\n</div>\n</body>\n</html>\n", encoding="utf-8")
print("index.html written,", len(head + page) // 1024, "KB")

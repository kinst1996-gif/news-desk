# News Desk: free 24/7 website on GitHub

Live at **https://kinst1996-gif.github.io/news-desk/**. No PC, server or Telegram needed.

| What | Runs on | How often |
|---|---|---|
| Website | GitHub Pages | Always on |
| News, pictures, hashtags | GitHub Actions (`news.yml`) | Every hour |
| Trending now | GitHub Actions (`trends.yml`) | Every 15 minutes |

## Posting a story to LinkedIn
1. Tap a story card (or a day in **This week's plan**). The LinkedIn preview opens.
2. Pick a **post style**, edit the text, switch hashtags on or off.
3. Tap **Download image** to save the picture.
4. Tap **Post on LinkedIn**. The text is copied and LinkedIn opens with it filled in. If the box is empty (some phones), paste.
5. Add the image in LinkedIn and publish.
6. Back on the dashboard, tap **Mark as posted**. It appears under **Posted to LinkedIn** (saved on that device).

## On your Android phone
Open the site in **Chrome → ⋮ → Add to Home screen**. It opens full-screen from its own icon.

## Good to know
- **Timers can run late** by a few minutes; that is normal on GitHub.
- **Inactive repositories pause their timers after 60 days.** The 15-minute trends update counts as activity, so this should not happen. If GitHub emails you, open the Actions tab and re-enable.
- **Run a refresh now:** Actions tab → **News refresh** or **Trends refresh** → **Run workflow**.
- **Changing the page:** edit `page.html`, run `python make_page.py`, then push.
- **Adding a news source:** add its feed address to `FEEDS` in `news_bot.py`, then push.
- The Telegram bot code (`news_bot.py`) stays because the builds use its feed list and readers; its timers were removed, so it never runs on GitHub.

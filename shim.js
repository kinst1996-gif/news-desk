/* Stand-in for the dashboard runtime: loads the JSON files the GitHub Actions publish,
   runs the page's calculations and tells the page when data changes. */
window.dash = (function () {
  const KEEP_DAYS = 7;
  const CHECK_EVERY = 5 * 60 * 1000;     // look for new data every 5 minutes while the page is open
  const FILES = { today_news: 'data/today_news.json', source_health: 'data/source_health.json', trends: 'data/trends.json' };
  const store = {}, calcs = {}, listeners = [], lastText = {};
  const emit = () => listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });
  // quiet: a background check. It shows no "refreshing" state and only redraws when the file really changed.
  async function load(id, quiet) {
    const prev = store[id];
    if (!quiet) store[id] = prev && prev.status === 'ok' ? Object.assign({}, prev, { refreshing: true }) : { status: 'loading', data: [] };
    try {
      // "no-cache" revalidates with the server: an unchanged file comes back as a tiny "not modified" reply.
      const res = await fetch(FILES[id], { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const text = await res.text();
      if (quiet && text === lastText[id] && prev && prev.status === 'ok') return;   // nothing new: no redraw
      lastText[id] = text;
      let data = JSON.parse(text);
      if (id === 'today_news' && Array.isArray(data)) {        // keep only the last 7 days (UAE time), whatever the file holds
        const cutoff = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Dubai' }).format(new Date(Date.now() - KEEP_DAYS * 86400000));
        data = data.filter(r => !r.date || r.date >= cutoff);
      }
      store[id] = { status: 'ok', data, refreshing: false };
    } catch (e) {
      if (quiet && prev) return;                                 // offline during a background check: keep what is shown
      store[id] = prev && prev.status === 'ok' ? Object.assign({}, prev, { refreshing: false }) : { status: 'error', data: [], message: String(e) };
    }
    emit();
  }
  // sync state the page can show: when the next automatic check is due, and whether one is running
  const sync = { every: CHECK_EVERY, nextAt: Date.now() + CHECK_EVERY, checking: false, lastChange: 0, listeners: [] };
  const tellSync = () => sync.listeners.forEach(fn => { try { fn(sync); } catch (e) { console.error(e); } });
  let timer = null;
  function schedule() { clearTimeout(timer); sync.nextAt = Date.now() + CHECK_EVERY; timer = setTimeout(checkAll, CHECK_EVERY); tellSync(); }
  async function checkAll() {
    if (document.hidden) { schedule(); return; }
    sync.checking = true; tellSync();
    const before = Object.keys(FILES).map(id => lastText[id] || '').join('|');
    await Promise.all(Object.keys(FILES).map(id => load(id, true)));
    if (Object.keys(FILES).map(id => lastText[id] || '').join('|') !== before) sync.lastChange = Date.now();
    sync.checking = false; schedule();
  }
  const api = {
    colors: ['#3fe0ff', '#a68bff', '#46f0a4', '#ffc457', '#ff6fcf', '#7fb8ff', '#ff8a3d', '#c9d6e8'],
    calc(id, def) { calcs[id] = def; },
    loader() {},
    data(id) {
      if (FILES[id]) { if (!store[id]) load(id); return store[id]; }
      const c = calcs[id];
      if (!c) return { status: 'missing', data: [] };
      const ins = c.inputs.map(i => api.data(i));
      if (ins.some(x => x.status !== 'ok')) return { status: ins.some(x => x.status === 'error') ? 'error' : 'loading', data: [] };
      try { return { status: 'ok', data: c.fn(...ins.map(x => x.data)) }; } catch (e) { console.error(e); return { status: 'error', data: [], message: String(e) }; }
    },
    onData(fn) { listeners.push(fn); try { fn(); } catch (e) { console.error(e); } },
    refresh(id) { if (FILES[id]) load(id); },
    onSync(fn) { sync.listeners.push(fn); fn(sync); },     // page draws the auto-sync countdown from this
    params() { return {}; }, setParams() {}, resetParams() {}, setLink() {}
  };
  let t = null;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(emit, 200); });
  schedule();
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkAll(); });   // opening the app again checks at once
  window.addEventListener('online', checkAll);               // back online: check at once
  return api;
})();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});

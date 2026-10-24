/* Stand-in for the dashboard runtime: loads the JSON files the GitHub Actions publish,
   runs the page's calculations and tells the page when data changes. */
window.dash = (function () {
  const KEEP_DAYS = 7;
  const FILES = { today_news: 'data/today_news.json', source_health: 'data/source_health.json', trends: 'data/trends.json' };
  const store = {}, calcs = {}, listeners = [];
  const emit = () => listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });
  async function load(id) {
    const prev = store[id];
    store[id] = prev && prev.status === 'ok' ? Object.assign({}, prev, { refreshing: true }) : { status: 'loading', data: [] };
    try {
      const res = await fetch(FILES[id] + '?v=' + Date.now(), { cache: 'no-store' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      let data = await res.json();
      if (id === 'today_news' && Array.isArray(data)) {        // keep only the last 7 days (UAE time), whatever the file holds
        const cutoff = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Dubai' }).format(new Date(Date.now() - KEEP_DAYS * 86400000));
        data = data.filter(r => !r.date || r.date >= cutoff);
      }
      store[id] = { status: 'ok', data, refreshing: false };
    } catch (e) {
      store[id] = prev && prev.status === 'ok' ? Object.assign({}, prev, { refreshing: false }) : { status: 'error', data: [], message: String(e) };
    }
    emit();
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
    params() { return {}; }, setParams() {}, resetParams() {}, setLink() {}
  };
  let t = null;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(emit, 200); });
  setInterval(() => { api.refresh('today_news'); api.refresh('source_health'); }, 30 * 60 * 1000);   // news: every 30 minutes
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { api.refresh('trends'); api.refresh('today_news'); } });
  return api;
})();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});

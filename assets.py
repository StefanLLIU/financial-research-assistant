"""Static presentation assets (CSS / JS / manifest) for the web UI."""

PAGE_CSS = """
<style>
  :root{
    --bg:#f9fafb; --card:#ffffff; --tile:#f8fafc; --text:#111827; --muted:#64748b;
    --border:#eef2f7; --border2:#f1f5f9; --accent:#1e3a5f; --accent2:#2d5480;
    --chip-bg:#eff6ff; --chip-tx:#1e3a5f; --th-bg:#f1f5f9; --th-tx:#334155;
    --link:#2563eb; --input-bd:#d1d5db; --shadow:rgba(0,0,0,.08); --overlay:rgba(249,250,251,.9);
    --up:#166534; --down:#991b1b;
  }
  :root[data-theme="dark"]{
    --bg:#0f172a; --card:#1e293b; --tile:#243449; --text:#e2e8f0; --muted:#94a3b8;
    --border:#334155; --border2:#334155; --accent:#93c5fd; --accent2:#bfdbfe;
    --chip-bg:#334155; --chip-tx:#dbeafe; --th-bg:#273449; --th-tx:#cbd5e1;
    --link:#60a5fa; --input-bd:#475569; --shadow:rgba(0,0,0,.4); --overlay:rgba(15,23,42,.9);
    --up:#4ade80; --down:#f87171;
  }
  @media(prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#0f172a; --card:#1e293b; --tile:#243449; --text:#e2e8f0; --muted:#94a3b8;
      --border:#334155; --border2:#334155; --accent:#93c5fd; --accent2:#bfdbfe;
      --chip-bg:#334155; --chip-tx:#dbeafe; --th-bg:#273449; --th-tx:#cbd5e1;
      --link:#60a5fa; --input-bd:#475569; --shadow:rgba(0,0,0,.4); --overlay:rgba(15,23,42,.9);
      --up:#4ade80; --down:#f87171;
    }
  }
  body{font-family:system-ui,sans-serif;margin:0;padding:0;background:var(--bg);color:var(--text);}
  .layout{display:flex;gap:28px;max-width:1180px;margin:40px auto;padding:0 20px;align-items:flex-start;}
  .main{flex:1;min-width:0;}
  .sidebar{width:240px;flex-shrink:0;background:var(--card);border-radius:10px;padding:18px 16px;box-shadow:0 2px 8px var(--shadow);position:sticky;top:40px;}
  .sidebar h4{margin:0 0 10px;color:var(--accent);font-size:15px;border-bottom:1px solid var(--border);padding-bottom:6px;}
  .sidebar .cat{border-bottom:1px solid var(--border2);}
  .sidebar .cat>summary{cursor:pointer;list-style:none;padding:9px 4px;color:var(--accent);font-size:14px;font-weight:600;display:flex;align-items:center;justify-content:space-between;user-select:none;}
  .sidebar .cat>summary::-webkit-details-marker{display:none;}
  .sidebar .cat>summary::after{content:"▾";font-size:11px;color:var(--muted);transition:transform .15s;}
  .sidebar .cat[open]>summary::after{transform:rotate(180deg);}
  .sidebar .cat>summary:hover{color:var(--accent2);}
  .sidebar .cat-stocks{display:flex;flex-wrap:wrap;gap:6px;padding:2px 0 12px;}
  .sidebar a.tk{display:inline-block;background:var(--chip-bg);color:var(--chip-tx);text-decoration:none;padding:4px 10px;border-radius:6px;font-size:13px;font-weight:600;transition:background .15s;}
  .sidebar a.tk:hover{background:var(--accent);color:#fff;}
  .sidebar .cat-title{flex:1;}
  .sidebar .cat-heat{font-size:12px;font-weight:800;margin:0 8px 0 auto;}
  .sidebar .cat-heat.up{color:var(--up);} .sidebar .cat-heat.down{color:var(--down);}
  .sidebar .cat-meta{font-size:11px;color:var(--muted);padding:0 2px 8px;line-height:1.7;}
  .sidebar .cat-meta a{color:var(--chip-tx);text-decoration:none;font-weight:700;}
  @media(max-width:860px){.layout{flex-direction:column;}.sidebar{width:auto;position:static;}}
  h1{color:var(--accent);}
  input{padding:10px 14px;font-size:16px;border:1px solid var(--input-bd);border-radius:6px;width:200px;background:var(--card);color:var(--text);}
  button{padding:10px 20px;font-size:16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;margin-left:8px;}
  .card{margin-top:30px;background:var(--card);border-radius:10px;padding:24px;box-shadow:0 2px 8px var(--shadow);}
  .metric{display:inline-block;background:var(--chip-bg);color:var(--chip-tx);border-radius:6px;padding:6px 12px;margin:4px;font-size:14px;}
  h2{color:var(--accent);border-bottom:2px solid var(--border);padding-bottom:8px;}
  h3{color:var(--text);}
  ul{padding-left:18px;}
  li{margin-bottom:6px;}
  a{color:var(--link);}
  .error{color:#dc2626;font-weight:bold;}
  table{width:100%;border-collapse:collapse;margin:8px 0 4px;}
  th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--border);font-size:15px;}
  th{background:var(--th-bg);color:var(--th-tx);font-weight:600;width:40%;}
  td.up{color:var(--up);font-weight:600;}
  td.down{color:var(--down);font-weight:600;}
  .score-table{width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
  .score-table td{border:none;padding:14px 18px;color:#fff;vertical-align:middle;}
  .score-table .score-num-cell{font-size:44px;font-weight:800;width:110px;text-align:center;}
  .score-table .score-label-cell{font-size:24px;font-weight:700;width:120px;}
  .score-table .score-reason-cell{font-size:14px;line-height:1.6;}
  .sc-bullish td{background:linear-gradient(135deg,#16a34a,#22c55e);}
  .sc-neutral td{background:linear-gradient(135deg,#64748b,#94a3b8);}
  .sc-bearish td{background:linear-gradient(135deg,#dc2626,#ef4444);}
  .score-den{font-size:18px;font-weight:500;opacity:.85;}
  .topbar{display:flex;justify-content:space-between;align-items:center;gap:8px;}
  .topbar-btns{display:flex;gap:8px;flex-shrink:0;}
  .lang-btn,.theme-btn{background:var(--card);border:1px solid var(--input-bd);border-radius:6px;padding:6px 12px;font-size:14px;text-decoration:none;color:var(--accent);white-space:nowrap;cursor:pointer;}
  .lang-btn:hover,.theme-btn:hover{background:var(--accent);color:#fff;}
  /* Dashboard stat tiles */
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0 6px;}
  .stat{background:var(--tile);border:1px solid var(--border);border-radius:12px;padding:14px 16px;}
  .stat .s-label{font-size:12px;color:var(--muted);margin-bottom:5px;}
  .stat .s-value{font-size:21px;font-weight:700;color:var(--accent);line-height:1.2;word-break:break-word;}
  .stat .s-value.up{color:var(--up);}
  .stat .s-value.down{color:var(--down);}
  .stat.hero{background:linear-gradient(135deg,#1e3a5f,#2d5480);border:none;}
  .stat.hero .s-label{color:#c7d6e8;}
  .stat.hero .s-value{color:#fff;font-size:24px;}
  /* Featured mini cards + sparklines */
  .featured-h{color:var(--accent);font-size:17px;margin:26px 0 10px;}
  .mini-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;}
  .mini{display:block;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:13px 15px;text-decoration:none;color:var(--text);box-shadow:0 1px 4px var(--shadow);transition:transform .12s,box-shadow .12s;}
  .mini:hover{transform:translateY(-2px);box-shadow:0 4px 12px var(--shadow);}
  .mini-top{display:flex;justify-content:space-between;align-items:baseline;}
  .mini-tk{font-weight:800;color:var(--accent);font-size:15px;}
  .mini-chg{font-size:13px;font-weight:700;}
  .mini-chg.up{color:var(--up);} .mini-chg.down{color:var(--down);}
  .mini-price{font-size:19px;font-weight:700;margin:4px 0 6px;}
  .mini-spark{height:34px;}
  .mini-spark svg{width:100%;height:34px;display:block;}
  /* Loading overlay */
  .loading-overlay{position:fixed;inset:0;background:var(--overlay);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;flex-direction:column;z-index:9999;}
  .loading-overlay.show{display:flex;}
  .spinner{width:46px;height:46px;border:4px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
  .loading-text{margin-top:16px;color:var(--accent);font-weight:600;font-size:15px;}
  /* Sticky section nav */
  .secnav{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:6px;padding:10px 0;margin:-8px 0 4px;background:var(--card);border-bottom:1px solid var(--border);}
  .secnav a{text-decoration:none;color:var(--muted);font-size:13px;font-weight:600;padding:5px 10px;border-radius:6px;}
  .secnav a:hover{background:var(--chip-bg);color:var(--chip-tx);}
  .sec{scroll-margin-top:52px;}
  /* Score breakdown */
  .breakdown{display:flex;flex-direction:column;gap:10px;margin:10px 0 4px;}
  .bd-row{display:grid;grid-template-columns:96px 46px 1fr;gap:10px;align-items:center;}
  .bd-name{font-size:13px;font-weight:600;color:var(--text);}
  .bd-score{font-size:15px;font-weight:800;text-align:center;border-radius:6px;padding:2px 0;}
  .bd-score.bullish{background:rgba(34,197,94,.16);color:var(--up);}
  .bd-score.neutral{background:rgba(148,163,184,.18);color:var(--muted);}
  .bd-score.bearish{background:rgba(239,68,68,.16);color:var(--down);}
  .bd-score.na{background:var(--th-bg);color:var(--muted);font-size:11px;font-weight:600;}
  .bd-exp{font-size:13px;color:var(--muted);}
  /* Factor lists */
  .factors{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:8px 0;}
  .fbox{background:var(--tile);border:1px solid var(--border);border-radius:12px;padding:14px 16px;}
  .fbox h4{margin:0 0 8px;font-size:14px;}
  .fbox.bull h4{color:var(--up);} .fbox.risk h4{color:var(--down);} .fbox.mon h4{color:var(--accent);}
  .fbox ul{margin:0;padding-left:18px;} .fbox li{font-size:13px;margin-bottom:5px;color:var(--text);}
  .fbox .none{font-size:13px;color:var(--muted);}
  /* Meta line + badges */
  .meta-line{font-size:12px;color:var(--muted);margin:2px 0 0;}
  .status-badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:6px;vertical-align:middle;}
  .status-badge.open{background:rgba(34,197,94,.16);color:var(--up);}
  .status-badge.closed{background:var(--th-bg);color:var(--muted);}
  .status-badge.ext{background:rgba(59,130,246,.16);color:var(--link);}
  .change-chip{font-size:14px;font-weight:700;margin-top:3px;}
</style>
"""

THEME_INIT = "try{var _t=localStorage.getItem('theme');if(_t)document.documentElement.setAttribute('data-theme',_t);}catch(e){}"

APP_JS = """
(function(){
  var ov=document.getElementById('loadingOverlay');
  function showLoading(){if(ov)ov.classList.add('show');}
  document.querySelectorAll('form').forEach(function(f){f.addEventListener('submit',showLoading);});
  document.querySelectorAll('a.tk,a.lang-btn,a.mini').forEach(function(a){a.addEventListener('click',showLoading);});
  window.addEventListener('pageshow',function(){if(ov)ov.classList.remove('show');});

  // Theme toggle (light <-> dark, persisted in localStorage)
  var tb=document.getElementById('themeBtn');
  function curTheme(){
    var a=document.documentElement.getAttribute('data-theme');
    if(a)return a;
    return (window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light';
  }
  function setIcon(){if(tb)tb.textContent=curTheme()==='dark'?'☀️':'🌙';}
  setIcon();
  if(tb)tb.addEventListener('click',function(){
    var next=curTheme()==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',next);
    try{localStorage.setItem('theme',next);}catch(e){}
    setIcon();
  });

  // Featured mini cards: draw sparkline SVG from returned closes
  function spark(el,pts,up){
    if(!pts||pts.length<2){el.innerHTML='';return;}
    var w=100,h=34,mn=Math.min.apply(null,pts),mx=Math.max.apply(null,pts),rng=(mx-mn)||1;
    var d=pts.map(function(v,i){var x=i/(pts.length-1)*w;var y=h-((v-mn)/rng)*(h-4)-2;return (i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}).join(' ');
    var col=up?'#22c55e':'#ef4444';
    el.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>';
  }
  document.querySelectorAll('.mini').forEach(function(c){
    var tk=c.getAttribute('data-ticker');
    fetch('/api/mini?ticker='+encodeURIComponent(tk)).then(function(r){return r.json();}).then(function(d){
      var pe=c.querySelector('.mini-price'),ce=c.querySelector('.mini-chg'),se=c.querySelector('.mini-spark');
      if(d.price==null){pe.textContent='N/A';return;}
      pe.textContent=(d.currency?d.currency+' ':'')+d.price.toFixed(2);
      var up=(d.change_pct||0)>=0;
      ce.textContent=(d.change_pct==null)?'':((up?'+':'')+d.change_pct.toFixed(2)+'%');
      ce.className='mini-chg '+(up?'up':'down');
      spark(se,d.spark,up);
    }).catch(function(){var pe=c.querySelector('.mini-price');if(pe)pe.textContent='N/A';});
  });

  // Market heat: fill each sector's daily/weekly/leader, then rank by daily %
  var sb=document.getElementById('sidebar');
  if(sb){
    var lang=sb.getAttribute('data-lang')||'zh';
    var LB=(lang==='en')?{wk:'1W',lead:'Top',news:'News activity'}:{wk:'周',lead:'领涨',news:'新闻活跃度'};
    fetch('/api/heat?lang='+lang).then(function(r){return r.json();}).then(function(rows){
      var byIdx={}; rows.forEach(function(r){byIdx[r.idx]=r;});
      document.querySelectorAll('.cat-heat').forEach(function(el){
        var r=byIdx[el.getAttribute('data-idx')];
        if(!r||r.daily==null){el.textContent='';return;}
        var up=r.daily>=0; el.textContent=(up?'+':'')+r.daily.toFixed(2)+'%';
        el.className='cat-heat '+(up?'up':'down');
      });
      document.querySelectorAll('.cat-meta').forEach(function(el){
        var r=byIdx[el.getAttribute('data-idx')]; if(!r)return;
        var parts=[];
        if(r.weekly!=null) parts.push(LB.wk+' '+(r.weekly>=0?'+':'')+r.weekly.toFixed(1)+'%');
        if(r.leader) parts.push(LB.lead+': <a href="/research-page?ticker='+r.leader+'&lang='+lang+'">'+r.leader+'</a> '+(r.leader_pct>=0?'+':'')+r.leader_pct.toFixed(1)+'%');
        parts.push(LB.news+': —');
        el.innerHTML=parts.join('<br>');
      });
      // reorder sectors by daily % (hottest first); data-less sectors go last
      rows.forEach(function(r){
        var d=sb.querySelector('details[data-idx="'+r.idx+'"]');
        if(d) sb.appendChild(d);
      });
      document.querySelectorAll('#sidebar details').forEach(function(d){
        if(byIdx[d.getAttribute('data-idx')]===undefined) sb.appendChild(d);
      });
    }).catch(function(){});
  }

  if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){});});}
})();
"""

CHART_TEMPLATE = """
<script>
(function(){
  var dates=__DATES__, closes=__CLOSES__, volumes=__VOLUMES__, ma50=__MA50__, ma200=__MA200__;
  var earn=__EARN__, spy=__SPY__, soxx=__SOXX__, prefix=__PREFIX__, ticker=__TICKER__, L=__LABELS__;
  var gd=document.getElementById('priceChart');
  if(!gd || !window.Plotly || !dates.length) return;

  var dark = (function(){
    var a=document.documentElement.getAttribute('data-theme');
    if(a) return a==='dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches;
  })();
  var fg = dark ? '#cbd5e1' : '#334155';
  var grid = dark ? 'rgba(148,163,184,0.15)' : 'rgba(100,116,139,0.12)';
  var up = closes[closes.length-1] >= closes[0];
  var priceColor = up ? '#22c55e' : '#ef4444';

  var traces = [];
  // Price
  traces.push({x:dates, y:closes, type:'scatter', mode:'lines', name:ticker,
    line:{color:priceColor, width:2},
    hovertemplate:'%{x|%Y-%m-%d}<br>'+prefix+'%{y:,.2f}<extra>'+ticker+'</extra>'});
  // Moving averages
  traces.push({x:dates, y:ma50, type:'scatter', mode:'lines', name:L.ma50,
    line:{color:'#f59e0b', width:1.3}, connectgaps:false, hoverinfo:'skip'});
  traces.push({x:dates, y:ma200, type:'scatter', mode:'lines', name:L.ma200,
    line:{color:'#8b5cf6', width:1.3}, connectgaps:false, hoverinfo:'skip'});
  // Volume on secondary axis
  var volColor = dark ? 'rgba(148,163,184,0.45)' : 'rgba(100,116,139,0.4)';
  traces.push({x:dates, y:volumes, type:'bar', name:L.vol, yaxis:'y2',
    marker:{color:volColor}, hovertemplate:'%{y:,}<extra>'+L.vol+'</extra>'});
  // Earnings markers (placed on the price line)
  if(earn && earn.length){
    var closeByDate={}; for(var i=0;i<dates.length;i++) closeByDate[dates[i]]=closes[i];
    var ex=[], ey=[];
    earn.forEach(function(dt){ if(closeByDate[dt]!=null){ ex.push(dt); ey.push(closeByDate[dt]); }});
    if(ex.length) traces.push({x:ex, y:ey, type:'scatter', mode:'markers', name:L.earn,
      marker:{symbol:'diamond', size:9, color:'#eab308', line:{color:'#fff', width:1}},
      hovertemplate:'%{x|%Y-%m-%d}<br>'+L.earn+'<extra></extra>'});
  }
  // Benchmark overlays (rebased to the stock's first price), hidden until toggled
  function rebased(b, name, color){
    if(!b || !b.closes || !b.closes.length) return null;
    var f = closes[0]/b.closes[0];
    return {x:b.dates, y:b.closes.map(function(v){return v*f;}), type:'scatter', mode:'lines',
      name:name, visible:'legendonly', line:{color:color, width:1.3, dash:'dot'},
      hovertemplate:'%{x|%Y-%m-%d}<br>'+name+' ('+L.rebased+')<extra></extra>'};
  }
  var rs=rebased(spy,'SPY','#38bdf8'); if(rs) traces.push(rs);
  var ro=rebased(soxx,'SOXX','#fb7185'); if(ro) traces.push(ro);

  var last=dates[dates.length-1];
  var d=new Date(last); d.setFullYear(d.getFullYear()-1);
  var start1y=d.toISOString().slice(0,10);

  function yRange(lo,hi){
    var loD=new Date(lo), hiD=new Date(hi), ys=[];
    for(var i=0;i<dates.length;i++){var dd=new Date(dates[i]); if(dd>=loD&&dd<=hiD) ys.push(closes[i]);}
    if(!ys.length) return null;
    var mn=Math.min.apply(null,ys), mx=Math.max.apply(null,ys);
    var pad=(mx-mn)*0.08||mx*0.05; return [Math.max(0,mn-pad), mx+pad];
  }

  var layout={
    autosize:true, margin:{l:55,r:15,t:8,b:26}, font:{color:fg, size:11},
    hovermode:'x unified', bargap:0.1,
    legend:{orientation:'h', x:0, y:1.16, font:{size:11}},
    xaxis:{type:'date', range:[start1y,last], rangeslider:{visible:false},
      gridcolor:grid, linecolor:grid,
      rangeselector:{x:0, y:1.32, bgcolor:'rgba(0,0,0,0)', activecolor:dark?'#334155':'#e2e8f0',
        font:{color:fg}, buttons:[
        {count:1,label:'1M',step:'month',stepmode:'backward'},
        {count:3,label:'3M',step:'month',stepmode:'backward'},
        {count:1,label:'1Y',step:'year',stepmode:'backward'},
        {step:'all',label:'5Y'}]}},
    yaxis:{domain:[0.24,1], tickprefix:prefix, fixedrange:true, gridcolor:grid, zeroline:false},
    yaxis2:{domain:[0,0.18], fixedrange:true, showgrid:false, tickformat:'.2s'},
    plot_bgcolor:'rgba(0,0,0,0)', paper_bgcolor:'rgba(0,0,0,0)', showlegend:true
  };
  var yr=yRange(start1y,last); if(yr) layout.yaxis.range=yr;

  Plotly.newPlot(gd,traces,layout,{responsive:true, displayModeBar:false}).then(function(){
    Plotly.Plots.resize(gd);
    setTimeout(function(){ Plotly.Plots.resize(gd); }, 100);
  });
  window.addEventListener('resize', function(){ Plotly.Plots.resize(gd); });

  gd.on('plotly_relayout', function(e){
    var lo,hi;
    if(e['xaxis.range[0]']){ lo=e['xaxis.range[0]']; hi=e['xaxis.range[1]']; }
    else if(e['xaxis.range']){ lo=e['xaxis.range'][0]; hi=e['xaxis.range'][1]; }
    else if(e['xaxis.autorange']){ lo=dates[0]; hi=last; }
    else return;
    var yr2=yRange(lo,hi); if(yr2) Plotly.relayout(gd,{'yaxis.range':yr2});
  });
})();
</script>
"""

SERVICE_WORKER = """
const CACHE = 'fra-v1';
const SHELL = ['/', '/static/icon-192.png', '/static/apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

// Network-first for pages (fresh data); cache-first for static icons.
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match('/')))
  );
});
"""

MANIFEST = {
    "name": "股票研究助手 · Financial Research Assistant",
    "short_name": "股票研究",
    "description": "实时行情、财报分析、投资评分 · Live stock research & scoring",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f9fafb",
    "theme_color": "#1e3a5f",
    "icons": [
        {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}


const SB='https://unwzvhdwxmlmknvgvrhp.supabase.co/rest/v1/';
const KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVud3p2aGR3eG1sbWtudmd2cmhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTUwMjQ5MzUsImV4cCI6MjExMDYwMDkzNX0.g_500nSaAP5lF6N69ofsvozust1BpzbBU7kZXtooAyM';
const H={apikey:KEY,Authorization:'Bearer '+KEY};
const CATS=[['','الكل'],['mobiles','موبايلات'],['tablets','تابلت'],['laptops','لابتوب'],['tvs','شاشات'],['audio','سماعات'],['smartwatches','ساعات ذكية'],['appliances','أجهزة منزلية'],['electronics','إلكترونيات'],['gaming','ألعاب فيديو'],['grocery','سوبرماركت'],['beauty','جمال'],['health','صحة ونظافة'],['home','البيت والمطبخ'],['fashion','موضة'],['kids','أطفال'],['sports','رياضة'],['computer_acc','إكسسوارات كمبيوتر'],['mobile_acc','إكسسوارات موبايل'],['auto','عربيات'],['books_office','كتب ومكتب'],['other','أخرى']];
const SORTS=[['new','🆕 الأحدث'],['drop','📉 أكبر نزول في السعر'],['score','🔥 أقوى لقطة'],['pct','٪ أعلى خصم'],['low','📉 أقل سعر في تاريخه'],['cheap','💸 الأرخص']];
const TYPES=[['','كل العروض'],['drop','📉 نزل سعره'],['disc','🏷 خصم المتجر'],['lowest','🔥 أقل سعر تاريخي']];
const SINCE=[[0,'أي وقت'],[1,'آخر ساعة'],[24,'آخر 24 ساعة'],[168,'آخر أسبوع']];
const PCTS=[[0,'أي خصم'],[20,'+20%'],[40,'+40%'],[60,'+60%'],[80,'+80%']];
let BOT_URL='https://t.me/AmazonEGOffersBot';
let SITE={};
const STORES=[['amazon','أمازون مصر','amazon.eg',1],['amazon_resale','أمازون مستعمل','amazon.eg',1],['amazon_now','أمازون ناو','amazon.eg',1],['noon','نون مصر','noon.com',0],['noon_minutes','نون مينتس','noon.com',0],['jumia','جوميا','jumia.com.eg',0],['talabat','طلبات مارت','talabat.com',0],['breadfast','بريد فاست','breadfast.com',0],['carrefour','كارفور','carrefouregypt.com',0],['btech','B.TECH','btech.com',0],['2b','2B','2b.com.eg',0],['vodafone','فودافون','vodafone.com.eg',0],['etisalat','اتصالات','eand.com.eg',0],['orange','أورنج','orange.eg',0],['we','وي WE','te.eg',0]];
const st={type:'',since:0,store:'',sort:'new',cat:'',pct:0,q:'',limit:48,seen:new Set(),first:true};
const fmt=n=>n==null?'':Number(n).toLocaleString('en-US',{maximumFractionDigits:2});
const ago=t=>{const s=(Date.now()-new Date(t))/1000;if(s<60)return'من ثواني';if(s<3600)return'من '+Math.floor(s/60)+' د';if(s<86400)return'من '+Math.floor(s/3600)+' س';return'من '+Math.floor(s/86400)+' يوم'};
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function q(path){const r=await fetch(SB+path,{headers:H});if(!r.ok)throw new Error(r.status);return r.json()}
function buildQuery(){
  let p='products?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change,in_stock&in_stock=eq.true&price=gt.0&hidden=eq.false';
  if(st.store)p+='&store=eq.'+st.store;
  if(st.type==='drop')p+='&drop_pct=gt.0';
  else if(st.type==='disc')p+='&discount_pct=gt.0';
  else if(st.type==='lowest')p+='&drop_pct=gt.0&low_at=not.is.null';
  else p+='&or=(discount_pct.gt.0,drop_pct.gt.0)';
  if(st.since)p+='&last_change=gte.'+new Date(Date.now()-st.since*3600e3).toISOString();
  if(st.cat)p+='&category=eq.'+st.cat;
  if(st.pct)p+='&discount_pct=gte.'+st.pct;
  if(st.q)p+='&title=ilike.*'+encodeURIComponent(st.q.replace(/[*,()]/g,' '))+'*';
  const o={new:'last_change.desc',score:'score.desc.nullslast,last_change.desc',pct:'discount_pct.desc.nullslast',low:'low_at.desc.nullslast',cheap:'price.asc',drop:'drop_pct.desc.nullslast,last_change.desc'}[st.sort];
  if(st.sort==='drop'&&!st.type)p+='&drop_pct=gt.0';
  if(st.sort==='low')p+='&drop_pct=gt.0';
  return p+'&order='+o+'&limit='+st.limit;
}
function storeName(k){return (STORES.find(x=>x[0]===k)||[,'المتجر'])[1]}
function storeTag(k){const s=STORES.find(x=>x[0]===k);return s?`<div class="store-name"><img src="https://www.google.com/s2/favicons?domain=${s[2]}&sz=32" alt="">${s[1]}</div>`:''}
function card(p){
  const fresh=!st.first&&!st.seen.has(p.id+p.price);st.seen.add(p.id+p.price);
  const atLow=p.low_price&&Number(p.price)<=Number(p.low_price);
  const b=[];if(p.discount_pct>0)b.push(`<span class="b pct">-${p.discount_pct}%</span>`);
  if(p.drop_pct>0)b.push(`<span class="b drop">↓ نزل ${p.drop_pct}%</span>`);
  if(atLow&&p.drop_pct>0)b.push('<span class="b low">أقل سعر</span>');
  if(p.fake_discount)b.push('<span class="b fake">خصم مشكوك</span>');
  const sc=p.score||0;
  return `<a class="card ${fresh?'fresh':''} ${sc>=70?'s70':''} ${p.drop_pct>0?'dropped':''}" href="#/p/${encodeURIComponent(p.id)}">
  <div class="img"><img loading="lazy" src="${esc(p.image)}" alt=""></div><div class="badges">${b.join('')}</div>
  <div class="body"><div class="title">${esc(p.title)}</div>
  <div class="price"><b>${fmt(p.price)} ج</b>${p.list_price&&+p.list_price>+p.price?`<s>${fmt(p.list_price)}</s>`:''}</div>${p.drop_pct>0&&p.prev_price?`<div class="wasline">📉 كان ${fmt(p.prev_price)} ج · وفّرت ${fmt(p.prev_price-p.price)} ج</div>`:''}
  <div class="power" title="قوة اللقطة"><div class="bar" style="width:${Math.max(4,sc)}%"></div></div>
  <div class="meta"><span>قوة اللقطة ${sc}</span><span>${ago(p.last_change)}</span></div>${storeTag(p.store)}</div></a>`;
}
let timer;
async function loadFeed(){
  const g=document.getElementById('grid');if(!g)return;
  try{const rows=await q(buildQuery());
    g.innerHTML=rows.length?rows.map(card).join(''):'<div class="empty">مفيش عروض بالفلتر دا دلوقتي</div>';
    st.first=false;
  }catch(e){document.getElementById('liveText').dataset.off='1'}
}
async function loadStats(){
  try{const r=await fetch(SB+'products?select=id&limit=1',{headers:{...H,Prefer:'count=exact'}});
    const total=(r.headers.get('content-range')||'').split('/')[1]||'—';
    const since=new Date(Date.now()-3600e3).toISOString();
    const r2=await fetch(SB+'products?select=id&limit=1&drop_pct=gt.0&last_change=gte.'+since,{headers:{...H,Prefer:'count=exact'}});
    const drops=(r2.headers.get('content-range')||'').split('/')[1]||'0';
    document.getElementById('stats').innerHTML=`<div class="stat"><b>${Number(total).toLocaleString('en-US')}</b>منتج</div><div class="stat"><b>${drops}</b>سعر نزل آخر ساعة</div><div class="stat"><b>⚡</b>تحديث لحظي</div>`;
  }catch(e){}
}
function chips(id,list,key){
  const el=document.getElementById(id);
  el.innerHTML=list.map(([v,t])=>`<button class="chip ${st[key]==v?'on':''}" data-v="${v}">${t}</button>`).join('');
  el.onclick=e=>{const b=e.target.closest('.chip');if(!b)return;st[key]=(key==='pct'||key==='since')?+b.dataset.v:b.dataset.v;st.limit=48;st.first=true;st.seen.clear();chips(id,list,key);loadFeed()};
}
function feed(){document.body.classList.remove('pp-open');
  const app=document.getElementById('app');app.innerHTML='';app.append(document.getElementById('feedTpl').content.cloneNode(true));
  chips('sortChips',SORTS,'sort');chips('catChips',visibleCats(),'cat');chips('pctChips',PCTS,'pct');chips('typeChips',TYPES,'type');chips('sinceChips',SINCE,'since');
  const qi=document.getElementById('q');qi.value=st.q;let d;qi.oninput=()=>{clearTimeout(d);d=setTimeout(()=>{st.q=qi.value.trim();st.first=true;loadFeed()},400)};
  document.getElementById('moreBtn').onclick=()=>{st.limit+=48;loadFeed()};
  st.first=true;loadFeed();loadStats();
  clearInterval(timer);timer=setInterval(()=>{if(!document.hidden){loadFeed();loadStats()}},10000);
}
function verdict(p){
  const pr=+p.price,low=+p.low_price,hi=+p.high_price;
  if(p.fake_discount)return['v-bad','⚠️ الخصم دا مشكوك فيه — السعر كان أقل من كدا قبل كدا.'];
  if(pr<=low&&hi>pr)return['v-good','✅ دا أقل سعر سجلناه للمنتج — لقطة حقيقية.'];
  if(pr<=low*1.05)return['v-good','✅ السعر قريب جداً من أقل سعر سجلناه.'];
  return['v-ok','ℹ️ سعر عادي — ممكن يستاهل تستنى نزول.'];
}
function chart(cv,pts){
  const dpr=devicePixelRatio||1,w=cv.clientWidth,h=cv.clientHeight;cv.width=w*dpr;cv.height=h*dpr;const c=cv.getContext('2d');c.scale(dpr,dpr);
  if(pts.length<2){c.fillStyle='#9aa3b2';c.font='13px Cairo';c.textAlign='center';c.fillText('لسه بنجمع تاريخ السعر للمنتج دا',w/2,h/2);return}
  const xs=pts.map(p=>+new Date(p.at)),ys=pts.map(p=>+p.price);const x0=Math.min(...xs),x1=Math.max(...xs)||x0+1,y0=Math.min(...ys)*.97,y1=Math.max(...ys)*1.03;
  const X=t=>16+(w-32)*(t-x0)/((x1-x0)||1),Y=v=>h-24-(h-44)*(v-y0)/((y1-y0)||1);
  c.strokeStyle='#ff6a2b';c.lineWidth=2.5;c.beginPath();pts.forEach((p,i)=>{const x=X(+new Date(p.at)),y=Y(+p.price);if(i){c.lineTo(x,Y(+pts[i-1].price));c.lineTo(x,y)}else c.moveTo(x,y)});c.lineTo(w-16,Y(ys[ys.length-1]));c.stroke();
  c.fillStyle='#9aa3b2';c.font='11px Cairo';c.textAlign='left';c.fillText(fmt(Math.max(...ys))+' ج',8,14);c.fillText(fmt(Math.min(...ys))+' ج',8,h-6);
}
async function product(id){
  clearInterval(timer);const app=document.getElementById('app');app.innerHTML='<div class="empty">جاري التحميل…</div>';
  const [p]=await q('products?id=eq.'+encodeURIComponent(id)+'&select=*');
  if(!p){app.innerHTML='<div class="empty">المنتج مش موجود</div>';return}
  const hist=await q('price_history?product_id=eq.'+encodeURIComponent(id)+'&select=price,at&order=at.asc&limit=500');
  const [cls,txt]=hist.length<2&&!p.fake_discount?['v-ok','🆕 لسه بادئين نتابع سعر المنتج دا — هنقولك أول ما يتغير.']:verdict(p);document.body.classList.add('pp-open');document.title=p.title+' — عروض متتفوتش';
  app.innerHTML=`<a class="back" href="#/deals">→ رجوع للعروض</a><div class="pp"><div class="img"><img src="${esc(p.image)}" alt=""></div><div>
  <h2 style="font-size:18px;line-height:1.6;margin:0">${esc(p.title)}</h2>
  <div class="price" style="margin-top:8px"><b style="font-size:28px">${fmt(p.price)} ج</b>${p.list_price&&+p.list_price>+p.price?`<s>${fmt(p.list_price)}</s> <span class="b pct">-${p.discount_pct}%</span>`:''}</div>
  <div class="verdict ${cls}">${txt}</div>
  <div class="kv"><div><small>أقل سعر</small><b>${fmt(p.low_price)}</b></div><div><small>أعلى سعر</small><b>${fmt(p.high_price)}</b></div><div><small>قوة اللقطة</small><b>${p.score||0}</b></div></div>
  <h3 class="hist-h">📈 تاريخ السعر</h3>
  <canvas id="cv" class="${hist.length<2?'small':''}"></canvas>
  <p class="since">آخر تغيير في السعر ${ago(p.last_change)} · بنتابعه ${ago(p.first_seen)}</p></div></div>
  <div class="buybar"><a class="btn buy" href="${esc(p.url)}" target="_blank" rel="noopener sponsored">🛒 اشتري من ${storeName(p.store)} <small>${fmt(p.price)} ج</small></a><button class="btn share" id="share">🔗 مشاركة</button></div>`;
  chart(document.getElementById('cv'),hist);
  document.getElementById('share').onclick=()=>{const u=location.href;navigator.share?navigator.share({title:p.title,url:u}).catch(()=>{}):navigator.clipboard.writeText(u).then(()=>toast('اتنسخ اللينك ✅'))};
  scrollTo(0,0);
}
function toast(t){const d=document.createElement('div');d.className='toast';d.textContent=t;document.body.append(d);setTimeout(()=>d.remove(),2500)}
function applySite(){
  const s=SITE;const set=(id,v,html)=>{const e=document.getElementById(id);if(e&&v)html?e.innerHTML=v:e.textContent=v};
  set('landPill',s.hero_pill);set('landTitle',s.hero_title,1);set('landText',s.hero_text,1);
  if(s.bot_url)BOT_URL=s.bot_url;const bb=document.getElementById('botBtn');if(bb)bb.href=BOT_URL;
  if(s.channel_url)document.querySelectorAll('[data-chan]').forEach(a=>a.href=s.channel_url);
  const an=document.getElementById('annc');const A=s.announcement;
  if(A&&A.on&&A.text){an.hidden=false;an.innerHTML=A.link?`<a href="${esc(A.link)}" target="_blank" rel="noopener">${esc(A.text)}</a>`:esc(A.text);if(A.color)an.style.background=A.color}else an.hidden=true;
  if(s.colors){const r=document.documentElement.style;if(s.colors.brand)r.setProperty('--brand',s.colors.brand);if(s.colors.brand2)r.setProperty('--brand2',s.colors.brand2);if(s.colors.bg)r.setProperty('--bg',s.colors.bg)}
}
function visibleStores(){const o=SITE.stores||{};return STORES.filter(x=>!(o[x[0]]&&o[x[0]].hidden)).map(x=>{const c=o[x[0]];return c?[x[0],c.name||x[1],x[2],c.on===undefined?x[3]:(c.on?1:0)]:x})}
function visibleCats(){const h=SITE.hidden_cats||[];return CATS.filter(c=>!h.includes(c[0]))}
function home(){document.body.classList.remove('pp-open');
  clearInterval(timer);const app=document.getElementById('app');app.innerHTML='';app.append(document.getElementById('homeTpl').content.cloneNode(true));
  document.getElementById('botBtn').href=BOT_URL;
  applySite();
  const feat=async()=>{try{const rows=await q('products?select=id,title,image,price,list_price,discount_pct,drop_pct&featured=eq.true&hidden=eq.false&order=last_change.desc&limit=20');const sec=document.getElementById('featSec');if(!sec)return;sec.hidden=!rows.length;if(SITE.featured_title)document.getElementById('featTitle').textContent=SITE.featured_title;document.getElementById('featStrip').innerHTML=rows.map(p=>`<a class="dcard" href="#/p/${encodeURIComponent(p.id)}">${p.discount_pct>0?`<span class="dpct" style="background:var(--bad)">-${p.discount_pct}%</span>`:''}<img loading="lazy" src="${esc(p.image)}" alt=""><div class="dt">${esc(p.title)}</div><div class="dp"><b>${fmt(p.price)} ج</b>${p.list_price&&+p.list_price>+p.price?`<s>${fmt(p.list_price)}</s>`:''}</div></a>`).join('')}catch(e){}};feat();
  document.getElementById('storeGrid').innerHTML=visibleStores().map(([k,n,dom,on])=>`<a class="store ${on?'':'soon'}" href="${on?'#/deals?store='+k:'javascript:void 0'}" data-soon="${on?'':n}">${on?'<span class="tag">● مباشر</span>':''}<span class="lg"><img src="https://www.google.com/s2/favicons?domain=${dom}&sz=128" alt="${n}" onerror="this.replaceWith(document.createTextNode('${n[0]}'))"></span><b>${n}</b><small>${on?'خصومات لحد 90%':'قريباً'}</small></a>`).join('');
  document.getElementById('storeGrid').onclick=e=>{const s=e.target.closest('.store');if(s&&s.dataset.soon)toast('متجر '+s.dataset.soon+' هيتضاف قريباً 🔜')};
  const drops=async()=>{const el=document.getElementById('dropStrip');if(!el)return;try{const rows=await q('products?select=id,store,title,image,price,prev_price,drop_pct,last_change&drop_pct=gte.5&in_stock=eq.true&hidden=eq.false&prev_price=not.is.null&order=last_change.desc&limit=12');
    el.innerHTML=rows.map(p=>`<a class="dcard" href="#/p/${encodeURIComponent(p.id)}"><span class="dpct">↓ ${p.drop_pct}%</span><img loading="lazy" src="${esc(p.image)}" alt=""><div class="dt">${esc(p.title)}</div><div class="dp"><b>${fmt(p.price)} ج</b><s>${fmt(p.prev_price)}</s></div><small>${ago(p.last_change)}</small></a>`).join('')||'<div class="empty">لسه مفيش نزول جديد</div>'}catch(e){}};
  drops();
  const land=()=>{drops();if(!document.getElementById('landStats'))return;fetch(SB+'products?select=id&limit=1',{headers:{...H,Prefer:'count=exact'}}).then(r=>{const t=(r.headers.get('content-range')||'').split('/')[1]||'—';
    document.getElementById('landStats').innerHTML=`<div><b>${Number(t).toLocaleString('en-US')}</b><span>منتج</span></div><div><b>${STORES.length}</b><span>متجر مصري</span></div><div><b>24/7</b><span>مراقبة</span></div>`}).catch(()=>{});};land();timer=setInterval(()=>{if(!document.hidden)land()},10000);
  document.title='عروض متتفوتش — أفضل عروض المتاجر المصرية في مكان واحد';scrollTo(0,0);
}
document.getElementById('topSearch').onsubmit=e=>{e.preventDefault();const v=document.getElementById('topQ').value.trim();st.q=v;st.store='';st.first=true;const h='#/deals'+(v?'?q='+encodeURIComponent(v):'');if(location.hash===h)route();else location.hash=h;document.getElementById('topQ').blur()};
let tq;document.getElementById('topQ').oninput=()=>{if(!document.getElementById('grid'))return;clearTimeout(tq);tq=setTimeout(()=>{st.q=document.getElementById('topQ').value.trim();st.store='';st.first=true;loadFeed()},400)};
document.addEventListener('click',e=>{if(e.target.closest('#searchBtn')){e.preventDefault();const i=document.getElementById('topQ');scrollTo({top:0,behavior:'smooth'});setTimeout(()=>i.focus(),250)}});
function route(){const hsh=location.hash;const m=hsh.match(/^#\/p\/(.+)/);
  if(m)return product(decodeURIComponent(m[1]));
  if(hsh==='#stores'){if(!document.getElementById('storeGrid'))home();document.getElementById('stores').scrollIntoView({behavior:'smooth'});return}
  if(hsh.startsWith('#/deals')){const s=(hsh.match(/store=(\w+)/)||[])[1]||'';const ty=(hsh.match(/type=(\w+)/)||[])[1];st.type=ty||'';if(ty==='drop'){st.sort='new'}if(/[?&]q=/.test(hsh))st.q='';st.store=s;const qq=hsh.match(/[?&]q=([^&]+)/);st.q=qq?decodeURIComponent(qq[1]):st.q;document.getElementById('topQ').value=st.q;feed();const n=(STORES.find(x=>x[0]===s)||[])[1];document.getElementById('feedTitle').innerHTML=st.type==='drop'?'📉 <span>نزل سعره</span> دلوقتي':(n?`عروض <span>${n}</span>`:'اللي نزل <span>دلوقتي</span> — كل المتاجر');document.title='عروض متتفوتش';scrollTo(0,0);return}
  home()}
addEventListener('hashchange',route);
(async()=>{try{const rows=await q('site_config?select=key,value');rows.forEach(r=>SITE[r.key]=r.value)}catch(e){}applySite();route()})();

function clock(){const d=new Date();let h=d.getHours();const ap=h<12?'ص':'م';h=h%12||12;const p=n=>String(n).padStart(2,'0');const el=document.getElementById('liveText');el.textContent='مباشر · '+h+':'+p(d.getMinutes())+':'+p(d.getSeconds())+' '+ap}
clock();setInterval(clock,1000);

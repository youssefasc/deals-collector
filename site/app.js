const SB='https://unwzvhdwxmlmknvgvrhp.supabase.co/rest/v1/';
const KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVud3p2aGR3eG1sbWtudmd2cmhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTUwMjQ5MzUsImV4cCI6MjExMDYwMDkzNX0.g_500nSaAP5lF6N69ofsvozust1BpzbBU7kZXtooAyM';
const H={apikey:KEY,Authorization:'Bearer '+KEY};
const CATS=[['','الكل'],['mobiles','موبايلات'],['tablets','تابلت'],['laptops','لابتوب'],['tvs','شاشات'],['audio','سماعات'],['smartwatches','ساعات ذكية'],['appliances','أجهزة منزلية'],['electronics','إلكترونيات'],['gaming','ألعاب فيديو'],['grocery','سوبرماركت'],['beauty','جمال'],['health','صحة ونظافة'],['home','البيت والمطبخ'],['fashion','موضة'],['kids','أطفال'],['sports','رياضة'],['computer_acc','إكسسوارات كمبيوتر'],['mobile_acc','إكسسوارات موبايل'],['auto','عربيات'],['books_office','كتب ومكتب'],['other','أخرى']];
const SORTS=[['new','🆕 أحدث نزول'],['score','🔥 أقوى لقطة'],['pct','٪ أعلى خصم'],['low','📉 أقل سعر في تاريخه'],['cheap','💸 الأرخص']];
const PCTS=[[0,'أي خصم'],[20,'+20%'],[40,'+40%'],[60,'+60%'],[80,'+80%']];
const BOT_URL='https://t.me/AmazonEGOffersBot';
const STORES=[['amazon','أمازون مصر','A','#ff9900',1],['amazon_now','أمازون ناو','A','#00a8e1',0],['noon','نون مصر','n','#e6c200',0],['noon_minutes','نون مينتس','n','#d4b000',0],['jumia','جوميا','J','#f68b1e',0],['talabat','طلبات مارت','t','#ff5a00',0],['breadfast','بريد فاست','B','#7b2cbf',0],['carrefour','كارفور','C','#1e5bc6',0],['btech','B.TECH','B','#e30613',0],['2b','2B','2B','#0a4ea2',0]];
const st={store:'',sort:'new',cat:'',pct:0,q:'',limit:48,seen:new Set(),first:true};
const fmt=n=>n==null?'':Number(n).toLocaleString('en-US',{maximumFractionDigits:2});
const ago=t=>{const s=(Date.now()-new Date(t))/1000;if(s<60)return'من ثواني';if(s<3600)return'من '+Math.floor(s/60)+' د';if(s<86400)return'من '+Math.floor(s/3600)+' س';return'من '+Math.floor(s/86400)+' يوم'};
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function q(path){const r=await fetch(SB+path,{headers:H});if(!r.ok)throw new Error(r.status);return r.json()}
function buildQuery(){
  let p='products?select=id,title,image,price,list_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change,in_stock&in_stock=eq.true&price=gt.0';
  if(st.store)p+='&store=eq.'+st.store;
  if(st.cat)p+='&category=eq.'+st.cat;
  if(st.pct)p+='&discount_pct=gte.'+st.pct;
  if(st.q)p+='&title=ilike.*'+encodeURIComponent(st.q.replace(/[*,()]/g,' '))+'*';
  const o={new:'last_change.desc',score:'score.desc.nullslast,last_change.desc',pct:'discount_pct.desc.nullslast',low:'low_at.desc.nullslast',cheap:'price.asc'}[st.sort];
  if(st.sort==='low')p+='&drop_pct=gt.0';
  return p+'&order='+o+'&limit='+st.limit;
}
function card(p){
  const fresh=!st.first&&!st.seen.has(p.id+p.price);st.seen.add(p.id+p.price);
  const atLow=p.low_price&&Number(p.price)<=Number(p.low_price);
  const b=[];if(p.discount_pct>0)b.push(`<span class="b pct">-${p.discount_pct}%</span>`);
  if(p.drop_pct>0)b.push(`<span class="b drop">نزل ${p.drop_pct}%</span>`);
  if(atLow&&p.drop_pct>0)b.push('<span class="b low">أقل سعر</span>');
  if(p.fake_discount)b.push('<span class="b fake">خصم مشكوك</span>');
  const sc=p.score||0;
  return `<a class="card ${fresh?'fresh':''} ${sc>=70?'s70':''}" href="#/p/${encodeURIComponent(p.id)}">
  <div class="img"><img loading="lazy" src="${esc(p.image)}" alt=""></div><div class="badges">${b.join('')}</div>
  <div class="body"><div class="title">${esc(p.title)}</div>
  <div class="price"><b>${fmt(p.price)} ج</b>${p.list_price&&+p.list_price>+p.price?`<s>${fmt(p.list_price)}</s>`:''}</div>
  <div class="power" title="قوة اللقطة"><div class="bar" style="width:${Math.max(4,sc)}%"></div></div>
  <div class="meta"><span>قوة اللقطة ${sc}</span><span>${ago(p.last_change)}</span></div></div></a>`;
}
let timer;
async function loadFeed(){
  const g=document.getElementById('grid');if(!g)return;
  try{const rows=await q(buildQuery());
    g.innerHTML=rows.length?rows.map(card).join(''):'<div class="empty">مفيش عروض بالفلتر دا دلوقتي</div>';
    st.first=false;document.getElementById('liveText').textContent='مباشر · '+new Date().toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  }catch(e){document.getElementById('liveText').textContent='بيعيد الاتصال…'}
}
async function loadStats(){
  try{const r=await fetch(SB+'products?select=id&limit=1',{headers:{...H,Prefer:'count=exact'}});
    const total=(r.headers.get('content-range')||'').split('/')[1]||'—';
    const since=new Date(Date.now()-3600e3).toISOString();
    const r2=await fetch(SB+'products?select=id&limit=1&drop_pct=gt.0&last_change=gte.'+since,{headers:{...H,Prefer:'count=exact'}});
    const drops=(r2.headers.get('content-range')||'').split('/')[1]||'0';
    document.getElementById('stats').innerHTML=`<div class="stat"><b>${Number(total).toLocaleString('en-US')}</b>منتج متراقب</div><div class="stat"><b>${drops}</b>سعر نزل آخر ساعة</div><div class="stat"><b>10</b>ثواني بين كل تحديث</div>`;
  }catch(e){}
}
function chips(id,list,key){
  const el=document.getElementById(id);
  el.innerHTML=list.map(([v,t])=>`<button class="chip ${st[key]==v?'on':''}" data-v="${v}">${t}</button>`).join('');
  el.onclick=e=>{const b=e.target.closest('.chip');if(!b)return;st[key]=key==='pct'?+b.dataset.v:b.dataset.v;st.limit=48;st.first=true;st.seen.clear();chips(id,list,key);loadFeed()};
}
function feed(){
  const app=document.getElementById('app');app.innerHTML='';app.append(document.getElementById('feedTpl').content.cloneNode(true));
  chips('sortChips',SORTS,'sort');chips('catChips',CATS,'cat');chips('pctChips',PCTS,'pct');
  const qi=document.getElementById('q');qi.value=st.q;let d;qi.oninput=()=>{clearTimeout(d);d=setTimeout(()=>{st.q=qi.value.trim();st.first=true;loadFeed()},400)};
  document.getElementById('moreBtn').onclick=()=>{st.limit+=48;loadFeed()};
  st.first=true;loadFeed();loadStats();
  clearInterval(timer);timer=setInterval(()=>{if(!document.hidden)loadFeed()},10000);
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
  const [cls,txt]=verdict(p);document.title=p.title+' — عروض متتفوتش';
  app.innerHTML=`<a class="back" href="#/deals">→ رجوع للعروض</a><div class="pp"><div class="img"><img src="${esc(p.image)}" alt=""></div><div>
  <h2 style="font-size:18px;line-height:1.6;margin:0">${esc(p.title)}</h2>
  <div class="price" style="margin-top:8px"><b style="font-size:28px">${fmt(p.price)} ج</b>${p.list_price&&+p.list_price>+p.price?`<s>${fmt(p.list_price)}</s> <span class="b pct">-${p.discount_pct}%</span>`:''}</div>
  <div class="verdict ${cls}">${txt}</div>
  <div class="kv"><div><small>أقل سعر</small><b>${fmt(p.low_price)}</b></div><div><small>أعلى سعر</small><b>${fmt(p.high_price)}</b></div><div><small>قوة اللقطة</small><b>${p.score||0}</b></div></div>
  <canvas id="cv"></canvas>
  <div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap"><a class="btn buy" href="${esc(p.url)}" target="_blank" rel="noopener sponsored">اشتري من أمازون ←</a><button class="btn" id="share">مشاركة</button></div>
  <p style="color:var(--mute);font-size:12px">آخر تغيير في السعر ${ago(p.last_change)} · بنتابعه من ${ago(p.first_seen).replace('من ','')}</p></div></div>`;
  chart(document.getElementById('cv'),hist);
  document.getElementById('share').onclick=()=>{const u=location.href;navigator.share?navigator.share({title:p.title,url:u}).catch(()=>{}):navigator.clipboard.writeText(u).then(()=>alert('اتنسخ اللينك'))};
  scrollTo(0,0);
}
function toast(t){const d=document.createElement('div');d.className='toast';d.textContent=t;document.body.append(d);setTimeout(()=>d.remove(),2500)}
function home(){
  clearInterval(timer);const app=document.getElementById('app');app.innerHTML='';app.append(document.getElementById('homeTpl').content.cloneNode(true));
  document.getElementById('botBtn').href=BOT_URL;
  document.getElementById('storeGrid').innerHTML=STORES.map(([k,n,l,col,on])=>`<a class="store ${on?'':'soon'}" href="${on?'#/deals?store='+k:'javascript:void 0'}" data-soon="${on?'':n}">${on?'<span class="tag">● مباشر</span>':''}<span class="lg" style="background:${col}">${l}</span><b>${n}</b><small>${on?'خصومات لحد 90%':'قريباً'}</small></a>`).join('');
  document.getElementById('storeGrid').onclick=e=>{const s=e.target.closest('.store');if(s&&s.dataset.soon)toast('متجر '+s.dataset.soon+' هيتضاف قريباً 🔜')};
  fetch(SB+'products?select=id&limit=1',{headers:{...H,Prefer:'count=exact'}}).then(r=>{const t=(r.headers.get('content-range')||'').split('/')[1]||'—';
    document.getElementById('landStats').innerHTML=`<div><b>${Number(t).toLocaleString('en-US')}</b><span>منتج متراقب</span></div><div><b>${STORES.length}</b><span>متجر مصري</span></div><div><b>24/7</b><span>مراقبة</span></div>`}).catch(()=>{});
  document.title='عروض متتفوتش — أفضل عروض المتاجر المصرية في مكان واحد';scrollTo(0,0);
}
function route(){const hsh=location.hash;const m=hsh.match(/^#\/p\/(.+)/);
  if(m)return product(decodeURIComponent(m[1]));
  if(hsh==='#stores'){if(!document.getElementById('storeGrid'))home();document.getElementById('stores').scrollIntoView({behavior:'smooth'});return}
  if(hsh.startsWith('#/deals')){const s=(hsh.match(/store=(\w+)/)||[])[1]||'';st.store=s;feed();const n=(STORES.find(x=>x[0]===s)||[])[1];document.getElementById('feedTitle').innerHTML=n?`عروض <span>${n}</span>`:'اللي نزل <span>دلوقتي</span> — كل المتاجر';document.title='عروض متتفوتش';scrollTo(0,0);return}
  home()}
addEventListener('hashchange',route);route();

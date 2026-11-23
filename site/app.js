const SB='https://unwzvhdwxmlmknvgvrhp.supabase.co/rest/v1/';
const KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVud3p2aGR3eG1sbWtudmd2cmhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTUwMjQ5MzUsImV4cCI6MjExMDYwMDkzNX0.g_500nSaAP5lF6N69ofsvozust1BpzbBU7kZXtooAyM';
const H={apikey:KEY,Authorization:'Bearer '+KEY};
const CATS=[['','🛍️','الكل'],['mobiles','📱','موبايلات'],['laptops','💻','لابتوب'],['tvs','📺','شاشات'],['appliances','🧺','أجهزة منزلية'],['audio','🎧','سماعات'],['smartwatches','⌚','ساعات ذكية'],['tablets','📲','تابلت'],['gaming','🎮','ألعاب فيديو'],['grocery','🛒','سوبرماركت'],['beauty','💄','جمال'],['health','🧴','صحة ونظافة'],['home','🏠','البيت والمطبخ'],['fashion','👟','موضة'],['kids','🧸','أطفال'],['sports','⚽','رياضة'],['electronics','🔌','إلكترونيات'],['computer_acc','🖱️','إكسسوارات كمبيوتر'],['mobile_acc','🔋','إكسسوارات موبايل'],['auto','🚗','عربيات'],['books_office','✏️','أدوات مكتبية'],['other','📦','أخرى']];
const RAILS=[['mobiles','📱 موبايلات بخصم'],['laptops','💻 لابتوبات'],['tvs','📺 شاشات'],['appliances','🧺 أجهزة منزلية'],['audio','🎧 سماعات'],['gaming','🎮 جيمنج'],['grocery','🛒 سوبرماركت'],['beauty','💄 جمال وعناية'],['home','🏠 البيت والمطبخ'],['fashion','👟 موضة']];
const SORTS=[['new','🆕 الأحدث'],['score','🔥 أقوى لقطة'],['pct','٪ أعلى خصم'],['drop','📉 أكبر نزول'],['low','⭐ أقل سعر في تاريخه'],['cheap','💸 الأرخص'],['exp','💎 الأغلى']];
const TYPES=[['','كل العروض'],['fresh','🆕 وصل حالاً'],['drop','📉 نزل سعره'],['lowest','⭐ أقل سعر تاريخي'],['disc','🏷 عليه خصم']];
const SINCE=[[0,'أي وقت'],[1,'آخر ساعة'],[24,'آخر 24 ساعة'],[168,'آخر أسبوع']];
const PCTS=[[0,'أي خصم'],[20,'+20%'],[40,'+40%'],[60,'+60%'],[80,'+80%']];
const PAGE=30;
let BOT_URL='https://t.me/AmazonEGOffersBot';
let SITE={},HOME=null;
const STORES=[['amazon','أمازون مصر','amazon.eg',1],['amazon_resale','أمازون مستعمل','amazon.eg',1],['amazon_now','أمازون ناو','amazon.eg',1],['carrefour','كارفور','carrefouregypt.com',1],['talabat','طلبات مارت','talabat.com',1],['btech','B.TECH','btech.com',1],['2b','2B','2b.com.eg',1],['dream2000','دريم 2000','dream2000.com',1],['dubaiphone','دبي فون','dubaiphone.net',1],['noon','نون مصر','noon.com',0],['noon_minutes','نون مينتس','noon.com',0],['jumia','جوميا','jumia.com.eg',0],['breadfast','بريد فاست','breadfast.com',0],['vodafone','فودافون','vodafone.com.eg',0],['etisalat','اتصالات','eand.com.eg',0],['orange','أورنج','orange.eg',0],['we','وي WE','te.eg',0]];
const st={type:'',since:0,store:'',sort:'new',cat:'',pct:0,q:'',offset:0,seen:new Set(),first:true,done:false};
const SEEN=new Map(); // id -> row (for instant product page)
const $=id=>document.getElementById(id);
const fmt=n=>n==null?'':Number(n).toLocaleString('en-US',{maximumFractionDigits:0});
const ago=t=>{const s=(Date.now()-new Date(t))/1000;if(s<60)return'دلوقتي';if(s<3600)return'من '+Math.floor(s/60)+' د';if(s<86400)return'من '+Math.floor(s/3600)+' س';return'من '+Math.floor(s/86400)+' يوم'};
const thumb=u=>u&&/media-amazon\.com/.test(u)?u.replace(/\._[^/]*_\.(jpg|jpeg|png|webp)$/i,'.$1').replace(/\.(jpg|jpeg|png|webp)$/i,'._AC_UL320_.$1'):u;
const big=u=>u&&/media-amazon\.com/.test(u)?u.replace(/\._[^/]*_\.(jpg|jpeg|png|webp)$/i,'.$1').replace(/\.(jpg|jpeg|png|webp)$/i,'._AC_SL800_.$1'):u;
const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ls={get(k){try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
async function q(path){const r=await fetch(SB+path,{headers:H});if(!r.ok)throw new Error(r.status);return r.json()}
async function cdn(path,signal){const r=await fetch('/api/feed?p='+encodeURIComponent(path),{signal});if(!r.ok)throw new Error(r.status);return r.json()}

/* ---------- stores ---------- */
function allStores(){const o=SITE.stores||{};const extra=Object.keys(o).filter(k=>!STORES.some(s=>s[0]===k)).map(k=>[k,o[k].name||k,o[k].domain||'',o[k].on?1:0]);return STORES.concat(extra)}
function storeLogo(k,dom,sz){const c=(SITE.stores||{})[k];return c&&c.logo?c.logo:`https://www.google.com/s2/favicons?domain=${dom}&sz=${sz||128}`}
function visibleStores(){const o=SITE.stores||{};return allStores().filter(x=>!(o[x[0]]&&o[x[0]].hidden)).map(x=>{const c=o[x[0]];return c?[x[0],c.name||x[1],x[2],c.on===undefined?x[3]:(c.on?1:0)]:x}).sort((a,b)=>b[3]-a[3])}
function storeName(k){const o=(SITE.stores||{})[k];return (o&&o.name)||(allStores().find(x=>x[0]===k)||[,'المتجر'])[1]}
function storeTag(k){const s=allStores().find(x=>x[0]===k);return s?`<span class="store-name"><img src="${storeLogo(k,s[2],32)}" alt="" loading="lazy" width="16" height="16">${esc(storeName(k))}</span>`:''}
function visibleCats(){const h=SITE.hidden_cats||[];return CATS.filter(c=>!h.includes(c[0]))}

/* ---------- card ---------- */
function card(p,live){
  SEEN.set(p.id,p);
  const fresh=live&&!st.first&&!st.seen.has(p.id+p.price);if(live)st.seen.add(p.id+p.price);
  const lp=+p.list_price,pr=+p.price,prev=+p.prev_price;
  const was=lp>pr?lp:(p.drop_pct>0&&prev>pr?prev:0);
  const pct=p.discount_pct>0?p.discount_pct:(was?Math.round((1-pr/was)*100):0);
  const atLow=p.low_price&&pr<=+p.low_price&&p.drop_pct>0;
  const sc=p.score||0;
  return `<a class="card${fresh?' fresh':''}" href="#/p/${encodeURIComponent(p.id)}">
  <div class="img">${p.image?`<img loading="lazy" decoding="async" src="${esc(thumb(p.image))}" alt="" onload="this.classList.add('ok')" onerror="this.outerHTML='<span class=noimg>📦</span>'">`:'<span class="noimg">📦</span>'}
  ${pct>0?`<span class="off">-${pct}%</span>`:''}${p.fake_discount?'<span class="fakeb">⚠️ خصم مشكوك</span>':atLow?'<span class="lowb">⭐ أقل سعر</span>':''}${p.drop_pct>0?`<span class="dropb">↓ نزل ${p.drop_pct}%</span>`:''}${p.first_seen&&Date.now()-new Date(p.first_seen)<864e5?`<span class="newb">🆕 ${ago(p.first_seen)}</span>`:''}</div>
  <div class="body"><div class="title">${esc(p.title)}</div>
  <div class="price"><b>${fmt(pr)} <small>ج.م</small></b>${was?`<s>${fmt(was)}</s>`:''}</div>
  ${was&&was-pr>=1?`<div class="save">وفّر ${fmt(was-pr)} ج</div>`:''}
  <div class="hotbar" title="قوة اللقطة ${sc}"><i style="width:${Math.max(4,sc)}%"></i></div>
  <div class="cfoot">${storeTag(p.store)}<span title="آخر تحديث للسعر">🕒 ${ago(p.last_change)}</span></div></div></a>`;
}
const skel=n=>Array.from({length:n},()=>'<div class="sk"></div>').join('');

const stale=k=>{const t=HOME&&HOME.lastseen&&HOME.lastseen[k];return t&&Date.now()-new Date(t)>6*3600e3?t:null};
/* ---------- home ---------- */
async function getHome(){
  const r=await fetch('/api/home');if(!r.ok)throw 0;const h=await r.json();if(!h||!h.hot)throw 0;
  HOME=h;if(h.config)Object.assign(SITE,h.config);
  try{const rows=await q('site_config?select=key,value');rows.forEach(r=>{SITE[r.key]=r.value;h.config=h.config||{};h.config[r.key]=r.value})}catch(e){}
  ls.set('home_v2',h);return h;
}
function home(){setNav('home');document.body.classList.remove('pp-open');clearInterval(timer);
  const app=$('app');const s=SITE;
  app.innerHTML=`<section class="hero2"><span class="pill" id="landPill">${s.hero_pill||'⚡ بنتابع الأسعار 24 ساعة'}</span>
  <h1 id="landTitle">${s.hero_title||'أقوى العروض في مصر… <span>من غير ما تدوّر</span> 🔥'}</h1>
  <p id="landText">${s.hero_text||'بنراقب أسعار <b>آلاف المنتجات</b> في <b>أهم المتاجر المصرية</b> لحظة بلحظة، ونكشفلك الخصم الحقيقي من الوهمي بتاريخ السعر كامل.'}</p>
  <div class="nums" id="landStats"></div></section>
  <section class="storebox" id="stores"><div class="sec-h"><div><h2>🏪 تسوّق حسب المتجر</h2><p>اختار متجرك وشوف كل عروضه</p></div><a href="#/deals">كل المتاجر ←</a></div><div class="stores" id="storeGrid"></div></section>
  <nav class="quick">
   <a class="main" href="#/deals"><i>⚡</i>أحدث المنتجات</a>
   <a href="#/collections"><i>🔥</i>عروض نوفمبر</a>
   <a href="#stores"><i>🏪</i>اختار المتجر</a>
   <a href="#/deals?type=drop"><i>📉</i>نزل سعره دلوقتي</a>
   <a href="#/coupons"><i>🎟</i>الكوبونات</a>
   <a class="botLink" target="_blank" rel="noopener"><i>🤖</i>بوت تتبع الأسعار</a>
   <a href="https://t.me/offer_egypt" data-chan target="_blank" rel="noopener"><i>📢</i>قناة التليجرام</a>
   <a href="#" id="searchBtn"><i>🔍</i>ابحث عن منتج</a>
  </nav>
  <section class="sec"><div class="cats" id="homeCats"></div></section>
  <section class="sec" id="featSec" hidden><div class="sec-h"><h2 id="featTitle">${esc(s.featured_title||'⭐ اخترنالك')}</h2></div><div class="rail" id="featRail"></div></section>
  <section class="sec"><div class="sec-h"><div><h2>🔥 أقوى لقطات النهارده</h2><p>أعلى عروض في قوة اللقطة آخر 24 ساعة</p></div><a href="#/deals?sort=score">شوف الكل ←</a></div><div class="rail" id="hotRail">${skel(6)}</div></section>
  <section class="sec"><div class="sec-h"><div><h2>🆕 وصل حالاً</h2><p>منتجات لسه متضافة على المنصة من كل المتاجر — بتتحدث لوحدها</p></div><a href="#/deals?type=fresh">شوف الكل ←</a></div><div class="rail" id="freshRail">${skel(6)}</div></section>
  <section class="sec"><div class="sec-h"><div><h2>📉 نزل سعره دلوقتي</h2><p>سعرها نزل بجد عن آخر سعر سجلناه</p></div><a href="#/deals?type=drop">شوف الكل ←</a></div><div class="rail" id="dropRail">${skel(6)}</div></section>
  <section class="sec" id="rvSec" hidden><div class="sec-h"><div><h2>👀 كمّل من حيث وقفت</h2><p>المنتجات اللي اتفرجت عليها</p></div><a href="javascript:void 0" id="rvClr">امسح</a></div><div class="rail" id="rvRail"></div></section>
  <section class="sec" id="cpSec" hidden><div class="sec-h"><div><h2>🎟 كوبونات الخصم</h2><p>دوس على الكود وهيتنسخ</p></div><a href="#/coupons">كل الكوبونات ←</a></div><div class="cprail" id="cpRail"></div></section>
  <a class="tgban" href="https://t.me/offer_egypt" data-chan target="_blank" rel="noopener"><span>📢</span><div><b>انضم لقناة التليجرام — أهم حاجة!</b><small>أقوى اللقطات بتوصلك أول بأول قبل ما تخلص</small></div><i>انضم ←</i></a>
  <div id="rails"></div>
  <section class="sec how"><div class="sec-h"><h2>إزاي بنشتغل؟</h2></div><div class="steps"><div><i>1</i><b>بنراقب الأسعار</b><span>بنمر على كل المتاجر كل دقايق ونسجّل سعر كل منتج.</span></div><div><i>2</i><b>بنفلتر الخصم الوهمي</b><span>لو السعر اترفع قبل الخصم بنعلّم عليه "مشكوك".</span></div><div><i>3</i><b>بنعرّفك فوراً</b><span>على الموقع والقناة والبوت، ومعاه تاريخ السعر كامل.</span></div></div></section>
  <section class="trust"><div><b>📉 كشف الخصم الوهمي</b><span>بنقارن السعر بتاريخه ونقولك لو الخصم حقيقي ولا متضخم.</span></div><div><b>⚡ تحديث لحظي</b><span>العروض بتتحدث قدامك من غير ما تعمل ريفريش.</span></div><div><b>🔔 تنبيه بالسعر</b><span>تابع أي منتج من أمازون على البوت ونبعتلك أول ما ينزل.</span></div></section>`;
  applySite();
  $('homeCats').innerHTML=visibleCats().slice(1).map(([k,i,n])=>`<a class="cat" href="#/deals?cat=${k}">${i} ${n}</a>`).join('');
  $('storeGrid').onclick=e=>{const a=e.target.closest('.store');if(a&&a.dataset.soon){e.preventDefault();toast('متجر '+a.dataset.soon+' هيتضاف قريباً 🔜')}};
  const cached=HOME||ls.get('home_v2');if(cached)drawHome(cached);
  const fresh=()=>cdn(freshQuery(0,20).replace(/&store=[^&]*|&category=[^&]*|&discount_pct=[^&]*/g,'')).then(r=>{const el=$('freshRail');if(el&&r.length)el.innerHTML=r.map(p=>card(p)).join('')}).catch(()=>{});
  const refresh=()=>{getHome().then(drawHome).catch(()=>{});fresh()};refresh();
  timer=setInterval(()=>{if(!document.hidden)refresh()},30000);
  document.title='عروض متتفوتش — أفضل عروض المتاجر المصرية في مكان واحد';
}
function drawHome(h){
  {const el=$('freshRail');if(el&&h&&h.fresh&&h.fresh.length&&el.querySelector('.sk'))el.innerHTML=h.fresh.map(p=>card(p)).join('')}
  if(!$('hotRail'))return;const c=h.counts||{},ac=h.all_counts||{};
  $('storeGrid').innerHTML=visibleStores().map(([k,n,dom,on])=>`<a class="store ${on?'':'soon'}" href="${on?'#/deals?store='+k:'#'}" data-soon="${on?'':esc(n)}">${on?'<span class="tag"></span>':''}<span class="lg"><img src="${storeLogo(k,dom)}" alt="" loading="lazy" onerror="this.replaceWith(document.createTextNode('${esc(n[0])}'))"></span><b>${esc(n)}</b><small>${on?(ac[k]?fmt(ac[k])+' منتج':'مباشر'):'قريباً'}</small>${on&&c[k]?`<em class="dealsn">🔥 ${fmt(c[k])} عرض</em>`:''}${on&&stale(k)?`<em class="paused">⏸ آخر تحديث ${ago(stale(k))}</em>`:on&&(h.maxdisc||{})[k]?`<em class="upto">خصم لحد ${h.maxdisc[k]}%</em>`:''}</a>`).join('');
  $('landStats').innerHTML=`<div><b>${fmt(h.all_total||h.total)}</b><span>منتج بنتابعه</span></div><div><b>${fmt(h.total)}</b><span>عرض شغال</span></div><div><b>${visibleStores().filter(x=>x[3]).length}</b><span>متجر مصري</span></div><div><b>${fmt(h.drops_24h)}</b><span>سعر نزل النهارده</span></div>`;
  const rail=(el,rows)=>{const e=$(el);if(e)e.innerHTML=rows.length?rows.map(p=>card(p)).join(''):'<div class="empty">لسه مفيش</div>'};
  rail('hotRail',h.hot||[]);rail('dropRail',h.drops||[]);
  const f=h.featured||[];$('featSec').hidden=!f.length;if(f.length)rail('featRail',f);
  const rv=ls.get('rv')||[];$('rvSec').hidden=!rv.length;if(rv.length)rail('rvRail',rv);
  $('rvClr').onclick=()=>{ls.set('rv',[]);$('rvSec').hidden=true};
  const cd=h.codes||[];$('cpSec').hidden=!cd.length;
  $('cpRail').innerHTML=cd.map(r=>`<button class="cpmini" data-code="${esc(r.code)}">${storeTag(r.store)}<b>${esc(r.code)}</b><small>${esc(r.discount||r.title||'')}</small><em>📋 انسخ</em></button>`).join('');
  $('cpRail').onclick=e=>{const b=e.target.closest('.cpmini');if(b)navigator.clipboard.writeText(b.dataset.code).then(()=>toast('اتنسخ الكود '+b.dataset.code+' ✅'))};
  applySite();
  const hid=SITE.hidden_cats||[];
  $('rails').innerHTML=RAILS.filter(([k])=>!hid.includes(k)&&(h.rails||{})[k]&&h.rails[k].length>=4).map(([k,t])=>`<section class="sec"><div class="sec-h"><h2>${t}</h2><a href="#/deals?cat=${k}">شوف الكل ←</a></div><div class="rail">${h.rails[k].map(p=>card(p)).join('')}</div></section>`).join('');
}

/* ---------- feed ---------- */
function freshQuery(off,limit){
  let q='products?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change,first_seen&hidden=is.false&in_stock=is.true&image=not.is.null';
  if(st.store)q+='&store=eq.'+st.store;else if(st.stores&&st.stores.length)q+='&store=in.('+st.stores.join(',')+')';
  if(st.cat)q+='&category=eq.'+st.cat;
  if(st.pct)q+='&discount_pct=gte.'+st.pct;
  return q+'&order=first_seen.desc&limit='+(limit||PAGE)+'&offset='+(off||0);
}
function buildQuery(off){
  if(st.type==='fresh'&&!st.q)return freshQuery(off);
  if(st.q){ // البحث بيدوّر في كل المنتجات، وكل كلمة لوحدها (مش الجملة لازقة)
    const words=st.q.replace(/[*,()%.]/g,' ').split(/\s+/).filter(w=>w.length>0).slice(0,6);
    let q='products?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change&hidden=is.false&in_stock=is.true';
    // كل كلمة بنبحث بيها بالعربي والإنجليزي (سامسونج = samsung)
    const SYN=[['samsung','سامسونج','سامسونغ'],['apple','ابل','أبل'],['iphone','ايفون','آيفون'],['ultra','الترا','ألترا'],['pro','برو'],['max','ماكس'],['plus','بلس'],['galaxy','جالاكسي','جالكسي','غالاكسي'],['xiaomi','شاومي'],['redmi','ريدمي'],['oppo','اوبو','أوبو'],['realme','ريلمي'],['honor','هونر','اونر'],['huawei','هواوي'],['infinix','انفينكس'],['tecno','تكنو'],['vivo','فيفو'],['nokia','نوكيا'],['lenovo','لينوفو'],['hp','اتش بي'],['dell','ديل'],['asus','اسوس','أسوس'],['acer','ايسر'],['sony','سوني'],['lg','ال جي'],['laptop','لابتوب'],['tablet','تابلت'],['airpods','ايربودز'],['watch','ساعة'],['tv','شاشة','تلفزيون'],['charger','شاحن'],['cable','كابل'],['case','جراب'],['headphones','سماعة'],['playstation','بلايستيشن'],['ps5','بلايستيشن 5'],['mobile','موبايل'],['phone','موبايل','هاتف']];
    const alts=w=>{const l=w.toLowerCase();const g=SYN.find(s=>s.includes(l));return g?g:[w]};
    const cond=w=>{const v=alts(w);return v.length===1?'title.ilike.*'+encodeURIComponent(v[0])+'*':'or('+v.map(x=>'title.ilike.*'+encodeURIComponent(x)+'*').join(',')+')'};
    q+='&and=('+words.map(cond).join(',')+')';
    if(st.store)q+='&store=eq.'+st.store;else if(st.stores&&st.stores.length)q+='&store=in.('+st.stores.join(',')+')';
    if(st.cat)q+='&category=eq.'+st.cat;
    if(st.type==='drop')q+='&drop_pct=gt.0';else if(st.type==='disc')q+='&discount_pct=gt.0';
    if(st.pct)q+='&discount_pct=gte.'+st.pct;
    const so={cheap:'price.asc',exp:'price.desc',new:'last_change.desc',drop:'drop_pct.desc.nullslast'}[st.sort]||'discount_pct.desc.nullslast,last_change.desc';
    return q+'&order='+so+'&limit='+PAGE+'&offset='+off;
  }
  if(st.all&&st.store){ // كل منتجات المتجر (مش العروض بس)
    let q='products?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change&store=eq.'+st.store+'&hidden=is.false&in_stock=is.true';
    if(st.cat)q+='&category=eq.'+st.cat;
    if(st.q)q+='&title=ilike.*'+encodeURIComponent(st.q.replace(/[*,()]/g,' '))+'*';
    const ao={cheap:'price.asc',exp:'price.desc',pct:'discount_pct.desc.nullslast,last_change.desc'}[st.sort]||'last_change.desc';
    return q+'&order='+ao+'&limit='+PAGE+'&offset='+off;
  }
  let p='deals_feed?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change';
  if(st.store)p+='&store=eq.'+st.store;
  else if(st.stores&&st.stores.length)p+='&store=in.('+st.stores.join(',')+')';
  const minD=SITE.min_discount!=null&&SITE.min_discount!==''?+SITE.min_discount:10;
  if(st.type==='drop')p+='&drop_pct=gt.0';
  else if(st.type==='disc')p+='&discount_pct=gt.0';
  else if(st.type==='lowest')p+='&drop_pct=gt.0&low_at=not.is.null';
  else if(!st.q&&minD>0&&!st.pct)p+=`&or=(discount_pct.gte.${minD},drop_pct.gt.0)`;
  if(st.since)p+='&last_change=gte.'+new Date(Math.floor((Date.now()-st.since*3600e3)/60000)*60000).toISOString();
  if(st.cat)p+='&category=eq.'+st.cat;
  if(st.pct)p+='&discount_pct=gte.'+st.pct;
  if(st.q)p+='&title=ilike.*'+encodeURIComponent(st.q.replace(/[*,()]/g,' '))+'*';
  const o={new:'last_change.desc',score:'score.desc.nullslast,last_change.desc',pct:'discount_pct.desc.nullslast',low:'low_at.desc.nullslast',cheap:'price.asc',exp:'price.desc',drop:'drop_pct.desc.nullslast,last_change.desc'}[st.sort]||'last_change.desc';
  if((st.sort==='drop'||st.sort==='low')&&!st.type)p+='&drop_pct=gt.0';
  return p+'&order='+o+'&limit='+PAGE+'&offset='+off;
}
let timer,feedCtl,io;
async function loadPage(reset){
  const g=$('grid');if(!g)return;
  if(reset){st.offset=0;st.done=false;g.innerHTML=skel(12);}
  if(st.done)return;
  if(feedCtl&&reset)feedCtl.abort();const ctl=feedCtl=new AbortController();
  const off=st.offset;st.loading=true;$('sent').textContent='بنحمّل…';
  try{const rows=await cdn(buildQuery(off),ctl.signal);if(ctl!==feedCtl&&reset)return;
    if(off===0)g.innerHTML='';
    g.insertAdjacentHTML('beforeend',rows.map(p=>card(p,1)).join(''));
    st.offset=off+rows.length;st.done=rows.length<PAGE;st.first=false;
    if(off===0&&rows.length<6&&st.store&&!st.all&&!st.q&&!st.type){st.all=true;st.autoAll=true;st.done=false;feedCtl=null;return loadPage(true);}
    if(off===0&&st.autoAll&&rows.length)g.insertAdjacentHTML('afterbegin','<div class="notice" style="grid-column:1/-1">المتجر ده مفيهوش عروض كتير دلوقتي، فبنعرضلك كل منتجاته بأسعارها الحالية 👇</div>');
    if(off===0&&!rows.length)g.innerHTML='<div class="empty">'+(st.q?'مفيش منتج بالاسم دا — جرّب كلمة أقصر':'مفيش عروض بالفلتر دا دلوقتي')+' 🤷‍♂️<br><br><button class="chip" onclick="location.hash=\'#/deals\'">امسح الفلاتر</button></div>';
    $('sent').textContent=st.done?(st.offset?'✅ ده كل اللي موجود':''):'';
  }catch(e){if(e.name!=='AbortError')$('sent').textContent='حصلت مشكلة — اسحب لتحت تاني'}
  finally{st.loading=false}
}
async function liveTop(){ // refresh first page silently, prepend new items
  if(document.hidden||!$('grid')||st.loading)return;
  try{const rows=await cdn(buildQuery(0));const g=$('grid');
    const fresh=rows.filter(p=>!st.seen.has(p.id+p.price));if(!fresh.length||st.sort!=='new')return;
    fresh.forEach(p=>{const old=g.querySelector(`a[href="#/p/${CSS.escape(encodeURIComponent(p.id))}"]`);if(old)old.remove()});
    g.insertAdjacentHTML('afterbegin',fresh.map(p=>card(p,1)).join(''));st.offset+=fresh.length;
  }catch(e){}
}
function activeFilters(){return (st.cat?1:0)+(st.pct?1:0)+(st.since?1:0)+((st.stores||[]).length?1:0)}
function feed(){setNav(st.type==='drop'?'drop':'deals');document.body.classList.remove('pp-open');clearInterval(timer);
  const app=$('app');const sn=st.store?storeName(st.store):'';const cn=st.cat?(CATS.find(c=>c[0]===st.cat)||[])[2]:'';
  const title=st.q?`نتايج «<span>${esc(st.q)}</span>»`:st.type==='fresh'?'🆕 <span>وصل حالاً</span> — أحدث المنتجات':st.type==='drop'?'📉 <span>نزل سعره</span> دلوقتي':sn?`عروض <span>${esc(sn)}</span>`:cn?`عروض <span>${esc(cn)}</span>`:'أحدث <span>العروض</span>';
  const cnt=st.store&&HOME&&HOME.counts?HOME.counts[st.store]:HOME&&HOME.total;const cntAll=st.store&&HOME&&HOME.all_counts?HOME.all_counts[st.store]:HOME&&HOME.all_total;
  app.innerHTML=`<div class="fhead"><h1>${title}</h1><p>${cntAll?fmt(cntAll)+' منتج بنتابعه · ':''}${cnt?fmt(cnt)+' منهم عليه عرض · ':''}بيتحدث لحظياً ⚡</p></div>
  <div class="bar"><div class="chips" id="typeChips"></div>
  <div class="row2"><select id="sortSel">${SORTS.map(([v,t])=>`<option value="${v}" ${st.sort===v?'selected':''}>${t}</option>`).join('')}</select>
  <button class="chip flt" id="fltBtn">⚙️ فلترة${activeFilters()?`<b>${activeFilters()}</b>`:''}</button>${st.store?`<button class="chip" id="clrStore">✕ ${esc(sn)}</button>`:''}</div></div>
  ${st.store&&stale(st.store)?`<div class="notice">⏸ أسعار ${esc(sn)} متحدثة آخر مرة ${ago(stale(st.store))} — بنحدّثها على فترات، فاتأكد من السعر في المتجر قبل ما تشتري.</div>`:''}<section class="grid" id="grid"></section><div class="sentinel" id="sent"></div>`;
  $('typeChips').innerHTML=TYPES.map(([v,t])=>`<button class="chip ${st.type===v?'on':''}" data-v="${v}">${t}</button>`).join('');
  $('typeChips').onclick=e=>{const b=e.target.closest('.chip');if(!b)return;st.type=b.dataset.v;rerender()};
  $('sortSel').onchange=e=>{st.sort=e.target.value;loadPage(true)};
  $('fltBtn').onclick=openSheet;
  if($('clrStore'))$('clrStore').onclick=()=>{st.store='';rerender()};
  st.first=true;st.seen.clear();loadPage(true);
  if(io)io.disconnect();io=new IntersectionObserver(es=>{if(es[0].isIntersecting&&!st.loading&&!st.done&&st.offset)loadPage(false)},{rootMargin:'900px'});io.observe($('sent'));
  timer=setInterval(liveTop,15000);
}
function rerender(){st.all=false;st.autoAll=false;const y=scrollY;feed();scrollTo(0,Math.min(y,140))}
function openSheet(){
  let bg=$('sheetBg');if(!bg){document.body.insertAdjacentHTML('beforeend','<div class="sheet-bg" id="sheetBg"></div><div class="sheet" id="sheet"></div>');bg=$('sheetBg')}
  const sh=$('sheet');const tmp={cat:st.cat,pct:st.pct,since:st.since,stores:[...(st.stores||[])]};
  const draw=()=>{sh.innerHTML=`${st.store?'':`<h3>المتاجر <small class="mute">(اختار متجر أو أكتر — من غير اختيار = كل المتاجر)</small></h3><div class="chips" data-k="stores">${visibleStores().filter(x=>x[3]).map(([k,n])=>`<button class="chip ${tmp.stores.includes(k)?'on':''}" data-v="${k}">${esc(n)}</button>`).join('')}</div>`}<h3>القسم</h3><div class="chips" data-k="cat">${visibleCats().map(([v,i,t])=>`<button class="chip ${tmp.cat===v?'on':''}" data-v="${v}">${i} ${t}</button>`).join('')}</div>
  <h3>نسبة الخصم</h3><div class="chips" data-k="pct">${PCTS.map(([v,t])=>`<button class="chip ${tmp.pct==v?'on':''}" data-v="${v}">${t}</button>`).join('')}</div>
  <h3>اتحدث في</h3><div class="chips" data-k="since">${SINCE.map(([v,t])=>`<button class="chip ${tmp.since==v?'on':''}" data-v="${v}">${t}</button>`).join('')}</div>
  <button class="go" id="goF">عرض النتايج</button>`};
  draw();sh.onclick=e=>{const b=e.target.closest('.chip');if(b){const k=b.parentElement.dataset.k;if(k==='stores'){const v=b.dataset.v;tmp.stores=tmp.stores.includes(v)?tmp.stores.filter(x=>x!==v):[...tmp.stores,v]}else tmp[k]=k==='cat'?b.dataset.v:+b.dataset.v;draw()}if(e.target.id==='goF'){Object.assign(st,tmp);close();rerender()}};
  const close=()=>{bg.classList.remove('on');sh.classList.remove('on')};bg.onclick=close;
  requestAnimationFrame(()=>{bg.classList.add('on');sh.classList.add('on')});
}

/* ---------- product ---------- */
function verdict(p){
  const pr=+p.price,low=+p.low_price,hi=+p.high_price;
  if(p.fake_discount)return['v-bad','⚠️ الخصم دا مشكوك فيه — السعر كان أقل من كدا قبل كدا.'];
  if(low&&pr<=low&&hi>pr)return['v-good','✅ دا أقل سعر سجلناه للمنتج — لقطة حقيقية.'];
  if(low&&pr<=low*1.05)return['v-good','✅ السعر قريب جداً من أقل سعر سجلناه.'];
  return['v-ok','ℹ️ سعر عادي — ممكن يستاهل تستنى نزول.'];
}
function chart(cv,pts){
  const dpr=devicePixelRatio||1,w=cv.clientWidth,h=cv.clientHeight;cv.width=w*dpr;cv.height=h*dpr;const c=cv.getContext('2d');c.scale(dpr,dpr);
  if(pts.length<2){c.fillStyle='#6b7280';c.font='600 13px Cairo';c.textAlign='center';c.fillText('لسه بنجمع تاريخ السعر للمنتج دا',w/2,h/2+4);return}
  const xs=pts.map(p=>+new Date(p.at)),ys=pts.map(p=>+p.price);const x0=Math.min(...xs),x1=Math.max(...xs,Date.now()),y0=Math.min(...ys)*.97,y1=Math.max(...ys)*1.03;
  const X=t=>16+(w-32)*(t-x0)/((x1-x0)||1),Y=v=>h-24-(h-44)*(v-y0)/((y1-y0)||1);
  const path=()=>{c.beginPath();pts.forEach((p,i)=>{const x=X(+new Date(p.at)),y=Y(+p.price);if(i){c.lineTo(x,Y(+pts[i-1].price));c.lineTo(x,y)}else c.moveTo(x,y)});c.lineTo(w-16,Y(ys[ys.length-1]))};
  path();c.lineTo(w-16,h-20);c.lineTo(X(xs[0]),h-20);c.closePath();const g=c.createLinearGradient(0,0,0,h);g.addColorStop(0,'#ff5a1f33');g.addColorStop(1,'#ff5a1f00');c.fillStyle=g;c.fill();
  path();c.strokeStyle='#ff5a1f';c.lineWidth=2.5;c.stroke();
  c.fillStyle='#6b7280';c.font='600 11px Cairo';c.textAlign='left';c.fillText(fmt(Math.max(...ys))+' ج',8,14);c.fillText(fmt(Math.min(...ys))+' ج',8,h-6);
}
function ppHTML(p,full){
  const lp=+p.list_price,pr=+p.price;const [cls,txt]=full?(full.hist<2&&!p.fake_discount?['v-ok','🆕 لسه بادئين نتابع سعر المنتج دا — هنقولك أول ما يتغير.']:verdict(p)):['v-ok','… بنحلل السعر'];
  return `<a class="back" href="javascript:history.length>1?history.back():location.hash='#/deals'">→ رجوع</a><div class="pp"><div class="pimg"><img src="${esc(big(p.image))}" alt="">${p.discount_pct>0?`<span class="off">-${p.discount_pct}%</span>`:''}</div><div>
  ${storeTag(p.store)}<h1>${esc(p.title)}</h1>
  <div class="price"><b>${fmt(pr)} <small>ج.م</small></b>${lp>pr?`<s>${fmt(lp)}</s> <span class="save">وفّر ${fmt(lp-pr)} ج</span>`:''}</div>
  <div class="verdict ${cls}">${txt}</div>${stale(p.store)?`<div class="notice">⏸ السعر ده من آخر تحديث لينا ${ago(stale(p.store))} — اتأكد منه في ${esc(storeName(p.store))}.</div>`:''}
  <div class="kv"><div><small>أقل سعر</small><b>${fmt(p.low_price)||'—'}</b></div><div><small>أعلى سعر</small><b>${fmt(p.high_price)||'—'}</b></div><div><small>قوة اللقطة</small><b>${p.score||0}</b></div></div>
  <h3 class="hist-h">📈 تاريخ السعر</h3><canvas id="cv"></canvas>
  ${/^amazon/.test(p.store)?`<a class="btn trackbtn" href="${BOT_URL}?start=t_${esc(p.pid||String(p.id).split(':')[1])}" target="_blank" rel="noopener">🔔 تابع سعر المنتج ده على البوت — ونبهك أول ما ينزل</a>`:''}
  ${full?`<p class="since">آخر تغيير في السعر ${ago(p.last_change)} · بنتابعه ${ago(p.first_seen)}</p>`:''}
  <div class="buybar"><a class="btn buy" id="buyBtn" href="${p.url?esc(affLink(p.url)):'#'}" data-ready="${p.url?1:0}" target="_blank" rel="noopener sponsored">🛒 اشتري من ${esc(storeName(p.store))} <small>${fmt(pr)} ج</small></a><button class="btn share" id="share">🔗 مشاركة</button></div></div></div>
  <section class="sec" id="simSec" hidden><div class="sec-h"><h2>عروض شبهه</h2></div><div class="rail" id="simRail"></div></section>`;
}
async function product(id){
  setNav('');clearInterval(timer);document.body.classList.add('pp-open');const app=$('app');scrollTo(0,0);
  const pre=SEEN.get(id);app.innerHTML=pre?ppHTML(pre,null):'<div class="sk" style="height:520px;margin-top:20px"></div>';
  if(pre)chart($('cv'),[]);
  let p,hist=[];
  try{[[p],hist]=await Promise.all([q('products?id=eq.'+encodeURIComponent(id)+'&select=*'),q('price_history?product_id=eq.'+encodeURIComponent(id)+'&select=price,at&order=at.asc&limit=500')])}catch(e){}
  if(!location.hash.includes(encodeURIComponent(id))&&!location.hash.includes(id))return;
  if(!p){app.innerHTML='<div class="empty">المنتج مش موجود أو اتشال 🤷‍♂️<br><br><a class="chip" href="#/deals">شوف العروض</a></div>';return}
  app.innerHTML=ppHTML(p,{hist:hist.length});$('cv').classList.toggle('small',hist.length<2);chart($('cv'),hist);
  document.title=p.title+' — عروض متتفوتش';
  {const row=SEEN.get(id)||{id:p.id,store:p.store,title:p.title,image:p.image,price:p.price,list_price:p.list_price,discount_pct:p.discount_pct,drop_pct:p.drop_pct,score:p.score,last_change:p.last_change};const rv=(ls.get('rv')||[]).filter(x=>x.id!==id);rv.unshift(row);ls.set('rv',rv.slice(0,15))}
  const bb=$('buyBtn');if(bb)bb.onclick=e=>{e.preventDefault();if(bb.dataset.ready!=='1')return;const w=window.open(bb.href,'_blank');if(w){try{w.opener=null}catch(_){}}else location.href=bb.href};
  $('share').onclick=()=>{const u=location.href;navigator.share?navigator.share({title:p.title,url:u}).catch(()=>{}):navigator.clipboard.writeText(u).then(()=>toast('اتنسخ اللينك ✅'))};
  if(p.category)cdn(`deals_feed?select=id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change&category=eq.${p.category}&discount_pct=gte.15&order=score.desc.nullslast&limit=12`).then(r=>{r=r.filter(x=>x.id!==p.id);if(r.length&&$('simRail')){$('simSec').hidden=false;$('simRail').innerHTML=r.map(x=>card(x)).join('')}}).catch(()=>{});
}

/* ---------- coupons ---------- */
async function coupons(){
  setNav('coupons');clearInterval(timer);document.body.classList.remove('pp-open');const app=$('app');
  app.innerHTML=`<div class="fhead"><h1>🎟 <span>الكوبونات</span></h1><p>اضغط على أي كود وهيتنسخ على طول.</p></div><div class="bar"><div class="chips" id="cpStores"></div></div><div id="cpList"><section class="grid">${skel(6)}</section></div>`;
  let rows=[];try{rows=await q('coupons?select=*&order=source.desc,last_seen.desc&limit=400')}catch(e){}
  const stores=[...new Set(rows.map(r=>r.store))];let cur='';
  const draw=()=>{const list=rows.filter(r=>!cur||r.store===cur);
    $('cpStores').innerHTML=[['','الكل'],...stores.map(s=>[s,storeName(s)])].map(([k,n])=>`<button class="chip ${k===cur?'on':''}" data-s="${k}">${esc(n)}</button>`).join('');
    const codes=list.filter(r=>r.code),clip=list.filter(r=>!r.code);
    $('cpList').innerHTML=(codes.length?`<div class="cp-codes">${codes.map(r=>`<div class="cp"><div class="cp-h">${storeTag(r.store)||esc(storeName(r.store))}${r.discount?`<span class="b pct">${esc(r.discount)}</span>`:''}</div>${r.title?`<p>${esc(r.title)}</p>`:''}<button class="cp-code" data-code="${esc(r.code)}">${esc(r.code)} <small>📋 نسخ</small></button>${r.url?`<a class="cp-go" href="${esc(affLink(r.url))}" target="_blank" rel="noopener">روح للمتجر ←</a>`:''}${r.expires_at?`<small class="mute">ينتهي ${new Date(r.expires_at).toLocaleDateString('ar-EG')}</small>`:''}</div>`).join('')}</div>`:'')+
    (clip.length?`<div class="sec-h" style="margin-top:24px"><div><h2>✂️ منتجات عليها كوبون خصم</h2><p>الكوبون بيتفعّل من صفحة المنتج نفسها بدوسة.</p></div></div><section class="grid">${clip.map(r=>`<a class="card" href="${r.product_id?'#/p/'+encodeURIComponent(r.product_id):esc(affLink(r.url))}"><div class="img"><img loading="lazy" src="${esc(thumb(r.image))}" alt="" onload="this.classList.add('ok')"><span class="off">✂️ ${esc(r.discount)}</span></div><div class="body"><div class="title">${esc(r.title)}</div><div class="cfoot">${storeTag(r.store)}</div></div></a>`).join('')}</section>`:'')||'<div class="empty">مفيش كوبونات دلوقتي</div>'};
  draw();$('cpStores').onclick=e=>{const b=e.target.closest('.chip');if(b){cur=b.dataset.s;draw()}};
  $('cpList').onclick=e=>{const b=e.target.closest('.cp-code');if(!b)return;navigator.clipboard.writeText(b.dataset.code).then(()=>toast('اتنسخ الكود '+b.dataset.code+' ✅'))};
  document.title='الكوبونات — عروض متتفوتش';scrollTo(0,0);
}

function catsPage(){setNav('cats');clearInterval(timer);document.body.classList.remove('pp-open');
  $('app').innerHTML=`<div class="fhead"><h1>🗂 <span>الأقسام</span></h1><p>اختار القسم اللي يهمك</p></div><div class="catgrid">${visibleCats().slice(1).map(([k,i,n])=>`<a href="#/deals?cat=${k}"><i>${i}</i><b>${n}</b></a>`).join('')}</div>`;
  document.title='الأقسام — عروض متتفوتش';scrollTo(0,0)}
const COLS=[['top100','🏆 أفضل 100 عرض','أقوى العروض دلوقتي حسب قوة اللقطة'],['save','💰 أكبر توفير بالجنيه','الفرق الأكبر بين السعر قبل وبعد'],['pct','٪ أعلى نسبة خصم','خصومات 30% وأكتر على منتجات حقيقية'],['bundles','🎁 اشتري واحصل / باكدجات','عروض الهدية والقطعتين والباكدجات'],['lowest','⭐ أقل سعر في تاريخه','السعر دلوقتي هو الأقل من ساعة ما بدأنا نتابعه'],['drops','📉 نزل سعره فعلاً','سعره نزل عن آخر سعر سجلناه في آخر أسبوع'],['stockup','📦 يستاهل التخزين','منظفات وبقالة وحفاضات ومناديل بخصم 15% وأكتر'],['inflated','⚠️ خصم مشكوك فيه','السعر كان أقل قبل كده — الخصم متضخم، خلي بالك']];
let COLD=null;
async function collections(){setNav('cols');clearInterval(timer);document.body.classList.remove('pp-open');const app=$('app');
  const cur=(location.hash.split('?k=')[1])||'top100';const meta=COLS.find(c=>c[0]===cur)||COLS[0];
  app.innerHTML=`<div class="fhead"><h1>🔥 <span>عروض نوفمبر</span></h1><p>مجموعات بتتحدث تلقائياً كل نص ساعة من كل المتاجر</p></div><div class="bar"><div class="chips">${COLS.map(([k,t])=>`<a class="chip ${k===meta[0]?'on':''}" href="#/collections?k=${k}">${t}</a>`).join('')}</div></div><p class="sub">${meta[2]}</p><section class="grid" id="grid">${skel(12)}</section>`;
  try{if(!COLD){const r=await fetch('/api/collections');COLD=await r.json()}}catch(e){}
  const rows=(COLD&&COLD[meta[0]])||[];$('grid').innerHTML=rows.length?rows.map(p=>card(p)).join(''):'<div class="empty">مفيش عروض في المجموعة دي دلوقتي</div>';
  document.title=meta[1]+' — عروض متتفوتش';scrollTo(0,0)}
/* ---------- misc ---------- */
function toast(t){document.querySelectorAll('.toast').forEach(x=>x.remove());const d=document.createElement('div');d.className='toast';d.textContent=t;document.body.append(d);setTimeout(()=>d.remove(),2500)}
const AFF_TAG='3rodmattfwt4-21';
function affLink(u){try{const x=new URL(u);if(/(^|\.)amazon\.eg$/.test(x.hostname)){x.searchParams.set('tag',SITE.aff_tag||AFF_TAG);return x.toString()}}catch(e){}return u}
function applySite(){
  const s=SITE;if(s.bot_url)BOT_URL=s.bot_url;
  document.querySelectorAll('.botLink,#botTop').forEach(a=>a.href=BOT_URL);
  if(s.channel_url)document.querySelectorAll('[data-chan]').forEach(a=>a.href=s.channel_url);
  const an=$('annc');const A=s.announcement;
  if(A&&A.on&&A.text){an.hidden=false;an.innerHTML=A.link?`<a href="${esc(affLink(A.link))}" target="_blank" rel="noopener">${esc(A.text)}</a>`:esc(A.text);if(A.color)an.style.background=A.color}else an.hidden=true;
  if(s.colors){const r=document.documentElement.style;if(s.colors.brand)r.setProperty('--brand',s.colors.brand);if(s.colors.brand2)r.setProperty('--brand2',s.colors.brand2)}
}
function setNav(r){document.querySelectorAll('#bnav a').forEach(a=>a.classList.toggle('on',a.dataset.r===r))}
$('topSearch').onsubmit=e=>{e.preventDefault();const v=$('topQ').value.trim();$('topQ').blur();go({q:v,store:'',cat:'',type:''})};
document.addEventListener('click',e=>{if(e.target.closest('#searchBtn')){e.preventDefault();scrollTo({top:0,behavior:'smooth'});setTimeout(()=>$('topQ').focus(),250)}});
function go(o){const p=new URLSearchParams();for(const k of ['q','store','cat','type','sort'])if(o[k])p.set(k,o[k]);const h='#/deals'+(p.toString()?'?'+p:'');if(location.hash===h)route();else location.hash=h}
function route(){const hsh=location.hash;
  if(SITE.maintenance&&SITE.maintenance.on){$('app').innerHTML=`<div class="empty" style="padding:80px 16px;font-size:18px">🛠 ${esc(SITE.maintenance.text||'الموقع تحت الصيانة — راجعين قريب جداً')}</div>`;return}
  if(hsh.startsWith('#/coupons'))return coupons();
  if(hsh.startsWith('#/cats'))return catsPage();
  if(hsh.startsWith('#/collections'))return collections();
  const m=hsh.match(/^#\/p\/(.+)/);if(m)return product(decodeURIComponent(m[1]));
  if(hsh==='#stores'){if(!$('storeGrid'))home();setNav('stores');setTimeout(()=>$('stores').scrollIntoView({behavior:'smooth',block:'start'}),30);return}
  if(hsh.startsWith('#/deals')){const p=new URLSearchParams(hsh.split('?')[1]||'');
    Object.assign(st,{stores:(p.get('stores')||'').split(',').filter(Boolean),store:p.get('store')||'',type:p.get('type')||'',cat:p.get('cat')||'',q:p.get('q')||'',pct:0,since:0,all:false,autoAll:false,sort:p.get('sort')||SITE.default_sort||'new'});
    $('topQ').value=st.q;feed();document.title=(st.q||'العروض')+' — عروض متتفوتش';scrollTo(0,0);return}
  home()}
addEventListener('hashchange',route);
function clock(){const d=new Date();let h=d.getHours();const ap=h<12?'ص':'م';h=h%12||12;const p=n=>String(n).padStart(2,'0');$('liveText').textContent='مباشر · '+h+':'+p(d.getMinutes())+':'+p(d.getSeconds())+' '+ap}
clock();setInterval(clock,1000);
/* boot: paint instantly from cache, then refresh */
(async()=>{const c=ls.get('home_v2');if(c&&c.config){Object.assign(SITE,c.config);HOME=c}
  applySite();
  if(!c){try{await Promise.race([getHome(),new Promise((_,rj)=>setTimeout(rj,3000))])}catch(e){}}
  applySite();route();
  if(c)getHome().then(()=>applySite()).catch(()=>{});
})();

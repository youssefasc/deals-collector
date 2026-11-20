-- =====================================================================
-- عروض متتفوتش — نسخة قاعدة البيانات الكاملة (الهيكل + الدوال + الجدولة)
-- شغّل الملف ده كله مرة واحدة في: Supabase > SQL Editor (على مشروع جديد)
-- بعده شغّل settings.sql
-- =====================================================================

create extension if not exists pg_trgm;
create extension if not exists pg_cron;

-- ========================= SEQUENCES =========================
create sequence if not exists public.price_history_id_seq;

-- ========================= TABLES =========================
create table if not exists public.collector_state (
  key text not null,
  value jsonb,
  updated_at timestamp with time zone default now(),
  constraint collector_state_pkey PRIMARY KEY (key)
);
alter table public.collector_state enable row level security;

create table if not exists public.coupons (
  id text not null,
  store text not null,
  code text,
  title text,
  discount text,
  url text,
  image text,
  product_id text,
  source text default 'manual'::text not null,
  active boolean default true not null,
  expires_at timestamp with time zone,
  created_at timestamp with time zone default now(),
  last_seen timestamp with time zone default now(),
  constraint coupons_pkey PRIMARY KEY (id)
);
alter table public.coupons enable row level security;

create table if not exists public.deals_feed (
  id text not null,
  store text,
  pid text,
  title text,
  image text,
  price numeric,
  list_price numeric,
  prev_price numeric,
  discount_pct smallint,
  drop_pct smallint,
  low_price numeric,
  low_at timestamp with time zone,
  score smallint,
  fake_discount boolean,
  last_change timestamp with time zone,
  category text,
  featured boolean,
  constraint deals_feed_pkey PRIMARY KEY (id)
);
alter table public.deals_feed enable row level security;

create table if not exists public.products (
  id text not null,
  store text not null,
  pid text not null,
  title text,
  image text,
  url text,
  category text,
  src_category text,
  price numeric(12,2),
  list_price numeric(12,2),
  discount_pct smallint,
  drop_pct smallint,
  prev_price numeric(12,2),
  low_price numeric(12,2),
  low_at timestamp with time zone,
  high_price numeric(12,2),
  in_stock boolean default true,
  score smallint default 0,
  fake_discount boolean default false,
  first_seen timestamp with time zone default now(),
  last_seen timestamp with time zone default now(),
  last_change timestamp with time zone default now(),
  src_prices jsonb,
  hidden boolean default false not null,
  featured boolean default false not null,
  constraint products_pkey PRIMARY KEY (id)
);
alter table public.products enable row level security;

create table if not exists public.price_history (
  id bigint default nextval('price_history_id_seq'::regclass) not null,
  product_id text not null,
  price numeric(12,2) not null,
  at timestamp with time zone default now() not null,
  constraint price_history_pkey PRIMARY KEY (id)
);
alter table public.price_history enable row level security;

create table if not exists public.product_region_prices (
  product_id text not null,
  region text not null,
  price numeric not null,
  list_price numeric,
  in_stock boolean default true,
  updated_at timestamp with time zone default now(),
  constraint product_region_prices_pkey PRIMARY KEY (product_id, region)
);
alter table public.product_region_prices enable row level security;

create table if not exists public.site_config (
  key text not null,
  value jsonb,
  updated_at timestamp with time zone default now(),
  constraint site_config_pkey PRIMARY KEY (key)
);
alter table public.site_config enable row level security;

create table if not exists public.site_snapshot (
  k text not null,
  v jsonb,
  at timestamp with time zone default now(),
  constraint site_snapshot_pkey PRIMARY KEY (k)
);
alter table public.site_snapshot enable row level security;

-- ========================= FOREIGN KEYS =========================
alter table public.price_history add constraint price_history_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;

-- ========================= INDEXES =========================
CREATE INDEX products_last_change_idx ON public.products USING btree (last_change DESC);
CREATE INDEX products_cat_idx ON public.products USING btree (category, last_change DESC);
CREATE INDEX products_score_idx ON public.products USING btree (score DESC);
CREATE INDEX products_store_idx ON public.products USING btree (store, last_change DESC);
CREATE INDEX price_history_pid_idx ON public.price_history USING btree (product_id, at DESC);
CREATE INDEX products_featured_idx ON public.products USING btree (featured) WHERE featured;
CREATE INDEX coupons_store_idx ON public.coupons USING btree (store, last_seen DESC);
CREATE INDEX df_recent ON public.deals_feed USING btree (last_change DESC);
CREATE INDEX df_drop ON public.deals_feed USING btree (drop_pct DESC, last_change DESC) WHERE (drop_pct > 0);
CREATE INDEX df_drop_recent ON public.deals_feed USING btree (last_change DESC) WHERE (drop_pct > 0);
CREATE INDEX df_disc ON public.deals_feed USING btree (discount_pct DESC NULLS LAST);
CREATE INDEX df_score ON public.deals_feed USING btree (score DESC NULLS LAST, last_change DESC);
CREATE INDEX df_price ON public.deals_feed USING btree (price);
CREATE INDEX df_cat ON public.deals_feed USING btree (category, last_change DESC);
CREATE INDEX products_drops_recent_idx ON public.products USING btree (last_change DESC) WHERE ((drop_pct > 0) AND in_stock AND (NOT hidden));
CREATE INDEX products_deals_recent_idx ON public.products USING btree (last_change DESC) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX products_featured_recent_idx ON public.products USING btree (last_change DESC) WHERE featured;
CREATE INDEX products_drop_rank_idx ON public.products USING btree (drop_pct DESC, last_change DESC) WHERE ((drop_pct > 0) AND in_stock AND (NOT hidden));
CREATE INDEX products_disc_rank_idx ON public.products USING btree (discount_pct DESC NULLS LAST) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX products_score_rank_idx ON public.products USING btree (score DESC NULLS LAST, last_change DESC) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX products_cheap_idx ON public.products USING btree (price) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX products_cat_deals_idx ON public.products USING btree (category, last_change DESC) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX products_store_deals_idx ON public.products USING btree (store, last_change DESC) WHERE (((discount_pct > 0) OR (drop_pct > 0)) AND in_stock AND (NOT hidden));
CREATE INDEX df_store ON public.deals_feed USING btree (store, last_change DESC);
CREATE INDEX df_feat ON public.deals_feed USING btree (last_change DESC) WHERE featured;
CREATE INDEX deals_feed_title_trgm ON public.deals_feed USING gin (title gin_trgm_ops);
CREATE INDEX products_title_trgm ON public.products USING gin (title gin_trgm_ops);

-- ========================= FUNCTIONS =========================

CREATE OR REPLACE FUNCTION public._is_admin(token text)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'public'
AS $function$
  select token is not null and token = (select value #>> '{}' from collector_state where key='admin_token');
$function$;

CREATE OR REPLACE FUNCTION public.is_book(src text, title text)
 RETURNS boolean LANGUAGE sql IMMUTABLE
AS $function$
  select coalesce(src,'') ~* '(gl_book|gl_ebooks|ABIS_BOOK|ABIS_EBOOK)'
      or (coalesce(title,'') !~* '^\s*(لعبة|فونوغراف|سماع|ساعة)' and coalesce(title,'') ~* '(\mpaperback\M|\mhardcover\M|kindle edition|\misbn\M|student.?s? book|\mworkbook\M|activity book|graphic novel|\mnovel\M|^\s*كتاب\s|^\s*رواية|^\s*الرواية|\mرواية\M|للنشر|\mترجمات\M|سلسلة روايات|من ديوان|مجموعة قصصية|قصص الأطفال|قصص اطفال)');
$function$;

CREATE OR REPLACE FUNCTION public.collector_set_state(token text, k text, v jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key = 'ingest_token') then
    raise exception 'unauthorized';
  end if;
  insert into collector_state(key, value, updated_at) values (k, v, now())
  on conflict (key) do update set value = excluded.value, updated_at = now();
end $function$;

CREATE OR REPLACE FUNCTION public.collector_get_config(token text)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key = 'ingest_token') then raise exception 'unauthorized'; end if;
  return coalesce((select value from collector_state where key='config'), '{}'::jsonb);
end $function$;

CREATE OR REPLACE FUNCTION public.collector_get_state(token text, k text)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key='ingest_token') then raise exception 'unauthorized'; end if;
  if k in ('ingest_token','admin_token','admin_pass','manual_token') then raise exception 'forbidden'; end if;
  return (select value from collector_state where key=k);
end $function$;

CREATE OR REPLACE FUNCTION public.products_block_words()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare w jsonb;
begin
  -- الكتب ممنوعة نهائياً: بالتصنيف، بالاسم، أو برقم ISBN (أكواد أمازون للكتب أرقام ١٠ خانات)
  if public.is_book(new.src_category, new.title)
     or (new.store like 'amazon%' and coalesce(new.pid,'') ~ '^[0-9]{9}[0-9X]$') then return null; end if;
  select value into w from site_config where key = 'blocked_words';
  if w is not null and jsonb_typeof(w) = 'array' and exists (
       select 1 from jsonb_array_elements_text(w) x where length(x) > 1 and new.title ilike '%'||x||'%') then
    return null;
  end if;
  return new;
end $function$;

CREATE OR REPLACE FUNCTION public.sync_deals_feed()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if tg_op = 'DELETE' then delete from deals_feed where id = old.id; return null; end if;
  if (coalesce(new.discount_pct,0) > 0 or coalesce(new.drop_pct,0) > 0) and new.in_stock and not new.hidden and new.price > 0 then
    insert into deals_feed values (new.id, new.store, new.pid, new.title, new.image, new.price, new.list_price, new.prev_price,
      new.discount_pct, new.drop_pct, new.low_price, new.low_at, new.score, new.fake_discount, new.last_change, new.category, new.featured)
    on conflict (id) do update set store=excluded.store, pid=excluded.pid, title=excluded.title, image=excluded.image, price=excluded.price,
      list_price=excluded.list_price, prev_price=excluded.prev_price, discount_pct=excluded.discount_pct, drop_pct=excluded.drop_pct,
      low_price=excluded.low_price, low_at=excluded.low_at, score=excluded.score, fake_discount=excluded.fake_discount,
      last_change=excluded.last_change, category=excluded.category, featured=excluded.featured;
  else
    delete from deals_feed where id = new.id;
  end if;
  return null;
end $function$;

CREATE OR REPLACE FUNCTION public.ingest_products(token text, items jsonb)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare
  it jsonb; pid_ text; new_price numeric; old record;
  changed int := 0; inserted int := 0;
  drop_ smallint; disc smallint; sc smallint; low_ numeric;
  src_ text; sp jsonb; eff numeric; exists_ boolean; raw_ numeric;
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key = 'ingest_token') then
    raise exception 'unauthorized';
  end if;
  for it in select * from jsonb_array_elements(items) loop
    pid_ := (it->>'store') || ':' || (it->>'pid');
    new_price := nullif(it->>'price','')::numeric;
    if new_price is null or new_price <= 0 then continue; end if;
    disc := nullif(it->>'discount_pct','')::smallint;
    raw_ := new_price;
    src_ := case when it->>'src_category' = 'search' then 'search' else 'deals' end;
    select * into old from products where id = pid_;
    exists_ := found;
    sp := coalesce(case when exists_ then old.src_prices end, '{}'::jsonb)
          || jsonb_build_object(src_, jsonb_build_object('p', new_price, 't', extract(epoch from now())));
    select min((v->>'p')::numeric) into eff from jsonb_each(sp) e(k, v)
      where (v->>'t')::numeric > extract(epoch from now()) - 10800;
    new_price := coalesce(eff, new_price);
    if not exists_ then
      sc := least(100, coalesce(disc, 0));
      insert into products(id, store, pid, title, image, url, category, src_category, price, list_price,
                           discount_pct, low_price, low_at, high_price, in_stock, score, src_prices)
      values (pid_, it->>'store', it->>'pid', it->>'title', it->>'image', it->>'url', coalesce(it->>'category', (select p2.category from products p2 where p2.id = 'amazon:' || (it->>'pid')), 'other'),
              it->>'src_category', new_price, nullif(it->>'list_price','')::numeric, disc,
              new_price, now(), new_price, coalesce((it->>'in_stock')::boolean, true), sc, sp);
      if found then
        insert into price_history(product_id, price) values (pid_, new_price);
        inserted := inserted + 1;
      end if;
    else
      low_ := least(coalesce(old.low_price, new_price), new_price);
      if old.price is distinct from new_price then
        drop_ := case when old.price > 0 and new_price < old.price
                      then round((1 - new_price / old.price) * 100) else 0 end;
        sc := least(100, greatest(coalesce(disc,0), drop_)
                         + case when new_price <= coalesce(old.low_price, new_price) then 25 else 0 end
                         + case when drop_ >= 20 then 10 else 0 end);
        update products set
          title = coalesce(it->>'title', title), image = coalesce(it->>'image', image),
          url = coalesce(it->>'url', url), category = coalesce(it->>'category', category),
          src_category = coalesce(it->>'src_category', src_category),
          prev_price = old.price, price = new_price,
          list_price = coalesce(nullif(it->>'list_price','')::numeric, list_price),
          discount_pct = disc, drop_pct = drop_,
          low_at = case when new_price < coalesce(old.low_price, new_price + 1) then now() else low_at end,
          low_price = low_, high_price = greatest(coalesce(old.high_price, new_price), new_price),
          in_stock = coalesce((it->>'in_stock')::boolean, true),
          score = sc,
          fake_discount = (coalesce(disc,0) >= 15 and new_price > low_ * 1.05),
          last_seen = now(), last_change = now(), src_prices = sp
        where id = pid_;
        insert into price_history(product_id, price) values (pid_, new_price);
        changed := changed + 1;
      elsif old.last_seen < now() - interval '30 minutes'
            or (old.src_prices->src_->>'p') is distinct from raw_::text
            or old.in_stock is distinct from coalesce((it->>'in_stock')::boolean, old.in_stock)
            or (disc is not null and old.discount_pct is distinct from disc)
            or exists (select 1 from products x where x.id = pid_ and ((it->>'image') is not null and x.image is distinct from (it->>'image')
                       or (it->>'title') is not null and x.title is distinct from (it->>'title'))) then
        -- بنكتب بس لو حاجة اتغيرت (أو كل نص ساعة) — بدل ما نعيد كتابة كل منتج في كل لفة
        update products set last_seen = now(), src_prices = sp,
          image = coalesce(it->>'image', image), title = coalesce(it->>'title', title), url = coalesce(it->>'url', url),
          discount_pct = coalesce(disc, discount_pct),
          in_stock = coalesce((it->>'in_stock')::boolean, in_stock)
        where id = pid_;
      end if;
    end if;
  end loop;
  return jsonb_build_object('inserted', inserted, 'changed', changed);
end $function$;

CREATE OR REPLACE FUNCTION public.ingest_coupons(token text, items jsonb)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n int;
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key = 'ingest_token') then raise exception 'unauthorized'; end if;
  insert into coupons(id, store, title, discount, url, image, product_id, source, last_seen)
  select x->>'id', x->>'store', x->>'title', x->>'discount', x->>'url', x->>'image', x->>'product_id', 'collector', now()
  from jsonb_array_elements(items) x
  on conflict (id) do update set discount=excluded.discount, title=excluded.title, last_seen=now(), active=true;
  get diagnostics n = row_count;
  -- كوبونات الجامع اللي ماتشافتش من يومين بتتقفل
  update coupons set active=false where source='collector' and last_seen < now() - interval '2 days';
  return n;
end $function$;

CREATE OR REPLACE FUNCTION public.ingest_region_prices(token text, rows jsonb)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n int;
begin
  if token is null or token <> (select value #>> '{}' from collector_state where key='ingest_token') then raise exception 'unauthorized'; end if;
  insert into product_region_prices(product_id, region, price, list_price, in_stock, updated_at)
  select x->>'product_id', x->>'region', (x->>'price')::numeric, nullif(x->>'list_price','')::numeric, coalesce((x->>'in_stock')::boolean,true), now()
  from jsonb_array_elements(rows) x where x->>'product_id' is not null and x->>'region' is not null and (x->>'price') is not null
  on conflict (product_id, region) do update set price=excluded.price, list_price=excluded.list_price, in_stock=excluded.in_stock, updated_at=now();
  get diagnostics n = row_count; return n;
end $function$;

CREATE OR REPLACE FUNCTION public.refresh_collections()
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' SET statement_timeout TO '300s'
AS $function$
declare c text := 'id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change';
  r jsonb := '{}'; j jsonb; q record;
begin
  for q in select * from (values
    ('top100', 'not coalesce(fake_discount,false) and discount_pct between 10 and 95', 'score desc nulls last, discount_pct desc', 100),
    ('pct', 'not coalesce(fake_discount,false) and discount_pct between 30 and 95 and price>=50', 'discount_pct desc, (list_price-price) desc', 40),
    ('save', 'not coalesce(fake_discount,false) and list_price>price and discount_pct<=95', '(list_price-price) desc', 40),
    ('bundles', $w$title ~* '(\+.{0,80}\mfree\M|\mbogo\M|buy \d+ get|pack of [2-9]|\(\s*[2-9] pieces\s*\)|اشتري.{0,10}(احصل|خد)|مجانا|مجاناً|\+ ?هدية)' and discount_pct>0$w$, '(list_price-price) desc nulls last', 40),
    ('lowest', 'drop_pct>0 and low_price is not null and price<=low_price and not coalesce(fake_discount,false)', 'drop_pct desc, last_change desc', 40),
    ('drops', $w$drop_pct>=5 and prev_price is not null and last_change>now()-interval '7 days'$w$, 'drop_pct desc', 40),
    ('inflated', 'coalesce(fake_discount,false) and discount_pct>0', 'discount_pct desc', 40),
    ('stockup', $w$discount_pct>=15 and not coalesce(fake_discount,false) and (category in ('grocery','health','home','kids')) and title ~* '(detergent|ariel|persil|tide|oxi|softener|tissue|toilet|diaper|حفاض|منظف|مسحوق|منعم|مناديل|ورق تواليت|rice|أرز|ارز|oil|زيت|سكر|sugar|pasta|مكرونة|شاي|tea|coffee|قهوة|tuna|تونة|wipes|shampoo|شامبو|soap|صابون)'$w$, '(list_price-price) desc', 40)
  ) v(k, w, o, n) loop
    execute format('select coalesce(jsonb_agg(to_jsonb(x)),''[]'') from (select %s from deals_feed where %s order by %s limit %s) x', c, q.w, q.o, q.n) into j;
    r := r || jsonb_build_object(q.k, j);
  end loop;
  insert into site_snapshot(k,v,at) values('collections', r, now()) on conflict (k) do update set v=excluded.v, at=excluded.at;
end $function$;

CREATE OR REPLACE FUNCTION public.refresh_site_snapshot()
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' SET statement_timeout TO '300s'
AS $function$
declare cols text := 'id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change';
 j jsonb; r jsonb := '{}'::jsonb; c text;
begin
  for c in select unnest(array['mobiles','laptops','tvs','appliances','audio','grocery','beauty','home','fashion','gaming']) loop
    execute format('select coalesce(jsonb_agg(to_jsonb(x)),''[]'') from (select %s from deals_feed where category=%L and discount_pct>=15 and price>=%s and not coalesce(fake_discount,false) and last_change>now()-interval ''3 days'' order by score desc nulls last, last_change desc limit 14) x', cols, c, case c when 'laptops' then 6000 when 'mobiles' then 2500 when 'tvs' then 3000 when 'appliances' then 1500 when 'gaming' then 300 else 100 end) into j;
    r := r || jsonb_build_object(c, j);
  end loop;
  insert into site_snapshot(k,v,at) values('home', jsonb_build_object(
    'hot',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (select id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change from deals_feed where last_change>now()-interval '24 hours' and not coalesce(fake_discount,false) and price>=250 and discount_pct>=25 order by score desc nulls last, discount_pct desc limit 24) x),
    'drops',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (select id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change from deals_feed where drop_pct>=5 and prev_price is not null order by last_change desc limit 16) x),
    'featured',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (select id,store,title,image,price,list_price,prev_price,discount_pct,drop_pct,low_price,score,fake_discount,last_change from deals_feed where featured order by last_change desc limit 20) x),
    'rails', r,
    'counts',(select coalesce(jsonb_object_agg(store,n),'{}') from (select store,count(*) n from deals_feed group by store) s),
    'total',(select count(*) from deals_feed),
    'all_counts',(select value->'by_store' from collector_state where key='admin_stats_cache'),
    'all_total',(select value->'total' from collector_state where key='admin_stats_cache'),
    'drops_24h',(select count(*) from deals_feed where drop_pct>0 and last_change>now()-interval '24 hours'),
    'coupons',(select count(*) from coupons),
    'lastseen',(select coalesce(jsonb_object_agg(store,ls),'{}') from (select store, max(last_change) ls from deals_feed where store in ('2b','talabat') group by store) s),
    'maxdisc',(select coalesce(jsonb_object_agg(store,m),'{}') from (select store,max(discount_pct) filter (where discount_pct<=95) m from deals_feed where last_change>now()-interval '7 days' group by store) s),
    'codes',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from (select store,code,title,discount,url from coupons where code is not null order by last_seen desc nulls last limit 10) x),
    'config',(select coalesce(jsonb_object_agg(key,value),'{}') from site_config where key not like '%token%' and key not like '%pass%')
  ), now()) on conflict (k) do update set v=excluded.v, at=excluded.at;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_stats_compute(token text)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' SET statement_timeout TO '20s'
AS $function$
declare r jsonb; a record;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  select count(*) total,
    count(*) filter (where hidden) hidden, count(*) filter (where featured) featured,
    count(*) filter (where first_seen > now()-interval '1 hour') new_1h,
    count(*) filter (where first_seen > now()-interval '24 hours') new_24h,
    count(*) filter (where drop_pct>0 and last_change > now()-interval '1 hour') drops_1h,
    count(*) filter (where drop_pct>0 and last_change > now()-interval '24 hours') drops_24h,
    count(*) filter (where last_seen > now()-interval '10 minutes') seen_10m
  into a from products;
  select jsonb_build_object(
    'total', a.total, 'hidden', a.hidden, 'featured', a.featured, 'new_1h', a.new_1h, 'new_24h', a.new_24h,
    'drops_1h', a.drops_1h, 'drops_24h', a.drops_24h, 'seen_10m', a.seen_10m,
    'by_store', (select jsonb_object_agg(store, c) from (select store, count(*) c from products group by 1) x),
    'by_cat', (select jsonb_object_agg(coalesce(category,'?'), c) from (select category, count(*) c from products group by 1) x),
    'db_size', pg_size_pretty(pg_database_size(current_database())),
    'db_bytes', pg_database_size(current_database()),
    'history_rows', (select reltuples::bigint from pg_class where oid = 'public.price_history'::regclass),
    'coupons', (select count(*) from coupons where active),
    'collector', (select value from collector_state where key='stats'),
    'collector_at', (select updated_at from collector_state where key='stats'),
    'config', (select value from collector_state where key='config')
  ) into r;
  return r;
end $function$;

CREATE OR REPLACE FUNCTION public.refresh_admin_stats()
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' SET statement_timeout TO '300s'
AS $function$
declare tok text;
begin
  select value #>> '{}' into tok from collector_state where key='admin_token';
  insert into collector_state(key,value,updated_at) values ('admin_stats_cache', public.admin_stats_compute(tok), now())
  on conflict (key) do update set value=excluded.value, updated_at=now();
end $function$;

CREATE OR REPLACE FUNCTION public.admin_stats(token text)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare r jsonb;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  select value || jsonb_build_object('cached_at', updated_at,
      'collector', (select value from collector_state where key='stats'),
      'collector_at', (select updated_at from collector_state where key='stats'),
      'health', (select value from collector_state where key='health'),
      'collections_at', (select at from site_snapshot where k='collections'),
      'config', (select value from collector_state where key='config'))
    into r from collector_state where key='admin_stats_cache';
  return coalesce(r, '{}'::jsonb);
end $function$;

CREATE OR REPLACE FUNCTION public.admin_check(token text)
 RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path TO 'public'
AS $function$
  select public._is_admin(token);
$function$;

CREATE OR REPLACE FUNCTION public.site_counts(st text DEFAULT NULL::text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'public'
AS $function$
  select case when st is null or st = '' then
    jsonb_build_object('total', (value->>'total')::bigint, 'drops_1h', (value->>'drops_1h')::bigint)
  else
    jsonb_build_object('total', coalesce((value->'by_store'->>st)::bigint, 0),
      'drops_1h', (select count(*) from deals_feed where store = st and drop_pct > 0 and last_change > now() - interval '1 hour'))
  end
  from collector_state where key='admin_stats_cache';
$function$;

CREATE OR REPLACE FUNCTION public.admin_set_collector(token text, cfg jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  insert into collector_state(key,value,updated_at) values ('config', cfg, now())
  on conflict (key) do update set value = excluded.value, updated_at = now();
end $function$;

CREATE OR REPLACE FUNCTION public.admin_set_config(token text, k text, v jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  if v is null then delete from site_config where key=k;
  else insert into site_config(key,value,updated_at) values (k,v,now()) on conflict (key) do update set value=excluded.value, updated_at=now(); end if;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_change_password(token text, newpw text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  if length(coalesce(newpw,'')) < 8 then raise exception 'too short'; end if;
  update collector_state set value = to_jsonb(newpw), updated_at = now() where key = 'admin_token';
end $function$;

CREATE OR REPLACE FUNCTION public.admin_import_products(token text, items jsonb)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare tok text;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  if jsonb_array_length(items) > 2000 then raise exception 'max 2000 per batch'; end if;
  select value #>> '{}' into tok from collector_state where key='ingest_token';
  return to_jsonb(public.ingest_products(tok, items));
end $function$;

CREATE OR REPLACE FUNCTION public.admin_product(token text, pid text, patch jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  if patch ? 'delete' then delete from price_history where product_id=pid; delete from products where id=pid; return; end if;
  update products set
    hidden = coalesce((patch->>'hidden')::boolean, hidden),
    featured = coalesce((patch->>'featured')::boolean, featured),
    title = coalesce(patch->>'title', title),
    category = coalesce(patch->>'category', category)
  where id = pid;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_delete_store(token text, st text)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare ids text[]; n int;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  select array_agg(id) into ids from (select id from products where store = st limit 3000) x;
  if ids is null then return 0; end if;
  delete from price_history where product_id = any(ids);
  delete from products where id = any(ids);
  get diagnostics n = row_count;
  return n;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_coupon(token text, c jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  if c ? 'delete' then delete from coupons where id = c->>'id'; return; end if;
  insert into coupons(id, store, code, title, discount, url, source, active, expires_at)
  values (coalesce(c->>'id', 'm:' || md5(random()::text)), c->>'store', nullif(c->>'code',''), nullif(c->>'title',''),
          nullif(c->>'discount',''), nullif(c->>'url',''), 'manual', coalesce((c->>'active')::boolean, true),
          nullif(c->>'expires_at','')::timestamptz)
  on conflict (id) do update set store=excluded.store, code=excluded.code, title=excluded.title, discount=excluded.discount,
     url=excluded.url, active=excluded.active, expires_at=excluded.expires_at;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_coupons_list(token text)
 RETURNS SETOF coupons LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  return query select * from coupons order by source, created_at desc limit 500;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_prune_history(token text, days integer)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n int;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  delete from price_history where at < now() - make_interval(days => greatest(days,1));
  get diagnostics n = row_count; return n;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_bulk_hide(token text, pattern text, hide boolean)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n int;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  update products set hidden = hide where title ilike '%'||pattern||'%';
  get diagnostics n = row_count; return n;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_bulk_delete(token text, filt jsonb)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare ids text[]; n int;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  select array_agg(id) into ids from (select id from products
    where (filt->>'store' is null or store = filt->>'store')
      and (filt->>'category' is null or category = filt->>'category')
      and (filt->>'word' is null or title ilike '%'||(filt->>'word')||'%') limit 3000) x;
  if ids is null then return 0; end if;
  delete from price_history where product_id = any(ids);
  delete from products where id = any(ids);
  get diagnostics n = row_count; return n;
end $function$;

CREATE OR REPLACE FUNCTION public.admin_bulk(token text, filt jsonb, patch jsonb)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public'
AS $function$
declare n int;
begin
  if not public._is_admin(token) then raise exception 'unauthorized'; end if;
  update products set
    hidden = coalesce((patch->>'hidden')::boolean, hidden),
    drop_pct = case when patch ? 'reset_drops' then 0 else drop_pct end,
    prev_price = case when patch ? 'reset_drops' then null else prev_price end
  where (filt->>'store' is null or store = filt->>'store')
    and (filt->>'category' is null or category = filt->>'category')
    and (filt->>'word' is null or title ilike '%'||(filt->>'word')||'%');
  get diagnostics n = row_count; return n;
end $function$;

-- ========================= TRIGGERS =========================
CREATE TRIGGER trg_deals_feed_del AFTER DELETE ON public.products FOR EACH ROW EXECUTE FUNCTION sync_deals_feed();
CREATE TRIGGER trg_deals_feed_upd AFTER UPDATE OF price, list_price, discount_pct, drop_pct, in_stock, hidden, featured, title, category, image, score ON public.products FOR EACH ROW EXECUTE FUNCTION sync_deals_feed();
CREATE TRIGGER trg_deals_feed_ins AFTER INSERT ON public.products FOR EACH ROW EXECUTE FUNCTION sync_deals_feed();
CREATE TRIGGER trg_block_words BEFORE INSERT ON public.products FOR EACH ROW EXECUTE FUNCTION products_block_words();

-- ========================= POLICIES (قراءة عامة للموقع) =========================
create policy "public read products" on public.products for SELECT to anon,authenticated using (true);
create policy "public read history" on public.price_history for SELECT to anon,authenticated using (true);
create policy site_config_read on public.site_config for SELECT to anon,authenticated using (true);
create policy coupons_read on public.coupons for SELECT to anon,authenticated using ((active AND ((expires_at IS NULL) OR (expires_at > now()))));
create policy deals_feed_read on public.deals_feed for SELECT to anon,authenticated using (true);
create policy snap_read on public.site_snapshot for SELECT to public using (true);
create policy prp_read on public.product_region_prices for SELECT to public using (true);

-- ========================= CRON JOBS =========================
select cron.schedule('site_snapshot', '*/10 * * * *', 'select public.refresh_site_snapshot()');
select cron.schedule('refresh_admin_stats', '*/15 * * * *', 'select public.refresh_admin_stats()');
select cron.schedule('collections', '7,37 * * * *', 'select public.refresh_collections()');

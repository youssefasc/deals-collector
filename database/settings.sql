-- =====================================================================
-- إعدادات المنصة (المتاجر، الإعلان، إعدادات الجامع) — شغّله بعد schema.sql
-- قبل التشغيل: غيّر الكلمتين السريتين تحت لكلمات جديدة طويلة من عندك
-- =====================================================================

-- 1) كلمة سر لوحة التحكم (admin.html) — اختار كلمة قوية (٨ حروف أو أكتر)
insert into public.collector_state(key,value) values ('admin_token', to_jsonb('غيّرني_كلمة_سر_قوية'::text))
on conflict (key) do update set value=excluded.value;

-- 2) مفتاح الجامع السري — نفس القيمة دي لازم تتحط في متغير INGEST_TOKEN عند الجامع
insert into public.collector_state(key,value) values ('ingest_token', to_jsonb('غيّرني_مفتاح_طويل_عشوائي'::text))
on conflict (key) do update set value=excluded.value;

-- 3) إعدادات الموقع
insert into public.site_config(key,value) values ('announcement', '{"on":true,"link":"https://www.amazon.eg/whitefriday","text":"عروض الجمعة البيضاء بدأت! 🔥","color":"#ff6a2b"}'::jsonb) on conflict (key) do update set value=excluded.value;
insert into public.site_config(key,value) values ('min_discount', '0'::jsonb) on conflict (key) do update set value=excluded.value;
insert into public.site_config(key,value) values ('default_sort', '"pct"'::jsonb) on conflict (key) do update set value=excluded.value;
insert into public.site_config(key,value) values ('featured_title', '"🔥 أقوى عروض طلبات مارت"'::jsonb) on conflict (key) do update set value=excluded.value;
insert into public.site_config(key,value) values ('stores', '{"2b":{"on":true,"hidden":false},"we":{"on":true,"name":"وي","hidden":false},"noon":{"on":false,"hidden":false},"btech":{"on":true,"hidden":false},"jumia":{"on":false,"hidden":false},"amazon":{"on":true,"hidden":false},"orange":{"on":true,"hidden":false},"talabat":{"on":true,"hidden":false},"etisalat":{"on":true,"hidden":false},"vodafone":{"on":true,"hidden":false},"breadfast":{"on":false,"hidden":false},"carrefour":{"on":true,"hidden":false},"dream2000":{"on":true,"hidden":false},"amazon_now":{"on":true,"hidden":false},"dubaiphone":{"on":true,"hidden":false},"noon_minutes":{"on":false,"hidden":false},"amazon_resale":{"on":true,"hidden":false}}'::jsonb) on conflict (key) do update set value=excluded.value;

-- 4) إعدادات الجامع (المتاجر الموقوفة، السرعات، فيد أورنج)
-- ملاحظة: off_store_amazon = true يعني جامع أمازون الأساسي موقوف. شيله وقت اللانش.
insert into public.collector_state(key,value) values ('config', '{"feeds":[{"map":{"pid":"Id","url":"SEName","image":"Images.0.Url","price":"CashPrice.Price.Amount","title":"Name","in_stock":"IsAvailableForAddToCart","list_price":"CashPrice.OldPrice.Amount"},"url":"https://eshop.orange.eg/api/CatalogAPI/Products/GetFilterProducts?PageNumber={page}&PageSize=100","store":"orange","format":"json","every_min":120,"items_path":"Data.Products","page_delay":6,"url_prefix":"https://eshop.orange.eg/ar/"}],"2b_delay":20,"top_delay":1.2,"dream_delay":12,"sweep_delay":1.5,"search_delay":1.8,"we_every_min":30,"talabat_delay":5,"off_store_noon":true,"off_store_jumia":true,"off_store_amazon":true,"etisalat_every_min":60}'::jsonb)
on conflict (key) do update set value=excluded.value;

-- 5) أول تحديث للصفحة الرئيسية
select public.refresh_admin_stats();
select public.refresh_site_snapshot();
select public.refresh_collections();

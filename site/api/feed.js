import {pass} from './_sb.js';
export const config={runtime:'edge'};
export default async function(req){
  const p=new URL(req.url).searchParams.get('p')||'';
  if(!(/^deals_feed\?select=/.test(p)||(/^products\?select=/.test(p)&&(/&store=eq\.[a-z_0-9]+&/.test(p)||/&(title=ilike|and=\((or\()?title\.ilike)/.test(p))))||p.length>1800)return new Response('bad',{status:400});
  return pass(p,15);
}

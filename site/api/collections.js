import {pass} from './_sb.js';
export const config={runtime:'edge'};
export default async function(){
  const r=await pass('site_snapshot?k=eq.collections&select=v,at',20);
  if(!r.ok)return r;
  const [row]=await r.json();
  return new Response(JSON.stringify(row?{...row.v,at:row.at}:{}),{headers:r.headers});
}

export const SB='https://unwzvhdwxmlmknvgvrhp.supabase.co/rest/v1/';
export const KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVud3p2aGR3eG1sbWtudmd2cmhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTUwMjQ5MzUsImV4cCI6MjExMDYwMDkzNX0.g_500nSaAP5lF6N69ofsvozust1BpzbBU7kZXtooAyM';
export async function pass(path,maxAge){
  const r=await fetch(SB+path,{headers:{apikey:KEY,Authorization:'Bearer '+KEY}});
  const body=await r.text();
  return new Response(body,{status:r.status,headers:{'content-type':'application/json; charset=utf-8','cache-control':r.ok?`public, s-maxage=${maxAge}, stale-while-revalidate=300`:'no-store','access-control-allow-origin':'*'}});
}

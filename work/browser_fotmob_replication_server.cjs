// Browser-assisted acquisition bridge for environments where shell network is blocked.
const http=require('http');
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const raw=path.join(root,'outputs','big5_2025_carryover_replication','browser_raw');
fs.mkdirSync(raw,{recursive:true});
const leagues=[['Premier League',47,'ENG'],['LaLiga',87,'ESP'],['Serie A',55,'ITA'],['Bundesliga',54,'GER'],['Ligue 1',53,'FRA']];
const seasons=['2024/2025','2025/2026'];
const page=`<!doctype html><meta charset="utf-8"><title>Frozen FotMob replication acquisition</title><style>body{font:16px system-ui;max-width:900px;margin:40px auto}pre{white-space:pre-wrap;background:#eee;padding:16px}</style><h1>Frozen replication data acquisition</h1><p>This bounded worker downloads only the two seasons and date range in the saved test plan.</p><pre id="status">Ready</pre><button id="start">Start acquisition</button><script>
const leagues=${JSON.stringify(leagues)},seasons=${JSON.stringify(seasons)},status=document.querySelector('#status');
const log=s=>status.textContent=s;
async function send(route,obj){const r=await fetch(route,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error(await r.text());}
async function get(url){const r=await fetch(url,{credentials:'omit'});if(!r.ok)throw Error(r.status+' '+url);return r.json()}
async function run(){document.querySelector('#start').disabled=true;try{let selected=[];
for(const [league,id,ccode3] of leagues)for(const season of seasons){log('Fixture list: '+league+' '+season);const u='https://www.fotmob.com/api/data/leagues?'+new URLSearchParams({id,ccode3,season});const d=await get(u);await send('/save-fixture',{league,id,season,data:d});for(const m of d.fixtures.allMatches){const t=new Date(m.status?.utcTime);if(m.status?.finished&&t>=new Date('2025-03-17T00:00:00Z')&&t<new Date('2025-10-06T00:00:00Z'))selected.push({...m,league,league_id:id,season});}}
let done=0,failed=[];async function one(m){try{const d=await get('https://www.fotmob.com/api/data/matchDetails?matchId='+m.id);await send('/save-match',{meta:m,detail:d});}catch(e){failed.push({id:m.id,error:String(e)})}done++;if(done%10===0||done===selected.length)log('Match details '+done+'/'+selected.length+'; failures='+failed.length);}
let cursor=0;async function worker(){while(cursor<selected.length){const m=selected[cursor++];await one(m)}}await Promise.all([worker(),worker(),worker(),worker()]);await send('/done',{selected:selected.length,done,failed});log('COMPLETE: '+done+'/'+selected.length+'; failures='+failed.length+'\nYou may close this tab.');
}catch(e){log('BLOCKED: '+e.stack)}}document.querySelector('#start').onclick=run;</script>`;
function body(req){return new Promise((resolve,reject)=>{let chunks=[];req.on('data',c=>chunks.push(c));req.on('end',()=>{try{resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')))}catch(e){reject(e)}});req.on('error',reject)})}
const server=http.createServer(async(req,res)=>{try{
  if(req.method==='GET'){res.writeHead(200,{'content-type':'text/html; charset=utf-8'});return res.end(page)}
  const obj=await body(req);
  if(req.url==='/save-fixture'){fs.writeFileSync(path.join(raw,`league_${obj.id}_${obj.season.replace('/','-')}.json`),JSON.stringify(obj));}
  else if(req.url==='/save-match'){fs.writeFileSync(path.join(raw,`match_${obj.meta.id}.json`),JSON.stringify(obj));}
  else if(req.url==='/done'){fs.writeFileSync(path.join(raw,'done.json'),JSON.stringify(obj,null,2));}
  else throw Error('unknown route');res.writeHead(200,{'content-type':'application/json'});res.end('{"ok":true}');
}catch(e){res.writeHead(500);res.end(String(e))}});
server.listen(8770,'127.0.0.1',()=>console.log('READY http://127.0.0.1:8770'));

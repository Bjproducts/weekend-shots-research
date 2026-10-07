const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
const p=await b.newPage({viewport:{width:1440,height:1000}});
for(const [file,rows] of [['cross_league_research.html',4],['laliga_2015_16_validation/index.html',274],['seriea_2015_16_validation/index.html',291]]){
 const f=path.resolve('outputs',file);await p.goto('file:///'+f.replaceAll('\\','/'));
 if(await p.locator('table').last().locator('tr').count()!==rows)throw Error('Row count '+file);
 for(const h of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href'))))if(!h.startsWith('https:')&&!fs.existsSync(path.resolve(path.dirname(f),h)))throw Error('Broken link '+h);
 await p.setViewportSize({width:390,height:844});if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+file);
 await p.setViewportSize({width:1440,height:1000});
}
await p.goto('file:///'+path.resolve('outputs/cross_league_research.html').replaceAll('\\','/'));
await p.screenshot({path:'work/cross-league-research.png'});
console.log('PASS: comparison table, 563 new qualifying pick rows, data links, responsive layouts.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

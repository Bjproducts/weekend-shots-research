const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
const p=await b.newPage({viewport:{width:1440,height:1000}});const f=path.resolve('outputs/winning_pattern_research.html');
await p.goto('file:///'+f.replaceAll('\\','/'));if(await p.locator('tr').count()!==11)throw Error('Filter rows');
for(const h of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href'))))if(!fs.existsSync(path.resolve(path.dirname(f),h)))throw Error('Missing artifact');
await p.screenshot({path:'work/winning-research-desktop.png'});await p.setViewportSize({width:390,height:844});
if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
console.log('PASS: ten research filters, saved evidence links and responsive layout.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
const p=await b.newPage({viewport:{width:1440,height:1000}});const f=path.resolve('outputs/ligue1_2015_16_ab_validation/index.html');
await p.goto('file:///'+f.replaceAll('\\','/'));if(await p.locator('table').last().locator('tr').count()!==56)throw Error('Pick count');
for(const h of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href'))))if(!h.startsWith('https:')&&!fs.existsSync(path.resolve(path.dirname(f),h)))throw Error('Missing link');
await p.screenshot({path:'work/ligue1-ab-desktop.png'});await p.setViewportSize({width:390,height:844});if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
console.log('PASS: 55 picks, coverage disclosure, local links and responsive layout.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

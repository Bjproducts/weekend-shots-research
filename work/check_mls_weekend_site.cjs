const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
const p=await b.newPage({viewport:{width:1440,height:1050}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
const f=path.resolve('outputs/mls_2026_weekends/index.html');await p.goto('file:///'+f.replaceAll('\\','/'));
if(await p.locator('#weeks tr').count()!==39)throw Error('Weekend rows');
if(await p.locator('#week option').count()!==39)throw Error('Weekend choices');
await p.locator('#week').selectOption('2026-01-03');if(!(await p.locator('#coverage').innerText()).includes('No saved fixture coverage'))throw Error('Missing coverage status');
await p.locator('#week').selectOption('2026-08-15');if(await p.locator('#picks tr').count()<1)throw Error('No replay content');
for(const h of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href'))))if(!/^https?:/.test(h)&&!fs.existsSync(path.resolve(path.dirname(f),h)))throw Error('Missing artifact '+h);
await p.screenshot({path:'work/mls-weekend-desktop.png'});await p.setViewportSize({width:390,height:844});if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
if(errors.length)throw Error(errors.join(';'));console.log('PASS: weekend switcher, coverage states, report links, no JS errors and responsive layout.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

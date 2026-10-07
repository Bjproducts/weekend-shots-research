const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}});
 const f=path.resolve('outputs/bundesliga_2024_25_validation/index.html');
 await p.goto('file:///'+f.replaceAll('\\','/'));
 if(!(await p.locator('body').innerText()).includes('partial download'))throw Error('Partial status not visible');
 for(const h of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href'))))if(!fs.existsSync(path.resolve(path.dirname(f),h)))throw Error('Broken data link');
 await p.screenshot({path:'work/recent-season-desktop.png'});
 await p.setViewportSize({width:390,height:844});
 if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 console.log('PASS: partial status, saved-data links and desktop/mobile layout.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

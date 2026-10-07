const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}});
 const f=path.resolve('outputs/epl_2015_16_validation/index.html');
 await p.goto('file:///'+f.replaceAll('\\','/'));
 if(await p.locator('table').last().locator('tr').count()!==298)throw Error('Pick ledger');
 for(const href of await p.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href')))){
  if(!href.startsWith('https:')&&!fs.existsSync(path.resolve(path.dirname(f),href)))throw Error('Broken link');
 }
 await p.screenshot({path:'work/epl-validation-desktop.png'});
 await p.setViewportSize({width:390,height:844});
 if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow');
 await p.screenshot({path:'work/epl-validation-mobile.png'});
 console.log('PASS: all 297 picks visible, source/data links and responsive layout.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});

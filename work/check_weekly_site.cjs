const {chromium}=require('C:/Users/bjpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const file=path.resolve('outputs/weekly_pattern_replay.html');
 await page.goto('file:///'+file.replaceAll('\\','/'));
 if(await page.locator('details').count()!==53)throw Error('Missing active weeks');
 if(await page.locator('details table tr').count()!==713)throw Error('Missing picks');
 await page.locator('summary').first().click();
 if(!await page.locator('details').first().evaluate(e=>e.open))throw Error('Expansion');
 for(const href of await page.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href')))){
   if(!fs.existsSync(path.resolve(path.dirname(file),href.split('#')[0])))throw Error('Missing link '+href);
 }
 await page.screenshot({path:'work/weekly-backtest-desktop.png'});
 await page.setViewportSize({width:390,height:844});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 await page.screenshot({path:'work/weekly-backtest-mobile.png'});
 await browser.close();
 console.log('PASS: 53 expandable weeks, 660 picks, links, and desktop/mobile layout.');
})().catch(e=>{console.error(e);process.exit(1)});

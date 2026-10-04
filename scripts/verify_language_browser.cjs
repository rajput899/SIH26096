// Live localhost UI/API audit. Interface responses may use the existing server cache.
const {chromium,expect}=require('../frontend/node_modules/@playwright/test');
const fs=require('fs');
const catalog=require('../frontend/src/interface-strings.json');
const base='http://localhost:3000';
const report={mocked:false,interface_cache_may_be_used:true,routes:[],content_requests:0,errors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage();
  page.on('pageerror',e=>report.errors.push(e.message));
  page.on('request',r=>{
   if(r.url().endsWith('/interface/translations')){
    const b=r.postDataJSON();expect(Object.keys(b).sort()).toEqual(['keys','target_language']);
    for(const key of b.keys)expect(key in catalog).toBe(true);
   }
   if(/\/documents\/[^/]+\/translation$/.test(r.url()))report.content_requests++;
  });
  const capability=await(await page.request.get(base+'/api/archive/interface/languages')).json();
  expect(capability.confirmed_pairs).toEqual([['en','hi']]);
  report.capability=capability;
  for(const path of ['/','/archive','/archive?collection=manuscripts','/archive?collection=photographs','/archive?collection=videos','/speeches','/experience','/ai','/staff','/system','/archive/8ce2df4c-c4e2-4ed1-bf9e-244881273e82']){
   await page.goto(base+path);
   if(path.includes('/archive/'))await expect(page.locator('.text-page pre').first()).toBeVisible();
   await page.locator('.access-bar details > summary').click();
   await expect(page.getByTestId('interface-language').locator('option[value="hi"]')).toBeEnabled();
   const heading=await page.locator('h1').innerText();
   const originals=await page.locator('pre[translate="no"]').allTextContents();
   await page.getByTestId('interface-language').selectOption('hi');
   await expect(page.locator('html')).toHaveAttribute('lang','hi',{timeout:60000});
   await expect(page.locator('.settings-panel [role="status"]')).toContainText(/Some interface text remains English|Machine-translated interface|Translation unavailable; missing text remains English/,{timeout:60000});
   const translatedHeading=await page.locator('h1').innerText();
   report.last={path,heading,translatedHeading,settings:await page.locator('.settings-panel').innerText()};
   if(!path.includes('/archive/'))expect(translatedHeading).not.toBe(heading);
   expect(await page.locator('pre[translate="no"]').allTextContents()).toEqual(originals);
   expect(report.content_requests).toBe(0);
   report.routes.push({path,heading_changed:heading!==translatedHeading,source_text_unchanged:true,notice:await page.locator('.settings-panel [role="status"]').innerText()});
   if(path==='/'){
    await page.locator('.settings-panel select').nth(1).selectOption('140');
    await page.locator('.settings-panel input[type="checkbox"]').nth(0).check();
    await page.locator('.settings-panel input[type="checkbox"]').nth(1).check();
    await expect(page.locator('html')).toHaveCSS('font-size','22.4px');
    await page.locator('.site-header > button').click();
    await expect.poll(()=>page.evaluate(()=>Boolean(document.fullscreenElement))).toBe(true);
    await page.locator('.site-header > button').click();
    await expect.poll(()=>page.evaluate(()=>Boolean(document.fullscreenElement))).toBe(false);
    await page.screenshot({path:'outputs/resume-language-hindi-home.png',fullPage:true});
    report.hindi_accessibility_and_fullscreen=true;
   }
   await page.getByTestId('interface-language').selectOption('en');
   await expect(page.locator('html')).toHaveAttribute('lang','en');
   await expect(page.locator('h1')).toHaveText(heading);
  }
  // An explicit action on already public verified text, with real Bhashini inference.
  const section=page.getByTestId('content-translation').first();
  await section.getByRole('button',{name:'Translate this verified section into Hindi',exact:true}).click();
  await expect(section.getByText('Machine translation · unreviewed. Compare with the original.',{exact:true})).toBeVisible({timeout:60000});
  expect(await section.locator('pre').innerText()).toMatch(/[\u0900-\u097f]/);
  expect(report.content_requests).toBe(1);
  report.explicit_live_translation=true;
  expect(report.errors).toEqual([]);
  report.success=true;
 }finally{await browser.close();fs.writeFileSync('outputs/resume-language-live-browser.json',JSON.stringify(report,null,2));}
})().catch(e=>{console.error(e);process.exitCode=1;});

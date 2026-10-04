// Live interface audit only. No archive translation, generation, login or writes.
const {chromium,expect}=require('../frontend/node_modules/@playwright/test');
const fs=require('node:fs');
const catalog=require('../frontend/src/interface-strings.json');
const report={mocked:false,cache_may_be_used:true,interface_batches:0,content_requests:[],errors:[]};
const root='http://localhost:3000';
const outputStem=process.env.MULTILINGUAL_AUDIT_STEM||'multilingual-20261003-live-final';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',error=>report.errors.push(error.message));
  page.on('request',request=>{
   if(request.url().endsWith('/interface/translations')){
    const body=request.postDataJSON();
    expect(Object.keys(body).sort()).toEqual(['keys','target_language']);
    expect(body.target_language).toBe('mr');
    for(const key of body.keys)expect(key in catalog).toBe(true);
    report.interface_batches++;
   }else if(request.method()!=='GET')report.content_requests.push(request.url());
  });
  const response=await page.request.get(root+'/api/archive/interface/languages');
  expect(response.ok()).toBe(true);report.capability=await response.json();
  expect(report.capability.languages.filter(row=>row.enabled).map(row=>row.code)).toEqual(
   ['en','hi','bn','gu','kn','ml','mr','ne','or','pa','ta','te']);
  expect(report.capability.discovery).toBe('reviewed_service_allowlist');
  expect(report.capability.live_health_checked).toBe(false);
  const id='8ce2df4c-c4e2-4ed1-bf9e-244881273e82';
  const original=await(await page.request.get(root+`/api/archive/catalog/${id}`)).json();
  await page.goto(root+`/archive/${id}`);
  await expect(page.locator('.text-page pre').first()).toHaveText(original.pages[0].text);
  await page.locator('.access-bar details > summary').click();
  await page.getByTestId('interface-language').selectOption('mr');
  await expect(page.locator('html')).toHaveAttribute('lang','mr',{timeout:60000});
  await expect.poll(()=>report.interface_batches,{timeout:60000}).toBe(Math.ceil(Object.keys(catalog).length/30));
  await expect(page.locator('.settings-panel [role="status"]')).toContainText(
   /Some interface text remains English|Machine-translated interface/,{timeout:60000});
  report.notice=await page.locator('.settings-panel [role="status"]').innerText();
  await expect(page.locator('.text-page pre').first()).toHaveText(original.pages[0].text);
  report.source_text_unchanged=true;
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang','mr',{timeout:60000});
  await page.goto(root+'/staff');
  await expect(page.locator('html')).toHaveAttribute('lang','mr',{timeout:60000});
  report.anonymous_staff_heading=await page.locator('main h1').innerText();
  expect(report.anonymous_staff_heading).not.toBe('Curator workspace');
  report.persistence_reload_and_navigation=true;
  await page.goto(root+'/');
  await expect(page.locator('html')).toHaveAttribute('lang','mr',{timeout:60000});
  await page.locator('.access-bar details > summary').click();
  await expect(page.getByTestId('interface-language')).toHaveValue('mr');
  await expect(page.locator('.settings-panel [role="status"]')).toContainText(
   /Some interface text remains English|Machine-translated interface/,{timeout:60000});
  for(const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
   await page.setViewportSize({width,height});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
   expect(overflow).toBe(false);
   const bounds=await page.getByTestId('interface-language').boundingBox();
   expect(bounds.x+bounds.width).toBeLessThanOrEqual(width);
   await page.screenshot({path:`outputs/${outputStem}-${name}.png`,fullPage:true});
  }
  report.desktop_mobile_no_horizontal_overflow=true;
  expect(report.content_requests).toEqual([]);expect(report.errors).toEqual([]);
  report.passed=true;
 }finally{
  fs.writeFileSync(`outputs/${outputStem}.json`,JSON.stringify(report,null,2));
  await browser.close();
 }
})().catch(error=>{console.error(error);process.exitCode=1;});

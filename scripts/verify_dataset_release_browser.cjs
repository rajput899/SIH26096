// Live localhost checks. Credentials are accepted only through process environment; no traces.
const fs=require('node:fs');
const {chromium,expect}=require('../frontend/node_modules/@playwright/test');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const context=await browser.newContext({baseURL:'http://localhost:3000',viewport:{width:1366,height:900}});
 const page=await context.newPage(); const result={mocked:false,base:'http://localhost:3000',collections:{},media:[]};
 try{
  for(const [collection,count] of [['manuscripts',25],['photographs',36],['videos',7]]){
   console.log(`Checking public collection: ${collection}`);
   await page.goto(`/archive?collection=${collection}`);
   const section=page.getByRole('region',{name:collection==='manuscripts'?'Published collection records':'From the supplied dataset'});
   const ids=[];
   for(let offset=0;offset<count;offset+=12){
    await expect(section.locator('article.record')).toHaveCount(Math.min(12,count-offset));
    ids.push(...await section.locator('a.text-link').evaluateAll(links=>links.map(a=>a.getAttribute('href'))));
    if(offset+12<count)await section.getByRole('button',{name:'Next page',exact:true}).click();
   }
   expect(new Set(ids).size).toBe(count); result.collections[collection]=count;
   await expect(section.getByRole('button',{name:'Next page',exact:true})).toBeDisabled();
   await page.screenshot({path:`work/dataset-release-${collection}.png`,fullPage:true});
  }
  const rows=await(await context.request.get('/api/archive/catalog?origin=dataset&limit=200')).json();
  for(const group of ['manuscripts','photographs']){
   console.log(`Checking public original viewer: ${group}`);
   const row=rows.find(r=>r.dataset_collection===group);
   await page.goto(`/archive/${row.id}`);
   await expect(page.getByText(/Published under organizer-dataset authorization/)).toBeVisible();
   await page.getByRole('button',{name:'Open original scan / file',exact:true}).click();
   const original=page.getByAltText(`Preserved original scan: ${row.title}`);
   await expect(original).toBeVisible();
   await expect.poll(()=>original.evaluate(img=>img.naturalWidth)).toBeGreaterThan(0);
   await expect(page.getByText('No verified transcription is available. Unreviewed OCR is not shown publicly.')).toBeVisible();
  }
  for(const row of rows.filter(r=>r.mime_type.startsWith('video/')||r.mime_type.startsWith('audio/'))){
   console.log(`Checking public playback: ${row.id}`);
   await page.goto(`/archive/${row.id}`); const player=page.locator('video,audio');
   await expect.poll(()=>player.evaluate(el=>el.readyState),{timeout:60000}).toBeGreaterThanOrEqual(1);
   await player.evaluate(el=>{el.muted=true;return el.play();});
   await expect.poll(()=>player.evaluate(el=>el.currentTime),{timeout:20000}).toBeGreaterThan(0.3);
   const info=await player.evaluate(el=>{el.pause();return {duration:el.duration,time:el.currentTime,error:el.error?.code||null};});
   expect(info.error).toBeNull();result.media.push({id:row.id,...info});
  }
  const pdf=rows.find(r=>r.mime_type==='application/pdf');
  await page.goto(`/archive/${pdf.id}`);await page.getByRole('button',{name:'Open original scan / file',exact:true}).click();
  await expect(page.getByTitle(`Original PDF: ${pdf.title}`)).toBeVisible();result.pdfViewer=true;
  const txt=rows.find(r=>r.mime_type==='text/plain');
  await page.goto(`/archive/${txt.id}`);await page.getByRole('button',{name:'Open original scan / file',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Original plain-text file'})).toBeVisible();result.textViewer=true;
  if(process.env.SIH_LOCAL_STAFF_LOGIN&&process.env.SIH_LOCAL_STAFF_PASSWORD){
  await page.goto('/staff');
  await page.getByLabel('Staff login',{exact:true}).fill(process.env.SIH_LOCAL_STAFF_LOGIN);
  await page.getByLabel('Password',{exact:true}).fill(process.env.SIH_LOCAL_STAFF_PASSWORD);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('button',{name:'Next records',exact:true})).toBeVisible();
  await expect(page.getByRole('navigation',{name:'Staff tasks'})).toBeVisible();
  result.staffLogin=true;
  }else result.staffLogin='not run: credentials not supplied to this process';
  // Never save staff screenshots, storage state, credentials, traces or request headers.
  fs.writeFileSync('outputs/dataset-release-live-browser.json',JSON.stringify(result,null,2));
  console.log('PASS: live collections, pagination, original viewers and eight muted media playback checks. Staff login status is recorded separately.');
 } finally{await context.close();await browser.close();}
})().catch(()=>{console.error('Live dataset browser verification failed; no credential details logged.');process.exitCode=1;});

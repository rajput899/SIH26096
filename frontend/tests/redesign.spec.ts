import {expect,test} from '@playwright/test';
import fs from 'node:fs';

test('published catalogue opens original, reviewed full text and related exhibition',async({page,request})=>{
 const allRows=await(await request.get('/api/archive/catalog')).json();
 const rows=allRows.filter((row:{dataset_release_id?:string|null;mime_type:string})=>!row.dataset_release_id&&row.mime_type==='text/plain');
 test.skip(!rows.length,'Requires published source; no production fixture is created');
 await page.goto('/archive');
 await expect(page.getByRole('link',{name:'Speeches & recordings →'})).toHaveCount(0);
 await page.getByLabel('Search title or description').fill(rows[0].title);
 await page.getByRole('button',{name:'Search archive',exact:true}).click();
 await expect(page.locator('.catalogue-record')).toHaveCount(1);
 await page.getByRole('link',{name:'Read record & original ↗'}).click();
 await expect(page.getByRole('heading',{name:rows[0].title,exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Open original scan / file'}).click();
 if(rows[0].mime_type==='text/plain')await expect(page.getByRole('heading',{name:'Original plain-text file'})).toBeVisible();
 await expect(page.getByRole('region',{name:'Full reviewed text',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'AI summary & questions'}).click();
 await expect(page.getByRole('region',{name:'Source-specific AI'})).toBeVisible();
 await expect(page.getByText('AI-generated summaries and answers · verify against the source')).toBeVisible();
 // Opening the AI controls does not make a generation request.
 await page.getByRole('button',{name:'Full reviewed text',exact:true}).click();
 await expect(page.getByRole('region',{name:'Full reviewed text',exact:true})).toBeVisible();
});

test('native video captions follow reviewed cue timings (synthetic media, mocked public API)',async({page})=>{
 const fixture='work/redesign-caption-fixture.mp4';
 test.skip(!fs.existsSync(fixture),'Requires the documented synthetic ffmpeg fixture');
 const id='11111111-1111-4111-8111-111111111111';
 await page.route(`**/api/archive/catalog/${id}`,route=>route.fulfill({json:{document:{id,title:'Synthetic caption test',description:'Software fixture, not historical material',language:'English',material_type:'video',mime_type:'video/mp4',rights_statement:'Self-created test fixture',source_name:'Synthetic fixture',source_record_locator:'https://example.invalid',checksum:'test',original_filename:'synthetic.mp4'},pages:[],text_revision:null}}));
 await page.route(`**/api/archive/documents/${id}/recording`,route=>route.fulfill({json:{status:'verified',transcript:[{start:0,end:1,text:'Synthetic first cue'},{start:1,end:2,text:'Synthetic second cue'}]}}));
 await page.route(`**/api/archive/documents/${id}/playback`,route=>route.fulfill({contentType:'video/mp4',body:fs.readFileSync(fixture)}));
 await page.goto(`/archive/${id}`);
 await expect.poll(()=>page.locator('video').evaluate(e=>(e as HTMLMediaElement).duration)).toBe(2);
 await expect.poll(()=>page.locator('video').evaluate(e=>(e as HTMLMediaElement).textTracks[0]?.cues?.length)).toBe(2);
 await expect.poll(()=>page.locator('video').evaluate(e=>(e as HTMLMediaElement).readyState)).toBeGreaterThanOrEqual(2);
 await page.locator('video').evaluate(async e=>{const v=e as HTMLMediaElement;v.muted=true;await v.play();});
 await expect.poll(()=>page.locator('video').evaluate(e=>(e as HTMLMediaElement).currentTime),{intervals:[50]}).toBeGreaterThan(1);
 await page.locator('video').evaluate(e=>(e as HTMLMediaElement).pause());
 await expect(page.locator('.transcript-cue').filter({hasText:'Synthetic second cue'})).toHaveAttribute('data-active','true');
 await expect.poll(()=>page.locator('video').evaluate(e=>((e as HTMLMediaElement).textTracks[0]?.activeCues?.[0] as VTTCue)?.text)).toBe('Synthetic second cue');
 await page.getByLabel('Search this transcript').fill('first');await expect(page.locator('.transcript-cue')).toHaveCount(1);
});

test('exhibition topics lead to activities and evidence without duplicate catalogue',async({page,request})=>{
 const rows=await(await request.get('/api/archive/learning?kind=story')).json();
 test.skip(!rows.length,'Requires published activity');
 await page.goto('/experience');
 await expect(page.getByRole('heading',{name:'Explore the legacy'})).toBeVisible();
 await expect(page.getByRole('searchbox')).toHaveCount(0);
 await expect(page.getByRole('link',{name:/leaderboard/i})).toHaveCount(0);
 await page.locator('.exhibition-plaque').filter({hasText:rows[0].topic}).click();
 await expect(page.getByRole('heading',{name:rows[0].topic,exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:rows[0].title,exact:true}).first()).toBeVisible();
 await page.locator('.exhibit-evidence summary').first().click();
 const source=page.locator('.exhibit-evidence a').first();
 await expect(source).toHaveAttribute('href',/\/archive\/.+\?revision=/);
 await source.click();await expect(page.getByRole('heading',{level:1})).not.toHaveText('Document reader');
 await page.goto('/experience/not-a-published-topic');
 await expect(page.getByRole('heading',{name:'Exhibition unavailable'})).toBeVisible();
 await page.goto('/experience/100%25');await expect(page.getByRole('heading',{name:'100%',exact:true})).toBeVisible();
});

test('catalogue pagination uses applied filters and suppresses stale results on error',async({page})=>{
 // Explicit browser API simulation: not proof of production holdings or authorization.
 const queries:string[]=[];let fail=false;
 await page.route('**/api/archive/catalog?*',route=>{
  const url=new URL(route.request().url());queries.push(url.search);
  if(fail)return route.fulfill({status:503,json:{}});
  const start=Number(url.searchParams.get('offset')||0);
  return route.fulfill({json:Array.from({length:start===0?25:1},(_,i)=>({id:`fixture-${start+i}`,title:`Synthetic source ${start+i}`,description:'Browser fixture only',language:'English',material_type:'document',source_name:'Test fixture',mime_type:'text/plain'}))});
 });
 await page.goto('/archive');await expect(page.locator('.catalogue-record')).toHaveCount(24);
 await page.getByLabel('Search title or description').fill('not yet applied');
 await page.getByRole('button',{name:'Next page',exact:true}).click();
 await expect(page.locator('.catalogue-record')).toHaveCount(1);expect(queries.at(-1)).toContain('offset=24');expect(queries.at(-1)).not.toContain('not+yet+applied');
 fail=true;await page.getByRole('button',{name:'Search archive',exact:true}).click();
 await expect(page.getByRole('main').getByRole('alert')).toContainText('temporarily unavailable');await expect(page.locator('.catalogue-record')).toHaveCount(0);
 fail=false;await page.getByRole('button',{name:'Retry archive'}).click();await expect(page.locator('.catalogue-record')).toHaveCount(24);
});

test('exhibition and catalogue fit mobile and desktop viewports',async({page})=>{
 for(const width of [390,768,1366]){
  await page.setViewportSize({width,height:900});
  for(const path of ['/archive','/experience','/experience/Life%20and%20Constitution']){
   await page.goto(path);await expect(page.getByRole('heading',{level:1})).toBeVisible();
   if(path==='/archive')await expect(page.locator('.catalogue-record').first()).toBeVisible();else if(path==='/experience')await expect(page.locator('.exhibition-plaque').first()).toBeVisible();else await expect(page.locator('.exhibit-entry').first()).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
   await page.screenshot({path:`outputs/redesign-${path.split('/').length>2?'topic':path.split('/')[1]}-${width}.png`,fullPage:true});
  }
 }
});

test('catalogue and exhibition retain keyboard access at large text and high contrast',async({page,request})=>{
 const matches=await(await request.get('/api/archive/catalog?q=Constitution&limit=25')).json();
 expect(matches.length).toBeGreaterThan(0);
 await page.setViewportSize({width:390,height:844});await page.goto('/archive');
 await expect(page.locator('.catalogue-record').first()).toBeVisible();
 await page.getByText('Accessibility & language',{exact:true}).click();
 await page.getByRole('combobox',{name:'Text size',exact:true}).selectOption('140');
 await page.getByLabel('High contrast',{exact:true}).check();
 await page.getByLabel('Reduce motion',{exact:true}).check();
 await page.getByText('Accessibility & language',{exact:true}).click();
 await expect(page.locator('html')).toHaveCSS('font-size','22.4px');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByLabel('Search title or description').focus();await page.keyboard.type('Constitution');
 await page.getByRole('button',{name:'Search archive',exact:true}).focus();await page.keyboard.press('Enter');
 await expect(page.locator('.catalogue-record')).toHaveCount(Math.min(24,matches.length));
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'EXPERIENCE',exact:true}).click();
 await expect(page.locator('.exhibition-plaque')).toHaveCount(1);
 await page.locator('.exhibition-plaque').focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('heading',{name:'Life and Constitution',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'outputs/redesign-large-text-contrast.png',fullPage:true});
});








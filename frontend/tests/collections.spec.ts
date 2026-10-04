import {expect,test} from '@playwright/test';

test('archive collection navigation and legacy audio entry reuse existing destinations',async({page},testInfo)=>{
  const origin=new URL(testInfo.project.use.baseURL!).origin;
  await page.goto('/archive');
  await page.getByRole('navigation',{name:'Archive collections'}).getByRole('link',{name:'Photographs',exact:true}).click();
  await expect(page).toHaveURL(`${origin}/archive?collection=photographs`);
  await page.getByRole('navigation',{name:'Archive collections'}).getByRole('link',{name:'Videos',exact:true}).click();
  await expect(page).toHaveURL(`${origin}/archive?collection=videos`);
  await page.getByRole('button',{name:'← Back',exact:true}).click();
  await expect(page).toHaveURL(`${origin}/archive?collection=photographs`);
  await page.getByRole('navigation',{name:'Archive collections'}).getByRole('link',{name:'All archive records',exact:true}).click();
  await expect(page.getByRole('form',{name:'Search the archive'})).toBeVisible();
  await page.goto('/archive?collection=audio');
  await expect(page).toHaveURL(`${origin}/speeches`);
  await expect(page.getByRole('heading',{name:'Speeches & recordings',exact:true})).toBeVisible();
});

test('Back never leaves the app for a previous external origin (simulated entry page)',async({page},testInfo)=>{
  await page.route('http://entry.example.invalid/',route=>route.fulfill({contentType:'text/html',body:'<p>Test entry page</p>'}));
  await page.goto('http://entry.example.invalid/');
  await page.goto('/archive?collection=photographs');
  await page.getByRole('button',{name:'← Back',exact:true}).click();
  await expect(page).toHaveURL(`${new URL(testInfo.project.use.baseURL!).origin}/archive`);
});

test('photograph sections are disjoint and image opens its own reader (mocked records)',async({page})=>{
  const item={id:'11111111-1111-4111-8111-111111111111',title:'Synthetic approved image',description:'Software test only',mime_type:'image/png',material_type:'photograph',source_name:'Synthetic fixture'};
  await page.route('**/api/archive/catalog?*',route=>{
    const params=new URL(route.request().url()).searchParams;
    expect(params.get('collection')).toBe('photographs');
    return route.fulfill({json:params.get('origin')==='dataset'&&!params.get('q')?[item]:[]});
  });
  await page.route(`**/api/archive/catalog/${item.id}`,route=>route.fulfill({json:{document:{...item,language:'English',source_record_locator:'https://example.invalid',rights_statement:'Synthetic fixture',checksum:'test',original_filename:'synthetic.png'},pages:[],text_revision:null}}));
  await page.route('**/thumbnail',route=>route.fulfill({status:404}));
  await page.goto('/archive?collection=photographs');
  await expect(page.getByRole('region',{name:'From the supplied dataset'}).getByRole('heading',{name:item.title})).toBeVisible();
  await expect(page.getByRole('region',{name:'Other archive content'}).getByRole('heading',{name:'No approved records available'})).toBeVisible();
  await expect(page.getByText('Preview unavailable. Open the record for its original.')).toBeVisible();
  await page.getByRole('link',{name:'Open record & original ↗'}).click();
  await expect(page.getByRole('heading',{level:1,name:item.title})).toBeVisible();
  await expect(page.getByText('No verified transcription is available. Unreviewed OCR is not shown publicly.')).toBeVisible();
  await expect(page.getByRole('link',{name:'Download preserved original'})).toHaveAttribute('href',`/api/archive/documents/${item.id}/original`);
});

test('collection failure is not an empty result and retry recovers (mocked API)',async({page})=>{
  await page.route('**/api/archive/catalog?*',route=>route.fulfill({status:503,json:{detail:'unavailable'}}));
  await page.goto('/archive?collection=videos');
  await expect(page.locator('main').getByRole('alert')).toHaveCount(2);
  await expect(page.getByText('No approved records available')).toHaveCount(0);
  await page.unroute('**/api/archive/catalog?*');
  await page.route('**/api/archive/catalog?*',route=>route.fulfill({json:[]}));
  await page.getByRole('button',{name:'Retry collection'}).first().click();
  await expect(page.getByRole('region',{name:'From the supplied dataset'}).getByText('No approved records available')).toBeVisible();
});

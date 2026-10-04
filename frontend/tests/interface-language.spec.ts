import {expect, test, Page} from '@playwright/test';
import strings from '../src/interface-strings.json';

// Synthetic translations prove UI contracts, not Bhashini linguistic quality.
async function mockLanguage(page:Page, fail=false) {
  await page.route('**/api/archive/interface/languages', r=>r.fulfill({json:{languages:[
    {code:'en',label:'English',enabled:true},{code:'hi',label:'Hindi',enabled:true}
  ],confirmed_pairs:[['en','hi']]}}));
  await page.route('**/api/archive/interface/translations', r=>{
    const body=r.request().postDataJSON();
    expect(Object.keys(body).sort()).toEqual(['keys','target_language']);
    expect(body.target_language).toBe('hi');
    for(const key of body.keys) expect(key in strings).toBe(true);
    if(fail)return r.fulfill({status:503,json:{detail:'Synthetic unavailable'}});
    return r.fulfill({json:{translations:Object.fromEntries(body.keys.map((key:keyof typeof strings)=>[key,`हिन्दी ${strings[key]}`])),missing:[]}});
  });
}
async function switchHindi(page:Page) {
  await page.locator('.access-bar details > summary').click();
  await page.getByTestId('interface-language').selectOption('hi');
  await expect(page.locator('html')).toHaveAttribute('lang','hi');
  await expect(page.getByRole('button',{name:'हिन्दी Retry language service',exact:true})).toBeVisible();
}

test('visitor language switches dynamic labels and accessibility without translating content (mocked language)',async({page,request})=>{
  await mockLanguage(page);
  const recordingCount=(await(await request.get('/api/archive/recordings')).json()).length;
  const contentRequests:string[]=[];
  page.on('request',r=>{if(/\/translation$/.test(r.url())||r.url().endsWith('/research/ask'))contentRequests.push(r.url());});
  for(const path of ['/','/archive','/archive?collection=photographs','/speeches','/experience','/ai','/system']) {
    await page.goto(path);
    await switchHindi(page);
    await expect(page.locator('.site-header nav')).toContainText('हिन्दी ARCHIVE');
    if(path==='/speeches') await expect(page.locator('main > p[role="status"]')).toHaveText(`हिन्दी ${recordingCount} published recording${recordingCount===1?'':'s'} shown`);
    await page.getByTestId('interface-language').selectOption('en');
    await expect(page.locator('html')).toHaveAttribute('lang','en');
  }
  await page.goto('/');
  await page.locator('.access-bar details > summary').click();
  await page.getByRole('combobox',{name:'Text size',exact:true}).selectOption('140');
  await page.getByLabel('High contrast',{exact:true}).check();
  await page.getByLabel('Reduce motion',{exact:true}).check();
  await expect(page.locator('html')).toHaveCSS('font-size','22.4px');
  await expect(page.locator('html')).toHaveAttribute('data-contrast','true');
  await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
  expect(contentRequests).toEqual([]);
});

test('staff strings and entered data survive language switching (mocked staff and language; no production login)',async({page})=>{
  await mockLanguage(page);
  await page.route('**/api/archive/documents',r=>r.fulfill({json:[]}));
  await page.route('**/api/archive/staff/**',r=>{
    expect(r.request().method()).toBe('GET');
    return r.fulfill({json:r.request().url().endsWith('/me')?{role:'admin',login:'synthetic-curator'}:[]});
  });
  await page.goto('/staff');
  await expect(page.locator('main > p[role="status"]')).toHaveText('');
  await page.getByLabel('Staff login',{exact:true}).fill('synthetic-curator');
  await page.getByLabel('Password',{exact:true}).fill('synthetic-only');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('button',{name:'Sign out',exact:true})).toBeVisible();
  await page.locator('.staff-add input[type="file"]').setInputFiles({name:'synthetic.txt',mimeType:'text/plain',buffer:Buffer.from('SYNTHETIC UNSUBMITTED UI TEST')});
  await page.locator('.staff-add').getByRole('button',{name:'Continue',exact:true}).click();
  await page.locator('.staff-add input[name="title"]').fill('Unchanged synthetic entered title');
  await switchHindi(page);
  await expect(page.getByRole('heading',{name:'हिन्दी Curator workspace',exact:true})).toBeVisible();
  await expect(page.locator('main > p[role="status"]')).toHaveText('हिन्दी Signed in as synthetic-curator');
  await expect(page.getByRole('button',{name:'हिन्दी Needs Review',exact:true})).toBeVisible();
  await expect(page.locator('.staff-add input[name="title"]')).toHaveValue('Unchanged synthetic entered title');
  await page.getByTestId('interface-language').selectOption('en');
  await expect(page.getByRole('button',{name:'Sign out',exact:true})).toBeVisible();
});

test('reader translation is explicit, labelled and preserves source/citations (mocked translation only)',async({page,request})=>{
  await mockLanguage(page);
  const id='8ce2df4c-c4e2-4ed1-bf9e-244881273e82';
  const before=await(await request.get(`/api/archive/catalog/${id}`)).json();
  let calls=0;
  await page.route(`**/api/archive/documents/${id}/translation`,r=>{
    calls++;expect(r.request().postDataJSON()).toEqual({revision:before.text_revision,sequence:1,target_language:'hi',fallback:'none'});
    return r.fulfill({json:{translation:'कृत्रिम अनुवाद परीक्षण',machine_generated:true,review_status:'unreviewed',provider:'synthetic',source:{revision:before.text_revision,sequence:1,text_sha256:'synthetic-hash',reader_url:`/archive/${id}?revision=${before.text_revision}#page-1`}}});
  });
  await page.goto(`/archive/${id}`);
  await expect(page.locator('.text-page pre').first()).toHaveText(before.pages[0].text);
  await switchHindi(page);
  expect(calls).toBe(0);
  await expect(page.locator('.text-page pre').first()).toHaveText(before.pages[0].text);
  await page.getByRole('button',{name:'हिन्दी Translate this verified section into Hindi',exact:true}).first().click();
  await expect(page.getByText('हिन्दी Machine translation · unreviewed. Compare with the original.',{exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'हिन्दी Open exact source section',exact:true})).toHaveAttribute('href',`/archive/${id}?revision=${before.text_revision}#page-1`);
  expect(calls).toBe(1);
  expect(await(await request.get(`/api/archive/catalog/${id}`)).json()).toEqual(before);
});

test('unavailable interface translations retain usable English (mocked outage)',async({page})=>{
  await mockLanguage(page,true);
  await page.goto('/');await page.locator('.access-bar details > summary').click();
  await page.getByTestId('interface-language').selectOption('hi');
  await expect(page.getByText(/Translation unavailable; missing text remains English/)).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  await expect(page.getByRole('button',{name:'Enter Kiosk Mode',exact:true})).toBeVisible();
  await page.getByTestId('interface-language').selectOption('en');
});

test('malformed capability response cannot crash the shared layout (mocked response)',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/archive/interface/languages',r=>r.fulfill({json:[]}));
  await page.goto('/quiz/synthetic-unpublished');
  await page.locator('.access-bar details > summary').click();
  await expect(page.getByText('Language service unavailable. English remains available.',{exact:true})).toBeVisible();
  await expect(page.getByTestId('interface-language').locator('option[value="hi"]')).toHaveJSProperty('disabled',true);
  await expect(page.getByRole('button',{name:'Start reviewed quiz',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});

async function mockExpandedLanguages(page:Page) {
  await page.route('**/api/archive/interface/languages',r=>r.fulfill({json:{languages:[
    {code:'en',label:'English',enabled:true},
    {code:'hi',label:'हिन्दी - Hindi',enabled:true},
    {code:'mr',label:'मराठी - Marathi',enabled:true},
    {code:'ta',label:'தமிழ் - Tamil',enabled:false},
  ],confirmed_pairs:[['en','hi'],['en','mr']]}}));
  await page.route('**/api/archive/interface/translations',r=>{
    const body=r.request().postDataJSON();
    expect(['hi','mr']).toContain(body.target_language);
    expect(Object.keys(body).sort()).toEqual(['keys','target_language']);
    const prefix=body.target_language==='mr'?'मराठी':'हिन्दी';
    return r.fulfill({json:{target_language:body.target_language,missing:[],
      translations:Object.fromEntries(body.keys.map((key:keyof typeof strings)=>[key,`${prefix} ${strings[key]}`]))}});
  });
}

test('backend language list, persistence, navigation and per-language dictionaries (mocked)',async({page})=>{
  await mockExpandedLanguages(page);
  const contentRequests:string[]=[];
  page.on('request',r=>{if(/\/translation$|\/research\/ask$/.test(r.url()))contentRequests.push(r.url());});
  await page.goto('/');await page.locator('.access-bar details > summary').click();
  const selector=page.getByTestId('interface-language');
  await expect(selector.locator('option[value="mr"]')).toHaveText('मराठी - Marathi');
  await expect(selector.locator('option[value="ta"]')).toHaveJSProperty('disabled',true);
  await selector.selectOption('mr');
  await expect(page.locator('.site-header nav')).toContainText('मराठी ARCHIVE');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang','mr');
  await page.goto('/staff');
  await expect(page.getByRole('heading',{name:'मराठी Curator workspace',exact:true})).toBeVisible();
  await page.locator('.access-bar details > summary').click();
  await expect(selector).toHaveValue('mr');
  await selector.selectOption('hi');
  await expect(page.locator('.site-header nav')).toContainText('हिन्दी ARCHIVE');
  await expect(page.locator('.site-header nav')).not.toContainText('मराठी');
  await selector.selectOption('en');await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  expect(await page.evaluate(()=>localStorage.getItem('archive-interface-language'))).toBe('en');
  expect(contentRequests).toEqual([]);
});

for(const saved of ['ta','bra','../mr'])test(`unavailable or unsupported persisted language ${saved} falls back to English (mocked)`,async({page})=>{
  await mockExpandedLanguages(page);
  await page.addInitScript(value=>localStorage.setItem('archive-interface-language',value),saved);
  let translations=0;page.on('request',r=>{if(r.url().endsWith('/interface/translations'))translations++;});
  await page.goto('/');await page.locator('.access-bar details > summary').click();
  await expect(page.getByTestId('interface-language').locator('option[value="mr"]')).toBeAttached();
  await expect(page.getByTestId('interface-language')).toHaveValue('en');
  expect(translations).toBe(0);
});

test('blocked storage and malformed translations keep interface usable (mocked)',async({page})=>{
  await mockExpandedLanguages(page);
  await page.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw new Error('Synthetic blocked storage');}});});
  await page.route('**/api/archive/interface/translations',r=>r.fulfill({json:{translations:[],missing:[]}}));
  await page.goto('/');await page.locator('.access-bar details > summary').click();
  await page.getByTestId('interface-language').selectOption('mr');
  await expect(page.getByText('Translation unavailable; missing text remains English.',{exact:true})).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  await expect(page.getByRole('button',{name:'Enter Kiosk Mode',exact:true})).toBeVisible();
});

test('inconsistent capabilities cannot restore a saved language (mocked)',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('archive-interface-language','mr'));
  await page.route('**/api/archive/interface/languages',r=>r.fulfill({json:{
    languages:[{code:'en',label:'English',enabled:true},{code:'mr',label:'Marathi',enabled:true}],confirmed_pairs:[]}}));
  await page.goto('/');await page.locator('.access-bar details > summary').click();
  await expect(page.getByText('Language service unavailable. English remains available.',{exact:true})).toBeVisible();
  await expect(page.getByTestId('interface-language')).toHaveValue('en');
});

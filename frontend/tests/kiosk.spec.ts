import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import strings from '../src/interface-strings.json';

test.use({ launchOptions: { executablePath: process.env.ARCHIVE_E2E_BROWSER } });

// Deterministic UI/speech tests: interface provider responses are mocked here.
test.beforeEach(async ({page})=>{
  await page.route('**/api/archive/interface/languages',r=>r.fulfill({json:{
    languages:[{code:'en',label:'English',enabled:true},{code:'hi',label:'Hindi',enabled:true}],
    confirmed_pairs:[['en','hi']],
  }}));
  await page.route('**/api/archive/interface/translations',r=>{
    const translated:Record<string,string>={ARCHIVE:'अभिलेखागार','Audio guide':'ऑडियो सहायता'};
    return r.fulfill({json:{translations:Object.fromEntries(r.request().postDataJSON().keys.map((key:keyof typeof strings)=>[key,translated[strings[key]]||(strings[key].startsWith('Welcome to')?'हिन्दी '+strings[key]:strings[key])])),missing:[]}});
  });
});

test('visitor navigation, keyboard focus, portrait and landscape, and accessibility settings', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Discover a legacy');
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
  await page.keyboard.press('Control+Home');
  await page.getByRole('link', { name: 'Skip to main content' }).focus();
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused();
  await page.keyboard.press('Enter');
  for (const viewport of [{ width: 1366, height: 768 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/kiosk-${viewport.width}.png`, fullPage: true });
  }
  await page.getByText('Accessibility & language', { exact: true }).click();
  await page.getByRole('combobox', { name: 'Text size', exact: true }).selectOption('140');
  await expect(page.locator('html')).toHaveCSS('font-size', '22.4px');
  await page.getByLabel('High contrast', { exact: true }).check();
  await expect(page.locator('html')).toHaveAttribute('data-contrast', 'true');
  await page.getByLabel('Reduce motion', { exact: true }).check();
  await expect(page.locator('html')).toHaveAttribute('data-motion', 'reduced');
  await page.getByTestId('interface-language').selectOption('hi');
  await expect(page.getByRole('navigation')).toContainText('अभिलेखागार');
  await page.getByTestId('interface-language').selectOption('en');
  await page.getByRole('combobox', { name: 'Text size', exact: true }).selectOption('100');
  await page.getByRole('navigation').getByRole('link', { name: 'EXPERIENCE' }).click();
  await expect(page.getByRole('heading', {name:'Explore the legacy'})).toBeVisible();
  await expect(page.getByRole('button', { name: 'End session', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Enter Kiosk Mode', exact: true }).click();
  await page.getByRole('button', { name: 'End session', exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  expect(errors).toEqual([]);
});

test('browser fullscreen enters and exits through visible controls', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Enter Kiosk Mode', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Boolean(document.fullscreenElement))).toBe(true);
  await page.getByRole('button', { name: 'Exit Kiosk Mode', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Boolean(document.fullscreenElement))).toBe(false);
});

test('read-aloud controls use the speech API and expose missing voices (API simulation, not an audio listening test)', async ({ page }) => {
  await page.addInitScript(() => {
    let spoke = false;
    Object.defineProperty(window, 'speechSynthesis', { value: {
      getVoices: () => [{ localService: true, lang: 'en-US', name: 'Synthetic API test voice' }],
      speak: () => { spoke = true; document.documentElement.dataset.spoke = String(spoke); },
      cancel: () => {}, pause: () => {}, resume: () => {},
    } });
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: class { text: string; constructor(text: string) { this.text = text; } } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Audio guide', exact: false }).click();
  await expect(page.locator('html')).toHaveAttribute('data-spoke', 'true');
  await page.getByRole('button', { name: 'Pause audio' }).click();
  await page.getByRole('button', { name: 'Resume audio' }).click();
  await page.getByRole('button', { name: 'Stop audio' }).click();
  await expect(page.getByRole('button', { name: 'Pause audio' })).toBeDisabled();
  await page.getByText('Accessibility & language', { exact: true }).click();
  await page.getByTestId('interface-language').selectOption('hi');
  await expect(page.locator('.settings-panel [role="status"]')).toContainText('Machine-translated interface');
  await page.getByRole('button', { name: 'ऑडियो सहायता', exact: false }).click();
  await expect(page.locator('.access-bar > .notice')).toContainText('No local voice');
});

test('real isolated upload → processing → review → publication → visitor reader → research → withdrawal', async ({ page, request }) => {
  test.setTimeout(300000);
  test.skip(!process.env.ARCHIVE_E2E_AUTH_FILE, 'Requires isolated fixture server');
  const auth = JSON.parse(fs.readFileSync(process.env.ARCHIVE_E2E_AUTH_FILE!, 'utf8'));
  const headers = { Authorization: `Basic ${Buffer.from(`${auth.login}:${auth.password}`).toString('base64')}` };
  const content = 'SYNTHETIC KIOSK TEST ONLY. Synthetic reading rooms have blue chairs.';
  const metadata = { title: 'SYNTHETIC KIOSK TEST ONLY', source_name: 'Locally authored synthetic fixture', source_locator: 'https://example.invalid/kiosk-test', source_record_locator: 'https://example.invalid/kiosk-test/item', rights_statement: 'Locally authored software test only; not historical material.', provenance_confirmed: true, language: 'en', original_filename: 'synthetic-kiosk.txt', access_level: 'public' };
  const upload = await request.post(`/api/archive/staff/documents?metadata=${encodeURIComponent(JSON.stringify(metadata))}`, { headers: { ...headers, 'Content-Type': 'text/plain' }, data: content });
  expect(upload.status()).toBe(201);
  const item = (await upload.json()).id; const base = `/api/archive/staff/documents/${item}`;
  expect((await request.get(`/api/archive/catalog/${item}`)).status()).toBe(404);
  expect((await request.post(`${base}/processing`, { headers, data: {} })).status()).toBe(202);
  await expect.poll(async () => (await (await request.get(`${base}/processing`, { headers })).json()).status, { timeout: 190000, intervals: [1500] }).toBe('succeeded');
  const extraction = await (await request.get(`${base}/text`, { headers })).json();
  const pages = extraction.segments.map((p: { sequence: number; text: string }) => ({ sequence: p.sequence, text: p.text }));
  expect((await request.post(`${base}/text/revisions`, { headers, data: { base_revision: 1, pages, note: 'Synthetic kiosk review' } })).status()).toBe(201);
  expect((await request.post(`${base}/text/verify`, { headers, data: { revision: 2, original_compared: true } })).status()).toBe(200);
  expect((await request.post(`${base}/transition`, { headers, data: { action: 'verify', metadata_reviewed: true } })).status()).toBe(200);
  expect((await request.get(`/api/archive/catalog/${item}`)).status()).toBe(404);
  expect((await request.post(`${base}/transition`, { headers, data: { action: 'publish' } })).status()).toBe(200);
  await page.goto('/archive');
  await page.getByLabel('Search title or description').fill(metadata.title);
  await page.getByRole('button', { name: 'Search archive', exact: true }).click();
  await page.getByRole('heading', { name: metadata.title }).getByRole('link').click();
  await expect(page.getByRole('heading', { name: 'Curator-verified text' })).toBeVisible();
  await expect(page.getByRole('region',{name:'Verified text',exact:true}).locator('pre')).toHaveText(content);
  await page.getByRole('button', { name: 'Open original scan / file' }).click();
  await expect(page.getByRole('heading', { name: 'Original plain-text file' })).toBeVisible();
  expect(await (await request.get(`/api/archive/documents/${item}/original`)).text()).toBe(content);
  // Wait for the real worker's lexical index; this also checks the configured model, if present.
  await expect.poll(async () => {
    const response = await request.post('/api/archive/research/ask', { data: { question: 'blue chairs' }, timeout: 110000 });
    return (await response.json()).sources.some((s: { item_id: string }) => s.item_id === item);
  }, { timeout: 180000, intervals: [2000] }).toBe(true);
  await page.goto(`/ai?source=${item}`);
  await expect(page.getByLabel('Research scope')).toHaveValue(item);
  await page.getByLabel('Your question').fill('What color are the synthetic reading room chairs?');
  await page.getByRole('button', { name: 'Ask the archive', exact: false }).click();
  await expect(page.getByRole('heading', { name: 'Verified source excerpts' })).toBeVisible({ timeout: 110000 });
  const source = page.locator('details.source').filter({ hasText: metadata.title });
  await source.locator('summary').click();
  await expect(source.getByRole('blockquote')).toHaveText(content);
  await source.getByRole('link', { name: 'Read verified source' }).click();
  await expect(page).toHaveURL(new RegExp(`${item}\\?revision=2#page-1`));
  expect((await request.post(`${base}/transition`, { headers, data: { action: 'withdraw' } })).status()).toBe(200);
  expect((await request.get(`/api/archive/catalog/${item}`)).status()).toBe(404);
  expect((await request.get(`/api/archive/documents/${item}/original`)).status()).toBe(404);
});

test('assistant explains no results and offers retry on connection failure (UI error simulation)', async ({ page }) => {
  await page.route('**/api/archive/research/ask', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'insufficient_sources', paragraphs: [], sources: [], warning: '', message: 'The archive does not currently contain enough verified, published information to answer this question.' }) }));
  await page.goto('/ai');
  await page.getByLabel('Your question').fill('A question without sources');
  await page.getByRole('button', { name: 'Ask the archive', exact: false }).click();
  await expect(page.getByText('The archive does not currently contain enough verified, published information to answer this question.', { exact: true })).toBeVisible();
  await page.unroute('**/api/archive/research/ask');
  await page.route('**/api/archive/research/ask', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Synthetic connection failure' }) }));
  await page.getByLabel('Your question').fill('Try another question');
  await page.getByRole('button', { name: 'Ask the archive', exact: false }).click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('Synthetic connection failure');
  await expect(page.getByRole('button', { name: 'Retry question' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear conversation' }).click();
  await expect(page.getByRole('heading', { name: 'What would you like to explore?' })).toBeVisible();
});


test('real assistant greeting, scope and clear session without archival evidence', async ({page})=>{
 await page.goto('/ai');
 for(const question of ['Hello','Tell me a joke']) {
  await page.getByLabel('Your question').fill(question);
  await page.getByRole('button',{name:'Ask the archive',exact:false}).click();
  const turn=page.getByRole('article').last();
  await expect(turn).toContainText(question==='Hello'?'Hello! I can help':'No archive search was performed');
  await expect(turn.getByRole('heading',{name:'Verified source excerpts'})).toHaveCount(0);
 }
 await page.getByRole('button',{name:'Clear conversation'}).click();
 await expect(page.getByRole('article')).toHaveCount(0);
 await expect(page.getByLabel('Your question')).toHaveValue('');
});


test('explicit source scope stays narrow when source is absent from catalog (UI contract)',async({page})=>{
 const id='11111111-1111-4111-8111-111111111111';
 await page.route('**/api/archive/catalog',route=>route.fulfill({json:[]}));
 let requested='';await page.route('**/api/archive/research/ask',route=>{requested=route.request().postDataJSON().item_id;return route.fulfill({json:{status:'insufficient_sources',paragraphs:[],sources:[],warning:'',message:'No eligible source in this scope.'}});});
 await page.goto(`/ai?source=${id}`);
 await expect(page.getByLabel('Research scope')).toHaveValue(id);
 await page.getByLabel('Your question').fill('Summarize this source');
 await page.getByRole('button',{name:'Ask the archive',exact:false}).click();
 await expect(page.getByText('No eligible source in this scope.',{exact:true})).toBeVisible();
 expect(requested).toBe(id);
});



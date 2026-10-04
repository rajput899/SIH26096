import { expect, test } from '@playwright/test';
import fs from 'node:fs';

test.use({ launchOptions: { executablePath: process.env.ARCHIVE_E2E_BROWSER } });

test('real processing, page corrections, version history and independent text verification', async ({ page, request }) => {
  test.setTimeout(240000);
  test.skip(!process.env.ARCHIVE_E2E_AUTH_FILE || !process.env.PROCESSING_E2E_PDF,
    'Requires isolated processing fixture server and synthetic scanned PDF');
  const auth = JSON.parse(fs.readFileSync(process.env.ARCHIVE_E2E_AUTH_FILE!, 'utf8'));
  await page.goto('/staff');
  await expect(page.getByText('Loading archive…', { exact: true })).toHaveCount(0);
  await page.getByLabel('Staff login').fill(auth.login);
  await page.getByLabel('Password', { exact: true }).fill(auth.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Upload original' })).toBeVisible();
  await page.getByLabel('Original file', { exact: false }).setInputFiles(process.env.PROCESSING_E2E_PDF!);
  await page.getByRole('button', {name:'Continue',exact:true}).click();
  await page.locator('.staff-add').getByLabel('Title', { exact: true }).fill('SYNTHETIC PROCESSING TEST ONLY');
  await page.getByLabel('Language', { exact: true }).fill('en');
  await page.getByRole('button', {name:'Continue',exact:true}).click();
  await page.getByLabel('Source name').fill('Locally authored test fixture');
  await page.getByLabel('Verified source URL').fill('https://example.invalid/synthetic');
  await page.getByLabel('Source record URL').fill('https://example.invalid/synthetic/two-pages');

  await page.getByLabel('Rights / permission statement').fill('Locally authored synthetic test; not historical material');

  await page.getByLabel('Access after publication').selectOption('public');
  await page.getByLabel('I checked the source locator', { exact: false }).check();
  const uploaded = page.waitForResponse(r=>r.request().method()==='POST' && r.url().includes('/staff/documents?metadata='));
  await page.getByRole('button', { name: 'Preserve original' }).click();
  expect((await uploaded).status()).toBe(201);
  await expect(page.getByRole('article').filter({ hasText: 'SYNTHETIC PROCESSING TEST ONLY' })).toContainText('SYNTHETIC PROCESSING TEST ONLY');
  // Chrome may evict a completed browser response body from its inspector cache.
  // Resolve the newly rendered record through the authenticated API instead.
  const records = await request.get('/api/archive/staff/documents', {
    headers: {Authorization: `Basic ${Buffer.from(`${auth.login}:${auth.password}`).toString('base64')}`},
  });
  expect(records.status()).toBe(200);
  const matches = (await records.json()).filter((row: {title: string}) => row.title === 'SYNTHETIC PROCESSING TEST ONLY');
  expect(matches).toHaveLength(1);
  const id = matches[0].id;
  const record = page.getByRole('article').filter({hasText: 'SYNTHETIC PROCESSING TEST ONLY'});
  await record.getByText('Document processing and text review', { exact: true }).click();
  await record.getByRole('button', { name: 'Queue extraction' }).click();
  await expect(async () => {
    await record.getByRole('button', { name: 'Refresh processing status' }).click();
    await expect(record.getByLabel('Text segment 1', { exact: true })).toBeVisible();
  }).toPass({ timeout: 190000, intervals: [2000] });
  await expect(record.getByLabel('Text segment 1', { exact: true })).toHaveValue(/ALPHA/);
  await expect(record.getByLabel('Text segment 2', { exact: true })).toHaveValue(/BETA/);
  const original = await record.getByLabel('Text segment 1', { exact: true }).inputValue();
  await record.getByLabel('Text segment 1', { exact: true }).fill(`${original}\nSYNTHETIC REVIEW CORRECTION`);
  await record.getByLabel('Review/correction note').fill('Synthetic browser review evidence');
  await record.getByRole('button', { name: 'Save reviewed text as new revision' }).click();
  await expect(record.getByText('Text revision 2:', { exact: false })).toBeVisible();
  await record.getByLabel('Text history').selectOption('1');
  await expect(record.getByLabel('Text segment 1', { exact: true })).toHaveValue(original);
  await expect(record.getByLabel('Text segment 1', { exact: true })).toBeDisabled();
  await record.getByLabel('Text history').selectOption('2');
  await record.getByLabel('I compared every page with the original and checked corrections.').check();
  await record.getByRole('button', { name: 'Verify current text' }).click();
  await expect(record.getByText('Text revision 2:', { exact: false })).toContainText('verified');
  // Text verification must not change the document's separate metadata lifecycle.
  await expect(page.getByRole('article').filter({ hasText: 'SYNTHETIC PROCESSING TEST ONLY' })).toContainText('uploaded');
  await expect(record.getByRole('button', { name: 'Publish record and original' })).toHaveCount(0);
  await record.getByRole('button',{name:'Confirm original, metadata, provenance and rights reviewed'}).click();
  await record.getByRole('button',{name:'Publish record and original'}).click();
  await expect(record.getByText('published · public · document · en',{exact:true})).toBeVisible();
  await page.goto(`/archive/${id}`);
  await expect(page.getByRole('region',{name:'Verified text',exact:true}).getByRole('heading',{name:'Page 1',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next page',exact:true}).click();
  await expect(page.getByRole('region',{name:'Verified text',exact:true}).getByRole('heading',{name:'Page 2',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Open original scan / file'}).click();
  await expect(page.getByTitle('Original PDF: SYNTHETIC PROCESSING TEST ONLY')).toHaveAttribute('src',/#page=2/);
  await page.getByLabel('Scan zoom').selectOption('150');
  await expect(page.getByTitle('Original PDF: SYNTHETIC PROCESSING TEST ONLY')).toHaveAttribute('src',/zoom=150/);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await expect.poll(async()=>{const r=await request.post('/api/archive/research/ask',{data:{question:'Summarize this source',item_id:id}});return (await r.json()).sources?.length;},{timeout:30000}).toBeGreaterThan(0);
  await page.getByRole('button',{name:'AI summary & questions'}).click();
  const assistant=page.getByRole('region',{name:'Source-specific AI'});
  await assistant.getByRole('button',{name:'Summarize verified excerpts'}).click();
  await expect(assistant.locator('details')).not.toHaveCount(0);
  await assistant.getByRole('button',{name:'Clear source conversation'}).click();
  await expect(assistant.locator('details')).toHaveCount(0);

});



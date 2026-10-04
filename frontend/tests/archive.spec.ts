import { expect, test } from '@playwright/test';
import fs from 'node:fs';

test.use({ launchOptions: { executablePath: process.env.ARCHIVE_E2E_BROWSER } });

test('isolated real admin upload, reload, verification, publication and withdrawal', async ({ page, browser }) => {
  test.skip(!process.env.ARCHIVE_E2E_AUTH_FILE, 'Requires isolated browser fixture server');
  const auth = JSON.parse(fs.readFileSync(process.env.ARCHIVE_E2E_AUTH_FILE!, 'utf8'));
  await page.goto('/staff');
  await expect(page.getByRole('heading', { name: 'Curator workspace', exact: true })).toBeVisible();
  async function login() {
    await expect(page.getByText('Loading archive…', { exact: true })).toHaveCount(0);
    await page.getByLabel('Staff login').fill(auth.login);
    await page.getByLabel('Password', { exact: true }).fill(auth.password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Upload original' })).toBeVisible();
  }
  await login();
  await page.getByLabel('Original file', { exact: false }).setInputFiles({
    name: 'synthetic.txt', mimeType: 'text/plain', buffer: Buffer.from('SYNTHETIC BROWSER TEST ONLY\n'),
  });
  await page.getByRole('button', {name:'Continue',exact:true}).click();
  await page.locator('.staff-add').getByLabel('Title', { exact: true }).fill('SYNTHETIC BROWSER TEST ONLY');
  await page.getByLabel('Language', { exact: true }).fill('en');
  await page.getByRole('button', {name:'Continue',exact:true}).click();
  await page.getByLabel('Source name').fill('Synthetic test source');
  await page.getByLabel('Verified source URL').fill('https://example.invalid/fixture');
  await page.getByLabel('Source record URL').fill('https://example.invalid/fixture/item');

  await page.getByLabel('Rights / permission statement').fill('Synthetic fixture; no archival holdings');
  await page.getByLabel('Access after publication').selectOption('public');

  await page.getByLabel('I checked the source locator', { exact: false }).check();
  const uploadResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().includes('/staff/documents?metadata='));
  await page.getByRole('button', { name: 'Preserve original' }).click();
  expect((await uploadResponse).status()).toBe(201);
  await expect(page.getByRole('article').getByText('uploaded · public · document · en', {exact:true})).toBeVisible();
  await page.reload();
  await login();
  await expect(page.getByRole('article')).toContainText('SYNTHETIC BROWSER TEST ONLY');
  const visitor = await browser.newPage();
  await visitor.goto('/archive');
  await expect(visitor.getByText('Loading published records…', { exact: true })).toHaveCount(0);
  await expect(visitor.getByRole('article')).toHaveCount(0);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download original' }).click();
  const download = await downloadPromise;
  expect(fs.readFileSync((await download.path())!, 'utf8')).toBe('SYNTHETIC BROWSER TEST ONLY\n');
  await page.getByRole('button', { name: 'Confirm original, metadata, provenance and rights reviewed' }).click();
  await expect(page.getByRole('article').getByText('verified · public · document · en', {exact:true})).toBeVisible();
  await visitor.reload();
  await expect(visitor.getByText('Loading published records…', { exact: true })).toHaveCount(0);
  await expect(visitor.getByRole('article')).toHaveCount(0);
  await page.getByRole('button', { name: 'Publish record and original' }).click();
  await expect(page.getByRole('article').getByText('published · public · document · en', {exact:true})).toBeVisible();
  await visitor.reload();
  await expect(visitor.getByText('Loading published records…', { exact: true })).toHaveCount(0);
  await expect(visitor.getByRole('article')).toContainText('SYNTHETIC BROWSER TEST ONLY');
  await page.screenshot({ path: 'test-results/archive-staff.png', fullPage: true });
  await page.getByRole('button', { name: 'Withdraw', exact: true }).click();
  await expect(page.getByRole('article').getByText('withdrawn · public · document · en', {exact:true})).toBeVisible();
  await visitor.reload();
  await expect(visitor.getByText('Loading published records…', { exact: true })).toHaveCount(0);
  await expect(visitor.getByRole('article')).toHaveCount(0);
  await visitor.close();
});


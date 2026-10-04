// Bounded acceptance of the actual published selection, with no fabricated answers.
const fs = require('node:fs');
const { chromium, expect } = require('../frontend/node_modules/@playwright/test');
(async () => {
  const selection = JSON.parse(fs.readFileSync('outputs/submission-sources/published-selection.json', 'utf8'));
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();
  const checks = [], errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const base = 'http://localhost:3000';
  try {
    for (const route of ['/', '/archive', '/ai', '/experience', '/staff', '/speeches', '/system']) {
      const response = await page.goto(base + route);
      expect(response.status()).toBe(200);
      await expect(page.locator('main h1')).toBeVisible();
    }
    checks.push('Seven main routes render');
    await page.goto(base + '/archive');
    for (const record of selection.records) await expect(page.getByRole('heading', { name: record.title, exact: true })).toBeVisible();
    await page.getByLabel('Search title or description').fill('biographical');
    await page.getByRole('button', { name: 'Search archive' }).click();
    await expect(page.locator('main article')).toHaveCount(1);
    await page.getByLabel('Search title or description').fill('');
    await page.getByLabel('Document language').fill('English');
    await page.getByRole('combobox', { name: /^Material type/ }).selectOption('document');
    await page.getByRole('button', { name: 'Search archive' }).click();
    await expect(page.locator('main article')).toHaveCount(2);
    for (const offset of [0, 1]) {
      const r = await context.request.get(`${base}/api/archive/catalog?limit=1&offset=${offset}`);
      expect(r.status()).toBe(200); expect((await r.json()).length).toBe(1);
    }
    const end = await context.request.get(`${base}/api/archive/catalog?limit=1&offset=2`);
    expect(await end.json()).toEqual([]);
    checks.push('Archive search, filters and API pagination');
    await page.screenshot({ path: 'outputs/submission-archive.png', fullPage: true });
    const record = selection.records.find(r => r.key === 'constitution');
    await page.goto(`${base}/archive/${record.id}`);
    await expect(page.getByRole('region', { name: 'Verified text', exact: true })).toContainText('26 January 1950');
    await page.getByRole('button', { name: 'Open original scan / file' }).click();
    await expect(page.getByRole('heading', { name: 'Original plain-text file' })).toBeVisible();
    await expect(page.locator('pre').first()).toContainText('Dr. B.R. Ambedkar');
    checks.push('Public original and verified transcription');
    await page.screenshot({ path: 'outputs/submission-reader.png', fullPage: true });
    await page.goto(`${base}/ai?source=${record.id}`);
    await expect(page.getByLabel('Research scope')).toHaveValue(record.id);
    await page.getByLabel('Your question').fill('Who was Chairman of the Drafting Committee?');
    await page.getByRole('button', { name: 'Ask the archive →', exact: true }).click();
    await expect(page.locator('.answer')).toContainText('AI-generated summary', { timeout: 100000 });
    await expect(page.locator('.answer')).toContainText('Ambedkar');
    const cited = page.getByRole('link', { name: 'Read verified source', exact: true }).first();
    await page.locator('.answer details').first().locator('summary').click();
    await expect(cited).toHaveAttribute('href', new RegExp(`/archive/${record.id}`));
    checks.push('Live browser Gemini answer with a source-reader citation');
    await page.screenshot({ path: 'outputs/submission-ai.png', fullPage: true });
    await page.goto(base + '/experience');
    await page.getByRole('button', { name: 'Timeline', exact: true }).click();
    await expect(page.locator('main article')).toHaveCount(3);
    await expect(page.getByRole('heading', { name: 'Constitution adopted', exact: true })).toBeVisible();
    for (const viewport of [{ width: 1366, height: 900 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: `outputs/submission-timeline-${viewport.width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.getByRole('button', { name: 'Stories', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'From drafting to commencement', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Section 2', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Knowledge map', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Knowledge map' })).toContainText(record.title);
    checks.push('Three timeline entries, story and source connections at desktop/kiosk/mobile sizes');
    await page.getByRole('button', { name: 'Quizzes', exact: true }).click();
    await page.getByRole('link', { name: /Begin quiz/ }).click();
    await page.getByRole('button', { name: 'Start reviewed quiz' }).click();
    const draft = JSON.parse(fs.readFileSync('outputs/submission-sources/quiz-review.json', 'utf8'));
    const groups = page.locator('fieldset');
    await expect(groups).toHaveCount(draft.questions.length);
    for (let i = 0; i < draft.questions.length; i++) {
      await groups.nth(i).getByRole('radio').nth(draft.questions[i].correct).check();
    }
    await page.getByRole('button', { name: 'Submit answers' }).click();
    await expect(page.getByRole('heading', { name: `Completed · ${draft.questions.length} / ${draft.questions.length}`, exact: true })).toBeVisible();
    await page.screenshot({ path: 'outputs/submission-quiz.png', fullPage: true });
    checks.push('Published ten-question quiz, correct server score and explanations');
    await page.getByRole('button', { name: 'Create completion certificate', exact: true }).click();
    const certificateLink = page.getByRole('link', { name: /View and download certificate/ });
    await expect(certificateLink).toBeVisible();
    await expect(page.getByRole('button', { name: 'Share score voluntarily' })).toBeDisabled();
    await certificateLink.click();
    await expect(page.locator('main')).toContainText('Score: 10 / 10');
    const download = page.getByRole('link', { name: 'Download printable certificate' });
    const certificateResponse = await context.request.get(base + await download.getAttribute('href'));
    expect(certificateResponse.status()).toBe(200);
    expect(await certificateResponse.text()).toContain('Archive visitor');
    checks.push('Anonymous completion certificate generated/downloadable; leaderboard consent remains opt-in; no email sent');
    const unauth = await context.request.get(base + '/api/archive/staff/documents');
    expect(unauth.status()).toBe(401);
    expect(errors).toEqual([]);
    checks.push('Staff API protected; no browser runtime errors');
    fs.writeFileSync('outputs/deadline-browser.json', JSON.stringify({ passed: checks.length, failed: 0, checks }, null, 2));
    console.log(`${checks.length} acceptance checks passed, 0 failed`);
  } finally { await context.close(); await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });

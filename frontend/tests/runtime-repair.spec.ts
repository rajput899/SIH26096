import {test,expect} from '@playwright/test';
test('routes remain separate through direct loads and navigation; live recording counts',async({page,request},info)=>{
 for(const [route,title] of [['/','Discover a legacy.'],['/archive','The Archive'],['/experience','Explore the legacy'],['/speeches','Speeches & recordings'],['/ai','AI Research Assistant']]){
  await page.goto(route);await expect(page.locator('main')).toHaveCount(1);await expect(page.locator('main h1')).toContainText(title);await expect(page.locator('.path-card')).toHaveCount(route==='/'?6:0);
  if(route==='/speeches'){const rows=await(await request.get('/api/archive/recordings')).json();await expect(page.getByText(`${rows.length} published recordings shown`,{exact:true})).toBeVisible();if(!rows.length)await expect(page.getByRole('heading',{name:'No recordings have been published yet'})).toBeVisible();}
 }
 await page.getByRole('link',{name:'Home',exact:true}).click();await page.locator('.path-card[href="/speeches"]').click();await expect(page.locator('.hero')).toHaveCount(0);await page.getByRole('link',{name:'Home',exact:true}).click();await expect(page.locator('.path-card')).toHaveCount(6);await expect(page.getByLabel('Find a recording')).toHaveCount(0);
 await page.screenshot({path:info.outputPath('home-desktop.png'),fullPage:true});
});
test('normal browsing does not auto-clear; kiosk warns, clears explicitly and times out only in kiosk',async({page})=>{
 await page.clock.install();await page.goto('/ai');await page.getByLabel('Your question').fill('Keep this unsent question');await expect(page.getByRole('button',{name:'End session',exact:true})).toHaveCount(0);
 await page.clock.fastForward(420000);await expect(page.getByLabel('Your question')).toHaveValue('Keep this unsent question');await expect(page.getByText('Session cleared. Welcome to the archive.',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Enter Kiosk Mode',exact:true}).click();await expect(page.getByRole('button',{name:'End session',exact:true})).toBeVisible();await page.clock.fastForward(305000);await expect(page.getByText('This session will clear after one more minute of inactivity.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Continue my visit'}).click();await expect(page.getByLabel('Your question')).toHaveValue('Keep this unsent question');await page.getByRole('button',{name:'End session',exact:true}).click();await expect(page).toHaveURL('http://localhost:3000/');await expect(page.getByText('Session cleared. Welcome to the archive.',{exact:true})).toBeVisible();
 await page.clock.fastForward(11000);await expect(page.getByText('Session cleared. Welcome to the archive.',{exact:true})).toHaveCount(0);
 await page.locator('.path-card[href="/ai"]').click();await page.getByLabel('Your question').fill('Kiosk timeout draft');await page.clock.fastForward(365000);await expect(page).toHaveURL('http://localhost:3000/');
 await page.getByRole('button',{name:'Exit Kiosk Mode',exact:true}).click();await expect(page.getByRole('button',{name:'End session',exact:true})).toHaveCount(0);
});
test('accessibility controls fit desktop/mobile at enlarged text without covering content (live interface cache)',async({page},info)=>{
 test.setTimeout(120000);
 for(const width of [1366,390]){await page.setViewportSize({width,height:900});await page.goto('/');await page.getByText('Accessibility & language',{exact:true}).click();await page.getByRole('combobox',{name:'Text size',exact:true}).selectOption('140');await page.getByLabel('High contrast',{exact:true}).check();await page.getByLabel('Reduce motion',{exact:true}).check();await page.getByTestId('interface-language').selectOption('hi');await expect(page.locator('.site-header nav')).toContainText(/[\u0900-\u097f]/,{timeout:60000});await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');await expect(page.locator('html')).toHaveCSS('font-size','22.4px');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const footer=await page.locator('.access-bar').boundingBox(),main=await page.locator('main').boundingBox();expect(footer!.y).toBeGreaterThanOrEqual(main!.y+main!.height-1);
 await page.getByTestId('interface-language').selectOption('en');await page.getByLabel('High contrast',{exact:true}).uncheck();await page.screenshot({path:info.outputPath(`settings-${width}.png`),fullPage:true});await page.getByRole('combobox',{name:'Text size',exact:true}).selectOption('100');await page.getByText('Accessibility & language',{exact:true}).click();await page.screenshot({path:info.outputPath(`home-${width}.png`),fullPage:true});}
});

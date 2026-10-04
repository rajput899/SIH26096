import {expect,test} from '@playwright/test';

test('six matching boxed cards remain in one section on desktop tablet and phone',async({page},info)=>{
 for(const width of [1366,768,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/');
  await expect(page.getByText('An accessible reading and research space. Take your time.',{exact:true})).toBeVisible();
  const cards=page.locator('section[aria-labelledby="choose"] a.path-card');await expect(cards).toHaveCount(6);
  for(const title of ['AI Research Assistant','The Archive','Timeline & stories','Speeches & recordings','Manuscripts & Letters','Media'])await expect(cards.getByRole('heading',{name:title,exact:true})).toHaveCount(1);
  for(const title of ['Manuscripts & Letters','Media']){
   const card=cards.filter({has:page.getByRole('heading',{name:title,exact:true})});
   await expect(card).toHaveCSS('border-top-width','1px');await expect(card).toHaveCSS('border-radius','10px');
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.locator('.path-grid').scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath(`home-${width}.png`),fullPage:true});
 }
});

test('Media reuses photo/video archive destinations and audio remains speeches',async({page},info)=>{
 const origin=new URL(info.project.use.baseURL!).origin;
 await page.goto('/');await page.locator('.path-card').filter({has:page.getByRole('heading',{name:'Media',exact:true})}).click();
 await expect(page).toHaveURL(`${origin}/archive?collection=media`);
 for(const [kind,label] of [['photographs','Browse photographs →'],['videos','Browse videos →']]){
  await page.getByRole('link',{name:label,exact:true}).click();await expect(page).toHaveURL(`${origin}/archive?collection=${kind}`);
  await expect(page.getByRole('heading',{name:'From the supplied dataset',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Other archive content',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'← Back',exact:true}).click();await expect(page).toHaveURL(`${origin}/archive?collection=media`);
 }
 await page.getByRole('link',{name:'Home',exact:true}).click();
 await page.locator('.path-card[href="/speeches"]').click();await expect(page).toHaveURL(`${origin}/speeches`);
 await page.goto('/');await page.locator('.path-card[href="/archive?collection=manuscripts"]').click();
 await expect(page.getByRole('heading',{level:1,name:'Manuscripts & Letters'})).toBeVisible();
});

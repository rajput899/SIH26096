import {expect,test} from '@playwright/test';

test('recording service failure, retry and true empty collection are distinct (API simulation)',async({page})=>{
 let unavailable=true;
 await page.route('**/api/archive/recordings',route=>route.fulfill({status:unavailable?503:200,json:unavailable?{detail:'Synthetic outage'}:[]}));
 await page.goto('/speeches');
 await expect(page.getByRole('main').getByRole('alert')).toContainText('temporarily unavailable');
 await expect(page.getByRole('heading',{name:'No recordings have been published yet'})).toHaveCount(0);
 unavailable=false;await page.getByRole('button',{name:'Retry recordings'}).click();
 await expect(page.getByRole('heading',{name:'No recordings have been published yet'})).toBeVisible();
 await expect(page.getByRole('main').getByRole('status')).toHaveText('0 published recordings shown');
 await expect(page.getByRole('link',{name:'Browse published source records →'})).toHaveAttribute('href','/archive');
});

test('recording filters show no-match feedback and clear without losing results (API simulation)',async({page})=>{
 const id='11111111-1111-4111-8111-111111111111';
 await page.route('**/api/archive/recordings',route=>route.fulfill({json:[{id,title:'Synthetic recording fixture',description:'A software testing room',mime_type:'audio/wav',language:'English',rights_statement:'Self-created test fixture'}]}));
 await page.route(`**/api/archive/documents/${id}/recording`,route=>route.fulfill({json:null}));
 await page.route(`**/api/archive/documents/${id}/playback`,route=>route.fulfill({status:404}));
 await page.setViewportSize({width:390,height:844});await page.goto('/speeches');
 await expect(page.getByRole('heading',{name:'Synthetic recording fixture'})).toBeVisible();
 await page.getByLabel('Find a recording').fill('not present');
 await expect(page.getByRole('heading',{name:'No recordings match these filters'})).toBeVisible();
 await page.getByRole('button',{name:'Clear recording filters'}).click();
 await page.getByLabel('Find a recording').fill('software testing');
 await expect(page.getByRole('heading',{name:'Synthetic recording fixture'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

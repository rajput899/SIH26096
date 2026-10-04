import {expect,test,Page} from '@playwright/test';
const id='11111111-1111-4111-8111-111111111111';
test('reader presents structured API validation errors as an unavailable state (mocked)',async({page})=>{
 await page.route(`**/api/archive/catalog/${id}`,route=>route.fulfill({status:422,json:{detail:[{type:'uuid_parsing',msg:'Invalid identifier'}]}}));
 await page.goto(`/archive/${id}`);
 await expect(page.getByRole('main').getByRole('alert')).toContainText('Document unavailable. Check the record link or retry.');
 await expect(page.getByRole('button',{name:'Retry document',exact:true})).toBeVisible();
 await expect(page.getByRole('main')).not.toContainText('[object Object]');
 await expect(page.locator('.archival-reader')).toHaveCount(0);
});
async function fixture(page:Page,video=false,text=true){
 await page.route('**/api/archive/**',route=>{const url=route.request().url();
 if(url.endsWith(`/catalog/${id}`))return route.fulfill({json:{document:{id,title:'Synthetic reviewed source',description:'Browser fixture only',mime_type:video?'video/mp4':'image/png',material_type:video?'video':'manuscript',language:'English',source_name:'Fixture source',source_record_locator:'https://example.invalid',rights_statement:'Test fixture only',original_filename:'fixture',checksum:'test'},pages:text?[{sequence:1,page_number:video?null:1,start_seconds:video?2:null,end_seconds:video?8:null,text:'Reviewed fixture passage.'}]:[],text_revision:text?1:null}});
 if(url.endsWith('/provider'))return route.fulfill({json:{cloud:false}});
 if(url.endsWith('/recording'))return route.fulfill({json:{transcript:text?[{start:2,end:8,text:'Reviewed fixture passage.'}]:[]}});
 if(url.endsWith('/ask')){expect(route.request().postDataJSON().item_id).toBe(id);return route.fulfill({json:{status:'answered',message:'Fixture answer',warning:'',paragraphs:[{text:'Grounded fixture response',evidence:[{passage_id:'p1',quote:'Reviewed fixture passage.'}]}],sources:[{passage_id:'p1',title:'Synthetic reviewed source',excerpt:'Reviewed fixture passage.',reader_url:`/archive/${id}#page-1`,page_number:video?null:1,start_seconds:video?2:null,end_seconds:video?8:null}]}});}
 return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
 });
 await page.goto(`/archive/${id}`);
}
test('reader scan left, reviewed text details and scoped AI right; responsive (mocked)',async({page},info)=>{
 await page.setViewportSize({width:1366,height:1000});await fixture(page);
 const left=page.locator('.original-panel'),right=page.locator('.archival-reader > .verified-panel');await expect(right).toBeVisible();
 expect((await left.boundingBox())!.x).toBeLessThan((await right.boundingBox())!.x);
 const details=right.locator('.metadata'),ai=right.getByRole('region',{name:'Source-specific AI',exact:true});
 expect((await details.boundingBox())!.y).toBeGreaterThan((await right.locator('.text-page').boundingBox())!.y);
 expect((await ai.boundingBox())!.y).toBeGreaterThan((await details.boundingBox())!.y);
 await expect(details).toContainText('Unknown — not supplied');
 await page.getByLabel('Question about this source').fill('What does this source say?');await page.getByRole('button',{name:'Ask this source',exact:true}).click();
 await expect(page.getByText('Grounded fixture response')).toBeVisible();await expect(page.getByText('Synthetic reviewed source · Page 1',{exact:true})).toBeVisible();
 for(const width of [1366,390]){await page.setViewportSize({width,height:1000});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`reader-${width}.png`),fullPage:true});}
});
test('video scoped assistant renders supplied timestamps; no reviewed text disables assistant (mocked)',async({page})=>{
 await fixture(page,true);await expect(page.getByRole('button',{name:'Play from 2.0 seconds'})).toBeVisible();
 await page.getByLabel('Question about this source').fill('Explain this video');await page.getByRole('button',{name:'Ask this source',exact:true}).click();
 await expect(page.getByText('Synthetic reviewed source · 2–8 seconds',{exact:true})).toBeVisible();
 await page.unrouteAll();await fixture(page,true,false);await expect(page.getByRole('heading',{name:'AI-assisted reading unavailable'})).toBeVisible();await expect(page.getByLabel('Question about this source')).toHaveCount(0);
});
test('quiz long options align and wrap; server score and opt-in remain intact (mocked)',async({page},info)=>{
 const prompt='A long synthetic question about a reviewed source. '.repeat(8),option='A long answer option with several words to wrap cleanly. '.repeat(8);
 await page.route('**/api/archive/**',route=>{const url=route.request().url();if(url.endsWith('/attempts'))return route.fulfill({json:{attempt_id:'test-attempt',title:'Synthetic quiz',questions:[{prompt,options:[option,'Other answer']},{prompt:'Second question',options:['First','Second']}]}});if(url.endsWith('/submit')){expect(route.request().postDataJSON().answers).toEqual([0,0]);return route.fulfill({json:{score:1,total:2,feedback:[{prompt,correct_option:option,explanation:'Fixture explanation',source:{item_id:id,quote:'Fixture'}},{prompt:'Second question',correct_option:'Second',explanation:'Fixture explanation',source:{item_id:id,quote:'Fixture'}}]}});}return route.fulfill({json:[]});});
 await page.goto('/quiz/test');await page.getByRole('button',{name:'Start reviewed quiz'}).click();await expect(page.getByRole('button',{name:'Submit answers'})).toBeDisabled();
 for(const width of [1366,390]){await page.setViewportSize({width,height:1000});const labels=page.locator('.quiz-question').first().locator('.quiz-option');expect(Math.abs((await labels.nth(0).boundingBox())!.x-(await labels.nth(1).boundingBox())!.x)).toBeLessThan(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`quiz-${width}.png`),fullPage:true});}
 await page.locator('input[name="question-0"]').first().check();await page.locator('input[name="question-1"]').first().check();await expect(page.getByText('2 of 2 answered',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Submit answers'}).click();await expect(page.getByRole('heading',{name:'Completed · 1 / 2'})).toBeVisible();await expect(page.locator('.feedback-status').getByText('Correct',{exact:true})).toBeVisible();await expect(page.locator('.feedback-status').getByText('Incorrect',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Share score voluntarily'})).toBeDisabled();await expect(page.getByRole('checkbox')).not.toBeChecked();
});

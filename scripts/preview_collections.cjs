// Screenshots of the current-source production preview; no content is mutated.
const {chromium} = require('../frontend/node_modules/@playwright/test');
(async()=>{
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({viewport:{width:1366,height:900}});
  await page.goto('http://127.0.0.1:3002/');
  await page.getByRole('heading',{name:'Browse by collection'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:'outputs/collections-home-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  await page.goto('http://127.0.0.1:3002/archive?collection=photographs');
  await page.getByRole('heading',{name:'No approved records available'}).first().waitFor();
  await page.screenshot({path:'outputs/collections-mobile.png',fullPage:true});
  await browser.close();
})();

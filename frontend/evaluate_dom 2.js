const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Navigate to the app
  await page.goto('http://localhost:3000', {waitUntil: 'networkidle0'});
  
  // Click History
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find(b => b.textContent && b.textContent.includes('HISTORY'));
    if (b) b.click();
  });
  
  await page.waitForTimeout(500);
  
  // Click 'test'
  await page.evaluate(() => {
    const divs = Array.from(document.querySelectorAll('div'));
    const d = divs.find(d => d.textContent && d.textContent.includes('test'));
    if (d) d.click();
  });
  
  await page.waitForTimeout(2000);
  
  // Extract SVG
  const svgHtml = await page.evaluate(() => {
    const svg = document.querySelector('svg');
    return svg ? svg.innerHTML : 'no svg';
  });
  
  console.log(svgHtml);
  await browser.close();
})();

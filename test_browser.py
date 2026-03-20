import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        await page.goto("http://localhost:3000")
        # Click History
        await page.click("button:has-text('History')")
        # Click project test
        await page.click("text='test'")
        await page.wait_for_timeout(2000)
        svg_html = await page.evaluate("document.querySelector('svg').innerHTML")
        svg_children = await page.evaluate("document.querySelector('svg').childElementCount")
        print(f"SVG CHILDREN: {svg_children}")
        print(f"SVG HTML snippet: {svg_html[:500]}")
        await browser.close()

asyncio.run(main())

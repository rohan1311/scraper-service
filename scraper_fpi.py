import asyncio
from pyppeteer import launch


async def scrape_today():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    # Navigate to the initial page
    await page.goto("https://www.ccilindia.com/web/ccil/fpi-home-page")

    # Scrape data from the initial page
    div_selector = 'div.component-html'
    await page.waitForSelector(div_selector)
    iframes = await page.evaluate(f'''() => {{
        const div = document.querySelector('{div_selector}');
        return Array.from(div.querySelectorAll('iframe')).map(iframe => iframe.src);
    }}''')

    print('List of iframe src URLs:')
    for iframe_src in iframes:
        print(iframe_src)
        await page.goto(iframe_src)
        await page.waitForSelector('tbody')
        rows_data = await page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('tbody tr'));
            return rows.map(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                return cells.reduce((rowData, cell, index) => {
                    rowData['col' + (index + 1)] = cell.innerText;
                    return rowData;
                }, {});
            });
        }''')

        # Print the structured data
        print(rows_data)

    await browser.close()

async def scrape_yesterday():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    # Navigate to the initial page
    url = "https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FFPI&reportUnit=%2Freports%2FBondMarket%2FFPI%2Ffn_fpi_far_holding_arcv&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no&Date=2024-08-01"
    await page.goto(url, {'waitUntil': 'networkidle0'})

    # await page.waitForSelector('tbody')
    rows_data = await page.evaluate('''() => {
        const rows = Array.from(document.querySelectorAll('tbody tr'));
        return rows.map(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            return cells.reduce((rowData, cell, index) => {
                rowData['col' + (index + 1)] = cell.innerText;
                return rowData;
            }, {});
        });
    }''')

    # await page.waitForSelector('span.wrap#page_total')
    span_content = await page.evaluate('''() => {
        const span = document.querySelector('span.wrap#page_total');
        return span ? span.innerText : null;
    }''')
    number_of_pages = int(span_content.split(' ', 1)[1])

    for click in range(number_of_pages - 1):
        button_selector = 'button#page_next'
        # await page.waitForSelector(button_selector)
        await page.click(button_selector)
        print('Next Page Button clicked.')
        await page.waitForSelector('tbody')
        rows_data = await page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('tbody tr'));
            return rows.map(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                return cells.reduce((rowData, cell, index) => {
                    rowData['col' + (index + 1)] = cell.innerText;
                    return rowData;
                }, {});
            });
        }''')
        print(rows_data)

    await browser.close()

if __name__ == "__main__":
    # asyncio.get_event_loop().run_until_complete(scrape_today())
    asyncio.get_event_loop().run_until_complete(scrape_yesterday())

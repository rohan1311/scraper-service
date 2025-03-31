import os
import asyncio
import json
import time
import constants
from pyppeteer import launch
from ses import send_email
from prettytable import PrettyTable


async def scrape_table(browser, table_url):
    table_map = {}
    page = await browser.newPage()
    await page.goto(table_url, {'waitUntil': 'networkidle0'})
    await asyncio.sleep(3)
    await page.waitForSelector('span.wrap#page_total')
    span_content = await page.evaluate('''() => {
        const span = document.querySelector('span.wrap#page_total');
        return span ? span.innerText : null;
    }''')
    total_pages = 1 if (span_content is None or len(span_content.split(' ', 1)) < 2) else int(span_content.split(' ', 1)[1])
    for page_number in range(total_pages):
        if page_number > 0:
            button_selector = 'button.action.square.move.right.up#page_next'
            await page.waitForSelector(button_selector)
            next_button = await page.querySelector(button_selector)
            initial_table_content = await page.evaluate('document.querySelector("tbody").innerText')
            safe_initial_content = json.dumps(initial_table_content)
            await next_button.click()
            print('Next Page Button clicked.')
            await page.waitForFunction(
                f'document.querySelector("tbody").innerText !== {safe_initial_content}',
                timeout=60000  # Adjust timeout as needed
            )
        rows_selector = "tbody tr"
        rows = await page.querySelectorAll(rows_selector)
        await get_table_map(page, rows, table_map)

    await page.close()
    return table_map


async def get_table_map(page, rows, table_map):
    for row in rows[3:]:
        key_element = await row.querySelector('td:nth-child(3) span')
        if key_element:
            key_text = await page.evaluate('(element) => element.innerText', key_element)
            if key_text and key_text != 'Total':
                value_element = await row.querySelector('td:nth-child(4) span')
                if value_element:
                    value_text = await page.evaluate('(element) => element.innerText', value_element)
                    table_map[key_text] = float(value_text)
            else:
                break


async def compute_fpi(yesterday):
    start_time = time.time()
    url = "https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FFPI&reportUnit=%2Freports%2FBondMarket%2FFPI%2Ffn_fpi_far_holding_arcv_home&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no"
    url_prev = "https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FFPI&reportUnit=%2Freports%2FBondMarket%2FFPI%2Ffn_fpi_far_holding_arcv&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no&Date=" + yesterday
    browser = await launch(headless=True, args=['--no-sandbox'], executablePath=os.getenv('PUPPETEER_EXECUTABLE_PATH'))
    map_today = await scrape_table(browser, url)
    map_prev = await scrape_table(browser, url_prev)
    await browser.close()

    table_li = []
    head = ['Security Description', '   ', 'FPI Holding', '    ', 'D-o-D']
    diff = 0
    for key in map_today.keys():
        ind_diff = 0
        if key in map_prev.keys():
            ind_diff = round(float(map_today.get(key)) - float(map_prev.get(key)), 2)
        if ind_diff != 0:
            li = [key, '   ', round(float(map_today.get(key)), 2), '    ', ind_diff]
            table_li.append(li)
            diff = diff + ind_diff

    final_table = PrettyTable(head)
    table_li.sort(key=lambda x: x[-1], reverse=True)
    for li in table_li:
        final_table.add_row(li, divider=False)

    print(final_table.get_string())
    table_str = final_table.get_html_string()
    print("Scraped website and got cumulative difference as: ", diff)
    cumalative_diff = constants.FAR_HOLDING_EMAIL_TEXT + str(diff)
    html_body = f"""
                    <html>
                        <head></head>
                        <body>
                            <p>{cumalative_diff}</p>
                            <br>
                            {table_str}
                        </body>
                    </html>
                """
    send_email(constants.FAR_HOLDING_EMAIL_SUBJECT, constants.TEST_RECIPIENT, html_body, "html", "", "")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Time taken: {elapsed_time:.2f} seconds')


if __name__ == "__main__":
    asyncio.run(compute_fpi("2024-08-12"))

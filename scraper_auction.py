import os
import asyncio
import time
import constants
from pyppeteer import launch
from ses import send_email
from prettytable import PrettyTable, MSWORD_FRIENDLY

govt_auction_href = 'government-stock-auction-results-cut-off'
state_govt_auction_href = 'result-of-yield-based-auction-of-state-government-securities'


async def scrape_releases(browser, url):
    page = await browser.newPage()
    await page.goto(url, {'waitUntil': 'networkidle0'})
    flag = False
    while not flag:
        start_time = time.time()
        await page.waitForSelector('a.mtm_list_item_heading')
        hrefs = await page.evaluate('''() => {
               const anchors = Array.from(document.querySelectorAll('a.mtm_list_item_heading')).slice(0, 60);
               return anchors.map(anchor => anchor.href);
           }''')
        for href in hrefs:
            if state_govt_auction_href in href:
                flag = True
                await page.goto(href, {'waitUntil': 'networkidle0'})
                await page.waitForSelector('tbody')
                # rows = await page.querySelectorAll('tbody tr')
                # row_data = []
                # for row in rows[1:]:
                #     columns = await row.querySelectorAll('td')
                #     row_tuple = []
                #     for column in columns:
                #         cell_text = ''
                #         p_tag = await column.querySelector('p')
                #         p_text = await page.evaluate('(element) => element.innerText', p_tag)
                #         cell_text += p_text + ' '
                #         row_tuple.append(cell_text.strip())
                #     row_data.append(tuple(row_tuple))
                # print(row_data)
                await page.screenshot({'path': 'auction.jpg', 'fullPage': True})
        end_time = time.time()
        elapsed_time = end_time - start_time
        wait_time = 0 if elapsed_time > 1 else (2 - elapsed_time)
        print(f'Sleeping for {wait_time} seconds')
        await asyncio.sleep(wait_time)
        await page.reload()
    # return row_data


async def monitor_press_releases():
    url = "https://website.rbi.org.in/web/rbi/press-releases?delta=100"
    browser = await launch(headless=False, args=['--no-sandbox'], executablePath=os.getenv('PUPPETEER_EXECUTABLE_PATH'))
    # auction_table = await scrape_releases(browser, url)
    await scrape_releases(browser, url)
    # head = auction_table[0]
    # final_table = PrettyTable(head)
    # for li in auction_table[1:]:
    #     final_table.add_row(li)
    # final_table.set_style(MSWORD_FRIENDLY)
    # table_str = final_table.get_html_string(format=True)
    # html_body = f"""
    #                 <html>
    #                     <head></head>
    #                     <body>
    #                         <p>{constants.GOVT_AUCTION_RESULTS_EMAIL_TEXT}</p>
    #                         <br>
    #                         {table_str}
    #                     </body>
    #                 </html>
    #             """

    send_email(constants.GOVT_AUCTION_RESULTS_EMAIL_SUBJECT, constants.TEST_RECIPIENT, 'Test', "html", "./auction.jpg", "auction.jpg")
    await browser.close()


if __name__ == "__main__":
    asyncio.run(monitor_press_releases())
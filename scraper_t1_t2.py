import os
import asyncio
import json
import time
import constants
from datetime import datetime
from decimal import Decimal
from pyppeteer import launch
from ses import send_email
from prettytable import PrettyTable, MSWORD_FRIENDLY

from dynamo import get_previous_total, update_previous_total, get_previous_t1_unconfirmed, update_t1_unconfirmed


def get_total_and_update_map(security_map, deals, today, lot_type):
    total = 0
    security_to_total_map = {}
    if deals is not None:
        for deal in deals:
            security_to_total_map[deal[1]] = security_to_total_map.get(deal[1], 0) + float(deal[3])
        for security in security_to_total_map:
            total = total + security_to_total_map[security]
            security_map[security] = [str(round(security_to_total_map[security], 2)), lot_type]

        prev_security_map = get_previous_t1_unconfirmed(today)
        for security in prev_security_map:
            if security not in security_map and prev_security_map[security][1] is lot_type:
                security_map[security] = prev_security_map[security]
                total = total + float(prev_security_map[security])
    return total


async def scrape_link(browser, link_selector, idx, page_number, table):
    table_url = table['table_url']
    start_marker = 'Trade Timestamp' if table['status'] == 'confirmed' else 'Deal Timestamp'
    end_marker = 'Trades' if table['status'] == 'confirmed' else 'Deals'
    data = []
    try:
        page = await browser.newPage()
        await page.goto(table_url, {'waitUntil': 'networkidle0'})

        for click in range(page_number):
            button_selector = 'button.action.square.move.right.up#page_next'
            await page.waitForSelector(button_selector)
            await page.waitForSelector('tbody')
            next_button = await page.querySelector(button_selector)
            initial_table_content = await page.evaluate('document.querySelector("tbody").innerText')
            safe_initial_content = json.dumps(initial_table_content)
            await next_button.click()
            print('Next Page Button clicked here.')
            await page.waitForFunction(
                f'document.querySelector("tbody").innerText !== {safe_initial_content}',
                timeout=60000  # Adjust timeout as needed
            )

        await page.waitForSelector(link_selector)
        links = await page.querySelectorAll(link_selector)
        if idx < len(links):
            link = links[idx]
            await link.click()
            await page.waitForSelector('tbody tr')
            rows = await page.querySelectorAll("tbody tr")
            row_flag = False
            security_desc_row = await rows[2].querySelectorAll('td')
            security_desc_cell_data = [await page.evaluate('(cell) => cell.innerText', cell) for cell in
                                       security_desc_row]
            security_description = security_desc_cell_data[1].strip()
            for row in rows:
                cells = await row.querySelectorAll("td")
                cell_data = [await page.evaluate('(cell) => cell.innerText', cell) for cell in cells]
                if len(cell_data) > 2:
                    if start_marker in cell_data[1]:
                        row_flag = True
                        continue
                    if end_marker in cell_data[1]:
                        break
                    if row_flag:
                        data.append([table['deal_type'], security_description, cell_data[1], cell_data[2], cell_data[3], cell_data[4]])
    except Exception as e:
        print(f"Error navigating to link: {e}")
    finally:
        await page.close()

    return data


async def scrape_table(browser, table):
    table_url = table['table_url']
    combined_result = []
    total = 0
    page = await browser.newPage()
    await page.goto(table_url, {'waitUntil': 'networkidle0'})
    await asyncio.sleep(2)
    await page.waitForSelector('span.wrap#page_total')
    span_content = await page.evaluate('''() => {
        const span = document.querySelector('span.wrap#page_total');
        return span ? span.innerText : null;
    }''')
    total_pages = 1 if (span_content is None or len(span_content.split(' ', 1)) < 2) else int(span_content.split(' ', 1)[1])
    try:
        await page.waitForSelector('tbody tr', {'timeout': 1000})
        total = await page.evaluate('''() => {
                const rows = document.querySelectorAll('tbody tr');
                for (let i = 0; i < rows.length; i++) {
                    const spans = [...rows[i].querySelectorAll('td span')];
                    for (let j = 0; j < spans.length; j++) {
                        if (spans[j].innerText.includes('Total')) {
                            if (j + 2 < spans.length) {
                                return spans[j + 2].innerText;
                            }
                        }
                    }
                }
                return 0;
            }''')
        print(f'Total was found to be {total}')
    except Exception as e:
        print(f"Timeout waiting for selector tbody tr on page {table_url}: {e}")

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

        link_selector = 'tbody span._jrHyperLink.ReportExecution'
        try:
            await page.waitForSelector(link_selector, {'timeout': 1000})
        except Exception as e:
            print(f"Timeout waiting for selector {link_selector} on page {table_url}: {e}")
            continue
        links = await page.querySelectorAll(link_selector)
        tasks = [scrape_link(browser, link_selector, link_idx, page_number, table) for link_idx in
                 range(len(links))]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        page_list = [item for sublist in results if isinstance(sublist, list) for item in sublist]
        combined_result.extend(page_list)

    await page.close()
    return total, combined_result


async def compute_t1_t2():
    start_time = time.time()
    today = datetime.strftime(datetime.now(), '%d-%b-%Y')
    browser = await launch(headless=False, args=['--no-sandbox'], executablePath=os.getenv('PUPPETEER_EXECUTABLE_PATH'))
    tables = [
        {'deal_type': 't+1', 'lot_type': 'standard', 'status': 'unconfirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_unstandard_odd_lot_t1_03&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
        {'deal_type': 't+1', 'lot_type': 'odd', 'status': 'unconfirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_unstandard_odd_lot_t1_04&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
        {'deal_type': 't+2', 'lot_type': 'standard', 'status': 'confirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_standard_odd_lot_t2_01&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
        {'deal_type': 't+2', 'lot_type': 'odd', 'status': 'confirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_standard_odd_lot_t2_02&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
        {'deal_type': 't+2', 'lot_type': 'standard', 'status': 'unconfirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_unstandard_odd_lot_t2_03&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
        {'deal_type': 't+2', 'lot_type': 'odd', 'status': 'unconfirmed',
         'table_url': 'https://r.ccilindia.com/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&ParentFolderUri=%2Freports%2FBondMarket%2FNDS_OM&reportUnit=%2Freports%2FBondMarket%2FNDS_OM%2Fndsom_unstandard_odd_lot_t2_04&standAlone=true&pp=vkGhz3w3Gx6JFbnxyIcJaTL/9OiYvXo0NzCLp2C6MIn4Mx7Aub2QdLnVNJBvybJ9&decorate=no'},
    ]

    # table_tasks = [scrape_table(browser, table_url) for table_url in table_urls]
    # table_results = await asyncio.gather(*table_tasks, return_exceptions=True)
    final_results = []
    security_map = {}
    current_total = 0
    for table in tables:
        table_total, table_result = await scrape_table(browser, table)
        if table['deal_type'] == 't+1':
            table_total = get_total_and_update_map(security_map, table_result, today, table['lot_type'])
        final_results.extend(table_result)
        current_total += float(table_total)
    current_total = Decimal(str(current_total))
    print(f'current total: {current_total} and final results: {final_results}')
    await browser.close()
    # update_t1_unconfirmed(today, security_map)
    final_list_of_deals = sorted(final_results, key=lambda x: x[2])

    pretty_table = PrettyTable(
        ["Settlement", "Security Description", "Deal Timestamp", "Amount (Crs.)", "Price", "Yield"])
    for row in final_list_of_deals:
        pretty_table.add_row(row)
    pretty_table.set_style(MSWORD_FRIENDLY)
    mail_table = pretty_table.get_html_string(format=True)

    heading = "Change of Rs 100Cr detected in  FPI trades"
    html_body = f"""
                        <html>
                            <head></head>
                            <body>
                                <p>{heading}</p>
                                <br>
                                {mail_table}
                                <br>
                                {current_total}
                            </body>
                        </html>
                    """
    prev_total = get_previous_total(constants.T1_T2_TRADE_NAME_DYNAMO)
    diff = current_total - prev_total
    # if diff >= 100:
    #     send_email(constants.T1_T2_DEALS_EMAIL_SUBJECT, constants.TEST_RECIPIENT, html_body, "html", "", "")
    #     update_previous_total(constants.T1_T2_TRADE_NAME_DYNAMO, current_total)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Time taken: {elapsed_time:.2f} seconds')


if __name__ == "__main__":
    asyncio.run(compute_t1_t2())
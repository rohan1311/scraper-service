import os
import asyncio
import time
import constants
import requests
from pyppeteer import launch
from ses import send_email


async def scrape_releases(browser, url):
    page = await browser.newPage()
    await page.goto(url, {"waitUntil": "networkidle0"})
    monitoring_start_time = time.time()
    monitored_minute = 0
    while True:
        start_time = time.time()
        await page.waitForSelector('a.link2')
        href = await page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a.link2'));
                const targetAnchor = anchors.find(anchor => anchor.textContent.trim() === "Government Stock - Auction Results: Cut-off");
                return targetAnchor ? targetAnchor.href : null;
            }''')
        if href is not None:
            await page.goto(href, {"waitUntil": "networkidle0"})
            await page.waitForSelector("tbody")
            pdf_url = await page.evaluate('''() => {
                    const a_tags = Array.from(document.querySelectorAll('a[target="_blank"]'))
                    const target_a_tag = a_tags.find(a_tag => a_tag.href.trim().includes("PDF"));
                    return target_a_tag ? target_a_tag.href : null;
            }''')
            response = requests.get(pdf_url)
            if response.status_code == 200:
                with open('auction.pdf', 'wb') as f:
                    f.write(response.content)
                print(f'Downloaded PDF at {time.gmtime()} time')
            else:
                print(f"Failed to download PDF. Status code: {response.status_code}")
            # print(f'Took screenshot at {time.gmtime()} time')
            # await page.screenshot({"path": "auction.jpg", "fullPage": True})
            break
        end_time = time.time()
        elapsed_time = end_time - start_time
        wait_time = 0 if elapsed_time > 1 else (1 - elapsed_time)
        time_since_monitored = end_time - monitoring_start_time
        await asyncio.sleep(wait_time)
        # print(f'Sleeping for {wait_time} seconds')
        await page.reload()
        if (time_since_monitored / 60) > monitored_minute:
            monitored_minute = monitored_minute + 1
            print(f"Monitored for {monitored_minute} mins")


async def monitor_press_releases():
    url = 'https://rbi.org.in/scripts/BS_PressReleaseDisplay.aspx'
    browser = await launch(
        headless=False,
        args=["--no-sandbox"],
        executablePath=os.getenv("PUPPETEER_EXECUTABLE_PATH"),
    )
    await scrape_releases(browser, url)
    send_email(
        constants.GOVT_AUCTION_RESULTS_EMAIL_SUBJECT,
        constants.TEST_RECIPIENT,
        "Test",
        "html",
        "./auction.pdf",
        "auction.pdf",
    )
    if os.path.exists("auction.pdf"):
        os.remove("auction.pdf")
        print("auction.pdf was removed")
    else:
        print("The file does not exist")
    await browser.close()


if __name__ == "__main__":
    asyncio.run(monitor_press_releases())

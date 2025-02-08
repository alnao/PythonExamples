# SEE https://www.youtube.com/watch?v=RGR5Xj0Qqfs
# with     https://brdta.com/pysimplified
# see https://brightdata.com/products/scraping-browser?utm_source=brand&utm_campaign=brnd-mkt_youtube_pythonsimplified&promo=pysimplified

# PAYMENT REQUIRED

# SEE https://www.youtube.com/watch?v=RGR5Xj0Qqfs
# PART 5 starting by part4

from playwright.sync_api import sync_playwright

proxies = {
    "server": "localhost", #host from  brightdata console
    "username": "xxx", # host from  brightdata console
    "password": "xxx", # host from  brightdata console
}

#start
pw = sync_playwright().start()

#launch browser and navigate 
browser = pw.firefox.launch(
    headless=False, ## SHOW BROWSER window
    slow_mo=100    ## COLLAPSE browser afer 5 seconds
    , proxy = proxies
)
page = browser.new_page()

content = page.goto("https://www.walmart.com")
page.locator("xpath=//input[@aria-label='Search']").fill("laptop")
page.keyboard.press("Enter")

#print result
#print ( page.title )
#print ( page.url )
#print ( page.content() )

#save screenshot
#page.screenshot(path="screenshot.png")

#close browser
browser.close()


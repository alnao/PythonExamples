# SEE https://www.youtube.com/watch?v=RGR5Xj0Qqfs
# PART 4 starting by part3

from playwright.sync_api import sync_playwright
from urllib.request import urlretrieve

#start
pw = sync_playwright().start()

#launch browser and navigate 
browser = pw.firefox.launch(
    headless=False, ## SHOW BROWSER window
    slow_mo=100    ## COLLAPSE browser afer 5 seconds
)
page = browser.new_page()
content = page.goto("https://arxiv.org/search/")

# insert value in input field and click button
page.get_by_placeholder("Search term...").fill("java")
page.get_by_role("button").get_by_text("Search").nth(1).click() 
#nth(1) perchè ce ne sono 2 e devo usare il secondo

# use locator & xPath to split/extract the information
links=page.locator("xpath=//a[contains(@href, 'arxiv.org/pdf')]").all()

# print all links to PDF
for link in links:
    url = link.get_attribute("href")
    urlretrieve(url, "/tmp/" + url.split("/")[-1] + ".pdf" )
    print(url)
    # 
    


#print result
#print ( page.title )
#print ( page.url )
#print ( page.content() )

#save screenshot
#page.screenshot(path="screenshot.png")

#close browser
browser.close()

# SEE https://www.youtube.com/watch?v=RGR5Xj0Qqfs
# PART 1

# command to 
# pip install playwright --break-system-packages
# playwright install 
# playwright install-deps

# import playwright
from playwright.sync_api import sync_playwright

#start
pw = sync_playwright().start()

#launch browser and navigate 
browser = pw.firefox.launch()
page = browser.new_page()
content = page.goto("https://alnao.com/")

#print result
print ( page.title )
print ( page.url )
print ( page.content() )

#save screenshot
page.screenshot(path="screenshot.png")

#close browser
browser.close()





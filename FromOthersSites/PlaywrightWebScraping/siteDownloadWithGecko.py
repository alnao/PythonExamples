# SEE https://www.youtube.com/watch?v=RGR5Xj0Qqfs
# PART 2 starting by part1
# from https://github.com/mozilla/geckodriver/releases download version
# download geckodriver-v0.35.0-linux64.tar.gz in same folder

from playwright.sync_api import sync_playwright

#start
pw = sync_playwright().start()

#launch browser and navigate 
browser = pw.firefox.launch(
    headless=False, ## SHOW BROWSER window
    slow_mo=2000    ## COLLAPSE browser afer 5 seconds
)

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



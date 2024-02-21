from apscheduler.schedulers.background import BlockingScheduler
#"pip install apscheduler" or "apt-geg install python3-apscheduler" on debian

from plyer import notification 
#"pip install plyer" or "apt-get install python3-plyer"on debian

#ßee https://www.youtube.com/watch?v=7ahUnBhdI5o
# import requests

def sendNotification():
    notification.notify(
        title="Titolo",
        message="Messaggio",
        #app_icon=icon.png",
        timeout=10
    )

scheduler = BlockingScheduler() 
scheduler.add_job(sendNotification,'cron',hour=14,minute=39,timezone='Europe/Vienna')
#sched.add_job(run_batch, 'cron', day_of_week='mon-fri', hour='12-16', minute='5,15,25,35,45,55', timezone='America/Chicago')
scheduler.start()
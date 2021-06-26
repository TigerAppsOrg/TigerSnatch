# ----------------------------------------------------------------------
# send_notifs_cron.py
# Manages regular execution of the email notification script using a
# cron wrapper. Disable/enable using admin panel or _set_cron_status.py.
#
# Set execution interval in config:     NOTIFS_INTERVAL_SECS
# ----------------------------------------------------------------------

from sys import path
path.append('src')  # noqa

from send_notifs import *
from datetime import datetime
import pytz
from config import NOTIFS_INTERVAL_SECS
from apscheduler.schedulers.blocking import BlockingScheduler


def schedule_jobs(sched: BlockingScheduler):
    times = generate_time_intervals()
    '''uncomment the below code if we figure out a way to make the script
    automatically poll the Google Sheet for changes (i.e. need to place
    this function in a BlockingScheduler job, but as of now we're not
    sure how to do that given that it takes the BlockingScheduler itself
    as an argument)'''
    # if not did_notifs_spreadsheet_change(times):
    #     return
    # update_notifs_schedule(times)
    set_status_indicator_to_off()
    tz = pytz.timezone('US/Eastern')
    for time in times:
        start, end = time[0], time[1]
        if end <= datetime.now(tz):
            continue
        print('adding job between', start, 'and', end)
        sched.add_job(cronjob, 'interval',
                      start_date=start,
                      end_date=end,
                      timezone=tz,
                      seconds=NOTIFS_INTERVAL_SECS)
        sched.add_job(set_status_indicator_to_on, 'date',
                      run_date=start,
                      timezone=tz)
        sched.add_job(set_status_indicator_to_off, 'date',
                      run_date=end,
                      timezone=tz)
        if start <= datetime.now(tz) <= end:
            set_status_indicator_to_on()


sched = BlockingScheduler()
schedule_jobs(sched)
sched.start()

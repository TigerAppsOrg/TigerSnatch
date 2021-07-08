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
from sys import stderr
import pytz
from config import NOTIFS_INTERVAL_SECS, NOTIFS_SHEET_POLL_MINS
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler


def schedule_jobs(update_db=False):
    try:
        sched = BackgroundScheduler()
        times = generate_time_intervals()
        if update_db:
            update_notifs_schedule(times)  # update database
        set_status_indicator_to_off(log=False)
        tz = pytz.timezone('US/Eastern')
        for time in times:
            start, end = time[0], time[1]
            print('[Scheduler] adding job between', start, 'and', end)
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
        print('[Scheduler] booting new notifs scheduler')
        sched.start()
        print('[Scheduler] done booting scheduler')
        return sched
    except:
        print('[Scheduler] an error occurred in function schedule_jobs()', file=stderr)


def check_spreadsheet_maybe_schedule_new_notifs(scheds: list[BackgroundScheduler]):
    try:
        times = generate_time_intervals()
        if not did_notifs_spreadsheet_change(times):
            print('[Scheduler] no new spreadsheet datetimes detected')
            return
        print('[Scheduler] new datetimes detected - rescheduling jobs')
        print('[Scheduler] shutting down current notifs scheduler')
        scheds[-1].shutdown()  # stop and clear all current notifs jobs
        update_notifs_schedule(times)  # update database
        new_sched = schedule_jobs()  # schedule all new notifs jobs
        print('[Scheduler] replacing notifs scheduler')
        scheds.pop(0)
        scheds.append(new_sched)
        print('[Scheduler] done updating notifs scheduler')
    except:
        print('[Scheduler] an error occurred in function check_spreadsheet_maybe_schedule_new_notifs()', file=stderr)


if __name__ == '__main__':
    print('[Scheduler] this script reads from https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/edit#gid=550138744 on an interval (configurable in Config Vars) and schedules all notifications jobs according to the datetimes in the spreadsheet')
    print('[Scheduler] reboot this dyno ("notifs") in Heroku to force a re-schedule using the spreadsheet')
    sched_spreadsheet_checker = BlockingScheduler()

    # perform one scheduling check initially
    new_sched = schedule_jobs(update_db=True)
    scheds = [new_sched]

    sched_spreadsheet_checker.add_job(check_spreadsheet_maybe_schedule_new_notifs, 'interval',
                                      minutes=NOTIFS_SHEET_POLL_MINS,
                                      args=[scheds])
    sched_spreadsheet_checker.start()

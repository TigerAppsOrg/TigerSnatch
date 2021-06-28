# ----------------------------------------------------------------------
# send_notifs.py
# Script that wraps core email notification logic - designed to be run
# on a regular interval.
#
# Approximate execution frequency: 2-5 minutes after the previous
# execution completion. The script itself can take a minute or two to
# run, depending on the number of waited-on classes.
# ----------------------------------------------------------------------

import pandas as pd
from datetime import datetime
import pytz
from notify import Notify
from monitor import Monitor
from database import Database
from sys import stdout, stderr
from random import shuffle
from time import time


def cronjob():
    tic = time()
    monitor = Monitor()
    db = Database()

    db._add_system_log('cron', {
        'message': 'emails script executing'
    })

    # get all class openings (for waited-on classes) from MobileApp
    new_slots = monitor.get_classes_with_changed_enrollments()

    total = 0
    for classid, n_new_slots in new_slots.items():
        if n_new_slots == 0:
            continue
        try:
            # n_notifs = min(db.get_class_waitlist_size(classid), n_new_slots)
            n_notifs = db.get_class_waitlist_size(classid)
        except Exception as e:
            print(e, file=stderr)
            continue

        # randomly iterate through lists to ensure fairness
        ordering = list(range(n_notifs))
        shuffle(ordering)

        for i in ordering:
            try:
                notify = Notify(classid, i, n_new_slots)

                print(notify)
                print('sending email to', notify.get_netid())
                stdout.flush()

                # only if email was sent, remove user from waitlist
                if notify.send_email_html():
                    print(i+1, '/', n_notifs, 'emails sent for this class')
                    total += 1
                    # db.remove_from_waitlist(notify.get_netid(), classid)
                else:
                    print('failed to send email')
            except Exception as e:
                print(e, file=stderr)

            print()

    if total > 0:
        db._add_admin_log(
            f'sent {total} emails in {round(time()-tic)} seconds')
        db._add_system_log('cron', {
            'message': f'sent {total} emails in {round(time()-tic)} seconds'
        })
    elif total == 0:
        db._add_system_log('cron', {
            'message': f'sent 0 emails in {round(time()-tic)} seconds'
        })
    print(f'sent {total} emails in {round(time()-tic)} seconds')


def set_status_indicator_to_on():
    db = Database()
    db.set_cron_notification_status(True)


def set_status_indicator_to_off():
    db = Database()
    db.set_cron_notification_status(False)


def did_notifs_spreadsheet_change(data):
    db = Database()
    return db.did_notifs_spreadsheet_change(data)


def update_notifs_schedule(data):
    db = Database()
    db.update_notifs_schedule(data)


def generate_time_intervals():
    tz = pytz.timezone('US/Eastern')
    # see https://towardsdatascience.com/read-data-from-google-sheets-into-pandas-without-the-google-sheets-api-5c468536550
    # for how to create this link
    google_sheets_url = 'https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/gviz/tq?tqx=out:csv&sheet=Data'
    data = pd.read_csv(google_sheets_url)[['start_datetime', 'end_datetime']]
    datetimes = list(data.itertuples(index=False, name=None))
    try:
        datetimes = list(map(lambda x:
                            [tz.localize(datetime.strptime(x[0], '%Y-%m-%d %I:%M %p')),
                            tz.localize(datetime.strptime(x[1], '%Y-%m-%d %I:%M %p'))],
                            datetimes))
    except:
        print('[Scheduler] error parsing datetimes - make sure that their format is YYYY-MM-DD HH:MM AM/PM')

    # validate list of datetimes
    flat = [item for sublist in datetimes for item in sublist]
    if not all(flat[i] < flat[i+1] for i in range(len(flat)-1)):
        print('[Scheduler] WARNING: datetime intervals either overlap or are not in ascending order. This may cause duplicate emails to be sent!', file=stderr)
        return []
    if flat[-1] <= datetime.now(tz):
        print('[Scheduler] WARNING: all time intervals are in the past - please update the schedule spreadsheet and be sure to use 24-hour time', file=stderr)

    return datetimes


if __name__ == '__main__':
    # can function via single file execution, but this is not the intent
    cronjob()

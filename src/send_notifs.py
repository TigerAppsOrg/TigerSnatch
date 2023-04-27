# ----------------------------------------------------------------------
# send_notifs.py
# Script that wraps core email notification logic - designed to be run
# on a regular interval.
#
# Approximate execution frequency: 2-5 minutes after the previous
# execution completion. The script itself can take a minute or two to
# run, depending on the number of waited-on classes.
# ----------------------------------------------------------------------

from datetime import datetime, timedelta
from os import cpu_count
from sys import stderr, stdout
from time import time

import pandas as pd
import pytz
import requests
from icalendar import Calendar
from multiprocess import Pool

from config import (
    AUTO_GENERATE_NOTIF_SCHEDULE,
    NOTIFS_INTERVAL_SECS,
    OIT_NOTIFS_OFFSET_MINS,
)
from database import Database
from log_utils import *
from monitor import Monitor
from notify import Notify, send_email, send_text


"""
- start and end times for add/drop and course selection periods
- assumed to be in Eastern time and constant across all periods
- (e.g. add/drop period always starts at 6:30 AM and ends at 5:00 PM)
"""
ADD_DROP_START = timedelta(hours=6, minutes=30)  # 6:30 AM
ADD_DROP_END = timedelta(hours=17, minutes=0)  # 5:00 PM
COURSE_SELECTION_START = timedelta(hours=7, minutes=30)  # 7:30 AM
COURSE_SELECTION_END = timedelta(hours=23, minutes=59)  # 11:59 PM

TZ = pytz.timezone("US/Eastern")
ICAL_URL = "https://registrar.princeton.edu/feeds/events/ical.ics"  # academic calendar iCal feed from Registrar

_db = Database()


def cronjob(end_time):
    tic = time()
    db = Database()
    monitor = Monitor(db)

    db._add_system_log(
        "cron",
        {"message": "notifications script executing"},
        log_fn=log_notifs,
    )

    if db.get_maintenance_status():
        db._add_system_log(
            "cron",
            {"message": "app in maintenance mode: notifications script killed"},
            log_fn=log_notifs,
        )
        return

    # get all class openings (for waited-on classes) from MobileApp
    new_slots, _ = monitor.get_classes_with_changed_enrollments()

    monitor.update_live_notifs_state_active("Sending notifs (0 sent so far)...")

    names = ""
    emails_to_send, texts_to_send = [], []
    n_sections = 0
    for classid, n_new_slots in new_slots.items():
        if n_new_slots == 0:
            # cover edge case where the number of open spots is 0 (not covered in Notify)
            # this case should already be covered in get_new_mobileapp_data(), but
            # we are keeping this logic for precaution
            db.update_users_notifs_history([], classid, 0)
            continue

        try:
            notify = Notify(classid, n_new_slots, db)
            netids = notify.get_netids()
            if len(netids) == 0:
                continue
            log_notifs(f"Sending notifs for classID {classid}")
            print(notify)
            stdout.flush()

            emails_to_send.extend(notify.send_emails_html())
            texts_to_send.extend(notify.send_sms())

            monitor.update_live_notifs_state_active(
                f"Sending notifs ({len(emails_to_send) + len(texts_to_send)} sent so far)..."
            )

            names += " " + notify.get_name() + ","
            n_sections += 1

        except Exception as e:
            print(e, file=stderr)

    with Pool(cpu_count()) as pool:
        emails_res = pool.starmap(send_email, emails_to_send)
        texts_res = pool.starmap(send_text, texts_to_send)

    n_emails_sent = sum(emails_res)
    if len(emails_res) > 0 and n_emails_sent == 0:
        log_error("Failed to send emails")

    n_texts_sent = sum(texts_res)
    if len(texts_res) > 0 and n_texts_sent == 0:
        log_error("Failed to send texts")

    total = n_emails_sent + n_texts_sent
    duration = round(time() - tic)

    if total > 0:
        db._add_admin_log(
            f"sent {total} notifs in {duration} seconds ({n_sections} sections):{names[:-1]}",
            print_=False,
        )
        db.add_stats_notif_log(
            f"{total} notif{'s'[:total^1]} sent for {n_sections} section{'s'[:n_sections^1]}:{names[:-1]}"
        )
        db._add_system_log(
            "cron",
            {
                "message": f"sent {total} notifs in {duration} seconds ({n_sections} sections):{names[:-1]}"
            },
            log_fn=log_notifs,
        )
        db.increment_email_counter(total)
    elif total == 0:
        db._add_system_log(
            "cron",
            {"message": f"sent 0 notifs in {duration} seconds ({n_sections} sections)"},
            log_fn=log_notifs,
        )
    stdout.flush()

    if datetime.now(TZ) >= end_time:
        _db.set_live_notifs_status("inactive", "")
        return

    monitor.update_live_notifs_state_countdown()


def update_live_notifs_countdown(sched_job):
    try:
        next_run_time = sched_job.next_run_time
    except:
        log_error(
            "Failed to get next run time - setting countdown to NOTIFS_INTERVAL_SECS"
        )
        _db.set_live_notifs_status(
            "countdown", NOTIFS_INTERVAL_SECS, update_countdown_state=False
        )

    if next_run_time is None:
        _db.set_live_notifs_status("inactive", "")
        return

    now = datetime.now(TZ)
    time_to_next_run = (next_run_time - now).seconds + 1
    if time_to_next_run >= NOTIFS_INTERVAL_SECS:
        return
    _db.set_live_notifs_status(
        "countdown", time_to_next_run, update_countdown_state=False
    )


def set_status_indicator_to_on():
    _db.set_cron_notification_status(True)


def set_status_indicator_to_off(log=True):
    _db.set_live_notifs_status("inactive", "")
    _db.set_cron_notification_status(False, log=log)


def did_notifs_spreadsheet_change(data):
    return _db.did_notifs_spreadsheet_change(data)


def update_notifs_schedule(data):
    _db.update_notifs_schedule(data)


def generate_time_intervals():
    if AUTO_GENERATE_NOTIF_SCHEDULE:
        res = requests.get(ICAL_URL)
        res.raise_for_status()
        raw_cal_data = res.text
        cal = list(Calendar.from_ical(raw_cal_data).walk())

        keywords = set(["add/drop", "course selection"])
        non_keywords = set(["graduate student"])

        cleaned_cal = []
        for event in cal:
            if event.name != "VEVENT":
                continue

            name = event.get("summary")
            name = name.lower()

            if not any([keyword in name for keyword in keywords]):
                continue

            if any([keyword in name for keyword in non_keywords]):
                continue

            start = event.get("dtstart").dt
            end = event.get("dtend").dt

            start = datetime(year=start.year, month=start.month, day=start.day)
            end = datetime(year=end.year, month=end.month, day=end.day)

            start = TZ.localize(start)
            end = TZ.localize(end)

            if datetime.now(TZ) > end:
                continue

            if (end - start).days > 1:
                continue

            cleaned_cal.append((name, start))

        datetimes = []
        i = 0
        while i < len(cleaned_cal):
            name, start_ = cleaned_cal[i]

            if "add/drop" in name:
                if i == len(cleaned_cal) - 1:
                    break
                start = start_ + ADD_DROP_START
                end = cleaned_cal[i + 1][1] + ADD_DROP_END
                i += 1
            elif "course selection" in name:
                start = start_ + COURSE_SELECTION_START
                end = start_ + COURSE_SELECTION_END

            datetimes.append((start + timedelta(minutes=OIT_NOTIFS_OFFSET_MINS), end))
            i += 1
    else:
        # see https://towardsdatascience.com/read-data-from-google-sheets-into-pandas-without-the-google-sheets-api-5c468536550
        # for how to create this link
        google_sheets_url = "https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/gviz/tq?tqx=out:csv&sheet=Schedule"
        # google_sheets_url = "https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/gviz/tq?tqx=out:csv&sheet=Test"
        datetime_fmt = "%m/%d/%Y %I:%M %p"
        try:
            data = pd.read_csv(google_sheets_url)[
                ["start_date", "start_time", "end_date", "end_time"]
            ]
            datetimes = list(data.itertuples(index=False, name=None))
            datetimes = list(
                map(lambda x: (f"{x[0]} {x[1]}", f"{x[2]} {x[3]}"), datetimes)
            )
        except:
            log_error(
                f"Error reading Google Sheet ({google_sheets_url}) - please update/fix the Schedule tab"
            )
            return []
        try:
            datetimes = list(
                map(
                    lambda x: [
                        TZ.localize(datetime.strptime(x[0], datetime_fmt))
                        + timedelta(minutes=OIT_NOTIFS_OFFSET_MINS),
                        TZ.localize(datetime.strptime(x[1], datetime_fmt)),
                    ],
                    datetimes,
                )
            )
            datetimes = list(filter(lambda x: x[1] > datetime.now(TZ), datetimes))
        except:
            log_error("Error parsing datetimes - please update/fix the Schedule tab")
            return []

    # validate list of datetimes
    flat = [item for sublist in datetimes for item in sublist]
    if not all(flat[i] < flat[i + 1] for i in range(len(flat) - 1)):
        log_error(
            "Datetime intervals either overlap or are not in ascending order - please update/fix the Schedule tab"
        )
        return []
    if flat[-1] <= datetime.now(TZ):
        log_warning(
            "All time intervals are in the past - please update the Schedule tab"
        )

    return datetimes


def update_stats():
    try:
        stats_top_subs = _db.get_top_subscriptions(target_num=15)
        stats_total_users = _db.get_total_user_count()
        stats_total_subs = _db.get_total_subscriptions()
        stats_subbed_users = _db.get_users_who_subscribe()
        stats_subbed_sections = _db.get_num_subscribed_sections()
        stats_subbed_courses = _db.get_num_subscribed_courses()
        stats_total_notifs = _db.get_email_counter()
        stats_current_notifs = _db.get_current_email_counter()
        stats_update_time = (
            f"{(datetime.now(TZ)).strftime('%b %-d, %Y @ %-I:%M %p ET')}"
        )

        _db._db.admin.update_one(
            {},
            {
                "$set": {
                    "stats_top_subs": stats_top_subs,
                    "stats_total_users": stats_total_users,
                    "stats_total_subs": stats_total_subs,
                    "stats_subbed_users": stats_subbed_users,
                    "stats_subbed_sections": stats_subbed_sections,
                    "stats_subbed_courses": stats_subbed_courses,
                    "stats_total_notifs": stats_total_notifs,
                    "stats_update_time": stats_update_time,
                    "stats_current_notifs": stats_current_notifs,
                }
            },
        )
    except Exception as e:
        log_error("Failed to update stats on activity page")
        print(e, file=stderr)


if __name__ == "__main__":
    # can function via single file execution, but this is not the intent
    cronjob()

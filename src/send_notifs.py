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
from datetime import datetime, timedelta
import pytz
from notify import Notify
from monitor import Monitor
from database import Database
from sys import stdout, stderr
from time import time
from config import OIT_NOTIFS_OFFSET_MINS
from notify import send_email, send_text
from multiprocess import Pool
from os import cpu_count

TZ = pytz.timezone("US/Eastern")


def cronjob():
    tic = time()
    db = Database()
    monitor = Monitor(db)

    db._add_system_log("cron", {"message": "notifications script executing"})

    if db.get_maintenance_status():
        db._add_system_log(
            "cron", {"message": "app in maintenance mode: notifications script killed"}
        )
        return

    # get all class openings (for waited-on classes) from MobileApp
    new_slots, _ = monitor.get_classes_with_changed_enrollments()

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
            print(notify)
            stdout.flush()

            emails_to_send.extend(notify.send_emails_html())
            texts_to_send.extend(notify.send_sms())

            names += " " + notify.get_name() + ","
            n_sections += 1

        except Exception as e:
            print(e, file=stderr)

    with Pool(cpu_count()) as pool:
        emails_res = pool.starmap(send_email, emails_to_send)
        texts_res = pool.starmap(send_text, texts_to_send)

    n_emails_sent = sum(emails_res)
    if len(emails_res) > 0 and n_emails_sent == 0:
        print("failed to send emails")

    n_texts_sent = sum(texts_res)
    if len(texts_res) > 0 and n_texts_sent == 0:
        print("failed to send texts")

    total = n_emails_sent + n_texts_sent
    print()

    duration = round(time() - tic)

    if total > 0:
        db._add_admin_log(
            f"sent {total} emails and texts in {duration} seconds ({n_sections} sections):{names[:-1]}",
            print_=False,
        )
        db.add_stats_notif_log(
            f"{total} notif{'s'[:total^1]} sent for {n_sections} section{'s'[:n_sections^1]}:{names[:-1]}"
        )
        db._add_system_log(
            "cron",
            {
                "message": f"✅ sent {total} emails and texts in {duration} seconds ({n_sections} sections):{names[:-1]}"
            },
        )
        db.increment_email_counter(total)
    elif total == 0:
        db._add_system_log(
            "cron",
            {
                "message": f"✅ sent 0 emails and texts in {duration} seconds ({n_sections} sections)"
            },
        )
        print(f"sent 0 emails and texts in {duration} seconds ({n_sections} sections)")
        stdout.flush()


def set_status_indicator_to_on():
    db = Database()
    db.set_cron_notification_status(True)


def set_status_indicator_to_off(log=True):
    db = Database()
    db.set_cron_notification_status(False, log=log)


def did_notifs_spreadsheet_change(data):
    db = Database()
    return db.did_notifs_spreadsheet_change(data)


def update_notifs_schedule(data):
    db = Database()
    db.update_notifs_schedule(data)


def generate_time_intervals():
    tz = pytz.timezone("US/Eastern")
    # see https://towardsdatascience.com/read-data-from-google-sheets-into-pandas-without-the-google-sheets-api-5c468536550
    # for how to create this link
    google_sheets_url = "https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/gviz/tq?tqx=out:csv&sheet=Schedule"
    datetime_fmt = "%m/%d/%Y %I:%M %p"
    try:
        data = pd.read_csv(google_sheets_url)[
            ["start_date", "start_time", "end_date", "end_time"]
        ]
        datetimes = list(data.itertuples(index=False, name=None))
        datetimes = list(map(lambda x: (f"{x[0]} {x[1]}", f"{x[2]} {x[3]}"), datetimes))
    except:
        print(
            f"[Scheduler] error reading Google Sheet ({google_sheets_url}) - make sure all columns in the Schedule tab are present and properly named/formatted",
            file=stderr,
        )
        return []
    try:
        datetimes = list(
            map(
                lambda x: [
                    tz.localize(datetime.strptime(x[0], datetime_fmt))
                    + timedelta(minutes=OIT_NOTIFS_OFFSET_MINS),
                    tz.localize(datetime.strptime(x[1], datetime_fmt)),
                ],
                datetimes,
            )
        )
        datetimes = list(filter(lambda x: x[1] > datetime.now(tz), datetimes))
    except:
        print(
            "[Scheduler] error parsing datetimes - make sure that their format is YYYY-MM-DD HH:MM AM/PM",
            file=stderr,
        )
        return []

    # validate list of datetimes
    flat = [item for sublist in datetimes for item in sublist]
    if not all(flat[i] < flat[i + 1] for i in range(len(flat) - 1)):
        print(
            "[Scheduler] WARNING: datetime intervals either overlap or are not in ascending order. This may cause duplicate emails and texts to be sent!",
            file=stderr,
        )
        return []
    if flat[-1] <= datetime.now(tz):
        print(
            "[Scheduler] WARNING: all time intervals are in the past - please update the schedule spreadsheet and be sure to use 24-hour time",
            file=stderr,
        )

    return datetimes


def update_stats():
    db = Database()
    try:
        stats_top_subs = db.get_top_subscriptions(target_num=10, unique_courses=True)
        stats_total_users = db.get_total_user_count()
        stats_total_subs = db.get_total_subscriptions()
        stats_subbed_users = db.get_users_who_subscribe()
        stats_subbed_sections = db.get_num_subscribed_sections()
        stats_subbed_courses = db.get_num_subscribed_courses()
        stats_total_notifs = db.get_email_counter()
        stats_update_time = (
            f"{(datetime.now(TZ)).strftime('%b %-d, %Y @ %-I:%M %p ET')}"
        )

        db._db.admin.update_one(
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
                }
            },
        )
    except:
        print("failed to update stats on activity page", file=stderr)


if __name__ == "__main__":
    # can function via single file execution, but this is not the intent
    cronjob()

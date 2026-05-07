# ----------------------------------------------------------------------
# send_notifs_cron.py
# Manages regular execution of the email and text message  notification
# script using a cron wrapper. Disable/enable using admin panel or
# _set_cron_status.py.
#
# Set execution interval in config:     NOTIFS_INTERVAL_SECS
# ----------------------------------------------------------------------

from sys import path

path.append("src")  # noqa

from datetime import datetime, timedelta
from sys import stderr

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from _email_all_users import notify_admins_of_schedule_change
from _exec_update_all_courses import do_update_async_HARD, do_update_async_SOFT
from config import (
    GLOBAL_COURSE_UPDATE_INTERVAL_MINS,
    NOTIFS_INTERVAL_SECS,
    NOTIFS_SHEET_POLL_MINS,
    STATS_INTERVAL_MINS,
)
from log_utils import *
from send_notifs import *


def _should_notify_admins_of_schedule_change(times):
    return AUTO_GENERATE_NOTIF_SCHEDULE and len(times) > 0


def _persist_notifs_schedule_if_changed(times):
    try:
        if not did_notifs_spreadsheet_change(times):
            return False

        update_notifs_schedule(times)

        if _should_notify_admins_of_schedule_change(times):
            notify_admins_of_schedule_change(times)
        elif len(times) == 0:
            log_warning(
                "Stored empty notifications schedule without sending schedule update email"
            )

        return True
    except Exception as e:
        log_error("Failed to persist notifications schedule update")
        print(e, file=stderr)
        return False


def _build_scheduler(times):
    sched = BackgroundScheduler()
    tz = pytz.timezone("US/Eastern")
    active_notifs_window = False

    log_cron("Adding global soft course update job at 4am ET daily")
    sched.add_job(
        do_update_async_SOFT,
        "cron",
        hour="4",
        timezone=tz,
    )

    log_cron("Adding global soft course update job at 5am ET daily")
    sched.add_job(
        do_update_async_SOFT,
        "cron",
        hour="5",
        timezone=tz,
    )

    log_cron("Adding stats update job every 10 mins")
    sched.add_job(
        update_stats,
        "interval",
        minutes=STATS_INTERVAL_MINS,
    )

    log_cron(
        f"Adding global hard course update job every {GLOBAL_COURSE_UPDATE_INTERVAL_MINS} mins"
    )
    sched.add_job(
        do_update_async_HARD,
        "interval",
        minutes=GLOBAL_COURSE_UPDATE_INTERVAL_MINS,
    )

    for i, time in enumerate(times):
        start, end = time[0], time[1]
        log_cron(f"Adding notifs job between {start} and {end}")
        sched.add_job(
            cronjob,
            "interval",
            start_date=start,
            end_date=end
            - timedelta(seconds=1),  # subtract 1 second to prevent run at closing time
            timezone=tz,
            seconds=NOTIFS_INTERVAL_SECS,
            max_instances=1,
            id=str(i),
            args=[end - timedelta(seconds=NOTIFS_INTERVAL_SECS)],
        )
        log_cron(f"Adding live notifs countdown job between {start} and {end}")
        sched.add_job(
            update_live_notifs_countdown,
            "interval",
            start_date=start,
            end_date=end
            - timedelta(
                seconds=NOTIFS_INTERVAL_SECS  # subtract NOTIFS_INTERVAL_SECS seconds to prevent weird edge cases at closing time
            ),
            timezone=tz,
            seconds=1,
            args=[sched.get_job(str(i))],
        )
        sched.add_job(
            set_status_indicator_to_on,
            "date",
            run_date=start,
            timezone=tz,
        )
        sched.add_job(
            set_status_indicator_to_off,
            "date",
            run_date=end,
            timezone=tz,
        )
        if start <= datetime.now(tz) <= end:
            active_notifs_window = True

    return sched, active_notifs_window


def _sync_status_indicator(active_notifs_window):
    set_status_indicator_to_off(log=False)
    if active_notifs_window:
        set_status_indicator_to_on()


def _start_scheduler(sched):
    log_cron("Booting notifs scheduler")
    sched.start()
    log_cron("Done booting notifs scheduler")


def _shutdown_scheduler(sched):
    if sched is None:
        log_warning("No current notifs scheduler was running")
        return True

    if hasattr(sched, "running") and not sched.running:
        log_warning("Current notifs scheduler was already stopped")
        return True

    try:
        sched.shutdown()
        return True
    except Exception as e:
        log_error("Failed to shut down current notifs scheduler")
        print(e, file=stderr)
        return False


def _replace_scheduler(scheds, new_sched):
    scheds[:] = [new_sched]


def schedule_jobs(update_db=False, times=None):
    try:
        if times is None:
            times = generate_time_intervals()

        sched, active_notifs_window = _build_scheduler(times)
        _sync_status_indicator(active_notifs_window)
        _start_scheduler(sched)

        if update_db:
            _persist_notifs_schedule_if_changed(times)

        return sched
    except Exception as e:
        log_error("An error occurred in function schedule_jobs()")
        print(e, file=stderr)


def check_spreadsheet_maybe_schedule_new_notifs(scheds: list[BackgroundScheduler]):
    try:
        times = generate_time_intervals()
        if not did_notifs_spreadsheet_change(times):
            return
        log_cron("New datetimes detected - rescheduling jobs")

        new_sched, active_notifs_window = _build_scheduler(times)

        log_cron("Shutting down current notifs scheduler")
        old_sched = scheds[-1] if len(scheds) > 0 else None
        if not _shutdown_scheduler(old_sched):
            return

        _sync_status_indicator(active_notifs_window)
        _start_scheduler(new_sched)

        log_cron("Replacing notifs scheduler")
        _replace_scheduler(scheds, new_sched)
        _persist_notifs_schedule_if_changed(times)
        log_cron("Done updating notifs scheduler")
    except Exception as e:
        log_error(
            "An error occurred in function check_spreadsheet_maybe_schedule_new_notifs()"
        )
        print(e, file=stderr)


if __name__ == "__main__":
    if AUTO_GENERATE_NOTIF_SCHEDULE:
        log_cron(
            "This script automatically schedules all notifications jobs according to the official academic calendar at https://registrar.princeton.edu/academic-calendar-and-deadlines"
        )
    else:
        log_cron(
            "This script reads from https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/edit#gid=550138744 on an interval (configurable in Config Vars) and schedules all notifications jobs according to the datetimes in the spreadsheet"
        )
    log_cron(
        "Reboot this dyno (notifs) in Heroku to force a re-schedule using the spreadsheet"
    )
    sched_spreadsheet_checker = BlockingScheduler()

    # perform one scheduling check initially
    new_sched = schedule_jobs(update_db=True)
    if new_sched is None:
        raise SystemExit(1)
    scheds = [new_sched]

    sched_spreadsheet_checker.add_job(
        check_spreadsheet_maybe_schedule_new_notifs,
        "interval",
        minutes=NOTIFS_SHEET_POLL_MINS,
        args=[scheds],
    )
    sched_spreadsheet_checker.start()

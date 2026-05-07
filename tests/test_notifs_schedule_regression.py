import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pytz

ROOT = Path(__file__).resolve().parents[1]


class ModulePatch:
    def __init__(self, modules):
        self.modules = modules
        self.originals = {}

    def __enter__(self):
        for name, module in self.modules.items():
            self.originals[name] = sys.modules.get(name)
            sys.modules[name] = module

    def __exit__(self, exc_type, exc, tb):
        for name in self.modules:
            original = self.originals[name]
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def make_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def load_module(name, path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeScheduler:
    actions = []

    def __init__(self):
        self.jobs = []
        self.running = False

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append((func, trigger, kwargs))

    def get_job(self, job_id):
        return {"id": job_id}

    def start(self):
        self.running = True
        self.actions.append("start")

    def shutdown(self):
        self.running = False
        self.actions.append("shutdown")


def noop(*args, **kwargs):
    return None


class NotifsCronRegressionTests(unittest.TestCase):
    def load_cron(self):
        FakeScheduler.actions = []
        actions = []
        tz = pytz.timezone("US/Eastern")
        future_start = tz.localize(datetime.now() + timedelta(days=30))
        future_end = future_start + timedelta(hours=2)
        send_notifs = make_module(
            "send_notifs",
            AUTO_GENERATE_NOTIF_SCHEDULE=True,
            cronjob=noop,
            update_live_notifs_countdown=noop,
            update_stats=noop,
            set_status_indicator_to_on=lambda: actions.append("status_on"),
            set_status_indicator_to_off=lambda log=True: actions.append("status_off"),
            generate_time_intervals=lambda: [(future_start, future_end)],
            did_notifs_spreadsheet_change=lambda times: True,
            update_notifs_schedule=lambda times: actions.append("update"),
        )
        modules = {
            "apscheduler": make_module("apscheduler"),
            "apscheduler.schedulers": make_module("apscheduler.schedulers"),
            "apscheduler.schedulers.background": make_module(
                "apscheduler.schedulers.background",
                BackgroundScheduler=FakeScheduler,
            ),
            "apscheduler.schedulers.blocking": make_module(
                "apscheduler.schedulers.blocking",
                BlockingScheduler=FakeScheduler,
            ),
            "_email_all_users": make_module(
                "_email_all_users",
                notify_admins_of_schedule_change=lambda times: actions.append("notify"),
            ),
            "_exec_update_all_courses": make_module(
                "_exec_update_all_courses",
                do_update_async_HARD=noop,
                do_update_async_SOFT=noop,
            ),
            "config": make_module(
                "config",
                GLOBAL_COURSE_UPDATE_INTERVAL_MINS=10,
                NOTIFS_INTERVAL_SECS=120,
                NOTIFS_SHEET_POLL_MINS=1,
                STATS_INTERVAL_MINS=10,
            ),
            "log_utils": make_module(
                "log_utils",
                log_cron=noop,
                log_error=noop,
                log_warning=noop,
            ),
            "send_notifs": send_notifs,
        }
        with ModulePatch(modules):
            cron = load_module("send_notifs_cron", ROOT / "send_notifs_cron.py")
        cron.actions = actions
        return cron, actions

    def test_reschedule_with_missing_current_scheduler_persists_before_email(self):
        cron, actions = self.load_cron()

        cron.check_spreadsheet_maybe_schedule_new_notifs([None])

        self.assertIn("update", actions)
        self.assertIn("notify", actions)
        self.assertLess(actions.index("update"), actions.index("notify"))
        self.assertNotIn("shutdown", FakeScheduler.actions)

    def test_empty_schedule_still_starts_global_jobs_and_does_not_email(self):
        cron, actions = self.load_cron()

        sched = cron.schedule_jobs(update_db=True, times=[])

        self.assertIsNotNone(sched)
        self.assertTrue(sched.running)
        self.assertEqual(len(sched.jobs), 4)
        self.assertIn("update", actions)
        self.assertNotIn("notify", actions)


class SendNotifsRegressionTests(unittest.TestCase):
    def test_generate_time_intervals_handles_no_future_calendar_events(self):
        warnings = []

        class FakeDatabase:
            pass

        class FakeCalendar:
            @staticmethod
            def from_ical(raw_cal_data):
                return make_module("fake_calendar", walk=lambda: [])

        class FakeResponse:
            text = "BEGIN:VCALENDAR\nEND:VCALENDAR"

            def raise_for_status(self):
                return None

        modules = {
            "config": make_module(
                "config",
                AUTO_GENERATE_NOTIF_SCHEDULE=True,
                NOTIFS_INTERVAL_SECS=120,
                OIT_NOTIFS_OFFSET_MINS=5,
            ),
            "database": make_module("database", Database=FakeDatabase),
            "icalendar": make_module("icalendar", Calendar=FakeCalendar),
            "log_utils": make_module(
                "log_utils",
                log_error=noop,
                log_warning=lambda message: warnings.append(message),
                log_notifs=noop,
            ),
            "monitor": make_module("monitor", Monitor=object),
            "multiprocess": make_module("multiprocess", Pool=object),
            "notify": make_module(
                "notify",
                Notify=object,
                send_email=noop,
                send_text=noop,
            ),
            "requests": make_module("requests", get=lambda url: FakeResponse()),
        }
        with ModulePatch(modules):
            send_notifs = load_module("send_notifs", ROOT / "src" / "send_notifs.py")

        self.assertEqual(send_notifs.generate_time_intervals(), [])
        self.assertIn("No future notification intervals found", warnings)


if __name__ == "__main__":
    unittest.main()

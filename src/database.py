# ----------------------------------------------------------------------
# database.py
# Contains Database, a class used to communicate with the TigerSnatch
# database.
# ----------------------------------------------------------------------

from sys import stderr, stdout
import re
import certifi
from activedirectory import ActiveDirectory
from config import (
    DB_CONNECTION_STR,
    COLLECTIONS,
    MAX_LOG_LENGTH,
    MAX_WAITLIST_SIZE,
    MAX_ADMIN_LOG_LENGTH,
    HEROKU_API_KEY,
    HEROKU_APP_NAME,
    MAX_AUTO_RESUB_NOTIFS,
    NOTIFS_INTERVAL_SECS,
)
from schema import COURSES_SCHEMA, CLASS_SCHEMA, MAPPINGS_SCHEMA, ENROLLMENTS_SCHEMA
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime, timedelta
from random import randint
import pytz
import heroku3
from log_utils import *


TZ = pytz.timezone("US/Eastern")


class Database:
    # creates a reference to the TigerSnatch MongoDB database

    def __init__(self):
        self._db = MongoClient(
            DB_CONNECTION_STR,
            serverSelectionTimeoutMS=5000,
            maxIdleTimeMS=600000,
            tlsCAFile=certifi.where(),
        )

        try:
            self._db.admin.command("ismaster")
        except ConnectionFailure:
            log_error("Failed (server not available)")
            raise Exception("server unavailable")

        self._db = self._db.tigersnatch
        self._check_basic_integrity()

    """
    Retired Trades method

    # core Trade matching algorithm!

    def find_matches(self, netid, courseid):
        user_waitlists = self.get_user(netid, "waitlists")

        # sections that user is waiting for for given courseid
        user_course_waitlists = []
        for classid in user_waitlists:
            try:
                if self.is_classid_in_courseid(classid, courseid):
                    user_course_waitlists.append(classid)
            except:
                continue

        # get user's currect section
        curr_section = self.get_current_section(netid, courseid)
        if curr_section is None:
            raise Exception(
                f"current section of course {courseid} for {netid} not found - match cannot be made"
            )

        # verify that current section exists (i.e. has not been deleted/removed)
        if self.get_class_enrollment(curr_section) is None:
            print(f"no matches found for user {netid} in course {courseid}")
            return []

        matches = []
        # for each section that user wants
        for classid in user_course_waitlists:
            # skip case where user subscribes to current section
            if classid == curr_section:
                continue

            try:
                # get netids that want to swap out of the sections you want
                swapout_list = self.get_swapout_for_class(classid)
            except:
                continue

            for match_netid in swapout_list:
                # prevents self match
                if match_netid == netid:
                    continue
                # check if match wants your section
                if not curr_section in self.get_user(match_netid, "waitlists"):
                    continue
                if match_netid in matches:
                    raise Exception(
                        f"user {match_netid} has more than one current section for course {courseid}"
                    )

                match_email = self.get_user(match_netid, "email")

                try:
                    match_section = self.classid_to_sectionname(classid)
                except:
                    continue

                # ensure that only sections of the same type (e.g. P, C, S, B) are matches
                # if match_section[0] != self.classid_to_sectionname(curr_section)[0]:
                #     continue

                matches.append([match_netid, match_section, match_email])

        if not matches:
            print(f"no matches found for user {netid} in course {courseid}")
        else:
            print(f"matches found for user {netid} in course {courseid}")

        return matches
    """

    # ----------------------------------------------------------------------
    # ADMIN PANEL METHODS
    # ----------------------------------------------------------------------

    def add_disabled_course(self, courseid):
        course_data = self.get_course(courseid)
        if not course_data:
            log_error(f"{courseid} is an invalid courseID")
            return False
        try:
            self._db.admin.update_one({}, {"$addToSet": {"disabled_courses": courseid}})
            self.clear_course_waitlists(courseid, "SYSTEM_AUTO")
            return True
        except:
            log_error(f"Could not add courseID {courseid} to list of disabled courses")
            return False

    def remove_disabled_course(self, courseid):
        course_data = self.get_course(courseid)
        if not course_data:
            log_error(f"{courseid} is an invalid courseID")
            return False
        try:
            self._db.admin.update_one({}, {"$pull": {"disabled_courses": courseid}})
            return True
        except:
            log_error(
                f"Could not remove courseID {courseid} from list of disabled courses"
            )
            return False

    # prints log and adds log to admin collection to track admin activity

    def _add_admin_log(self, log, print_=True):
        if print_:
            log_system(log)
        log = f"{(datetime.now(TZ)).strftime('%b %d, %Y @ %-I:%M %p ET')} \u2192 {log}"

        self._db.admin.update_one(
            {},
            {
                "$push": {
                    "logs": {
                        "$each": [log],
                        "$position": 0,
                        "$slice": MAX_ADMIN_LOG_LENGTH,
                    }
                }
            },
        )

    # check if netid is an admin is defined in the database

    def is_admin(self, netid):
        return netid in self._db.admin.find_one({}, {"admins": 1, "_id": 0})["admins"]

    # returns MAX_ADMIN_LOG_LENGTH most recent admin logs

    def get_admin_logs(self):
        return self._db.admin.find_one({}, {"logs": 1, "_id": 0})

    # returns dictionary with all admin data (excluding logs)

    def get_admin_data(self):
        return self._db.admin.find_one({}, {"logs": 0, "_id": 0})

    # returns dictionary with app-related data

    def get_app_data(self):
        num_users = self._db.users.count_documents({})
        num_users_on_waitlists = self._db.waitlists.count_documents(
            {"waitlists": {"$not": {"$size": 0}}}
        )
        num_courses_in_db = self._db.mappings.count_documents({})
        num_sections_with_waitlists = self._db.waitlists.count_documents({})
        return {
            "num_users": num_users,
            "num_users_on_waitlists": num_users_on_waitlists,
            "num_courses_in_db": num_courses_in_db,
            "num_sections_with_waitlists": num_sections_with_waitlists,
        }

    # sets notification script status to either True (on) or False (off)

    def set_cron_notification_status(self, status, admin_netid="SYSTEM_AUTO", log=True):
        if not isinstance(status, bool):
            raise Exception("status must be a boolean")

        try:
            new_status = "on" if status else "off"
            self._db.admin.update_one({}, {"$set": {"notifs_status": new_status}})
            if log:
                self._add_admin_log(f"notification script is now {new_status}")
            self._add_system_log(
                "cron",
                {"message": f"notification script set to {new_status}"},
                netid=admin_netid,
            )
        except:
            raise Exception('ensure that key "notifs_status" is in admin collection')

    # gets notification script status; either True (on) or False (off)

    def get_cron_notification_status(self):
        try:
            return (
                self._db.admin.find_one({}, {"notifs_status": 1, "_id": 0})[
                    "notifs_status"
                ]
                == "on"
            )
        except:
            raise Exception('ensure that key "notifs_status" is in admin collection')

    # checks whether notifs schedule csv is different than database version

    def did_notifs_spreadsheet_change(self, data):
        tz = pytz.timezone("UTC")
        curr = self._db.admin.find_one({}, {"notifs_schedule": 1, "_id": 0})[
            "notifs_schedule"
        ]
        curr = [[tz.localize(pair[0]), tz.localize(pair[1])] for pair in curr]
        return curr != data

    # generates a string representing the current/next notifications interval
    def get_current_or_next_notifs_interval(self, fmt="%-m/%-d @ %-I:%M %p"):
        tz_utc = pytz.timezone("UTC")
        tz_et = pytz.timezone("US/Eastern")
        curr = self._db.admin.find_one({}, {"notifs_schedule": 1, "_id": 0})[
            "notifs_schedule"
        ]
        if len(curr) == 0:
            return "Next notifications period isn't scheduled. Notify a TigerApps member if this isn't fixed soon!"
        start, end = tz_utc.localize(curr[0][0]), tz_utc.localize(curr[0][1])
        start, end = start.astimezone(tz_et), end.astimezone(tz_et)
        now = datetime.now(tz_et)
        if now >= end:
            return "Next notifications period isn't scheduled. Notify a TigerApps member if this isn't fixed soon!"
        end_fmt = end.strftime(fmt)
        if now >= start:
            return f"Current notifications period ending on {end_fmt}."
        start_fmt = start.strftime(fmt)
        return f"Next notifications period: {start_fmt} to {end_fmt}."

    # updates notifs_schedule entry in admin collection

    def update_notifs_schedule(self, data):
        self._db.admin.update_one({}, {"$set": {"notifs_schedule": data}})

    # clears and removes users from the waitlist for class classid

    def clear_class_waitlist(self, classid, admin_netid, log_classid_skip=True):
        try:
            class_waitlist = self.get_class_waitlist(classid)["waitlist"]
            self._add_admin_log(
                f"unsubscribing users {class_waitlist} from class {classid}"
            )

            for netid in class_waitlist:
                self.remove_from_waitlist(netid, classid)

            self._add_system_log(
                "admin",
                {"message": f"subscriptions for class {classid} cleared"},
                netid=admin_netid,
            )
            return True
        except Exception as e:
            if log_classid_skip:
                log_error(f"Waitlist for classID {classid} does not exist - skipping")
                print(e, file=stderr)
            return False

    # clears and removes users from all waitlists for class classid

    def clear_course_waitlists(self, courseid, admin_netid):
        try:
            course_data = self.get_course(courseid)
            classids = [
                i.split("_")[1] for i in course_data.keys() if i.startswith("class_")
            ]
            self._add_admin_log(f"clearing subscriptions for course {courseid}")

            for classid in classids:
                self.clear_class_waitlist(classid, admin_netid, log_classid_skip=False)

            self._add_system_log(
                "admin",
                {"message": f"subscriptions for course {courseid} cleared"},
                netid=admin_netid,
            )
            return True
        except Exception as e:
            log_error(f"Failed to clear waitlists for courseID {courseid}")
            print(e, file=stderr)
            return False

    # adds netid to app blacklist

    def add_to_blacklist(self, netid, admin_netid):
        # removes user profile from users collection
        # removes user from any waitlists
        def remove_user(netid):
            log_info(f"Removing all Subscriptions for user {netid}")
            classids = self.get_user(netid, "waitlists")
            for classid in classids:
                self.remove_from_waitlist(netid, classid)

            log_info(f"Removing user {netid} from users and logs collections")
            self._db.users.delete_one({"netid": netid})
            self._db.notifs.delete_one({"netid": netid})
            self._db.logs.delete_one({"netid": netid})

        try:
            if self.is_admin(netid):
                self._add_admin_log(f"user {netid} is an admin - cannot be blocked")
                return False

            if not self.is_user_created(netid):
                self._add_admin_log(f"user {netid} does not exist - cannot be blocked")
                return False

            blacklist = self.get_blacklist()

            # check if user is already in blacklist
            if netid in blacklist:
                self._add_admin_log(f"user {netid} already blocked - not added")
                return False

            if self.is_user_created(netid):
                remove_user(netid)

            blacklist.append(netid)
            self._db.admin.update_one({}, {"$set": {"blacklist": blacklist}})
            self._add_admin_log(f"user {netid} blocked and removed from database")

            self._add_system_log(
                "admin",
                {"message": f"user {netid} blocked and removed from database"},
                netid=admin_netid,
            )
            return True

        except Exception as e:
            log_error(f"Failed to block user {netid}")
            print(e, file=stderr)
            return False

    # remove netid from app blacklist

    def remove_from_blacklist(self, netid, admin_netid):
        try:
            blacklist = self.get_blacklist()
            if netid not in blacklist:
                self._add_admin_log(f"user {netid} not blocked - not removed")
                return False

            blacklist.remove(netid)
            self._db.admin.update_one({}, {"$set": {"blacklist": blacklist}})
            self._add_admin_log(f"user {netid} unblocked")

            self._add_system_log(
                "admin",
                {"message": f"user {netid} unblocked"},
                netid=admin_netid,
            )
            return True
        except Exception as e:
            log_error(f"Failed to unblock user {netid}")
            print(e, file=stderr)
            return False

    # returns list of blacklisted netids

    def get_blacklist(self):
        return self._db.admin.find_one({}, {"blacklist": 1, "_id": 0})["blacklist"]

    # returns a user's waited-on sections

    def get_waited_sections(self, netid):
        try:
            classids = self.get_user(netid, "waitlists")
            year = self.get_user(netid, "year")
        except Exception as e:
            log_error(f"Failed to get Subscriptions for user {netid}")
            print(e, file=stderr)
            return "missing"
        res = []

        for classid in classids:
            try:
                deptnum, name, section, _ = self.classid_to_classinfo(classid)
            except:
                continue
            res.append(f"{name} ({deptnum}): {section}")

        if not year:
            year = "Other"

        if len(res) == 0:
            return "{".join([f"Year: {year}", "No data"])

        return "{".join([f"Year: {year}"] + sorted(res))

    # generates TigerSnatch usage summary: # users, total subscriptions,
    # top n most-subscribed sections, list of scheduled notifications
    # intervals

    def get_usage_summary(self):
        def get_current_term_name():
            return self.get_current_term_code()[1]

        def get_total_users():
            return self._db.users.count_documents({})

        def get_user_distribution():
            res = self._db.users.aggregate(
                [
                    {"$group": {"_id": {"$toLower": "$year"}, "count": {"$sum": 1}}},
                    {
                        "$group": {
                            "_id": None,
                            "counts": {"$push": {"k": "$_id", "v": "$count"}},
                        }
                    },
                    {"$replaceRoot": {"newRoot": {"$arrayToObject": "$counts"}}},
                ]
            )

            counts = list(res)[0]
            counts = [(year, count) for year, count in counts.items()]
            counts.sort(key=lambda x: x[1], reverse=True)
            total_count = sum([e[1] for e in counts])

            ret = ""
            other_str = ""
            for year, count in counts:
                percentage = round(count / total_count * 100, 1)
                if not year:
                    other_str = f"other: {count} ({percentage}%)"
                    continue
                ret += f"{year}: {count} ({percentage}%), "

            if not other_str:
                return ret[:-2]

            return ret + other_str

        def get_total_subscriptions():
            data = self._db.waitlists.find({}, {"waitlist": 1, "_id": 0})
            return sum([len(k["waitlist"]) for k in data])

        def get_top_n_subscribed_sections(n):
            data = self.get_top_subscriptions(target_num=n)
            if len(data) == 0:
                return ["No Subscriptions found"]
            res = [f"Top {len(data)} most-subscribed courses:"]
            for s_data in data:
                res.append(f"[{s_data['size']}] {s_data['name']} ({s_data['deptnum']})")
            return res

        def get_disabled_courses():
            data = self._db.admin.find_one({}, {"disabled_courses": 1, "_id": 0})[
                "disabled_courses"
            ]
            if len(data) == 0:
                return ["No courses are disabled"]
            res = ["Disabled courses:"]
            for courseid in data:
                res.append(
                    f"{self.courseid_to_displayname(courseid)} (courseID: {courseid})"
                )
            return res

        def get_notifs_schedule(fmt="%b %d, %Y @ %-I:%M %p"):
            tz = pytz.timezone("UTC")
            datetimes = list(self._db.admin.find({}, {"notifs_schedule": 1, "_id": 0}))[
                0
            ]["notifs_schedule"]
            res = ["Scheduled notifications intervals (ET):"]
            for start, end in datetimes:
                start, end = (
                    tz.localize(start).astimezone(TZ),
                    tz.localize(end).astimezone(TZ),
                )
                res.append(f"{start.strftime(fmt)} to {end.strftime(fmt)}")
            return res

        def get_users_who_auto_resub():
            return len(
                list(
                    self._db.users.find(
                        {"auto_resub": {"$eq": True}}, {"_id": 0, "auto_resub": 1}
                    )
                )
            )

        def get_site_ref_counts():
            raw_counts = self._db.admin.find_one({}, {"site_ref_counts": 1, "_id": 0})[
                "site_ref_counts"
            ]
            counts = {}
            for site_ref, count in raw_counts.items():
                if site_ref == "princetoncourses":
                    counts["Princeton Courses"] = count
                elif site_ref == "recal":
                    counts["ReCal"] = count

            counts = [(k, v) for k, v in counts.items()]
            counts.sort(key=lambda x: x[1], reverse=True)
            total_count = sum([e[1] for e in counts])

            ret = ""
            for site_ref, count in counts:
                percentage = round(count / total_count * 100, 1)
                ret += f"{site_ref}: {count} ({percentage}%), "

            return ret[:-2]

        line_break = "===================="

        try:
            res = [
                f"Current term: {get_current_term_name()}",
                f"Users: {get_total_users()}",
                f"Userbase: {get_user_distribution()}",
                f"Users with >0 subscriptions: {self.get_users_who_subscribe()}",
                f"Users with auto resub on: {get_users_who_auto_resub()}",
                f"Subscriptions: {get_total_subscriptions()}",
                f"Subscribed sections: {self.get_num_subscribed_sections()}",
                f"Subscribed courses: {self.get_num_subscribed_courses()}",
                f"Notifications sent in current period: {self.get_current_email_counter()}",
                f"Notifications sent: {self.get_email_counter()}",
                f"Notification frequency: {NOTIFS_INTERVAL_SECS}s",
                f"Site refs: {get_site_ref_counts()}",
                line_break,
            ]
            res.extend(get_top_n_subscribed_sections(n=15))
            res.append(line_break)
            res.extend(get_notifs_schedule())
            res.append(line_break)
            res.extend(get_disabled_courses())
            return "{".join(res)

        except Exception as e:
            log_error("Failed to generate usage history")
            print(e, file=stderr)
            return "error"

    # generates a sorted (popularity primary; course code secondary) list of
    # all user subscriptions

    def get_all_subscriptions(self):
        def get_all_subscribed_sections():
            data = self.get_all_subscriptions_raw()
            if len(data) == 0:
                return ["No Subscriptions found"]
            res = []
            for s_data in data:
                try:
                    deptnum, name, section, _ = self.classid_to_classinfo(
                        s_data["classid"], entire_crosslisting=True
                    )
                except:
                    continue
                res.append(f"[{s_data['size']}] {name} ({deptnum}): {section}")
            return res

        try:
            return "{".join(get_all_subscribed_sections())
        except Exception as e:
            log_error("Failed to get all subscriptions")
            print(e, file=stderr)
            return "error"

    # ----------------------------------------------------------------------
    # STATS METHODS
    # ----------------------------------------------------------------------

    # if include_waitlist is True, include each section's waitlist array in result
    def get_all_subscriptions_raw(self, include_waitlist=False):
        fields = {"classid": 1, "size": 1, "_id": 0}
        if include_waitlist:
            fields["waitlist"] = 1
        data = list(
            self._db.waitlists.aggregate(
                [
                    {"$addFields": {"size": {"$size": "$waitlist"}}},
                    {"$sort": {"size": -1}},
                    {"$project": fields},
                ]
            )
        )
        return data

    # if unique_courses is True, removes entries for duplicate courses
    def get_top_subscriptions(self, target_num):
        if target_num <= 0:
            return []

        try:
            waitlists = self._db.waitlists.aggregate(
                [
                    {"$addFields": {"size": {"$size": "$waitlist"}}},
                    {"$project": {"classid": 1, "size": 1, "_id": 0}},
                ]
            )
            waitlists = list(waitlists)
            classids = [w["classid"] for w in waitlists]
            classid_to_size = {w["classid"]: w["size"] for w in waitlists}

            courseids_with_classids = self._db.enrollments.find(
                {"classid": {"$in": classids}}, {"_id": 0, "courseid": 1, "classid": 1}
            )
            courseids_with_classids = list(courseids_with_classids)

            courseid_to_waitlist_size = {}
            for e in courseids_with_classids:
                if e["courseid"] not in courseid_to_waitlist_size:
                    courseid_to_waitlist_size[e["courseid"]] = classid_to_size[
                        e["classid"]
                    ]
                else:
                    courseid_to_waitlist_size[e["courseid"]] += classid_to_size[
                        e["classid"]
                    ]

            courseids_with_mappings = self._db.mappings.find(
                {"courseid": {"$in": list(courseid_to_waitlist_size.keys())}},
                {
                    "_id": 0,
                    "courseid": 1,
                    "title": 1,
                    "displayname": 1,
                },
            )
            courseids_with_mappings = list(courseids_with_mappings)

            courseid_to_waitlist_size = [
                (k, v) for k, v in courseid_to_waitlist_size.items()
            ]
            courseid_to_waitlist_size.sort(key=lambda x: x[1], reverse=True)
            courseid_to_waitlist_size = courseid_to_waitlist_size[:target_num]

            courseid_to_title_and_displayname = {
                m["courseid"]: (m["title"], m["displayname"])
                for m in courseids_with_mappings
            }

            res = []
            for courseid, waitlist_size in courseid_to_waitlist_size:
                title, displayname = courseid_to_title_and_displayname[courseid]
                res.append(
                    {
                        "name": title,
                        "deptnum": displayname.split("/")[0],
                        "size": waitlist_size,
                    }
                )

            return res

        except Exception as e:
            log_error("Failed to retrieve top subscribed courses")
            print(e, file=stderr)

    def get_total_user_count(self):
        return self._db.users.count_documents({})

    def get_total_subscriptions(self):
        data = self._db.waitlists.find({}, {"waitlist": 1, "_id": 0})
        return sum([len(k["waitlist"]) for k in data])

    def get_users_who_subscribe(self):
        data = self._db.users.find({}, {"waitlists": 1, "_id": 0})
        return sum([len(k["waitlists"]) > 0 for k in data])

    def get_num_subscribed_sections(self):
        return self._db.waitlists.count_documents({})

    def get_num_subscribed_courses(self):
        waited_classes = list(self.get_waited_classes())
        classids = [e["classid"] for e in waited_classes]
        courseids = self._db.enrollments.find(
            {"classid": {"$in": [classid for classid in classids]}}
        )
        return len(set([e["courseid"] for e in courseids]))

    def get_email_counter(self):
        return self._db.admin.find_one({}, {"_id": 0, "stats_total_notifs": 1})[
            "stats_total_notifs"
        ]

    def get_current_email_counter(self):
        return self._db.admin.find_one({}, {"_id": 0, "stats_current_notifs": 1})[
            "stats_current_notifs"
        ]

    def add_stats_notif_log(self, log):
        stats_notifs_logs = self._db.admin.find_one(
            {}, {"_id": 0, "stats_notifs_logs": 1}
        )["stats_notifs_logs"]

        try:
            if (
                len(stats_notifs_logs) > 0
                and stats_notifs_logs[0].split(" \u2192 ")[1] == log
            ):
                log_info("Duplicate stats notifs log detected - skipping")
                return
        except:
            pass

        log = f"{(datetime.now(TZ)).strftime('%b %d, %Y @ %-I:%M %p ET')} \u2192 {log}"

        self._db.admin.update_one(
            {},
            {
                "$push": {
                    "stats_notifs_logs": {
                        "$each": [log],
                        "$position": 0,
                        "$slice": 5,
                    }
                }
            },
        )

    def get_stats(self):
        stats = self._db.admin.find_one(
            {},
            {
                "stats_top_subs": 1,
                "stats_total_users": 1,
                "stats_total_subs": 1,
                "stats_subbed_users": 1,
                "stats_subbed_sections": 1,
                "stats_subbed_courses": 1,
                "stats_total_notifs": 1,
                "stats_notifs_logs": 1,
                "stats_update_time": 1,
                "stats_current_notifs": 1,
                "_id": 0,
            },
        )
        return stats

    def increment_site_ref(self, ref: str):
        if not ref:
            return
        self._db.admin.update_one(
            {},
            {"$inc": {f"site_ref_counts.{ref}": 1}},
        )
        log_info(f"Incremented site ref count for {ref}")

    # ----------------------------------------------------------------------
    # BLACKLIST UTILITY METHODS
    # ----------------------------------------------------------------------

    # returns True if netid is on app blacklist

    def is_blacklisted(self, netid):
        try:
            blacklist = self.get_blacklist()
            return netid in blacklist
        except Exception as e:
            log_error(f"Failed to check if {netid} is blocked")
            print(e, file=stderr)

    # ----------------------------------------------------------------------
    # USER METHODS
    # ----------------------------------------------------------------------

    # checks if user exists in users collection

    def is_user_created(self, netid):
        return (
            self._db.users.find_one({"netid": netid.rstrip()}, {"netid": 1}) is not None
        )

    # creates user entry in users collection

    def create_user(self, netid):
        def get_year():
            data = ActiveDirectory(Database()).get_user(netid)

            if not data:
                log_info(f"No ActiveDirectory data found for user {netid}")
                return None

            data = data[0]
            pustatus = data["pustatus"]
            if pustatus == "graduate":
                return "Grad"
            elif pustatus == "undergraduate":
                return data["department"].split(" ")[-1]
            elif pustatus == "fac" or pustatus == "stf":
                return "Faculty"

            return None

        if self.is_user_created(netid):
            log_error(f"Failed to create user {netid} - already exists")
            return
        netid = netid.strip()
        self._db.users.insert_one(
            {
                "netid": netid,
                "email": f"{netid}@princeton.edu",
                "phone": "",
                "waitlists": [],
                "auto_resub": False,
                "year": get_year(),
            }
        )
        self._db.notifs.insert_one({"netid": netid})
        self._db.logs.insert_one({"netid": netid, "waitlist_log": []})
        log_info(f"Succesfully created user {netid}")

    # update user netid's waitlist log

    def update_user_waitlist_log(self, netid, entry):
        entry = (
            f"{(datetime.now(TZ)).strftime('%b %-d, %Y @ %-I:%M %p ET')} \u2192 {entry}"
        )

        self._db.logs.update_one(
            {"netid": netid},
            {
                "$push": {
                    "waitlist_log": {
                        "$each": [entry],
                        "$position": 0,
                        "$slice": MAX_LOG_LENGTH,
                    }
                }
            },
        )

    # gets user netid's waitlist log in array-of-strings format

    def get_user_waitlist_log(self, netid):
        return self._db.logs.find_one({"netid": netid}, {"waitlist_log": 1, "_id": 0})[
            "waitlist_log"
        ]

    # returns user data given netid and a key from the users collection

    def get_user(self, netid, key):
        try:
            return self._db.users.find_one({"netid": netid}, {key: 1, "_id": 0})[key]
        except:
            raise Exception(f"failed to get key {key} for netid {netid}")

    # return data for all users in array netids

    def get_users(self, netids):
        return list(self._db.users.find({"netid": {"$in": netids}}))

    # returns all data needed to display user waitlists on dashboard

    def get_dashboard_data(self, netid):
        dashboard_data = {}
        try:
            waitlists = self._db.users.find_one({"netid": netid})["waitlists"]
        except:
            raise RuntimeError(f"user {netid} does not exist")
        for classid in waitlists:
            class_stats = self.get_class_enrollment(classid)
            if class_stats is None:
                continue

            dashboard_data[classid] = {}

            courseid = class_stats["courseid"]
            course_data = self.get_course(courseid)
            try:
                class_data = course_data[f"class_{classid}"]
            except Exception as e:
                log_error(f"ClassID {classid} not found in courses")
                print(e, file=stderr)
                del dashboard_data[classid]
                continue

            dashboard_data[classid]["courseid"] = courseid
            dashboard_data[classid]["displayname"] = course_data["displayname"]
            dashboard_data[classid]["section"] = class_data["section"]
            dashboard_data[classid]["start_time"] = class_data["start_time"]
            dashboard_data[classid]["end_time"] = class_data["end_time"]
            dashboard_data[classid]["days"] = class_data["days"]
            dashboard_data[classid]["enrollment"] = class_stats["enrollment"]
            dashboard_data[classid]["capacity"] = class_stats["capacity"]

            try:
                time_of_last_notif = self.get_time_of_last_notif(classid)
            except Exception:
                time_of_last_notif = None
            dashboard_data[classid]["time_of_last_notif"] = (
                time_of_last_notif if time_of_last_notif is not None else "-"
            )

        return dashboard_data

    # returns course displayname corresponding to courseid

    def update_user(self, netid, email):
        try:
            self._db.users.update_one({"netid": netid}, {"$set": {"email": email}})
        except:
            raise RuntimeError(f"attempt to update email for {netid} failed")

    def update_user_phone(self, netid, phone):
        try:
            self._db.users.update_one({"netid": netid}, {"$set": {"phone": phone}})
        except:
            raise RuntimeError(f"attempt to update phone for {netid} failed")

    # returns list of results whose netid
    # contain user query string

    def search_for_user(self, query):
        if query is None:
            return [], ""

        query = " ".join(query.split())
        query = re.sub(r"[^0-9a-zA-Z]+", "", query)
        query_re = re.compile(query, re.IGNORECASE)
        res = list(self._db.users.find({"netid": {"$regex": query_re}}))
        res.reverse()
        total_users = self._db.users.count_documents({})
        return res, query, total_users

    # sets auto resubscribe flag for user

    def update_user_auto_resub(self, netid, auto_resub):
        try:
            self._db.users.update_one(
                {"netid": netid}, {"$set": {"auto_resub": auto_resub}}
            )
            return True
        except Exception as e:
            log_error(f"Attempt to update auto_resub for {netid} failed")
            print(e, file=stderr)
            return False

    # returns whether user opted to auto resubscribe

    def get_user_auto_resub(self, netid, classid="", print_max_resub_msg=False):
        try:
            auto_resub_dict = self._db.users.find_one(
                {"netid": netid}, {"auto_resub": 1, "_id": 0}
            )
            if "auto_resub" not in auto_resub_dict:
                return False

            # if classID is not provided (i.e. old behavior), just return the actual value of auto_resub
            # (the only time classID is provided is when we're checking whether to unsub the user of not)
            if classid == "":
                return auto_resub_dict["auto_resub"]

            # if classID is provided, check whether or not the user has exceeded the maximum notification
            # count for the given classID (the user is subscribed to this classID)

            # if auto-resub is False, just return False (and unsub them)
            if not auto_resub_dict["auto_resub"]:
                return False

            # if auto-resub is True, check whether user has exceeded max number of notifs for the classID

            user_notifs_history = self.get_user_notifs_history(netid, classid)
            num_notifs_for_classid = user_notifs_history.get("num_notifs", 0)

            # if the max number of notifs is reached, return False (and unsub them)
            if num_notifs_for_classid >= MAX_AUTO_RESUB_NOTIFS:
                if print_max_resub_msg:
                    log_info(
                        f"User {netid} reached maximum auto resubs ({MAX_AUTO_RESUB_NOTIFS}) for classID {classid}"
                    )
                return False

            # otherwise the max number of notifs has not yet been exceeded, so return True (auto-resub them)
            return True
        except:
            raise Exception(f"failed to get key auto_resub flag for netid {netid}")

    # returns data in notifs collection corresponding to netid > classid

    def get_user_notifs_history(self, netid, classid):
        return self._db.notifs.find_one({"netid": netid}, {classid: 1, "_id": 0})[
            classid
        ]

    # updates n_open_spots and last_notif fields for data in notifs collection

    def update_users_notifs_history(
        self, netids, classid, n_open_spots, reserved_seats=False
    ):
        # if the class has reserved seating, update only the num_notifs counter
        if reserved_seats:
            self._db.notifs.update_many(
                {"netid": {"$in": netids}, classid: {"$exists": True}},
                {
                    "$inc": {
                        f"{classid}.num_notifs": 1
                    },  # increments by 1 if exists, otherwise sets to 1
                },
            )
            return

        # update n_open_spots for all users subbed to classid (key classid exists)
        self._db.notifs.update_many(
            {classid: {"$exists": True}},
            {"$set": {f"{classid}.n_open_spots": n_open_spots}},
        )

        # update last_notif for only users who received notifs (i.e. netids)
        # add or subtract a random small amount of time to help spread out notifs
        RAND_OFFSET_MINS = 5
        new_last_notif = datetime.now(TZ) + timedelta(
            minutes=randint(-RAND_OFFSET_MINS, RAND_OFFSET_MINS)
        )
        self._db.notifs.update_many(
            {"netid": {"$in": netids}, classid: {"$exists": True}},
            {
                "$set": {f"{classid}.last_notif": new_last_notif},
                "$inc": {
                    f"{classid}.num_notifs": 1
                },  # increments by 1 if exists, otherwise sets to 1
            },
        )

    # ----------------------------------------------------------------------
    # TERM METHODS
    # ----------------------------------------------------------------------

    # gets current term code from admin collection

    def get_current_term_code(self):
        res = self._db.admin.find_one(
            {}, {"current_term_code": 1, "current_term_name": 1, "_id": 0}
        )
        return res["current_term_code"], res["current_term_name"]

    # updates current term code from admin collection

    def update_current_term_code(self, code, name):
        if self.get_current_term_code()[0] == code:
            return False

        self._db.admin.update_one(
            {}, {"$set": {"current_term_code": code, "current_term_name": name}}
        )
        return True

    # ----------------------------------------------------------------------
    # COURSE METHODS
    # ----------------------------------------------------------------------

    # returns course displayname corresponding to courseid

    def courseid_to_displayname(self, courseid):
        try:
            displayname = self._db.mappings.find_one({"courseid": courseid})[
                "displayname"
            ]
        except:
            raise RuntimeError(f"courseid {courseid} not found in courses")

        return displayname.split("/")[0]

    # return basic course details for course with given courseid

    def get_course(self, courseid):
        return self._db.courses.find_one({"courseid": courseid}, {"_id": 0})

    # returns list of tuples (section_name, classid) for a course
    # set include_lecture to True if you want Lecture section included

    def get_section_names_in_course(self, courseid, include_lecture=False):
        section_name_list = []
        course_dict = self.get_course(courseid)
        for key in course_dict.keys():
            if key.startswith("class_"):
                section_name = course_dict[key]["section"]
                classid = course_dict[key]["classid"]
                if not include_lecture and section_name.startswith("L"):
                    continue
                section_name_list.append((section_name, classid))
        return section_name_list

    # return list of class ids for a course

    def get_classes_in_course(self, courseid):
        classid_list = []
        course_dict = self.get_course(courseid)
        for key in course_dict.keys():
            if key.startswith("class_"):
                classid_list.append(course_dict[key]["classid"])
        return classid_list

    # returns dictionary with basic course details AND enrollment,
    # capacity, and boolean isFull field for each class
    # for the given courseid

    def get_course_with_enrollment(self, courseid):
        course_info = self.get_course(courseid)
        has_reserved_seats = course_info["has_reserved_seats"]
        for key in course_info.keys():
            if key.startswith("class_"):
                class_dict = course_info[key]
                classid = class_dict["classid"]
                class_data = self.get_class_enrollment(classid)
                class_dict["enrollment"] = class_data["enrollment"]
                class_dict["capacity"] = class_data["capacity"]
                # we mark a class as full (i.e. allow subbing) if at least one is true:
                #   1. capacity is non-zero and enrollment is at least as large as capacity
                #   2. class has reserved seating and positive enrollment
                #   3. class is closed
                class_dict["isFull"] = (
                    (
                        class_dict["capacity"] > 0
                        and class_dict["enrollment"] >= class_dict["capacity"]
                    )
                    or (has_reserved_seats and class_dict["enrollment"] > 0)
                    or not class_dict["status_is_open"]
                )
        return course_info

    # updates time that a course page was last updated

    def update_course_time(self, courseid, curr_time):
        try:
            self._db.mappings.update_one(
                {"courseid": courseid}, {"$set": {"time": curr_time}}
            )
        except:
            raise RuntimeError(f"courseid {courseid} not found in courses")

    # returns time that a course page was last updated

    def get_course_time_updated(self, courseid):
        try:
            time = self._db.mappings.find_one({"courseid": courseid})["time"]
        except:
            raise RuntimeError(f"courseid {courseid} not found in courses")
        return time

    # checks if the courses collection contains a course with the
    # passed-in courseid

    def courses_contains_courseid(self, courseid):
        return self._db.courses.find_one({"courseid": courseid}) is not None

    # returns list of results whose title and displayname
    # contain user query string

    def search_for_course(self, query):
        autocomplete_fields = [
            {
                "autocomplete": {
                    "query": query,
                    "path": path,
                    "fuzzy": {
                        "maxEdits": 1,
                        "prefixLength": 1,
                        "maxExpansions": 256,
                    },
                }
            }
            for path in ["displayname", "displayname_whitespace", "title"]
        ]

        res = list(
            self._db.mappings.aggregate(
                [
                    {"$search": {"compound": {"should": autocomplete_fields}}},
                    {"$limit": 10},
                ]
            )
        )

        return res

    # checks if a course has been disabled (i.e. by an instructor request)

    def is_course_disabled(self, courseid):
        try:
            disabled_courses = self._db.admin.find_one(
                {}, {"disabled_courses": 1, "_id": 0}
            )["disabled_courses"]
            return courseid in disabled_courses
        except:
            return False

    # returns a list of disabled courses

    def get_disabled_courses(self):
        try:
            return self._db.admin.find_one({}, {"disabled_courses": 1, "_id": 0})[
                "disabled_courses"
            ]
        except:
            return []

    # checks if a course has reserved seating

    def does_course_have_reserved_seats(self, courseid):
        try:
            return self.get_course(courseid)["has_reserved_seats"]
        except:
            return False

    # checks if a course (via its entire original "displayname" key) is a top-N subscribed course

    def is_course_top_n_subscribed(self, displayname):
        try:
            displayname = " / ".join(displayname.split("/"))
            data = self._db.admin.find_one({}, {"_id": 0, "stats_top_subs": 1})
            top_courses = set([e["deptnum"] for e in data["stats_top_subs"]])
            return displayname in top_courses
        except:
            return False

    # ----------------------------------------------------------------------
    # CLASS METHODS
    # ----------------------------------------------------------------------

    # returns True if classid is found in course with courseid
    def is_classid_in_courseid(self, classid, courseid):
        try:
            return (
                self._db.enrollments.find_one(
                    {"classid": classid}, {"_id": 0, "courseid": 1}
                )["courseid"]
                == courseid
            )
        except:
            raise RuntimeError(f"classid {classid} not found in enrollments")

    # returns name of section specified by classid
    def classid_to_sectionname(self, classid):
        try:
            return self._db.enrollments.find_one(
                {"classid": classid}, {"_id": 0, "section": 1}
            )["section"]
        except:
            raise RuntimeError(f"classid {classid} not found in enrollments")

    # returns the corresponding course displayname and courseid for a given classid

    def classid_to_course_info(self, classid):
        try:
            courseid = self._db.enrollments.find_one({"classid": classid})["courseid"]
        except:
            raise RuntimeError(f"classid {classid} not found in enrollments")

        try:
            displayname = self._db.mappings.find_one({"courseid": courseid})[
                "displayname"
            ]
        except:
            raise RuntimeError(f"courseid {courseid} not found in courses")

        return (displayname.split("/")[0], courseid)

    # returns information about a class including course depts, numbers, title
    # and section number, for display in email/text messages

    def classid_to_classinfo(self, classid, entire_crosslisting=False):
        try:
            classinfo = self._db.enrollments.find_one({"classid": classid})
            courseid = classinfo["courseid"]
            sectionname = classinfo["section"]
        except:
            raise Exception(f"classid {classid} cannot be found")

        try:
            mapping = self._db.courses.find_one({"courseid": courseid})
            displayname = mapping["displayname"]
            title = mapping["title"]
        except:
            raise Exception(f"courseid {courseid} cannot be found")

        dept_num = displayname.split("/")[0]
        if entire_crosslisting:
            dept_num = " / ".join(displayname.split("/"))
        return dept_num, title, sectionname, courseid

    # get dictionary for class with given classid in courses

    def get_class(self, courseid, classid):
        try:
            course_data = self.get_course(courseid)
        except:
            raise RuntimeError(f"courseid {courseid} not found in courses")
        try:
            return course_data[f"class_{classid}"]
        except:
            raise RuntimeError(f"class {classid} not found in courses")

    # returns capacity and enrollment for course with given classid

    def get_class_enrollment(self, classid):
        return self._db.enrollments.find_one({"classid": classid}, {"_id": 0})

    # updates the enrollment and capacity for class classid

    def update_enrollment(
        self,
        classid,
        new_enroll,
        new_cap,
        entirely_new_enrollment,
        update_courses_entry=True,
        set_status_to_closed=False,
    ):
        # handles the situation where an additional section is added to a course after the initial TigerSnatch
        # term update. the previous issue was that `update_one` DOES NOT add to a collection; it simply updates
        # an entry if it exists; but an entry for a new section cannot exist. as a result, the new section was being
        # added to the courses collection but not the enrollments collection, causing an error on the frontend.
        if self._db.enrollments.find_one({"classid": classid}) is None:
            self.add_to_enrollments(entirely_new_enrollment)
            return
        self._db.enrollments.update_one(
            {"classid": classid},
            {"$set": {"enrollment": new_enroll, "capacity": new_cap}},
        )

        if update_courses_entry:
            courseid = self._db.enrollments.find_one(
                {"classid": classid}, {"_id": 0, "courseid": 1}
            )["courseid"]
            self._db.courses.update_one(
                {"courseid": courseid},
                {
                    "$set": {
                        f"class_{classid}.enrollment": new_enroll,
                        f"class_{classid}.capacity": new_cap,
                    }
                },
            )

        # used by the "fill section" feature on the admin panel so that subbing is possible
        if set_status_to_closed:
            self._db.courses.update_one(
                {"courseid": courseid},
                {
                    "$set": {
                        f"class_{classid}.status_is_open": False,
                    }
                },
            )

    # return the previous enrollment of a class whose course has reserved seats
    # defaults to 0 (which will not trigger notifications)
    # USE ONLY IF THE CORRESPONDING COURSE HAS RESERVED SEATS!
    def get_prev_enrollment_RESERVED_SEATS_ONLY(self, classid):
        try:
            return self._db.enrollments.find_one({"classid": classid}, {"_id": 0})[
                "prev_enrollment"
            ]
        except:
            return 0

    def update_prev_enrollment_RESERVED_SEATS_ONLY(self, classid, enrollment):
        try:
            self._db.enrollments.update_one(
                {"classid": classid}, {"$set": {"prev_enrollment": enrollment}}
            )
        except:
            raise RuntimeError(f"class {classid} not found in enrollments")

    # sets the time of last notif for class classid to NOW
    # time of last notif stored in enrollments collection
    def update_time_of_last_notif(self, classid):
        try:
            self._db.enrollments.update_one(
                {"classid": classid}, {"$set": {"last_notif": datetime.now(TZ)}}
            )
        except:
            raise RuntimeError(f"class {classid} not found in enrollments")

    # returns the time of last notif as a string, or None if it does not exist, for class classid
    # can pass a custom format string for the datetime
    def get_time_of_last_notif(self, classid, fmt="%-m/%-d @ %-I:%M %p"):
        try:
            tz_utc = pytz.timezone("UTC")
            tz_et = pytz.timezone("US/Eastern")
            time = self._db.enrollments.find_one({"classid": classid}, {"_id": 0})[
                "last_notif"
            ]
            time = tz_utc.localize(time)
            time = time.astimezone(tz_et)
            return time.strftime(fmt)
        except:
            return None

    # ----------------------------------------------------------------------
    # WAITLIST METHODS
    # ----------------------------------------------------------------------

    # returns all classes to which there are waitlisted students

    def get_waited_classes(self):
        return self._db.waitlists.find({}, {"courseid": 1, "classid": 1, "_id": 0})

    # returns a specific classid's waitlist document

    def get_class_waitlist(self, classid):
        try:
            return self._db.waitlists.find_one({"classid": classid})
        except:
            raise Exception(f"classid {classid} does not exist")

    # returns a specific classid's waitlist size

    def get_class_waitlist_size(self, classid):
        try:
            return len(self.get_class_waitlist(classid)["waitlist"])
        except:
            raise Exception(f"classid {classid} does not exist")

    # adds user of given netid to waitlist for class classid

    def add_to_waitlist(self, netid, classid, disable_checks=False):
        # validation checks
        def validate(courseid):
            # helper method to check if class is full
            def is_class_full(enrollment_dict):
                return enrollment_dict["enrollment"] >= enrollment_dict["capacity"]

            has_reserved_seats = self.does_course_have_reserved_seats(
                self.classid_to_course_info(classid)[1]
            )

            # if user does not exist, do not allow sub
            if not self.is_user_created(netid):
                raise Exception(f"user {netid} does not exist")

            class_enrollment = self.get_class_enrollment(classid)
            # if class does not exist, do not allow sub
            if class_enrollment is None:
                raise Exception(f"class {classid} does not exist")

            # if user is already subbed to class, do not allow sub
            if classid in self.get_user(netid, "waitlists"):
                raise Exception(
                    f"user {netid} is already in waitlist for class {classid}"
                )

            # if class is in a disabled course, do not allow sub
            if self.is_course_disabled(courseid):
                raise Exception(
                    f"User {netid}: class {classid} is in disabled course {courseid}"
                )

            course_info = self.get_course(courseid)
            class_status_is_open = course_info[f"class_{classid}"]["status_is_open"]

            # if class is open and doesn't have reserved seats, do not allow sub
            if class_status_is_open and not has_reserved_seats:
                raise Exception(f"class {classid} is not Closed")

            # otherwise if class is closed, allow sub in all cases
            if not class_status_is_open:
                return

            # if class is not full and does not have reserved seats, do not allow sub
            if not is_class_full(class_enrollment) and not has_reserved_seats:
                raise Exception(
                    f"user cannot enter waitlist for non-full class {classid}"
                )

            # if class has reserved seats and has 0 enrollment, do not allow sub
            #   in this case, we know the class is open, has reserved seats, and all
            #   seat categories are empty, so subbing is useless
            if has_reserved_seats and class_enrollment["enrollment"] == 0:
                raise Exception(
                    f"user cannot enter waitlist for reserved class {classid} because its enrollment is 0"
                )

        netid = netid.strip()
        coursedeptnum, courseid = self.classid_to_course_info(classid)
        if not disable_checks:
            validate(courseid)

        # add classid to user's waitlist
        user_waitlists = self.get_user(netid, "waitlists")
        try:
            if len(user_waitlists) >= MAX_WAITLIST_SIZE:
                log_info(
                    f"User {netid} exceeded the waitlist limit of {MAX_WAITLIST_SIZE}"
                )
                return 0
        except Exception as e:
            print(e, file=stderr)

        user_waitlists.append(classid)
        self._db.users.update_one(
            {"netid": netid}, {"$set": {"waitlists": user_waitlists}}
        )

        # add user to waitlist for classid
        waitlist = self.get_class_waitlist(classid)
        if waitlist is None:
            self._db.waitlists.insert_one({"classid": classid, "waitlist": []})
            class_waitlist = []
        else:
            class_waitlist = waitlist["waitlist"]

        class_waitlist.append(netid)
        self._db.waitlists.update_one(
            {"classid": classid}, {"$set": {"waitlist": class_waitlist}}
        )

        # add class to user's document in notifs collection with default values
        self._db.notifs.update_one(
            {"netid": netid},
            {
                "$set": {
                    classid: {
                        "n_open_spots": 0,
                        "last_notif": datetime.now(TZ),
                        "num_notifs": 0,
                    }
                }
            },
        )

        self._add_system_log(
            "subscription",
            {
                "message": f"User {netid} subscribed to class {classid} ({coursedeptnum})"
            },
            netid=netid,
        )

        return 1

    # removes user of given netid to waitlist for class classid
    # if waitlist for class is empty now, delete entry from waitlists collection

    def remove_from_waitlist(self, netid, classid, force_remove=False):
        def validate(courseid):
            if not self.is_user_created(netid):
                raise Exception(f"user {netid} does not exist")
            waitlist = self.get_class_waitlist(classid)
            if waitlist is None:
                raise Exception(
                    f"no waitlist for class {classid} exists (user {netid})"
                )
            if (
                classid not in self.get_user(netid, "waitlists")
                or netid not in waitlist["waitlist"]
            ):
                raise Exception(f"user {netid} not in waitlist for class {classid}")
            if self.is_course_disabled(courseid):
                raise Exception(
                    f"User {netid}: class {classid} is in disabled course {courseid}"
                )

        netid = netid.strip()
        coursedeptnum, courseid = self.classid_to_course_info(classid)
        if not force_remove:
            validate(courseid)

        # remove classid from user's waitlist
        user_waitlists = self.get_user(netid, "waitlists")
        if classid in user_waitlists:
            user_waitlists.remove(classid)
            self._db.users.update_one(
                {"netid": netid}, {"$set": {"waitlists": user_waitlists}}
            )

        # remove user from waitlist for classid
        class_waitlist = self.get_class_waitlist(classid)["waitlist"]
        if netid in class_waitlist:
            class_waitlist.remove(netid)
            if len(class_waitlist) == 0:
                self._db.waitlists.delete_one({"classid": classid})
                # reset prev_enrollment to 0 if the course has reserved seats
                if self.does_course_have_reserved_seats(
                    self.classid_to_course_info(classid)[1]
                ):
                    self.update_prev_enrollment_RESERVED_SEATS_ONLY(classid, 0)
            else:
                self._db.waitlists.update_one(
                    {"classid": classid}, {"$set": {"waitlist": class_waitlist}}
                )

        # remove class from user's document in notifs collection
        self._db.notifs.update_one({"netid": netid}, {"$unset": {classid: ""}})

        self._add_system_log(
            "subscription",
            {
                "message": f"User {netid} unsubscribed from class {classid} ({coursedeptnum})"
            },
            netid=netid,
        )

    # ----------------------------------------------------------------------
    # LIVE NOTIFICATION STATUS METHODS
    # ----------------------------------------------------------------------

    # returns the current state of live notifications and the data associated with it
    def get_live_notifs_status(self):
        try:
            res = self._db.admin.find_one({}, {"_id": 0, "live_notifs_status": 1})[
                "live_notifs_status"
            ]
            return res["state"], res["data"]
        except Exception as e:
            log_error("Failed to get live notifs status")
            print(e, file=stderr)
            return "error", None

    # sets the current state of live notifications and the data associated with it
    def set_live_notifs_status(self, state, data):
        try:
            if not isinstance(data, str):
                raise Exception("data must be a string")

            self._db.admin.update_one(
                {},
                {
                    "$set": {
                        "live_notifs_status.state": state,
                        "live_notifs_status.data": data,
                    }
                },
            )
        except Exception as e:
            log_error("Failed to set live notifs status")
            print(e, file=stderr)

    # ----------------------------------------------------------------------
    # DATABASE POPULATION METHODS
    # ----------------------------------------------------------------------

    # adds a document containing course data to the courses collection
    # (see Technical Documentation for schema)

    def add_to_courses(self, data):
        def validate(data):
            # validates the keys of the passed-in course data dictionary

            if not all(k in data for k in COURSES_SCHEMA):
                raise RuntimeError("invalid courses document schema")

            for k in data:
                if not k.startswith("class_"):
                    continue
                if not all(k_ in data[k] for k_ in CLASS_SCHEMA):
                    raise RuntimeError("invalid individual class document schema")

        validate(data)
        self._db.courses.insert_one(data)

    # updates course entry in courses, mappings, and enrollment
    # collections with data dictionary

    def update_course_all(
        self,
        courseid,
        new_course,
        new_mapping,
        new_enroll,
        new_cap,
        entirely_new_enrollments,
    ):
        def validate(new_course, new_mapping):
            if not all(k in new_course for k in COURSES_SCHEMA):
                raise RuntimeError("invalid courses document schema")

            for k in new_course:
                if not k.startswith("class_"):
                    continue
                if not all(k_ in new_course[k] for k_ in CLASS_SCHEMA):
                    raise RuntimeError("invalid individual class document schema")

            if not all(k in new_mapping for k in MAPPINGS_SCHEMA):
                raise RuntimeError("invalid mappings document schema")

        validate(new_course, new_mapping)
        self._db.courses.replace_one({"courseid": courseid}, new_course)
        for classid in new_enroll.keys():
            self.update_enrollment(
                classid,
                new_enroll[classid],
                new_cap[classid],
                entirely_new_enrollments[classid],
                update_courses_entry=False,
            )
        self._db.mappings.replace_one({"courseid": courseid}, new_mapping)

    # adds a document containing mapping data to the mappings collection
    # (see Technical Documentation for schema)

    def add_to_mappings(self, data):
        def validate(data):
            # validates the keys of the passed-in mappings data
            # dictionary

            if not all(k in data for k in MAPPINGS_SCHEMA):
                raise RuntimeError("invalid mappings document schema")

        validate(data)
        self._db.mappings.insert_one(data)

    # adds a document containing enrollment data to the enrollments
    # collection (see Technical Documentation for schema)

    def add_to_enrollments(self, data):
        def validate(data):
            # validates the keys of the passed-in enrollments data
            # dictionary

            if not all(k in data for k in ENROLLMENTS_SCHEMA):
                raise RuntimeError("invalid enrollments document schema")

        validate(data)
        self._db.enrollments.insert_one(data)

    # ----------------------------------------------------------------------
    # DATABASE RESET METHODS
    # ----------------------------------------------------------------------

    # does the following:
    #   * clears all waitlists and current sections for each user
    #   * deletes all documents from mappings
    #   * deletes all documents from courses
    #   * deletes all documents from enrollments
    #   * deletes all documents from waitlists
    # NOTE: does not affect user-specific data apart from clearing a
    # user's subscriptions

    def reset_db(self):
        def clear_coll(coll):
            log_info(f"Clearing {coll}")
            self._db[coll].delete_many({})

        log_info("Clearing waitlists in users")
        self._db.users.update_many({}, {"$set": {"waitlists": []}})

        log_info("Resetting user logs")
        self._db.logs.update_many({}, {"$set": {"waitlist_log": []}})

        log_info("Clearing disabled courses")
        self._db.admin.update_one({}, {"$set": {"disabled_courses": []}})

        log_info("Resetting current notification count to 0")
        self._db.admin.update_one({}, {"$set": {"stats_current_notifs": 0}})

        clear_coll("mappings")
        clear_coll("courses")
        clear_coll("enrollments")
        clear_coll("waitlists")
        clear_coll("notifs")

        log_info("Repopulating documents in notifs")
        for doc in self._db.users.find({}, {"netid": 1}):
            self._db.notifs.insert_one({"netid": doc["netid"]})

    # does the following:
    #   * deletes all documents from mappings
    #   * deletes all documents from courses
    #   * deletes all documents from enrollments
    #   * deletes all user current sections
    # NOTE: does NOT clear waitlist-related data, unlike self.reset_db()

    def soft_reset_db(self):
        def clear_coll(coll):
            log_info(f"Clearing {coll}")
            self._db[coll].delete_many({})

        clear_coll("mappings")
        clear_coll("courses")
        clear_coll("enrollments")

    # ----------------------------------------------------------------------
    # UTILITY METHODS
    # ----------------------------------------------------------------------

    def increment_email_counter(self, n):
        if n <= 0:
            return
        self._db.admin.update_one(
            {}, {"$inc": {"stats_total_notifs": n, "stats_current_notifs": n}}
        )

    def _get_all_emails_csv(self):
        data = self._db.users.find({}, {"_id": 0, "email": 1})
        emails = [k["email"] for k in data]
        return ",".join(emails)

    # checks that all required collections are available in self._db;
    # raises a RuntimeError if not

    def _check_basic_integrity(self):
        if COLLECTIONS != set(self._db.list_collection_names()):
            raise RuntimeError(
                "one or more database collections is misnamed and/or missing"
            )

    # turn Heroku maintenance mode ON (True) or OFF (False)

    def set_maintenance_status(self, status):
        if not isinstance(status, bool):
            raise Exception("status must be a boolean")

        app = self._connect_to_heroku()
        if status:
            # app.process_formation()["notifs"].scale(0)
            app.enable_maintenance_mode()
        else:
            # app.process_formation()["notifs"].scale(1)
            app.disable_maintenance_mode()

        self._add_system_log(
            "heroku",
            {"message": f'maintenance mode set to {"on" if status else "off"}'},
        )

    # get Heroku maintenance status: ON (True) or OFF (False)

    def get_maintenance_status(self):
        app = self._connect_to_heroku()
        return app.maintenance

    # connects to Heroku and returns app variable so you can do
    # operations with Heroku

    def _connect_to_heroku(self):
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.apps()[HEROKU_APP_NAME]
        return app

    # adds log message to logs array in system collection

    def _add_system_log(self, type, meta, netid=None, print_=True, log_fn=log_system):
        meta["type"] = type
        meta["time"] = datetime.now(TZ)
        if netid is not None:
            meta["netid"] = netid
        if "message" in meta and print_:
            log_fn(meta["message"])
            stdout.flush()
        self._db.system.insert_one(meta)

    # prints database name, its collections, and the number of documents
    # in each collection

    def __str__(self):
        self._check_basic_integrity()
        ret = f"database {self._db.name} with collections:\n"
        for coll in self._db.list_collection_names():
            ref = self._db[coll]
            ret += f"\t{coll:<15}(#docs: {ref.estimated_document_count()})\n"
        return ret


if __name__ == "__main__":
    Database().set_live_notifs_status("active", "computing open spots")

    # generate list of all sections that had open-spot notifs with timestamps
    # db = Database()._db
    # start_date = datetime(2022, 9, 5)
    # res = db.system.find(
    #     {
    #         "type": "cron",
    #         "message": {"$regex": ":"},
    #         "time": {"$gte": start_date, "$lte": start_date + timedelta(days=1)},
    #     }
    # )

    # with open("all-notifs.txt", "w") as f:
    #     for doc in res:
    #         sections = doc["message"].split(": ")
    #         if len(sections) < 2:
    #             continue
    #         for section in sections[1].split(", "):
    #             f.write(f'{doc["time"].isoformat()} {section}\n')

    # # generate unique number of users who subscribed in a given period
    # db = Database()._db
    # # change the datetime
    # res = db.system.find(
    #     {
    #         "type": "subscription",
    #         "time": {"$gt": datetime.datetime(2022, 3, 24, 0, 0, 0, 0)},
    #         "message": {"$regex": " subscribed"},
    #     },
    #     {"message": 1, "_id": 0},
    # )
    # res = list(res)

    # user_set = set()
    # for message in res:
    #     text = message["message"]
    #     end_idx = text.find(" successfully")
    #     start_idx = 5
    #     name = text[start_idx:end_idx]
    #     user_set.add(name)

    # print(len(user_set))

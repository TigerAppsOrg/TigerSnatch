# ----------------------------------------------------------------------
# app_helper.py
# Defines helper methods to construct endpoints.
# ----------------------------------------------------------------------

from database import Database
from monitor import Monitor
import re
from sys import stderr
from markdown import markdown
import json
import os
from log_utils import *

MAX_QUERY_LENGTH = 150


def validate_query(query):
    if len(query) > MAX_QUERY_LENGTH:
        return False
    return re.match("^[^0-9a-zA-Z ]+$", query)


# searches for course based on user query
def do_search(query, db: Database):
    if query is None or not isinstance(query, str):
        return None, ""

    res = []
    if query.strip() == "":
        return None, ""

    query = " ".join(query.split())
    # query = re.sub(r'[^0-9a-zA-Z"?:%\'\-, ]+', "", query)
    query = query.replace("/", " ")
    res = db.search_for_course(query)

    return res, query


# pulls most recent course info and returns dictionary with
# course details and list with class info
def pull_course(courseid, db: Database):
    def generate_subs_stats_string(classid):
        # "|" represents a newline character
        waitlist_obj = db.get_class_waitlist(classid)

        if not waitlist_obj or not waitlist_obj.get("waitlist"):
            fail_msg = "Failed to get data"
            return fail_msg, fail_msg

        netids = waitlist_obj.get("waitlist")
        users = db.get_users(netids)

        netids = {}
        for user in users:
            try:
                year = user["year"]
                netid = user["netid"]
            except:
                continue

            if not year:
                year = "Other"

            if year not in netids:
                netids[year] = []

            netids[year].append(netid)

        years_fmt = [f"{year}: {len(users)}" for year, users in netids.items()]
        years_fmt_admin = [
            f"{year}: {len(users)} ({', '.join(users)})"
            for year, users in netids.items()
        ]

        years_fmt.sort()
        years_fmt_admin.sort()

        header = ["Who's subscribed?"]
        years_fmt = header + years_fmt
        years_fmt_admin = header + years_fmt_admin

        return "|".join(years_fmt), "|".join(years_fmt_admin)

    if courseid is None or courseid == "" or db.get_course(courseid) is None:
        return None, None

    # updates course info if it has been 2 minutes since last update
    Monitor(db).pull_course_updates(courseid)
    course = db.get_course_with_enrollment(courseid)

    # split course data into basic course details, and list of classes
    # with enrollmemnt data
    course_details = {}
    classes_list = []
    for key in course.keys():
        if key.startswith("class_"):
            curr_class = course[key]
            classid = curr_class["classid"]
            try:
                waitlist_count = db.get_class_waitlist_size(classid)
            except Exception:
                waitlist_count = 0
            try:
                time_of_last_notif = db.get_time_of_last_notif(classid)
            except Exception:
                time_of_last_notif = None
            curr_class["wl_size"] = waitlist_count
            curr_class["time_of_last_notif"] = (
                time_of_last_notif if time_of_last_notif is not None else "-"
            )
            (
                curr_class["subs_stats"],
                curr_class["subs_stats_admin"],
            ) = generate_subs_stats_string(classid)
            classes_list.append(curr_class)
        else:
            course_details[key] = course[key]

    return course_details, classes_list


def is_admin(netid, db):
    return db.is_admin(netid)


# get release notes to display on About page
def get_release_notes():
    # delimiters used in RELEASE_NOTES.md
    NOTE_DELIMITER = "<!-- NOTE -->"
    BODY_DELIMITER = "<!-- BODY -->"

    # path of main directory
    main_dir = f"{os.path.dirname(__file__)}/../"

    try:
        with open(f"{main_dir}/RELEASE_NOTES.md") as f1, open(
            f"{main_dir}/static/release_notes_metadata.json"
        ) as f2:
            read_data = f1.read()
            notes_raw = read_data.split(NOTE_DELIMITER)[1:]

            # get body of each release note and convert to HTML
            bodies = []
            for note in notes_raw:
                split_note = note.split(BODY_DELIMITER)
                # if RELEASE_NOTES.md is wrongly formatted
                if len(split_note) != 2:
                    return False, []
                bodies.append(markdown(split_note[1]))

            # get metadata for each release note
            metadata = json.load(f2)

            # if two files are wrongly formatted / do not contain equal # of notes
            num_notes = len(bodies)
            if num_notes != len(metadata):
                return False, []

            # construct list of release notes (metadata + body)
            notes = []
            for i in range(num_notes):
                data = metadata[i]
                # if metadata obj does not contain correct keys
                if "title" not in data or "date" not in data or "tags" not in data:
                    return False, []
                data["body"] = bodies[i]
                notes.append(data)

            return True, notes
    except:
        log_error("Failed to open or parse release note files")
        return False, []


def get_notifs_status_data():
    db = Database()
    return {
        "notifs_online": db.get_cron_notification_status(),
        "next_notifs": db.get_current_or_next_notifs_interval(),
        "term_name": db.get_current_term_code()[1],
    }


def log_page_visit(page, netid):
    Database()._add_system_log(
        "user",
        {"message": f"{page} page visited by user {netid}"},
        netid=netid,
    )


if __name__ == "__main__":
    res = do_search("zishuoz", search_netid=True)
    print(res)

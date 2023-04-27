# ----------------------------------------------------------------------
# update_all_courses_utils.py
# Contains utilities for update_all_courses.py for the purpose of
# multiprocessing (top-level functions required).
# ----------------------------------------------------------------------

import time
from sys import stderr

from database import Database
from log_utils import *
from mobileapp import MobileApp

_api = MobileApp()


# return all department codes (e.g. COS, ECE, etc.)
def get_all_dept_codes(term):
    # hidden feature of MobileApp API (thanks to Jonathan Wilding
    # from OIT for helping us find this)
    res = _api.get_courses(term=term, subject="list")

    try:
        codes = tuple([k["code"] for k in res["term"][0]["subjects"]])
        codes[0] and codes[1]
    except:
        raise Exception("failed to get all department codes")

    return codes


# fetches and inserts new course information into the database
def process_dept_codes(dept_codes: str, current_term_code: str, hard_reset: bool):
    try:
        db = Database()
        old_enrollments = list(
            db._db.enrollments.find(
                {},
                {
                    "_id": 0,
                    "classid": 1,
                    "last_notif": 1,
                    "prev_enrollment": 1,
                },
            )
        )
        old_courses = list(db._db.courses.find({}, {"_id": 0, "displayname": 1}))
        old_courses = set(map(lambda x: x["displayname"], old_courses))
        new_courses = set()

        # precompute dictionary of times of last notif
        old_last_notifs = {}
        old_prev_enrollments = {}
        for enrollment in old_enrollments:
            if "last_notif" in enrollment:
                old_last_notifs[enrollment["classid"]] = enrollment["last_notif"]
            if "prev_enrollment" in enrollment:
                old_prev_enrollments[enrollment["classid"]] = enrollment[
                    "prev_enrollment"
                ]

        courses = _api.get_courses(term=current_term_code, subject=dept_codes)

        if "subjects" not in courses["term"][0]:
            raise RuntimeError("no query results")

        if hard_reset:
            db.reset_db()
        else:
            db.soft_reset_db()

        n_courses = 0
        n_sections = 0

        # iterate through all subjects, courses, and classes
        for subject in courses["term"][0]["subjects"]:
            log_info(f"Processing dept code {subject['code']}")
            for course in subject["courses"]:
                courseid = course["course_id"]
                if db.courses_contains_courseid(courseid):
                    log_info(f"Already processed courseID {courseid} - skipping")
                    continue

                # "new" will contain a single course document to be entered
                # in the courses (and, in part, the mapppings) collection
                new = {
                    "courseid": courseid,
                    "displayname": subject["code"] + course["catalog_number"],
                    "displayname_whitespace": subject["code"]
                    + " "
                    + course["catalog_number"],
                    "title": course["title"],
                    "time": time.time(),
                    "has_reserved_seats": course["detail"]["seat_reservations"] == "Y",
                }

                for x in course["crosslistings"]:
                    new["displayname"] += "/" + x["subject"] + x["catalog_number"]
                    new["displayname_whitespace"] += (
                        "/" + x["subject"] + " " + x["catalog_number"]
                    )

                new_courses.add(new["displayname"])

                log_info(f"Inserting {new['displayname']} into mappings")
                db.add_to_mappings(new)

                del new["time"]

                all_new_classes = []
                lecture_idx = 0

                for class_ in course["classes"]:
                    meetings = class_["schedule"]["meetings"][0]
                    section = class_["section"]

                    # skip dummy sections (end with 99)
                    if section.endswith("99"):
                        continue

                    # skip 0-capacity sections
                    if int(class_["capacity"]) == 0:
                        continue

                    classid = class_["class_number"]

                    # in the (very) occurrence that a class does not have any meetings...
                    start_time_ = (
                        "Unknown"
                        if "start_time" not in meetings
                        else meetings["start_time"]
                    )
                    end_time_ = (
                        "Unknown"
                        if "end_time" not in meetings
                        else meetings["end_time"]
                    )
                    days_ = (
                        ["Unknown"] if len(meetings["days"]) == 0 else meetings["days"]
                    )

                    # new_class will contain a single lecture, precept,
                    # etc. for a given course
                    new_class = {
                        "classid": classid,
                        "section": section,
                        "type_name": class_["type_name"],
                        "start_time": start_time_,
                        "end_time": end_time_,
                        "days": " ".join(days_),
                        "enrollment": int(class_["enrollment"]),
                        "capacity": int(class_["capacity"]),
                        "status_is_open": class_["pu_calc_status"] == "Open",
                    }

                    # new_class_enrollment will contain enrollment and
                    # capacity for a given class within a course
                    new_class_enrollment = {
                        "classid": classid,
                        "courseid": courseid,
                        "section": section,
                        "enrollment": int(class_["enrollment"]),
                        "capacity": int(class_["capacity"]),
                    }

                    if not hard_reset and classid in old_last_notifs:
                        log_info(f"Preserving time of last notif for classID {classid}")
                        new_class_enrollment["last_notif"] = old_last_notifs[classid]

                    if not hard_reset and classid in old_prev_enrollments:
                        log_info(
                            f"Preserving previous enrollment for classID {classid}"
                        )
                        new_class_enrollment["prev_enrollment"] = old_prev_enrollments[
                            classid
                        ]

                    log_info(
                        f"Inserting {new['displayname']} {new_class['section']} into enrollments"
                    )
                    db.add_to_enrollments(new_class_enrollment)

                    # pre-recorded lectures are marked as 01:00 AM start
                    if new_class["start_time"] == "01:00 AM":
                        new_class["start_time"] = "Pre-Recorded"
                        new_class["end_time"] = ""

                    # lectures should appear before other section types
                    if class_["type_name"] == "Lecture":
                        all_new_classes.insert(lecture_idx, new_class)
                        lecture_idx += 1
                    else:
                        all_new_classes.append(new_class)

                    n_sections += 1

                for i, new_class in enumerate(all_new_classes):
                    new[f'class_{new_class["classid"]}'] = new_class

                log_info(f"Inserting {new['displayname']} into courses")
                db.add_to_courses(new)

                n_courses += 1

        log_info(f"Processed {n_courses} courses and {n_sections} sections")
        log_info(f"Performed a {'hard' if hard_reset else 'soft'} reset")
        return n_courses, n_sections, list(new_courses - old_courses)

    except Exception as e:
        log_error(f"Failed to get new course data")
        print(e, file=stderr)
        return 0, 0

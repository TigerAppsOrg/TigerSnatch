# ----------------------------------------------------------------------
# monitor_utils.py
# Contains utilities for the Monitor class for the purpose of
# multiprocessing (top-level functions required).
# ----------------------------------------------------------------------

from database import Database
from mobileapp import MobileApp


# gets the latest term code
def get_latest_term():
    return Database().get_current_term_code()[0]


# returns two dictionaries: one containing new class enrollments, one
# containing new class capacities
def get_new_mobileapp_data(
    term: str, courseids: list, classids: list, default_empty_dicts=False
):
    data = MobileApp().get_seats(term=term, course_ids=",".join(courseids))

    if "course" not in data:
        if default_empty_dicts:
            return {}, {}
        raise Exception("no query results")

    new_enroll = {}
    new_cap = {}
    courseids = set(courseids)
    classids = set(classids)
    db = Database()

    for course in data["course"]:
        courseid = course["course_id"]
        # the below checks should never fail if MobileApp is working properly
        if courseid not in courseids:
            continue
        if "classes" not in course:
            continue

        has_reserved_seats = db.does_course_have_reserved_seats(courseid)

        """
        Create the following structure for each of new_cap and new_enroll:
        {
            courseid1: {
                classid1: enroll/cap,
                classid2: enroll/cap,
                ...
            },
            courseid2: {
                classid1: enroll/cap,
                classid2: enroll/cap,
                ...
            },
            ...
        }
        """
        for class_ in course["classes"]:
            classid = class_["class_number"]
            # skip classids that people are not subscribed to
            if classid not in classids:
                continue
            # skip classes whose status is not "Open" (enrollment is not possible)
            if class_["pu_calc_status"] != "Open":
                # for classes with reserved seats that are currenly Closed, update (rolling)
                # previous enrollment to the class's capacity. this will ensure that if the
                # class's status changes to Open, notifs will be sent with accurate # of open
                # seats.
                # if the class is open, this will happen in CourseWrapper.
                if has_reserved_seats:
                    db.update_prev_enrollment_RESERVED_SEATS_ONLY(
                        classid, int(class_["capacity"])
                    )
                continue
            if courseid not in new_enroll:
                new_enroll[courseid] = {}
                new_cap[courseid] = {}
            new_enroll[courseid][classid] = int(class_["enrollment"])
            new_cap[courseid][classid] = int(class_["capacity"])

    return new_enroll, new_cap


# returns course data and parses its data into dictionaries
# ready to be inserted into database collections
def get_course_in_mobileapp(term, course_, curr_time, db: Database):
    # the prepended space in catnum is intentional
    data = MobileApp().get_courses(
        term=term, subject=course_[:3], catnum=f" {course_[3:]}"
    )

    if "subjects" not in data["term"][0]:
        raise RuntimeError("no query results")

    new_enroll = {}
    new_cap = {}
    entirely_new_enrollments = {}

    # iterate through all subjects, courses, and classes
    for subject in data["term"][0]["subjects"]:
        for course in subject["courses"]:
            courseid = course["course_id"]

            new = {
                "courseid": courseid,
                "displayname": subject["code"] + course["catalog_number"],
                "displayname_whitespace": subject["code"]
                + " "
                + course["catalog_number"],
                "title": course["title"],
                "time": curr_time,
                "has_reserved_seats": course["detail"]["seat_reservations"] == "Y",
            }

            if new["displayname"] != course_:
                continue

            for x in course["crosslistings"]:
                new["displayname"] += "/" + x["subject"] + x["catalog_number"]
                new["displayname_whitespace"] += (
                    "/" + x["subject"] + " " + x["catalog_number"]
                )

            new_mapping = new.copy()
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

                new_class = {
                    "classid": classid,
                    "section": section,
                    "type_name": class_["type_name"],
                    "start_time": meetings["start_time"],
                    "end_time": meetings["end_time"],
                    "days": " ".join(meetings["days"]),
                    "enrollment": int(class_["enrollment"]),
                    "capacity": int(class_["capacity"]),
                    "status_is_open": class_["pu_calc_status"] == "Open",
                }

                new_enroll[classid] = int(class_["enrollment"])
                new_cap[classid] = int(class_["capacity"])
                entirely_new_enrollments[classid] = {
                    "classid": classid,
                    "courseid": courseid,
                    "section": section,
                    "enrollment": int(class_["enrollment"]),
                    "capacity": int(class_["capacity"]),
                    "swap_out": [],
                }

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

            for i, new_class in enumerate(all_new_classes):
                new[f'class_{new_class["classid"]}'] = new_class

            break

        else:
            continue

        break

    return new, new_mapping, new_enroll, new_cap, entirely_new_enrollments


if __name__ == "__main__":
    new_enroll, new_cap = get_new_mobileapp_data(
        "1224",
        ["002051", "002054"],
        ["22797", "22795", "21931", "21927"],
        default_empty_dicts=True,
    )
    print(new_enroll)
    print(new_cap)

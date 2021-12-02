# ----------------------------------------------------------------------
# app_helper.py
# Defines helper methods to construct endpoints.
# ----------------------------------------------------------------------

from monitor import Monitor
import re
from sys import stderr


MAX_QUERY_LENGTH = 150


def validate_query(query):
    if len(query) > MAX_QUERY_LENGTH:
        return False
    return re.match("^[^0-9a-zA-Z ]+$", query)


# searches for course based on user query
def do_search(query, db):
    if query is None or not isinstance(query, str):
        return None, ""

    res = []
    if query.strip() == "":
        return None, ""
    elif "<" in query or ">" in query or "script" in query:
        print("HTML code detected in", query, file=stderr)
        return None, ""
    else:
        query = " ".join(query.split())
        query = re.sub(r'[^0-9a-zA-Z"?:%\'\-, ]+', "", query)
        res = db.search_for_course(query)

    return res, query


# pulls most recent course info and returns dictionary with
# course details and list with class info
def pull_course(courseid, db):

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
            try:
                waitlist_count = db.get_class_waitlist_size(curr_class["classid"])
            except Exception:
                waitlist_count = 0
            curr_class["wl_size"] = waitlist_count
            classes_list.append(curr_class)
        else:
            course_details[key] = course[key]

    return course_details, classes_list


def is_admin(netid, db):
    return db.is_admin(netid)


if __name__ == "__main__":
    res = do_search("zishuoz", search_netid=True)
    print(res)

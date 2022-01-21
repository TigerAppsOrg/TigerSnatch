# ----------------------------------------------------------------------
# monitor.py
# Manages enrollment updates through cross-referencing MobileApp and
# the database. Key class method: get_classes_with_changed_enrollments()
# ----------------------------------------------------------------------

from database import Database
from time import time
from sys import stderr
from coursewrapper import CourseWrapper
from monitor_utils import (
    get_latest_term,
    get_course_in_mobileapp,
    get_new_mobileapp_data,
)
from config import COURSE_UPDATE_INTERVAL_MINS


class Monitor:
    def __init__(self, _db: Database):
        self._db = _db

    # organizes all waited-on classes into groups by their parent course

    def _construct_waited_classes(self):
        waited_classes = list(self._db.get_waited_classes())
        disabled_courses = self._db.get_disabled_courses()
        data = {}

        for class_ in waited_classes:
            classid = class_["classid"]
            try:
                deptnum, courseid = self._db.classid_to_course_info(classid)
            except:
                continue

            # skip sections whose course is disabled
            if courseid in disabled_courses:
                print(deptnum, "with courseid", courseid, "is disabled - skipping")
                continue

            if courseid in data:
                data[courseid].append(classid)
            else:
                data[courseid] = [deptnum, classid]

        self._waited_classes = data

    # constructs CourseWrapper objects for all course buckets as
    # specified in _construct_waited_classes()

    def _analyze_classes(self):
        term = get_latest_term()
        courseids = []
        classids = []

        # build list of courseids and list of classids
        for courseid in self._waited_classes:
            courseids.append(courseid)
            classids.extend(self._waited_classes[courseid][1:])

        # get new enrollment and capacity for subscribed sections
        new_enroll_all, new_cap_all = get_new_mobileapp_data(
            term,
            courseids,
            classids,
            default_empty_dicts=True,
        )

        # construct list of CourseWrapper objects
        course_wrappers = []
        for courseid in new_enroll_all:
            course_deptnum = self._waited_classes[courseid][0]
            new_enroll = new_enroll_all[courseid]
            new_cap = new_cap_all[courseid]
            course_wrapper = CourseWrapper(
                course_deptnum, new_enroll, new_cap, courseid, self._db
            )
            # print(course_wrapper, end="")
            course_wrappers.append(course_wrapper)

        self._waited_course_wrappers = course_wrappers

    # generates, caches, and returns a dictionary in the form:
    # {
    #   classid1: n_slots_available,
    #   classid2: n_slots_available,
    #   ...
    # }
    # the result is to be used to determine to whom notifications are to
    # be sent. this method also updates the applicable enrollment data
    # in the enrollments collection.

    def get_classes_with_changed_enrollments(self):
        try:
            return self._changed_enrollments
        except:
            pass

        tic = time()
        print(f"🧮 calculating open spots")
        self._construct_waited_classes()
        try:
            self._waited_classes
        except:
            raise RuntimeError("missing _waited_classes")

        self._analyze_classes()
        try:
            self._waited_course_wrappers
        except:
            raise RuntimeError("missing _waited_course_wrappers")

        data = {}
        for course in self._waited_course_wrappers:
            if course is None:
                continue

            # class_ is classid
            for class_, n_slots in course.get_available_slots().items():
                data[class_] = n_slots

        self._changed_enrollments = data
        print(f"✅ calculated open spots: approx. {round(time()-tic)} seconds")
        return self._changed_enrollments, len(self._waited_course_wrappers)

    # updates all course data if it has been 2 minutes since last update

    def pull_course_updates(self, courseid):
        try:
            time_last_updated = self._db.get_course_time_updated(courseid)
        except Exception as e:
            print(e, file=stderr)
            return

        # if it hasn't been 2 minutes since last update, do not update
        curr_time = time()
        if curr_time - time_last_updated < COURSE_UPDATE_INTERVAL_MINS * 60:
            return

        # update time immediately
        try:
            self._db.update_course_time(courseid, curr_time)
        except Exception as e:
            print(e, file=stderr)

        current_term_code = get_latest_term()

        try:
            displayname = self._db.courseid_to_displayname(courseid)
            (
                new_course,
                new_mapping,
                new_enroll,
                new_cap,
                entirely_new_enrollments,
            ) = get_course_in_mobileapp(
                current_term_code, displayname, curr_time, self._db
            )

            # if no changes to course info, do not update
            if new_course == self._db.get_course(courseid):
                return

            # update course data in db
            self._db.update_course_all(
                courseid,
                new_course,
                new_mapping,
                new_enroll,
                new_cap,
                entirely_new_enrollments,
            )
        except Exception as e:
            print(e, file=stderr)


if __name__ == "__main__":
    monitor = Monitor(Database())
    print(monitor.get_classes_with_changed_enrollments())
    # call again to retrieve cached version
    print("cached version should print directly beneath this:")
    print(monitor.get_classes_with_changed_enrollments())

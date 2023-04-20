# ----------------------------------------------------------------------
# _exec_update_all_courses.py
# Resets and updates the TigerSnatch database with courses from the
# latest term.
#
# Specify one of the following flags:
#   --soft: resets only course-related data
# 	--hard: resets both course and subscription-related data
#
# Approximate execution frequency: once at the start of every course
# selection period i.e. on or after (asap) the date when courses for the
# next semester are released on the Registrar's Course Offerings
# website.
#
# WARNING: all subscription-related data will be CLEARED if the flag --hard
# is specified. We recommend running this script with --hard only ONCE
# at the very beginning of the course selection period. If you wish to
# refresh only course (non-subscription) data, run with --soft (this may be
# run safely throughout the semester, but that is not recommended unless
# there are MAJOR changes to the semester's course offerings).
#
# Example: python _exec_update_all_courses.py --soft
# ----------------------------------------------------------------------

from mobileapp import MobileApp
from database import Database
from sys import argv, exit
from time import time
from os import system
from update_all_courses_utils import get_all_dept_codes, process_dept_codes
from fix_partial_subscriptions import fix_partial_subscriptions
from log_utils import *


# True --> hard reset
# False --> soft reset
def do_update(reset_type):
    tic = time()
    hard_reset = reset_type
    db = Database()

    try:
        # get current term code
        terms = MobileApp().get_terms()
    except:
        raise Exception("failed to query MobileApp term endpoint")

    try:
        current_term_code = terms["term"][0]["code"]
        current_term_name = terms["term"][0]["cal_name"]
        did_update_term_code = db.update_current_term_code(
            current_term_code, current_term_name
        )
        if hard_reset and not did_update_term_code:
            return
    except:
        raise Exception("failed to get current term code")

    db.set_maintenance_status(True)
    try:
        db._add_system_log(
            "admin",
            {
                "message": f"{'hard' if hard_reset else 'soft'} course term update started"
            },
            netid="SYSTEM_AUTO",
        )
        log_info(f"Getting all courses in term code {current_term_code}")

        DEPT_CODES = ",".join(get_all_dept_codes(current_term_code))
        n_courses, n_classes, new_courses = process_dept_codes(
            DEPT_CODES, current_term_code, hard_reset
        )
    except:
        if hard_reset:
            raise Exception(
                "failed to hard-update courses and did not disable maintenance mode"
            )
        db.set_maintenance_status(False)
        raise Exception("failed to soft-update courses and disabled maintenance mode")

    try:
        fix_partial_subscriptions()
    except:
        raise Exception(
            "failed to run fix-subscriptions script and did not disable maintenance mode"
        )

    db.set_maintenance_status(False)

    log_msg = f"{'hard' if hard_reset else 'soft'}-updated to term code {current_term_code} in {round(time()-tic)} seconds ({n_courses} courses, {n_classes} sections)"
    if not hard_reset and len(new_courses) > 0:
        log_msg += f" - new courses: {', '.join(new_courses)}"

    db._add_admin_log(log_msg)

    db._add_system_log(
        "admin",
        {"message": log_msg},
        netid="SYSTEM_AUTO",
    )

    log_info(f"Success: approx. {round(time()-tic)} seconds")


def do_update_async_HARD():
    # needed for execution on heroku servers to avoid the 30 second
    # request timeout for syncronous processes
    system("python src/_exec_update_all_courses.py --hard &")


def do_update_async_SOFT():
    # needed for execution on heroku servers to avoid the 30 second
    # request timeout for syncronous processes
    system("python src/_exec_update_all_courses.py --soft &")


if __name__ == "__main__":

    def process_args():
        if len(argv) != 2 or (argv[1] != "--soft" and argv[1] != "--hard"):
            print("specify one of the following flags:")
            print("\t--soft: resets only course-related data")
            print("\t--hard: resets both course and waitlist-related data")
            exit(2)
        return argv[1] == "--hard"

    do_update(process_args())

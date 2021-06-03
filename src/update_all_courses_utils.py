# ----------------------------------------------------------------------
# update_all_courses_utils.py
# Contains utilities for update_all_courses.py for the purpose of
# multiprocessing (top-level functions required).
# ----------------------------------------------------------------------

from mobileapp import MobileApp
from database import Database
from random import random
from sys import stderr
import time

_api = MobileApp()


# return all department codes (e.g. COS, ECE, etc.)
def get_all_dept_codes(term):
    # hidden feature of MobileApp API (thanks to Jonathan Wilding
    # from OIT for helping us find this)
    res = _api.get_courses(term=term, subject='list')

    try:
        codes = tuple([k['code'] for k in res['term'][0]['subjects']])
        codes[0] and codes[1]
    except:
        raise Exception('failed to get all department codes')

    return codes


# helper method for multiprocessing: fetches and inserts new course
# information into the database
def process_dept_code(args):
    try:
        code, n, current_term_code, dummy_waitlists, hard_reset = args[
            0], args[1], args[2], args[3], args[4]
        db = Database()

        print('processing dept code', code)
        courses = _api.get_courses(term=current_term_code, subject=code)

        if 'subjects' not in courses['term'][0]:
            raise RuntimeError('no query results')

        if n == 0:
            if hard_reset:
                db.reset_db()
            else:
                db.soft_reset_db()

        # iterate through all subjects, courses, and classes
        for subject in courses['term'][0]['subjects']:
            for course in subject['courses']:
                courseid = course['course_id']
                if db.courses_contains_courseid(courseid):
                    print('already processed courseid', courseid, '- skipping')
                    continue

                # "new" will contain a single course document to be entered
                # in the courses (and, in part, the mapppings) collection
                new = {
                    'courseid': courseid,
                    'displayname': subject['code'] + course['catalog_number'],
                    'displayname_whitespace': subject['code'] + ' ' + course['catalog_number'],
                    'title': course['title'],
                    'time': time.time()}

                for x in course['crosslistings']:
                    new['displayname'] += '/' + \
                        x['subject'] + x['catalog_number']
                    new['displayname_whitespace'] += '/' + \
                        x['subject'] + ' ' + x['catalog_number']

                print('inserting', new['displayname'], 'into mappings')
                db.add_to_mappings(new)

                del new['time']

                all_new_classes = []
                lecture_idx = 0

                for class_ in course['classes']:
                    meetings = class_['schedule']['meetings'][0]
                    section = class_['section']

                    # skip dummy sections (end with 99)
                    if section.endswith('99'):
                        continue

                    # skip 0-capacity sections
                    if int(class_['capacity']) == 0:
                        continue

                    classid = class_['class_number']

                    # in the (very) occurrence that a class does not have any meetings...
                    start_time_ = 'Unknown' if 'start_time' not in meetings else meetings[
                        'start_time']
                    end_time_ = 'Unknown' if 'end_time' not in meetings else meetings[
                        'end_time']
                    days_ = ['Unknown'] if len(
                        meetings['days']) == 0 else meetings['days']

                    # new_class will contain a single lecture, precept,
                    # etc. for a given course
                    new_class = {
                        'classid': classid,
                        'section': section,
                        'type_name': class_['type_name'],
                        'start_time': start_time_,
                        'end_time': end_time_,
                        'days': ' '.join(days_),
                        'enrollment': int(class_['enrollment']),
                        'capacity': int(class_['capacity'])
                    }

                    # new_class_enrollment will contain enrollment and
                    # capacity for a given class within a course
                    new_class_enrollment = {
                        'classid': classid,
                        'courseid': courseid,
                        'section': section,
                        'enrollment': int(class_['enrollment']),
                        'capacity': int(class_['capacity']),
                        'swap_out': []
                    }

                    print('inserting', new['displayname'],
                          new_class['section'], 'into enrollments')
                    db.add_to_enrollments(new_class_enrollment)

                    # pre-recorded lectures are marked as 01:00 AM start
                    if new_class['start_time'] == '01:00 AM':
                        new_class['start_time'] = 'Pre-Recorded'
                        new_class['end_time'] = ''

                    # lectures should appear before other section types
                    if class_['type_name'] == 'Lecture':
                        all_new_classes.insert(lecture_idx, new_class)
                        lecture_idx += 1
                    else:
                        all_new_classes.append(new_class)

                    ####################################################

                    # randomly add waitlists for testing purposes
                    rand = random()
                    if dummy_waitlists and rand < 0.005:
                        print('> inserting', classid, 'into waitlists')
                        db.add_to_waitlist(
                            'sheh', classid, disable_checks=True)
                    elif dummy_waitlists and 0.005 <= rand < 0.01:
                        print('> inserting', classid, 'into waitlists')
                        db.add_to_waitlist(
                            'ntyp', classid, disable_checks=True)
                    elif dummy_waitlists and 0.01 <= rand < 0.015:
                        print('> inserting', classid, 'into waitlists')
                        db.add_to_waitlist(
                            'zishuoz', classid, disable_checks=True)

                    ####################################################

                for i, new_class in enumerate(all_new_classes):
                    new[f'class_{new_class["classid"]}'] = new_class

                print('inserting', new['displayname'], 'into courses')
                db.add_to_courses(new)

        print()

    except Exception as e:
        print(
            f'failed on code {args[0]} with exception message {e}', file=stderr)

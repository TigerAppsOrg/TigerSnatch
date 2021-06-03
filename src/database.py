# ----------------------------------------------------------------------
# database.py
# Contains Database, a class used to communicate with the TigerSnatch
# database.
# ----------------------------------------------------------------------

from sys import stderr
import re
from config import DB_CONNECTION_STR, COLLECTIONS, MAX_LOG_LENGTH, MAX_WAITLIST_SIZE, MAX_ADMIN_LOG_LENGTH, HEROKU_API_KEY, HEROKU_APP_NAME
from schema import COURSES_SCHEMA, CLASS_SCHEMA, MAPPINGS_SCHEMA, ENROLLMENTS_SCHEMA
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime, timedelta
import heroku3


class Database:

    # creates a reference to the TigerSnatch MongoDB database

    def __init__(self):
        self._db = MongoClient(DB_CONNECTION_STR,
                               serverSelectionTimeoutMS=5000,
                               maxIdleTimeMS=600000)

        try:
            self._db.admin.command('ismaster')
        except ConnectionFailure:
            print('failed (server not available)', file=stderr)
            raise Exception('server unavailable')

        self._db = self._db.tigersnatch
        self._check_basic_integrity()

# ----------------------------------------------------------------------
# TRADES METHODS
# ----------------------------------------------------------------------

    # core Trade matching algorithm!

    def find_matches(self, netid, courseid):
        user_waitlists = self.get_user(netid, 'waitlists')

        # sections that user is waiting for for given courseid
        user_course_waitlists = []
        for classid in user_waitlists:
            if self.is_classid_in_courseid(classid, courseid):
                user_course_waitlists.append(classid)

        # get user's currect section
        curr_section = self.get_current_section(netid, courseid)
        if curr_section is None:
            raise Exception(
                f'current section of course {courseid} for {netid} not found - match cannot be made')

        matches = []
        # for each section that user wants
        for classid in user_course_waitlists:
            # skip case where user subscribes to current section
            if classid == curr_section:
                continue
            # get netids that want to swap out of the sections you want
            swapout_list = self.get_swapout_for_class(classid)
            for match_netid in swapout_list:
                # prevents self match
                if match_netid == netid:
                    continue
                # check if match wants your section
                if not curr_section in self.get_user(match_netid, 'waitlists'):
                    continue
                if match_netid in matches:
                    raise Exception(
                        f'user {match_netid} has more than one current section for course {courseid}')

                match_email = self.get_user(match_netid, 'email')
                match_section = self.classid_to_sectionname(classid)

                # ensure that only sections of the same type (e.g. P, C, S, B) are matches
                # if match_section[0] != self.classid_to_sectionname(curr_section)[0]:
                #     continue

                matches.append([match_netid, match_section, match_email])

        if not matches:
            print(f'no matches found for user {netid} in course {courseid}')
        else:
            print(f'matches found for user {netid} in course {courseid}')

        return matches

    # returns list of users who want to swap out of a class

    def get_swapout_for_class(self, classid):
        return self._db.enrollments.find_one({'classid': classid},
                                             {'swap_out': 1, '_id': 0})['swap_out']

    # updates a user's current section (classid) for a course (courseid)

    def update_current_section(self, netid, courseid, classid):
        '''
        possibly need to check whether the desired classid is in the user's waitlists
        '''
        try:
            self.is_classid_in_courseid(classid, courseid)  # throws Exception
            current_sections = self.get_user(netid, 'current_sections')

            print('setting current section in course', courseid,
                  'to class', classid, 'for user', netid)
            current_sections[courseid] = classid
            self._db.users.update_one({'netid': netid}, {'$set': {
                'current_sections': current_sections
            }})

            self._db.enrollments.update_one({'classid': classid},
                                            {'$addToSet': {'swap_out': netid}})
        except:
            return False

        return True

    # removes a user's current section given a courseid

    def remove_current_section(self, netid, courseid):
        try:
            current_sections = self.get_user(netid, 'current_sections')
            print('removing current section in course',
                  courseid, 'for user', netid)

            if courseid in current_sections:
                classid = current_sections[courseid]
                del current_sections[courseid]

                self._db.users.update_one({'netid': netid}, {'$set': {
                    'current_sections': current_sections
                }})

                self._db.enrollments.update_one({'classid': classid},
                                                {'$pull': {'swap_out': netid}})
            else:
                print('user', netid, 'does not have a current section in course (non-fatal)',
                      courseid, file=stderr)
                return False
        except:
            return False

        return True

    # gets a user's current section given a courseid

    def get_current_section(self, netid, courseid):
        return self.get_user(netid, 'current_sections').get(courseid, None)

# ----------------------------------------------------------------------
# ADMIN PANEL METHODS
# ----------------------------------------------------------------------

    # prints log and adds log to admin collection to track admin activity

    def _add_admin_log(self, log):
        print(log)
        log = f"{(datetime.now()-timedelta(hours=4)).strftime('%b %d, %Y @ %-I:%M %p ET')} \u2192 {log}"

        self._db.admin.update_one({}, {
            '$push': {
                'logs': {
                    '$each': [log],
                    '$position': 0,
                    '$slice': MAX_ADMIN_LOG_LENGTH
                }
            }
        })

    # check if netid is an admin is defined in the database

    def is_admin(self, netid):
        return netid in self._db.admin.find_one({}, {'admins': 1, '_id': 0})['admins']

    # returns MAX_ADMIN_LOG_LENGTH most recent admin logs

    def get_admin_logs(self):
        return self._db.admin.find_one({}, {'logs': 1, '_id': 0})

    # returns dictionary with all admin data (excluding logs)

    def get_admin_data(self):
        return self._db.admin.find_one({}, {'logs': 0, '_id': 0})

    # returns dictionary with app-related data

    def get_app_data(self):
        num_users = self._db.users.count_documents({})
        num_users_on_waitlists = self._db.waitlists.count_documents(
            {'waitlists': {'$not': {'$size': 0}}})
        num_courses_in_db = self._db.mappings.count_documents({})
        num_sections_with_waitlists = self._db.waitlists.count_documents({})
        return {
            'num_users': num_users,
            'num_users_on_waitlists': num_users_on_waitlists,
            'num_courses_in_db': num_courses_in_db,
            'num_sections_with_waitlists': num_sections_with_waitlists
        }

    # sets notification script status to either True (on) or False (off)

    def set_cron_notification_status(self, status, admin_netid='SYSTEM_AUTO'):
        if not isinstance(status, bool):
            raise Exception('status must be a boolean')

        try:
            app = self._connect_to_heroku()
            app.process_formation()['notifs'].scale(1 if status else 0)

            self._add_admin_log(
                f'notification script is now {"on" if status else "off"}')
            self._add_system_log('cron', {
                'message': f'notification script set to {"on" if status else "off"}'
            }, netid=admin_netid)
        except:
            raise Exception(
                'something is badly wrong - check heroku website')

    # sets notification script status; either True (on) or False (off)

    def get_cron_notification_status(self):
        try:
            app = self._connect_to_heroku()
            return 'notifs' in app.dynos()
        except:
            raise Exception(
                'something is badly wrong - check heroku website')

    # clears and removes users from all waitlists

    def clear_all_waitlists(self, admin_netid):
        try:
            self._add_admin_log('clearing all subscriptions')
            self._db.users.update_many(
                {},
                {'$set': {'waitlists': []}}
            )

            self._db['waitlists'].delete_many({})

            self._add_system_log('admin', {
                'message': 'all subscriptions cleared'
            }, netid=admin_netid)
            return True
        except:
            return False

    # clears and removes users from all Trades

    def clear_all_trades(self, admin_netid):
        try:
            self._add_admin_log('clearing all trades')
            self._db.users.update_many(
                {},
                {'$set': {'current_sections': {}}}
            )

            self._db.enrollments.update_many(
                {},
                {'$set': {'swap_out': []}}
            )

            self._add_system_log('admin', {
                'message': 'all trades cleared'
            }, netid=admin_netid)
            return True
        except:
            return False

    # clears all user logs

    def clear_all_user_logs(self, admin_netid):
        try:
            self._add_admin_log(
                'clearing all user subscriptions and trades logs')
            self._db.logs.update_many(
                {},
                {'$set': {'waitlist_log': [],
                          'trade_log': []}}
            )

            self._add_system_log('admin', {
                'message': 'all user subscriptions and trades logs cleared'
            }, netid=admin_netid)
            return True
        except:
            return False

    # clears and removes users from the waitlist for class classid

    def clear_class_waitlist(self, classid, admin_netid, log_classid_skip=True):
        try:
            class_waitlist = self.get_class_waitlist(classid)['waitlist']
            self._add_admin_log(
                f'unsubscribing users {class_waitlist} from class {classid}')

            self._db.users.update_many({'netid': {'$in': class_waitlist}},
                                       {'$pull': {'waitlists': classid}})
            self._db.waitlists.delete_one({'classid': classid})

            self._add_system_log('admin', {
                'message': f'subscriptions for class {classid} cleared'
            }, netid=admin_netid)
            return True
        except:
            if log_classid_skip:
                print(
                    f'waitlist for class {classid} does not exist - skipping', file=stderr)
            return False

    # clears and removes users from all waitlists for class classid

    def clear_course_waitlists(self, courseid, admin_netid):
        try:
            course_data = self.get_course(courseid)
            classids = [i.split('_')[1]
                        for i in course_data.keys() if i.startswith('class_')]
            self._add_admin_log(
                f'clearing subscriptions for course {courseid}')

            for classid in classids:
                self.clear_class_waitlist(classid, log_classid_skip=False)

            self._add_system_log('admin', {
                'message': f'subscriptions for course {courseid} cleared'
            }, netid=admin_netid)
            return True
        except:
            print(
                f'failed to clear waitlists for course {courseid}', file=stderr)
            return False

    # adds netid to app blacklist

    def add_to_blacklist(self, netid, admin_netid):
        # removes user profile from users collection
        # removes user from any waitlists
        def remove_user(netid):
            print('removing user', netid, 'from all waitlists')
            classids = self.get_user(netid, 'waitlists')
            for classid in classids:
                self.remove_from_waitlist(netid, classid)

            print('removing user', netid, 'from all swap_out lists')
            courseids = self.get_user(netid, 'current_sections').keys()
            for courseid in courseids:
                self.remove_current_section(netid, courseid)

            print('removing user', netid, 'from users and logs collections')
            self._db.users.delete_one({'netid': netid})
            self._db.logs.delete_one({'netid': netid})

        try:
            if self.is_admin(netid):
                self._add_admin_log(
                    f'user {netid} is an admin - cannot be blacklisted')
                return

            blacklist = self.get_blacklist()

            # check if user is already in blacklist
            if netid in blacklist:
                self._add_admin_log(
                    f'user {netid} already on blacklist - not added')
                return

            if self.is_user_created(netid):
                remove_user(netid)

            blacklist.append(netid)
            self._db.admin.update_one(
                {}, {'$set': {'blacklist': blacklist}})
            self._add_admin_log(
                f'user {netid} added to blacklist and removed from database')

            self._add_system_log('admin', {
                'message': f'user {netid} added to blacklist and removed from database'
            }, netid=admin_netid)
            return True

        except Exception:
            print(f'failed to add user {netid} to blacklist', file=stderr)
            return False

    # remove netid from app blacklist

    def remove_from_blacklist(self, netid, admin_netid):
        try:
            blacklist = self.get_blacklist()
            if netid not in blacklist:
                self._add_admin_log(
                    f'user {netid} not on blacklist - not removed')
                return False

            blacklist.remove(netid)
            self._db.admin.update_one(
                {}, {'$set': {'blacklist': blacklist}})
            self._add_admin_log(f'user {netid} removed from blacklist')

            self._add_system_log('admin', {
                'message': f'user {netid} removed from blacklist'
            }, netid=admin_netid)
            return True
        except Exception:
            print(f'failed to remove user {netid} from blacklist', file=stderr)
            return False

    # returns list of blacklisted netids

    def get_blacklist(self):
        return self._db.admin.find_one(
            {}, {'blacklist': 1, '_id': 0})['blacklist']

    # returns a user's waited-on sections

    def get_waited_sections(self, netid, trades=False):
        try:
            classids = self.get_user(
                netid, 'current_sections').values() if trades else self.get_user(netid, 'waitlists')
        except:
            print('user', netid, 'does not exist', file=stderr)
            return 'missing'
        res = []

        for classid in classids:
            deptnum, name, section = self.classid_to_classinfo(classid)
            res.append(f'{name} ({deptnum}): {section}')

        if len(res) == 0:
            return 'No data'

        return '{'.join(sorted(res))


# ----------------------------------------------------------------------
# BLACKLIST UTILITY METHODS
# ----------------------------------------------------------------------

    # returns True if netid is on app blacklist

    def is_blacklisted(self, netid):
        try:
            blacklist = self.get_blacklist()
            return netid in blacklist
        except Exception:
            print(f'error in checking if {netid} is on blacklist', file=stderr)

# ----------------------------------------------------------------------
# USER METHODS
# ----------------------------------------------------------------------

    # checks if user exists in users collection

    def is_user_created(self, netid):
        return self._db.users.find_one({'netid': netid.rstrip()}, {'netid': 1}) is not None

    # creates user entry in users collection

    def create_user(self, netid):
        if self.is_user_created(netid):
            print(f'user {netid} already exists', file=stderr)
            return
        netid = netid.rstrip()
        self._db.users.insert_one(
            {'netid': netid,
             'email': f'{netid}@princeton.edu',
             'phone': '',
             'waitlists': [],
             'current_sections': {}})
        self._db.logs.insert_one(
            {'netid': netid,
             'waitlist_log': [],
             'trade_log': []})
        print(f'successfully created user {netid}')

    # update user netid's waitlist log

    def update_user_waitlist_log(self, netid, entry):
        entry = f"{(datetime.now()-timedelta(hours=4)).strftime('%b %d, %Y @ %-I:%M %p ET')} \u2192 {entry}"

        self._db.logs.update_one({'netid': netid}, {
            '$push': {
                'waitlist_log': {
                    '$each': [entry],
                    '$position': 0,
                    '$slice': MAX_LOG_LENGTH
                }
            }
        })

        print(
            f'waitlist log for user {netid} successfully updated with entry {entry}')

    # gets user netid's waitlist log in array-of-strings format

    def get_user_waitlist_log(self, netid):
        return self._db.logs.find_one({'netid': netid.rstrip()},
                                      {'waitlist_log': 1, '_id': 0})['waitlist_log']

    # update user netid's waitlist log

    def update_user_trade_log(self, netid, entry):
        entry = f"{(datetime.now()-timedelta(hours=4)).strftime('%b %d, %Y @ %-I:%M %p ET')} \u2192 {entry}"

        self._db.logs.update_one({'netid': netid}, {
            '$push': {
                'trade_log': {
                    '$each': [entry],
                    '$position': 0,
                    '$slice': MAX_LOG_LENGTH
                }
            }
        })
        print(
            f'trade log for user {netid} successfully updated with entry {entry}')

    # gets user netid's trade log in array-of-strings format

    def get_user_trade_log(self, netid):
        return self._db.logs.find_one({'netid': netid.rstrip()},
                                      {'trade_log': 1, '_id': 0})['trade_log']

    # returns user data given netid and a key from the users collection

    def get_user(self, netid, key):
        try:
            return self._db.users.find_one({'netid': netid.rstrip()},
                                           {key: 1, '_id': 0})[key]
        except:
            raise Exception(f'failed to get key {key} for netid {netid}')

    # returns all data needed to display user waitlists on dashboard

    def get_dashboard_data(self, netid):
        netid = netid.rstrip()
        dashboard_data = {}
        try:
            waitlists = self._db.users.find_one({'netid': netid})['waitlists']
        except:
            raise RuntimeError(f'user {netid} does not exist')
        for classid in waitlists:
            try:
                class_stats = self.get_class_enrollment(classid)
            except:
                raise RuntimeError(
                    f'classid {classid} not found in enrollments')

            dashboard_data[classid] = {}

            courseid = class_stats['courseid']
            course_data = self.get_course(courseid)
            try:
                class_data = course_data[f'class_{classid}']
            except:
                raise RuntimeError(
                    f'classid {classid} not found in courses')

            dashboard_data[classid]['courseid'] = courseid
            dashboard_data[classid]['displayname'] = course_data['displayname']
            dashboard_data[classid]['section'] = class_data['section']
            dashboard_data[classid]['start_time'] = class_data['start_time']
            dashboard_data[classid]['end_time'] = class_data['end_time']
            dashboard_data[classid]['days'] = class_data['days']
            dashboard_data[classid]['enrollment'] = class_stats['enrollment']
            dashboard_data[classid]['capacity'] = class_stats['capacity']

            try:
                class_waitlist = self._db.waitlists.find_one(
                    {'classid': classid})['waitlist']
                dashboard_data[classid]['position'] = class_waitlist.index(
                    netid)+1
            except ValueError:
                raise ValueError(
                    f'user {netid} not found in waitlist for {classid}')
            except:
                raise RuntimeError(
                    f'classid {classid} not found in waitlists')

        return dashboard_data

    # returns course displayname corresponding to courseid

    def update_user(self, netid, email):
        try:
            self._db.users.update_one({'netid': netid.rstrip()}, {
                '$set': {'email': email}})
        except:
            raise RuntimeError(f'attempt to update email for {netid} failed')

    # returns list of results whose netid
    # contain user query string

    def search_for_user(self, query):
        if query is None:
            return [], ''

        query = " ".join(query.split())
        query = re.sub(r'[^0-9a-zA-Z]+', '', query)
        query_re = re.compile(query, re.IGNORECASE)
        res = list(self._db.users.find({'netid': {'$regex': query_re}}))
        return res, query

    # returns a user's current sections

    def get_current_sections(self, netid):
        try:
            current_sections = self.get_user(netid, 'current_sections')
        except:
            print('user', netid, 'does not exist', file=stderr)
            return None
        res = []

        for courseid in current_sections.keys():
            course_name = self.courseid_to_displayname(courseid)
            section_name = self.classid_to_sectionname(
                current_sections[courseid])
            res.append((course_name, section_name, courseid))

        return res


# ----------------------------------------------------------------------
# TERM METHODS
# ----------------------------------------------------------------------

    # gets current term code from admin collection

    def get_current_term_code(self):
        res = self._db.admin.find_one(
            {}, {'current_term_code': 1, 'current_term_name': 1, '_id': 0})
        return res['current_term_code'], res['current_term_name']

    # updates current term code from admin collection

    def update_current_term_code(self, code, name):
        self._db.admin.update_one({}, {'$set': {'current_term_code': code,
                                                'current_term_name': name}})

# ----------------------------------------------------------------------
# COURSE METHODS
# ----------------------------------------------------------------------

    # returns course displayname corresponding to courseid

    def courseid_to_displayname(self, courseid):
        try:
            displayname = self._db.mappings.find_one(
                {'courseid': courseid})['displayname']
        except:
            raise RuntimeError(f'courseid {courseid} not found in courses')

        return displayname.split('/')[0]

    # return basic course details for course with given courseid

    def get_course(self, courseid):
        return self._db.courses.find_one(
            {'courseid': courseid}, {'_id': 0})

    # returns list of tuples (section_name, classid) for a course
    # set include_lecture to True if you want Lecture section included

    def get_section_names_in_course(self, courseid, include_lecture=False):
        section_name_list = []
        course_dict = self.get_course(courseid)
        for key in course_dict.keys():
            if key.startswith('class_'):
                section_name = course_dict[key]['section']
                classid = course_dict[key]['classid']
                if not include_lecture and section_name.startswith('L'):
                    continue
                section_name_list.append((section_name, classid))
        return section_name_list

    # return list of class ids for a course

    def get_classes_in_course(self, courseid):
        classid_list = []
        course_dict = self.get_course(courseid)
        for key in course_dict.keys():
            if key.startswith('class_'):
                classid_list.append(course_dict[key]['classid'])
        return classid_list

    # returns dictionary with basic course details AND enrollment,
    # capacity, and boolean isFull field for each class
    # for the given courseid

    def get_course_with_enrollment(self, courseid):
        course_info = self.get_course(courseid)
        for key in course_info.keys():
            if key.startswith('class_'):
                class_dict = course_info[key]
                classid = class_dict['classid']
                class_data = self.get_class_enrollment(classid)
                class_dict['enrollment'] = class_data['enrollment']
                class_dict['capacity'] = class_data['capacity']
                class_dict['isFull'] = (
                    class_dict['capacity'] > 0 and class_dict['enrollment'] >= class_dict['capacity'])
        return course_info

    # updates time that a course page was last updated

    def update_course_time(self, courseid, curr_time):
        try:
            self._db.mappings.update_one({'courseid': courseid}, {
                                         '$set': {'time': curr_time}})
        except:
            raise RuntimeError(f'courseid {courseid} not found in courses')

    # returns time that a course page was last updated

    def get_course_time_updated(self, courseid):
        try:
            time = self._db.mappings.find_one(
                {'courseid': courseid})['time']
        except:
            raise RuntimeError(f'courseid {courseid} not found in courses')
        return time

    # checks if the courses collection contains a course with the
    # passed-in courseid

    def courses_contains_courseid(self, courseid):
        return self._db.courses.find_one({'courseid': courseid}) is not None

    # returns list of results whose title and displayname
    # contain user query string

    def search_for_course(self, query):
        query = re.compile(query, re.IGNORECASE)

        res = list(self._db.mappings.find({'$or': [
            {'displayname': {'$regex': query}},
            {'displayname_whitespace': {'$regex': query}},
            {'title': {'$regex': query}}
        ]}))

        return res

# ----------------------------------------------------------------------
# CLASS METHODS
# ----------------------------------------------------------------------

    # returns True if classid is found in course with courseid
    def is_classid_in_courseid(self, classid, courseid):
        try:
            return self._db.enrollments.find_one(
                {'classid': classid}, {'_id': 0, 'courseid': 1})['courseid'] == courseid
        except:
            raise RuntimeError(f'classid {classid} not found in enrollments')

    # returns name of section specified by classid
    def classid_to_sectionname(self, classid):
        try:
            return self._db.enrollments.find_one(
                {'classid': classid}, {'_id': 0, 'section': 1})['section']
        except:
            raise RuntimeError(f'classid {classid} not found in enrollments')

    # returns the corresponding course displayname for a given classid

    def classid_to_course_deptnum(self, classid):
        try:
            courseid = self._db.enrollments.find_one(
                {'classid': classid})['courseid']
        except:
            raise RuntimeError(f'classid {classid} not found in enrollments')

        try:
            displayname = self._db.mappings.find_one(
                {'courseid': courseid})['displayname']
        except:
            raise RuntimeError(f'courseid {courseid} not found in courses')

        return displayname.split('/')[0]

   # returns information about a class including course depts, numbers, title
   # and section number, for display in email/text messages

    def classid_to_classinfo(self, classid):
        try:
            classinfo = self._db.enrollments.find_one(
                {'classid': classid})
            courseid = classinfo['courseid']
            sectionname = classinfo['section']
        except:
            raise Exception(f'classid {classid} cannot be found')

        try:
            mapping = self._db.courses.find_one(
                {'courseid': courseid})
            displayname = mapping['displayname']
            title = mapping['title']
        except:
            raise Exception(f'courseid {courseid} cannot be found')

        dept_num = displayname.split('/')[0]
        return dept_num, title, sectionname

    # get dictionary for class with given classid in courses

    def get_class(self, courseid, classid):
        try:
            course_data = self.get_course(courseid)
        except:
            raise RuntimeError(f'courseid {courseid} not found in courses')
        try:
            return course_data[f'class_{classid}']
        except:
            raise RuntimeError(f'class {classid} not found in courses')

    # returns capacity and enrollment for course with given classid

    def get_class_enrollment(self, classid):
        return self._db.enrollments.find_one({'classid': classid}, {'_id': 0})

    # updates the enrollment and capacity for class classid

    def update_enrollment(self, classid, new_enroll, new_cap, update_courses_entry=True):
        self._db.enrollments.update_one({'classid': classid},
                                        {'$set': {'enrollment': new_enroll,
                                                  'capacity': new_cap}})

        if update_courses_entry:
            courseid = self._db.enrollments.find_one({'classid': classid},
                                                     {'_id': 0, 'courseid': 1})['courseid']
            self._db.courses.update_one({'courseid': courseid},
                                        {'$set': {f'class_{classid}.enrollment': new_enroll,
                                                  f'class_{classid}.capacity': new_cap}})

# ----------------------------------------------------------------------
# WAITLIST METHODS
# ----------------------------------------------------------------------

    # returns all classes to which there are waitlisted students

    def get_waited_classes(self):
        return self._db.waitlists.find({}, {'courseid': 1, 'classid': 1, '_id': 0})

    # returns a specific classid's waitlist document

    def get_class_waitlist(self, classid):
        try:
            return self._db.waitlists.find_one({'classid': classid})
        except:
            raise Exception(f'classid {classid} does not exist')

    # returns a specific classid's waitlist size

    def get_class_waitlist_size(self, classid):
        try:
            return len(self.get_class_waitlist(classid)['waitlist'])
        except:
            raise Exception(f'classid {classid} does not exist')

    # adds user of given netid to waitlist for class classid

    def add_to_waitlist(self, netid, classid, disable_checks=False):
        # validation checks
        def validate():
            # helper method to check if class is full
            def is_class_full(enrollment_dict):
                return enrollment_dict['enrollment'] >= enrollment_dict['capacity']

            if not self.is_user_created(netid):
                raise Exception(f'user {netid} does not exist')
            class_enrollment = self.get_class_enrollment(classid)
            if class_enrollment is None:
                raise Exception(f'class {classid} does not exist')
            if not is_class_full(class_enrollment):
                raise Exception(
                    f'user cannot enter waitlist for non-full class {classid}')
            if classid in self.get_user(netid, 'waitlists'):
                raise Exception(
                    f'user {netid} is already in waitlist for class {classid}')

        netid = netid.rstrip()

        if not disable_checks:
            validate()

        # add classid to user's waitlist
        user_waitlists = self.get_user(netid, 'waitlists')
        try:
            if len(user_waitlists) >= MAX_WAITLIST_SIZE:
                print('user', netid, 'exceeded the waitlist limit of',
                      MAX_WAITLIST_SIZE, file=stderr)
                return 0
        except Exception as e:
            print(e, file=stderr)

        user_waitlists.append(classid)
        self._db.users.update_one({'netid': netid}, {
            '$set': {'waitlists': user_waitlists}})

        # add user to waitlist for classid
        waitlist = self.get_class_waitlist(classid)
        if waitlist is None:
            self._db.waitlists.insert_one({'classid': classid, 'waitlist': []})
            class_waitlist = []
        else:
            class_waitlist = waitlist['waitlist']

        class_waitlist.append(netid)
        self._db.waitlists.update_one({'classid': classid}, {
            '$set': {'waitlist': class_waitlist}})

        print(f'user {netid} successfully added to waitlist for class {classid}')
        return 1

    # removes user of given netid to waitlist for class classid
    # if waitlist for class is empty now, delete entry from waitlists collection

    def remove_from_waitlist(self, netid, classid):
        def validate():
            if not self.is_user_created(netid):
                raise Exception(f'user {netid} does not exist')
            waitlist = self.get_class_waitlist(classid)
            if waitlist is None:
                raise Exception(f'no waitlist for class {classid} exists')
            if classid not in self.get_user(netid, 'waitlists') or netid not in waitlist['waitlist']:
                raise Exception(
                    f'user {netid} not in waitlist for class {classid}')

        netid = netid.rstrip()
        validate()

        # remove classid from user's waitlist
        user_waitlists = self.get_user(netid, 'waitlists')
        user_waitlists.remove(classid)
        self._db.users.update_one({'netid': netid}, {
            '$set': {'waitlists': user_waitlists}})

        # remove user from waitlist for classid
        class_waitlist = self.get_class_waitlist(classid)['waitlist']
        class_waitlist.remove(netid)
        if len(class_waitlist) == 0:
            self._db.waitlists.delete_one({'classid': classid})
        else:
            self._db.waitlists.update_one({'classid': classid}, {
                '$set': {'waitlist': class_waitlist}})

        print(
            f'user {netid} successfully removed from waitlist for class {classid}')

# ----------------------------------------------------------------------
# DATABASE POPULATION METHODS
# ----------------------------------------------------------------------

    # adds a document containing course data to the courses collection
    # (see Technical Documentation for schema)

    def add_to_courses(self, data):
        def validate(data):
            # validates the keys of the passed-in course data dictionary

            if not all(k in data for k in COURSES_SCHEMA):
                raise RuntimeError('invalid courses document schema')

            for k in data:
                if not k.startswith('class_'):
                    continue
                if not all(k_ in data[k] for k_ in CLASS_SCHEMA):
                    raise RuntimeError(
                        'invalid individual class document schema')

        validate(data)
        self._db.courses.insert_one(data)

    # updates course entry in courses, mappings, and enrollment
    # collections with data dictionary

    def update_course_all(self, courseid, new_course, new_mapping, new_enroll, new_cap):
        def validate(new_course, new_mapping):
            if not all(k in new_course for k in COURSES_SCHEMA):
                raise RuntimeError('invalid courses document schema')

            for k in new_course:
                if not k.startswith('class_'):
                    continue
                if not all(k_ in new_course[k] for k_ in CLASS_SCHEMA):
                    raise RuntimeError(
                        'invalid individual class document schema')

            if not all(k in new_mapping for k in MAPPINGS_SCHEMA):
                raise RuntimeError('invalid mappings document schema')

        validate(new_course, new_mapping)
        self._db.courses.replace_one({'courseid': courseid}, new_course)
        for classid in new_enroll.keys():
            self.update_enrollment(
                classid, new_enroll[classid], new_cap[classid], update_courses_entry=False)
        self._db.mappings.replace_one({'courseid': courseid}, new_mapping)

    # adds a document containing mapping data to the mappings collection
    # (see Technical Documentation for schema)

    def add_to_mappings(self, data):
        def validate(data):
            # validates the keys of the passed-in mappings data
            # dictionary

            if not all(k in data for k in MAPPINGS_SCHEMA):
                raise RuntimeError('invalid mappings document schema')

        validate(data)
        self._db.mappings.insert_one(data)

    # adds a document containing enrollment data to the enrollments
    # collection (see Technical Documentation for schema)

    def add_to_enrollments(self, data):
        def validate(data):
            # validates the keys of the passed-in enrollments data
            # dictionary

            if not all(k in data for k in ENROLLMENTS_SCHEMA):
                raise RuntimeError('invalid enrollments document schema')

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
            print('clearing', coll)
            self._db[coll].delete_many({})

        print('clearing waitlists and current_sections in users')
        self._db.users.update_many(
            {},
            {'$set': {'waitlists': [],
                      'current_sections': {}}}
        )

        print('resetting user logs')
        self._db.logs.update_many(
            {},
            {'$set': {'waitlist_log': [],
                      'trade_log': []}}
        )

        clear_coll('mappings')
        clear_coll('courses')
        clear_coll('enrollments')
        clear_coll('waitlists')

    # does the following:
    #   * deletes all documents from mappings
    #   * deletes all documents from courses
    #   * deletes all documents from enrollments
    #   * deletes all user current sections
    # NOTE: does NOT clear waitlist-related data, unlike self.reset_db()

    def soft_reset_db(self):
        def clear_coll(coll):
            print('clearing', coll)
            self._db[coll].delete_many({})

        print('clearing current_sections in users')
        self._db.users.update_many(
            {},
            {'$set': {'current_sections': {}}}
        )

        clear_coll('mappings')
        clear_coll('courses')
        clear_coll('enrollments')

# ----------------------------------------------------------------------
# UTILITY METHODS
# ----------------------------------------------------------------------

    # checks that all required collections are available in self._db;
    # raises a RuntimeError if not

    def _check_basic_integrity(self):
        if COLLECTIONS != set(self._db.list_collection_names()):
            raise RuntimeError(
                'one or more database collections is misnamed and/or missing')

    # turn Heroku maintenance mode ON (True) or OFF (False)

    def set_maintenance_status(self, status):
        if not isinstance(status, bool):
            raise Exception('status must be a boolean')

        app = self._connect_to_heroku()
        if status:
            app.enable_maintenance_mode()
        else:
            app.disable_maintenance_mode()

        self._add_system_log('heroku', {
            'message': f'maintenance mode set to {"on" if status else "off"}'
        })

    # connects to Heroku and returns app variable so you can do
    # operations with Heroku

    def _connect_to_heroku(self):
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.apps()[HEROKU_APP_NAME]
        return app

    # adds log message to logs array in system collection

    def _add_system_log(self, type, meta, netid=None):
        meta['type'] = type
        meta['time'] = datetime.now()
        if netid is not None:
            meta['netid'] = netid
        self._db.system.insert_one(meta)

    # prints database name, its collections, and the number of documents
    # in each collection

    def __str__(self):
        self._check_basic_integrity()
        ret = f'database {self._db.name} with collections:\n'
        for coll in self._db.list_collection_names():
            ref = self._db[coll]
            ret += f'\t{coll:<15}(#docs: {ref.estimated_document_count()})\n'
        return ret


if __name__ == '__main__':
    db = Database()

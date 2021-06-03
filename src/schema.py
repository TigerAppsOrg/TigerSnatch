# ----------------------------------------------------------------------
# schema.py
# Contains tuples of keys that various database documents must contain.
# ----------------------------------------------------------------------

# courses collection
COURSES_SCHEMA = ('courseid', 'displayname', 'title')
CLASS_SCHEMA = ('classid', 'section', 'type_name',
                'start_time', 'end_time', 'days')

# mappings collection
MAPPINGS_SCHEMA = ('displayname', 'displayname_whitespace',
                   'title', 'courseid', 'time')

# enrollments collection
ENROLLMENTS_SCHEMA = ('classid', 'enrollment', 'capacity')

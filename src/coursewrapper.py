# ----------------------------------------------------------------------
# coursewrapper.py
# Helper class for Monitor, mainly used to compute available slots for
# all classes in a given course.
# ----------------------------------------------------------------------


class CourseWrapper:
    def __init__(self, course_deptnum, new_enroll, new_cap, courseid, db):
        self._db = db
        self._course_deptnum = course_deptnum
        self._new_enroll = new_enroll
        self._new_cap = new_cap
        self._courseid = courseid
        self._has_reserved_seats = self._db.does_course_have_reserved_seats(courseid)
        self._compute_available_slots()

    # returns _course_deptnum

    def get_course_deptnum(self):
        return self._course_deptnum

    # returns dictionary containing available slots for all inputted
    # classids

    def get_available_slots(self):
        try:
            return self._available_slots
        except:
            raise RuntimeError("available slots have not yet been calculated")

    # computes available slots for all classids

    def _compute_available_slots(self):
        diff = {}

        for k in self._new_enroll:
            try:
                if self._has_reserved_seats:
                    if self._new_enroll[k] >= self._new_cap[k]:
                        # detects the case where spots have opened but enrollment is still not possible (enrollment >= capacity)
                        d = 0
                    else:
                        # spot openings = previous enrollment - new enrollment
                        d = (
                            self._db.get_prev_enrollment_RESERVED_SEATS_ONLY(k)
                            - self._new_enroll[k]
                        )
                    # update (rolling) previous enrollment with new enrollment
                    self._db.update_prev_enrollment_RESERVED_SEATS_ONLY(
                        k, self._new_enroll[k]
                    )
                else:
                    # spot openings = new capacity - new enrollment
                    d = self._new_cap[k] - self._new_enroll[k]
            except:
                raise RuntimeError(f"missing key {k} in either new_cap or new_enroll")

            diff[k] = max(d, 0)

        self._db = None
        self._available_slots = diff

    # string representation; prints _course_deptnum, classids, and all
    # associated available slot counts

    def __str__(self):
        if sum(self._available_slots.values()) == 0:
            return ""

        ret = f"\ncourse {self._course_deptnum}\n"

        for k, v in self._available_slots.items():
            if v == 0:
                continue
            ret += f"   classid {k}: {v} open spot(s) with enrollment {self._new_enroll[k]}/{self._new_cap[k]}\n"

        return ret


if __name__ == "__main__":
    new_enroll = {"40268": 9}
    new_cap = {"40268": 10}
    course = CourseWrapper("COS126", new_enroll, new_cap, "002054")
    print(course, end="")

    new_enroll = {"40268": 10}
    course1 = CourseWrapper("COS126", new_enroll, new_cap, "002054")
    print(course1, end="")
    print(course, end="")
    print(course, end="")
    # print(course.get_available_slots())
    # print(course.get_course_deptnum())

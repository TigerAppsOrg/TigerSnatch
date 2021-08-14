# ----------------------------------------------------------------------
# coursewrapper.py
# Helper class for Monitor, mainly used to compute available slots for
# all classes in a given course.
# ----------------------------------------------------------------------


class CourseWrapper:
    def __init__(self, course_deptnum, new_enroll, new_cap):
        self._course_deptnum = course_deptnum
        self._new_enroll = new_enroll
        self._new_cap = new_cap
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
                d = self._new_cap[k] - self._new_enroll[k]
            except:
                raise RuntimeError(f"missing key {k} in either new_cap or new_enroll")

            diff[k] = max(d, 0)

        self._available_slots = diff

    # string representation; prints _course_deptnum, classids, and all
    # associated available slot counts

    def __str__(self):
        ret = f"CourseWrapper for course_deptnum {self._course_deptnum}:\n"

        for k, v in self._available_slots.items():
            ret += f"\tclassid {k}: {v} available slot(s) with enrollment "
            ret += f"{self._new_enroll[k]}/{self._new_cap[k]}\n"

        return ret


if __name__ == "__main__":
    new_enroll = {"1": 9, "2": 10, "3": 11}

    new_cap = {"1": 10, "2": 10, "3": 10}

    course = CourseWrapper("COS126", new_enroll, new_cap)

    print(course)
    print(course.get_available_slots())
    print(course.get_course_deptnum())

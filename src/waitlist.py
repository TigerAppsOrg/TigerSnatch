# ----------------------------------------------------------------------
# waitlist.py
# Contains Waitlist, a class which manages waitlist-related
# functionality for a given user
# ----------------------------------------------------------------------

from database import Database
from sys import stderr


class Waitlist:

  # pass-in netid for a user

  def __init__(self, netid):
    self._netid = netid
    self._db = Database()

  # add user to waitlist for class with given classid
  # status:
  # 0 - user waitlist limit reached
  # 1 - can enroll
  # 2 - some error
  def add_to_waitlist(self, classid):
    try:
      status = self._db.add_to_waitlist(self._netid, classid)
      return status
    except Exception as e:
      print(e, file=stderr)
      return 2

  # remove user from waitlist for class with given classid

  def remove_from_waitlist(self, classid):
    try:
      self._db.remove_from_waitlist(self._netid, classid)
      return True
    except Exception as e:
      print(e, file=stderr)
      return False


if __name__ == '__main__':
  waitlist = Waitlist('ntyp')
  waitlist.add_to_waitlist('40287')
  waitlist.remove_from_waitlist('40287')

  waitlist = Waitlist('sheh')
  waitlist.add_to_waitlist('43655')
  waitlist.remove_from_waitlist('43655')

# ----------------------------------------------------------------------
# _exec_reset_db.py
# Simple script to either soft or hard reset the database.
#
# Specify one of the following flags:
#   --soft: resets only course-related data
# 	--hard: resets both course and waitlist-related data
#
# WARNING: all waitlist-related data will be CLEARED if the flag --hard
# is specified. If you wish to refresh only course (non-waitlist) data,
# run with --soft.
#
# Example: python _exec_reset_db.py --soft
# ----------------------------------------------------------------------

from database import Database
from sys import exit, argv

if __name__ == "__main__":

    def process_args():
        if len(argv) != 2 or (argv[1] != "--soft" and argv[1] != "--hard"):
            print("specify one of the following flags:")
            print("\t--soft: resets only course-related data")
            print("\t--hard: resets both course and waitlist-related data")
            exit(2)
        return argv[1] == "--hard"

    hard_reset = process_args()

    if hard_reset:
        Database().reset_db()
        print("done")
    else:
        Database().soft_reset_db()
        print("done")

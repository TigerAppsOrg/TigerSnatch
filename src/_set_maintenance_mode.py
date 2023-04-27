# ----------------------------------------------------------------------
# _set_maintenance_mode.py
# Simple script to enable or disable maintenance mode. Also affects the
# notifs dyno in the same way.
#
# Specify one of the following flags:
#   --on: Enables maintenance mode
# 	--off: Disables maintenance mode
#
# Example: python _set_maintenance_mode.py --on
# ----------------------------------------------------------------------

from sys import argv, exit

from database import Database
from log_utils import *

if __name__ == "__main__":

    def process_args():
        if len(argv) != 2 or (argv[1] != "--on" and argv[1] != "--off"):
            print("specify one of the following flags:")
            print("\t--on: enable maintenance mode and notifs dyno")
            print("\t--off: disable maintenance mode and notifs dyno")
            exit(2)
        return argv[1] == "--on"

    turn_on = process_args()

    Database().set_maintenance_status(turn_on)
    log_info(f"Maintenance mode {'enabled' if turn_on else 'disabled'}")

# ----------------------------------------------------------------------
# _set_notif_status.py
# Simple script to enable or disable the cron notification script.
#
# Specify one of the following flags:
#   --on: Enables the cron notification script
#	--off: Disables the cron notification script
#
# See _cron_notifs.py and send_notifs.py headers for more information.
#
# Example: python _set_notif_status.py --on
# ----------------------------------------------------------------------

from sys import exit, argv
from database import Database

if __name__ == '__main__':
  def process_args():
    if len(argv) != 2 or (argv[1] != '--on' and argv[1] != '--off'):
      print('specify one of the following flags:')
      print('\t--on: enable notifications cron script')
      print('\t--off: disable notifications cron script')
      exit(2)
    return argv[1] == '--on'

  turn_on = process_args()

  Database().set_cron_notification_status(turn_on)
  print('done')

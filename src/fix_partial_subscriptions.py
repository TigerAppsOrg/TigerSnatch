from database import Database
from log_utils import *


def fix_partial_subscriptions():
    log_info("Fixing partial subscriptions/unsubscriptions...")

    database = Database()
    db = database._db

    users = list(db.users.find({}, {"_id": 0, "waitlists": 1, "netid": 1}))
    waitlists = list(db.waitlists.find({}, {"_id": 0, "waitlist": 1, "classid": 1}))

    inv = {}
    for user in users:
        netid = user["netid"]
        for classid in user["waitlists"]:
            if classid not in inv:
                inv[classid] = []
            inv[classid].append(netid)

    inv_clean = {}
    for classid, netids in inv.items():
        inv_clean[classid] = tuple(sorted(netids))

    ref = {}
    for waitlist in waitlists:
        classid = waitlist["classid"]
        ref[classid] = tuple(sorted(waitlist["waitlist"]))

    for classid, netids_from_users in inv_clean.items():
        netids_from_waitlists = ref[classid]
        netids_from_waitlists_set = set(netids_from_waitlists)
        netids_from_users_set = set(netids_from_users)

        if netids_from_waitlists_set != netids_from_users_set:
            diff = netids_from_waitlists_set ^ netids_from_users_set

            log_info(f"classID {classid}: user diff to unsubscribe {diff}")
            for netid in diff:
                database.remove_from_waitlist(netid, classid, force_remove=True)

    log_info("Done fixing partial subscriptions/unsubscriptions")


if __name__ == "__main__":
    fix_partial_subscriptions()

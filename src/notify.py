# ----------------------------------------------------------------------
# notify.py
# Sends users emails or text messages about enrollment updates
# ----------------------------------------------------------------------

from sendgrid import SendGridAPIClient
from sys import stderr
from twilio.rest import Client
from config import (
    SENDGRID_API_KEY,
    TS_EMAIL,
    TWILIO_PHONE,
    TWILIO_SID,
    TWILIO_TOKEN,
    TS_DOMAIN,
    MIN_NOTIFS_DELAY_MINS,
)
from datetime import datetime
import pytz

TZ_ET = pytz.timezone("US/Eastern")
TZ_UTC = pytz.timezone("UTC")


class Notify:
    # initializes Notify, fetching all information about a given classid
    # to format and send an email to the first student on the waitlist
    # for that classid

    def __init__(self, classid, n_new_slots, db):
        self._classid = classid
        self.n_new_slots = n_new_slots
        self.db = db
        try:
            (
                self._deptnum,
                self._title,
                self._sectionname,
                self._courseid,
            ) = db.classid_to_classinfo(classid)
            self._has_reserved_seats = db.does_course_have_reserved_seats(
                self._courseid
            )
            self._coursename = f"{self._deptnum}: {self._title}"
            self._netids = db.get_class_waitlist(classid)["waitlist"]

            user_log = f"{n_new_slots} spot{'s'[:n_new_slots^1]} available in {self._deptnum} {self._sectionname}"

            # courses with reserved seating use different logic for notifying
            if not self._has_reserved_seats:
                # reduce spam by filtering netIDs such that notifs are sent to users if either:
                #   1. the number of new spots (non-zero) has changed from the previous count
                #   2. it's been more than MIN_NOTIFS_DELAY_MINS minutes since the last notif was sent
                temp_netids = []
                for netid in self._netids:
                    # if user is not auto resubbed, then always send notif
                    # (they will be removed from waitlist in this script anyway)
                    if not db.get_user_auto_resub(netid):
                        temp_netids.append(netid)
                        continue

                    history = db.get_user_notifs_history(netid, classid)
                    open_spots_changed = n_new_slots != history["n_open_spots"]
                    time_diff_mins = (
                        datetime.now(TZ_ET) - TZ_UTC.localize(history["last_notif"])
                    ).total_seconds() / 60
                    notifs_delay_exceeded = (
                        n_new_slots == history["n_open_spots"]
                        and time_diff_mins >= MIN_NOTIFS_DELAY_MINS
                    )

                    # send notif if # open spots changes OR if last_notif time is >=MIN_NOTIFS_DELAY_MINS mins ago
                    if open_spots_changed or notifs_delay_exceeded:
                        temp_netids.append(netid)
                self._netids = temp_netids

            db.update_users_notifs_history(
                self._netids,
                classid,
                n_new_slots,
                reserved_seats=self._has_reserved_seats,
            )

            self._emails = []
            self._phones = []

            for netid in self._netids:
                self._emails.append(db.get_user(netid, "email"))
                self._phones.append(db.get_user(netid, "phone"))
                db.update_user_waitlist_log(netid, user_log)

            if len(self._netids) > 0:
                db.update_time_of_last_notif(classid)

        except Exception as e:
            raise Exception(
                f"unable to get notification data for subscriptions of class {classid} with error: {e}"
            )

    # returns the netIDs of this Notify object

    def get_netids(self):
        return self._netids

    # returns the phone numbers of this Notify object

    def get_phones(self):
        return self._phones

    # returns the deptnum + section name of this Notify object

    def get_name(self):
        return f"{self._deptnum} {self._sectionname}"

    # sends a formatted email

    def send_emails_html(self):
        send_email_args = []
        for i in range(len(self._emails)):
            try:
                if self._has_reserved_seats:
                    if self.db.get_user_auto_resub(
                        self._netids[i], classid=self._classid
                    ):
                        # yes auto-resub | yes reserved seats
                        template_id = "d-b32c7a8c99f2491899322ced801b216b"
                    else:
                        # no auto-resub | yes reserved seats
                        template_id = "d-632e8760499b40d680742b9acdb8d129"
                else:
                    if self.db.get_user_auto_resub(
                        self._netids[i], classid=self._classid
                    ):
                        # yes auto-resub | no reserved seats
                        template_id = "d-c04bc32123ea45ec80889919cc5c377e"
                    else:
                        # no auto-resub | no reserved seats
                        template_id = "d-2607514c41ef48cdb649bad3d4f0c660"

                data = {
                    "personalizations": [
                        {
                            "to": [{"email": self._emails[i]}],
                            "dynamic_template_data": {
                                "netid": self._netids[i],
                                "sectionname": self._sectionname,
                                "coursename": self._coursename,
                                "deptnum": self._deptnum,
                                "tigerhub_url": "https://phubprod.princeton.edu/psp/phubprod/?cmd=start",
                                "dashboard_url": f"{TS_DOMAIN}/dashboard?&skip&email",
                                "course_url": f"{TS_DOMAIN}/course?query=&courseid={self._courseid}&skip&email",
                                "n_open_spots": self.n_new_slots,
                                "n_other_students": len(self._netids) - 1,
                            },
                        }
                    ],
                    "from": {"email": TS_EMAIL, "name": "TigerSnatch"},
                    "template_id": template_id,
                }

                send_email_args.append([data])

                self.db._add_system_log(
                    "notif_email",
                    {
                        "netid": self._netids[i],
                        "sectionname": self._sectionname,
                        "coursename": self._coursename,
                        "deptnum": self._deptnum,
                        "n_other_students": len(self._netids) - 1,
                        "n_open_spots": self.n_new_slots,
                        "reserved_seats": self._has_reserved_seats,
                        "email": self._emails[i],
                    },
                    netid=self._netids[i],
                    print_=False,
                )
            except Exception as e:
                print(e, file=stderr)

        return send_email_args

    # sends an SMS

    def send_sms(self):
        reserved = "This course has reserved seats, so enrollment may not be possible. "
        msg_unsubbed = f"{self._sectionname} in {self._deptnum} has {self.n_new_slots} open spot(s)! {len(self._netids) - 1} other student(s) notified. {reserved if self._has_reserved_seats else ''}Resubscribe: {TS_DOMAIN}/course?courseid={self._courseid}&skip&sms"
        msg_resubbed = f"{self._sectionname} in {self._deptnum} has {self.n_new_slots} open spot(s)! {len(self._netids) - 1} other student(s) notified. {reserved if self._has_reserved_seats else ''}Unsubscribe: {TS_DOMAIN}/dashboard?&skip&sms"
        send_text_args = []
        for i, phone in enumerate(self._phones):
            try:
                is_auto_resub = self.db.get_user_auto_resub(
                    self._netids[i], classid=self._classid, print_max_resub_msg=True
                )
                if phone != "":
                    send_text_args.append(
                        [
                            phone,
                            msg_resubbed if is_auto_resub else msg_unsubbed,
                        ]
                    )
                if not is_auto_resub:
                    self.db.remove_from_waitlist(self._netids[i], self._classid)

                if phone != "":
                    self.db._add_system_log(
                        "notif_text",
                        {
                            "netid": self._netids[i],
                            "sectionname": self._sectionname,
                            "coursename": self._coursename,
                            "deptnum": self._deptnum,
                            "n_other_students": len(self._netids) - 1,
                            "n_open_spots": self.n_new_slots,
                            "reserved_seats": self._has_reserved_seats,
                            "phone": phone,
                        },
                        netid=self._netids[i],
                        print_=False,
                    )
            except Exception as e:
                print(e, file=stderr)

        return send_text_args

    def __str__(self):
        ret = f"\n{self._deptnum} {self._sectionname} ({self._classid}): {self.n_new_slots} open spot(s)\n"
        ret += f"   Notifying {', '.join(self._netids)}\n"
        ret += f"   Emailing {', '.join(self._emails)}\n"
        phones = list(filter(None, self._phones))
        if len(phones) == 0:
            return ret[:-1]
        ret += f"   Texting {', '.join(phones)}"
        return ret


def send_email(data):
    try:
        SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)
        return True
    except Exception as e:
        print(e, file=stderr)
        return False


def send_text(phone, msg):
    try:
        Client(TWILIO_SID, TWILIO_TOKEN).api.account.messages.create(
            to=f"+1{phone}",
            from_=TWILIO_PHONE,
            body=msg,
        )
        return True
    except Exception as e:
        print(e, file=stderr)
        return False


if __name__ == "__main__":
    from database import Database

    db = Database()
    n = Notify("42149", 1, db)
    # n.send_emails_html()

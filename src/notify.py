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
)


class Notify:
    # initializes Notify, fetching all information about a given classid
    # to format and send an email to the first student on the waitlist
    # for that classid

    def __init__(self, classid, n_new_slots, db):
        self._classid = classid
        self.db = db
        try:
            (
                self._deptnum,
                self._title,
                self._sectionname,
                self._courseid,
            ) = db.classid_to_classinfo(classid)
            self._coursename = f"{self._deptnum}: {self._title}"
            self._netids = db.get_class_waitlist(classid)["waitlist"]

            user_log = (
                f"{n_new_slots} spots available in {self._deptnum} {self._sectionname}"
            )
            self._emails = []
            self._phones = []
            for netid in self._netids:
                self._emails.append(db.get_user(netid, "email"))
                self._phones.append(db.get_user(netid, "phone"))
                db.update_user_waitlist_log(netid, user_log)
        except:
            raise Exception(
                f"unable to get notification data for subscriptions of class {classid}"
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
        next_step_unsubbed = f"""<p>You've been <b>automatically unsubscribed</b> from this section. If you didn't get the spot, you may re-subscribe here: <a href="{TS_DOMAIN}/course?query=&courseid={self._courseid}&skip">TigerSnatch | {self._deptnum}</a>.</p>"""

        next_step_resubbed = f"""<p>To stop receiving notifications for this section, unsubscribe here: <a href="{TS_DOMAIN}/dashboard?&skip">TigerSnatch | Dashboard</a>.</p>"""

        msg = f"""\
        <html>
        <head></head>
        <body style='font-size:1.3em'>
            <p>Greetings $$netid$$,</p>
            <p>Your subscribed section <b>{self._sectionname}</b> in <b>{self._coursename}</b> has one or more spots open! Note that some courses reserve spots or are closed, so enrollment may not be possible.</p>
            <p>Head over to <a href="https://phubprod.princeton.edu/psp/phubprod/?cmd=start">TigerHub</a> to Snatch your spot!</p>
            $$next_step$$
            <p>Best,<br>TigerSnatch Team <3</p>
        </body>
        </html>"""

        try:
            data = {
                "personalizations": [
                    {
                        "to": [{"email": self._emails[i]}],
                        "subject": f"TigerSnatch: a spot opened in {self._deptnum} {self._sectionname}",
                        "substitutions": {
                            "$$netid$$": self._netids[i],
                            "$$next_step$$": (
                                next_step_resubbed
                                if self.db.get_user_auto_resub(self._netids[i])
                                else next_step_unsubbed
                            ),
                        },
                    }
                    for i in range(len(self._emails))
                ],
                "from": {"email": TS_EMAIL},
                "content": [{"type": "text/html", "value": (msg)}],
            }

            SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)
            return True
        except Exception as e:
            print(e, file=stderr)
            return False

    # sends an SMS

    def send_sms(self):
        msg_unsubbed = f"{self._sectionname} in {self._deptnum} has open spots! You've been unsubscribed from this section. Resubscribe here: {TS_DOMAIN}/course?courseid={self._courseid}&skip"
        msg_resubbed = f"{self._sectionname} in {self._deptnum} has open spots! To stop receiving notifications for this section, unsubscribe here: {TS_DOMAIN}/dashboard?&skip"
        try:
            for i, phone in enumerate(self._phones):
                is_auto_resub = self.db.get_user_auto_resub(self._netids[i])
                if phone != "":
                    Client(TWILIO_SID, TWILIO_TOKEN).api.account.messages.create(
                        to=f"+1{phone}",
                        from_=TWILIO_PHONE,
                        body=(msg_resubbed if is_auto_resub else msg_unsubbed),
                    )
                if not is_auto_resub:
                    self.db.remove_from_waitlist(self._netids[i], self._classid)
            return True
        except Exception as e:
            print(e, file=stderr)
            return False

    def __str__(self):
        ret = "\nNotifications:\n"
        ret += f"\tNetIDs:\t\t{self._netids}\n"
        ret += f"\tEmails:\t\t{self._emails}\n"
        ret += f"\tPhones:\t\t{self._phones}\n"
        ret += f"\tCourse:\t\t{self._coursename}\n"
        ret += f"\tSection:\t{self._sectionname}\n"
        ret += f"\tClassID:\t{self._classid}"
        return ret


if __name__ == "__main__":
    n = Notify("43474")
    n.send_email_html()

# ----------------------------------------------------------------------
# notify.py
# Sends users emails or text messages about enrollment updates
# ----------------------------------------------------------------------

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sys import stderr
from config import SENDGRID_API_KEY, TS_EMAIL


class Notify:
    # initializes Notify, fetching all information about a given classid
    # to format and send an email to the first student on the waitlist
    # for that classid

    def __init__(self, classid, n_new_slots, db):
        self._classid = classid
        try:
            self._deptnum, self._title, self._sectionname = db.classid_to_classinfo(
                classid
            )
            self._coursename = f"{self._deptnum}: {self._title}"
            self._netids = db.get_class_waitlist(classid)["waitlist"]

            user_log = (
                f"{n_new_slots} spots available in {self._deptnum} {self._sectionname}"
            )
            self._emails = []
            for netid in self._netids:
                self._emails.append(db.get_user(netid, "email"))
                db.update_user_waitlist_log(netid, user_log)
        except:
            raise Exception(
                f"unable to get notification data for subscriptions of class {classid}"
            )

    # returns the netIDs of this Notify object

    def get_netids(self):
        return self._netids

    # sends a formatted email

    def send_emails_html(self):
        msg = f"""\
        <html>
        <head></head>
        <body style='font-size:1.3em'>
            <p>Greetings $$netid$$,</p>
            <p>Your subscribed section <b>{self._sectionname}</b> in <b>{self._coursename}</b> has one or more spots open!</p>
            <p>Head over to <a href="https://phubprod.princeton.edu/psp/phubprod/?cmd=start">TigerHub</a> to Snatch your spot!</p>
            <p>You'll continue to receive notifications for this section every 2 minutes if spots are still available. To unsubscribe from notifications for this section, visit your <a href="https://snatch.tigerapps.org/dashboard">TigerSnatch Dashboard</a>.</p>
            <p>Best,<br>TigerSnatch Team <3</p>
        </body>
        </html>"""

        data = {
            "personalizations": [
                {
                    "to": [{"email": self._emails[i]}],
                    "subject": f"TigerSnatch: a spot opened in {self._deptnum} {self._sectionname}",
                    "substitutions": {"$$netid$$": self._netids[i]},
                }
                for i in range(len(self._emails))
            ],
            "from": {"email": TS_EMAIL},
            "content": [{"type": "text/html", "value": msg}],
        }

        try:
            SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)
            return True
        except Exception as e:
            print(e, file=stderr)
            return False

    def __str__(self):
        ret = "Notify:\n"
        ret += f"\tNetIDs:\t\t{self._netids}\n"
        ret += f"\tEmails:\t\t{self._emails}\n"
        ret += f"\tCourse:\t\t{self._coursename}\n"
        ret += f"\tSection:\t{self._sectionname}\n"
        ret += f"\tClassID:\t{self._classid}"
        return ret


if __name__ == "__main__":
    n = Notify("43474")
    n.send_email_html()

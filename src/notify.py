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

    def __init__(self, classid, i, n_new_slots, db):
        self._classid = classid
        try:
            (
                self._deptnum,
                self._title,
                self._sectionname,
                self._courseid,
            ) = db.classid_to_classinfo(classid)
            self._coursename = f"{self._deptnum}: {self._title}"
            self._netid = db.get_class_waitlist(classid)["waitlist"][i]
        except:
            raise Exception(
                f"waitlist element {i} for class {classid} does not exist; user probably removed themself"
            )
        self._email = db.get_user(self._netid, "email")

        user_log = (
            f"{n_new_slots} spots available in {self._deptnum} {self._sectionname}"
        )
        db.update_user_waitlist_log(self._netid, user_log)

    # returns the netid of this Notify object

    def get_netid(self):
        return self._netid

    # sends a formatted email

    def send_email_html(self):
        msg = f"""\
        <html>
        <head></head>
        <body style='font-size:1.3em'>
            <p>Dear {self._netid},</p>
            <p>Your subscribed section <b>{self._sectionname}</b> in <b>{self._coursename}</b> has one or more spots open!</p>
            <p>Head over to <a href="https://phubprod.princeton.edu/psp/phubprod/?cmd=start">TigerHub</a> to Snatch your spot!</p>
            <p>You have been <b>automatically unsubscribed</b> from this section. If you didn't get the spot, you may re-subscribe here: <a href="https://snatch.tigerapps.org/course?query=&courseid={self._courseid}&skip">TigerSnatch | {self._deptnum}</a>.</p>
            <p>Best,<br>TigerSnatch Team <3</p>
        </body>
        </html>
        """

        message = Mail(
            from_email=TS_EMAIL,
            to_emails=self._email,
            subject=f"TigerSnatch: a spot opened in {self._deptnum} {self._sectionname}",
            html_content=msg,
        )

        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
            return True
        except Exception as e:
            print(e, file=stderr)
            return False

    def __str__(self):
        ret = "Notify:\n"
        ret += f"\tNetID:\t\t{self._netid}\n"
        ret += f"\tEmail:\t\t{self._email}\n"
        ret += f"\tCourse:\t\t{self._coursename}\n"
        ret += f"\tSection:\t{self._sectionname}\n"
        ret += f"\tClassID:\t{self._classid}"
        return ret


if __name__ == "__main__":
    n = Notify("43474")
    n.send_email_html()

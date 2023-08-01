# ----------------------------------------------------------------------
# _email_all_users.py
# Note: It is best to run this script *on your local computer*. You must
# make sure that all environment variables are already set. See Heroku
# Config Vars to get these variables.
#
# Script to email all TigerSnatch users. This uses a SendGrid dynamic
# template (edit on SendGrid --> Dynamic Templates). To use this script:
#
# 1. Create a file named MESSAGE (no extension) in the same directory as
#    this script and type the body of your email (can include new-lines
#    and HTML tags).
# 2. Create a file named SUBJECT (no extension) in the same directory as
#    this script and type the subject of your email (must be on a single
#    line, without any HTML tags).
# 3. Execute the script. Always test your email by first sending it to
#    admins with --test, before sending it to everyone with --all!
#
#    Specify one of the following flags:
#       --test <email1> <email2> ... : Send to 1+ specific emails.
# 	    --all: Send to ALL user emails.
#
#    Example: python _email_all_users.py --test x@x.com y@y.com
#    Example: python _email_all_users.py --all
# ----------------------------------------------------------------------

from sys import argv, exit

from sendgrid import SendGridAPIClient

from config import SENDGRID_API_KEY, TS_EMAIL
from database import Database
from log_utils import *

CLASS_YEARS = ["2024", "2025", "2026", None]

if __name__ == "__main__":

    def process_args():
        if len(argv) < 2 or (argv[1] != "--test" and argv[1] != "--all"):
            print("specify one of the following flags:")
            print("\t--test <email1> <email2> ...: send to 1+ specific emails")
            print("\t--all: send to ALL user emails")
            exit(2)
        return argv[1] == "--all"

    DIR = "/".join(__file__.split("/")[:-1])
    SUBJECT_FILEPATH = f"{DIR}/SUBJECT"
    MESSAGE_FILEPATH = f"{DIR}/MESSAGE"

    try:
        with open(SUBJECT_FILEPATH, "r") as subj, open(MESSAGE_FILEPATH, "r") as msg:
            SUBJECT = subj.read()
            MESSAGE = msg.read()
    except FileNotFoundError:
        log_error(
            "Make sure that files SUBJECT and MESSAGE (no extensions) exist in /src!"
        )
        exit(1)

    send_to_all_users = process_args()
    send_to_custom = not send_to_all_users

    if send_to_custom and len(argv) < 3:
        log_error(
            "--test requires a space-separated list of 1+ email addresses! Example: $ python _email_all_users.py --test x@x.com y@y.com"
        )
        exit(1)

    if send_to_all_users:
        emails = Database()._get_all_emails_csv(years=CLASS_YEARS).split(",")
    else:
        emails = argv[2:]

    # SendGrid will error only if there is no '@' in an address - this step is to prevent errors when sending
    # so that we don't end up with a partial set of emails processed
    emails = [email for email in emails if "@" in email]
    SUBJECT = SUBJECT.strip()
    MESSAGE = MESSAGE.strip().replace("\n", "<br>")

    if send_to_custom:
        SUBJECT = f"[Test] {SUBJECT}"
        MESSAGE = f"[This is a test email]<br>{MESSAGE}"

    print("---------------")
    print("SUBJECT:", SUBJECT)
    print()
    print("MESSAGE:")
    print(MESSAGE.replace("<br>", "\n"))
    print("---------------")
    print()
    if (
        input(
            f"Send the above email to {'ALL users' if send_to_all_users else argv[2:]} ({len(emails)} in total)? (y/n) "
        )
        != "y"
    ):
        print("Exiting...")
        exit(0)

    print("Sending...")

    n = len(emails)
    for i, email in enumerate(emails):
        print(f"({i+1}/{n}) Sending to {email}", end="...")
        data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {"subject": SUBJECT, "message": MESSAGE},
                }
            ],
            "from": {"email": TS_EMAIL, "name": "TigerSnatch"},
            "template_id": "d-e688d68d1bac424382aa8535026d6f36",
        }

        try:
            SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)
            print("success")
        except Exception as e:
            print("failed with exception:")
            print(e)

    log_info(
        f"Sent email to {'ALL users' if send_to_all_users else argv[2:]} ({len(emails)} in total)."
    )


def notify_admins_of_schedule_change(schedule):
    schedule_str = ""
    for start, end in schedule:
        schedule_str += f"{start.strftime('%Y-%m-%d @ %H:%M:%S')} ---> {end.strftime('%Y-%m-%d @ %H:%M:%S')}<br>"

    academic_cal_url = "https://registrar.princeton.edu/academic-calendar-and-deadlines"
    manual_schedule_spreadsheet = "https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/edit"
    emails = [
        "ntyp@alumni.princeton.edu",
        "taylory@princeton.edu",
        "jungp@princeton.edu",
        "youngseo@princeton.edu",
        "akelch@princeton.edu",
    ]

    SUBJECT = "TigerSnatch Schedule Update"
    MESSAGE = f"""<p>TigerSnatch notifications schedule has been auto-updated to:</p>

<p>{schedule_str}</p>

<p>Verify that this is correct by checking against <a href="{academic_cal_url}">{academic_cal_url}</a>.</p>

<p>If this is incorrect, immediately set the Config Var AUTO_GENERATE_NOTIF_SCHEDULE to "false" in Heroku! This will prevent bad notifications from getting sent. Try to find the bug later so that you can set the Config Var back to "true".</p>

<p>Then, manually update the schedule at <a href="{manual_schedule_spreadsheet}">{manual_schedule_spreadsheet}</a>. Verify that the new schedule has been registered by checking the Admin panel after ~1 minute.</p>
"""

    for email in emails:
        data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                }
            ],
            "from": {"email": TS_EMAIL, "name": "TigerSnatch"},
            "subject": SUBJECT,
            "content": [{"type": "text/html", "value": MESSAGE}],
        }

        try:
            SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)
        except Exception as e:
            print(e)

    log_info(f"Sent schedule update email to {emails}.")

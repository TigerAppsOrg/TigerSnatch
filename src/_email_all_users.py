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

from database import Database
from sys import exit, argv
from sendgrid import SendGridAPIClient
from config import SENDGRID_API_KEY, TS_EMAIL

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
        print("make sure that files SUBJECT and MESSAGE (no extensions) exist in /src!")
        exit(1)

    send_to_all_users = process_args()
    send_to_custom = not send_to_all_users

    if send_to_custom and len(argv) < 3:
        print("--test requires a space-separated list of 1+ email addresses!")
        print("Example: $ python _email_all_users.py --test x@x.com y@y.com")
        exit(1)

    if send_to_all_users:
        emails = Database()._get_all_emails_csv().split(",")
    else:
        emails = argv[2:]

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

    print("Sending... ", end="")

    data = {
        "personalizations": [
            {
                "to": [{"email": email}],
                "dynamic_template_data": {"subject": SUBJECT, "message": MESSAGE},
            }
            for email in emails
        ],
        "from": {"email": TS_EMAIL, "name": "TigerSnatch"},
        "template_id": "d-e688d68d1bac424382aa8535026d6f36",
    }

    SendGridAPIClient(SENDGRID_API_KEY).client.mail.send.post(request_body=data)

    print(f"{len(emails)} emails sent!")

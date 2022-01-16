# ----------------------------------------------------------------------
# _email_all_users.py
# Note: It is best to run this script *on your local computer*. You must
# make sure that all environment variables are already set. See Heroku
# Config Vars to get these variables.
#
# Note: Please don't commit your custom subject and message!
#
# Script to email all TigerSnatch users. This uses a SendGrid dynamic
# template (edit on SendGrid --> Dynamic Templates). To use this script,
# set the variable MESSAGE (can include new-line characters and HTML tags)
# to the body of the email you'd like to send, and SUBJECT to the subject.
# Then, execute the script. Always test your email by sending it to admins
# with --test, before sending it to everyone with --all!
#
# Specify one of the following flags:
#   --test: Send email to only admins
# 	--all: Send email to all users
#
# Example: python _email_all_users.py --test
# ----------------------------------------------------------------------

# set the email subject exactly as you want it displayed
SUBJECT = "Your subject goes here!"

# set the email message exactly as you want it displayed (leave the leading
# and trailing new-lines). you may use HTML tags and new-line characters!
# note: the email template already has "Greetings" at the beginning
# and "~ TigerSnatch Team" at the end
MESSAGE = """
Your <b><a href="https://tigersnatch.com">message</a></b> goes here!

You can use multiple lines if necessary.
"""

# ----------------------------------------------------------------------

from database import Database
from sys import exit, argv
from sendgrid import SendGridAPIClient
from config import SENDGRID_API_KEY, TS_EMAIL

if __name__ == "__main__":

    def process_args():
        if len(argv) != 2 or (argv[1] != "--test" and argv[1] != "--all"):
            print("specify one of the following flags:")
            print("\t--test: send email to only admins")
            print("\t--all: send email to ALL users")
            exit(2)
        return argv[1] == "--all"

    send_to_all_users = process_args()
    send_to_admins = not send_to_all_users
    db = Database()
    emails = (
        db._get_all_emails_csv() if send_to_all_users else db._get_admin_emails_csv()
    ).split(",")

    SUBJECT = SUBJECT.strip()
    MESSAGE = MESSAGE.strip().replace("\n", "<br>")

    if send_to_admins:
        SUBJECT = f"[Test] {SUBJECT}"
        MESSAGE = f"[This is a test email sent to TigerSnatch admins only]<br>{MESSAGE}"

    print("---------------")
    print("SUBJECT:", SUBJECT)
    print()
    print("MESSAGE:")
    print(MESSAGE.replace("<br>", "\n"))
    print("---------------")
    print()
    if (
        input(
            f"Send the above email to {'ALL users' if send_to_all_users else 'admins only'} ({len(emails)} in total)? (y/n) "
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

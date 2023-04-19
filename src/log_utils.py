from datetime import datetime
from sys import stdout


class _Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def _log(message, prefix, color):
    print(
        f'{color}[{datetime.now().strftime("%-I:%M:%S %p ET")}][{prefix}]\t{message}{_Colors.ENDC}'
    )
    stdout.flush()


def log_notifs(message):
    _log(message, "NOTIFS", _Colors.OKGREEN)


def log_error(message):
    _log(message, "ERROR", _Colors.FAIL)


def log_cron(message):
    _log(message, "CRON", _Colors.OKBLUE)


def log_system(message):
    _log(message, "SYSTEM", _Colors.OKCYAN)


if __name__ == "__main__":
    log_notifs("Notifs Notification")
    log_error("Error Notification")
    log_cron("Cron Notification")
    log_system("System Notification")

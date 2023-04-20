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


def _log(message: str, prefix, color):
    message = f"{message.split(' ')[0].capitalize()} {' '.join(message.split(' ')[1:])}"
    print()
    print(
        f'{_Colors.BOLD}{color}[{datetime.now().strftime("%-I:%M:%S %p ET")}] [{prefix}]{_Colors.ENDC} {message}'
    )
    print()
    stdout.flush()


def log_notifs(message):
    _log(message, "NOTIFS", _Colors.OKGREEN)


def log_error(message):
    _log(message, "ERROR", _Colors.FAIL)


def log_cron(message):
    _log(message, "CRON", _Colors.OKBLUE)


def log_system(message):
    _log(message, "SYSTEM", _Colors.OKCYAN)


def log_info(message):
    _log(message, "INFO", _Colors.OKCYAN)


def log_warning(message):
    _log(message, "WARNING", _Colors.WARNING)


if __name__ == "__main__":
    log_notifs("notifs notification")
    log_error("error Notification")
    log_cron("cron notification")
    log_system("system Notification")

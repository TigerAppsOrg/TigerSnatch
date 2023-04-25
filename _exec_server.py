# ----------------------------------------------------------------------
# _exec_server.py
# Manages Flask server execution with a given port. To alter the host
# address, change TS_HOST in config.py.
#
# Example: python _exec_server.py 12345
# ----------------------------------------------------------------------

from sys import path

path.append("src")  # noqa

from sys import argv, stderr, exit
from app import app, socketio
from config import PROD, TS_HOST


def main(argv):
    if len(argv) != 2:
        print("Incorrect number of arguments - specify port only", file=stderr)
        exit(1)

    try:
        port = int(argv[1])
    except Exception:
        print("Port must be an integer", file=stderr)
        exit(1)

    socketio.run(app, host=TS_HOST, port=port, debug=not PROD)


if __name__ == "__main__":
    main(argv)

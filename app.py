# ----------------------------------------------------------------------
# api.py
# Defines endpoints for TigerSnatch app.
# ----------------------------------------------------------------------

from sys import path

path.append("src")  # noqa

import logging
import traceback
from os import listdir
from os.path import isfile, join
from urllib.parse import quote_plus, unquote_plus

from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from app_helper import (
    do_search,
    get_notifs_status_data,
    get_release_notes,
    is_admin,
    log_page_visit,
    pull_course,
    update_user_settings,
)
from CASClient import CASClient
from config import (
    APP_SECRET_KEY,
    AUTO_GENERATE_NOTIF_SCHEDULE,
    MAX_AUTO_RESUB_NOTIFS,
    NOTIFS_INTERVAL_SECS,
)
from database import Database
from waitlist import Waitlist

log = logging.getLogger("werkzeug")
# log.disabled = True
log.setLevel(logging.ERROR)

app = Flask(__name__, template_folder="./views")
app.secret_key = APP_SECRET_KEY

_cas = CASClient()
_db = Database()


@app.errorhandler(Exception)
def handle_exception(e):
    if "404 Not Found" in str(e):
        return redirect(url_for("dashboard"))

    # assume that non-404 errors are generated by visiting an old/invalid courseID
    _db._add_system_log("error", {"message": request.path + ": " + str(e)})
    # print stack trace
    traceback.print_exc()
    return render_template("error.html")


# private method that redirects to landing page
# if user is not logged in with CAS
# or if user is logged in with CAS, but doesn't have entry in DB
def redirect_landing():
    return not _cas.is_logged_in() or not _db.is_user_created(_cas.authenticate())


# ----------------------------------------------------------------------
# ACCESSIBLE BY ALL, VIA URL
# ----------------------------------------------------------------------


@app.route("/", methods=["GET"])
def index():
    ref = request.args.get("ref")
    if not redirect_landing():
        return redirect(url_for("dashboard", ref=ref))

    log_page_visit("Landing", "N/A")
    _db.increment_site_ref(ref)

    notifs_status_data = get_notifs_status_data()

    html = render_template(
        "landing.html",
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        term_name=notifs_status_data["term_name"],
    )
    return make_response(html)


@app.route("/login", methods=["GET"])
def login():
    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blocked user {netid} attempted to access the app")
        return make_response(render_template("blocklisted.html"))

    _db._add_system_log("user", {"message": f"user {netid} logged in"}, netid=netid)

    if not _db.is_user_created(netid):
        _db.create_user(netid)
        return redirect(url_for("tutorial"))

    return redirect(url_for("dashboard"))


@app.route("/tutorial", methods=["GET"])
def tutorial():
    notifs_status_data = get_notifs_status_data()

    if redirect_landing():
        html = render_template(
            "tutorial.html",
            loggedin=False,
            notifs_online=notifs_status_data["notifs_online"],
            next_notifs=notifs_status_data["next_notifs"],
            term_name=notifs_status_data["term_name"],
        )
        return make_response(html)

    netid = _cas.authenticate()

    log_page_visit("Tutorial", netid)

    html = render_template(
        "tutorial.html",
        user_is_admin=is_admin(netid, _db),
        loggedin=True,
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        term_name=notifs_status_data["term_name"],
    )
    return make_response(html)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    ref = request.args.get("ref")
    if redirect_landing():
        return redirect(f"/?ref={ref}" if ref else "/")

    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blocked user {netid} attempted to access the app")
        return make_response(render_template("blocklisted.html"))

    log_page_visit("Dashboard", netid)
    _db.increment_site_ref(ref)

    data = _db.get_dashboard_data(netid)
    email = _db.get_user(netid, "email")
    phone = _db.get_user(netid, "phone")
    auto_resub = _db.get_user_auto_resub(netid)

    do_redirect = update_user_settings(netid, request)
    if do_redirect:
        return redirect(url_for("dashboard"))

    query = request.args.get("query")
    if query is None:
        query = ""
    if len(query) > 100:
        query = query[:100]
    search_res, new_query = do_search(query, _db)

    notifs_status_data = get_notifs_status_data()

    html = render_template(
        "base.html",
        is_dashboard=True,
        is_admin=False,
        netid=netid,
        user_is_admin=is_admin(netid, _db),
        search_res=search_res,
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        username=netid,
        data=data,
        email=email,
        phone=phone,
        auto_resub=auto_resub,
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        term_name=notifs_status_data["term_name"],
        max_auto_resub_notifs=MAX_AUTO_RESUB_NOTIFS,
        using_auto_notifs_scheduler=AUTO_GENERATE_NOTIF_SCHEDULE,
    )

    return make_response(html)


@app.route("/update_auto_resub/<auto_resub>", methods=["POST"])
def update_auto_resub(auto_resub):
    netid = _cas.authenticate()
    is_success = _db.update_user_auto_resub(netid, auto_resub.lower() == "true")
    return jsonify({"isSuccess": is_success})


@app.route("/about", methods=["GET"])
def about():
    release_notes_success, release_notes = get_release_notes()
    notifs_status_data = get_notifs_status_data()

    if redirect_landing():
        html = render_template(
            "about.html",
            loggedin=False,
            notifs_online=notifs_status_data["notifs_online"],
            next_notifs=notifs_status_data["next_notifs"],
            term_name=notifs_status_data["term_name"],
            release_notes_success=release_notes_success,
            release_notes=release_notes,
        )
        return make_response(html)

    netid = _cas.authenticate()

    log_page_visit("About", netid)

    html = render_template(
        "about.html",
        user_is_admin=is_admin(netid, _db),
        loggedin=True,
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        term_name=notifs_status_data["term_name"],
        release_notes_success=release_notes_success,
        release_notes=release_notes,
    )
    return make_response(html)


@app.route("/activity", methods=["GET"])
def activity():
    stats = _db.get_stats()
    notifs_status_data = get_notifs_status_data()

    if redirect_landing():
        html = render_template(
            "activity.html",
            loggedin=False,
            notifs_online=notifs_status_data["notifs_online"],
            next_notifs=notifs_status_data["next_notifs"],
            term_name=notifs_status_data["term_name"],
            stats=stats,
        )
        return make_response(html)

    netid = _cas.authenticate()

    log_page_visit("Activity", netid)

    waitlist_logs = _db.get_user_waitlist_log(netid)

    html = render_template(
        "activity.html",
        user_is_admin=is_admin(_cas.authenticate(), _db),
        loggedin=True,
        waitlist_logs=waitlist_logs,
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        term_name=notifs_status_data["term_name"],
        stats=stats,
    )

    return make_response(html)


@app.route("/course", methods=["GET"])
def get_course():
    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blocked user {netid} attempted to access the app")
        return make_response(render_template("blocklisted.html"))

    if not _db.is_user_created(netid):
        _db.create_user(netid)
        return redirect(url_for("tutorial"))

    courseid = request.args.get("courseid")
    query = request.args.get("query")
    ref = request.args.get("ref")

    if courseid is None:
        return redirect(url_for("dashboard"))

    _db.increment_site_ref(ref)

    if query is None:
        query = ""
    if len(query) > 100:
        query = query[:100]
    search_res, new_query = do_search(query, _db)

    course_details, classes_list = pull_course(courseid, _db)
    curr_waitlists = _db.get_user(netid, "waitlists")
    num_full = sum(class_data["isFull"] for class_data in classes_list)
    term_code, term_name = _db.get_current_term_code()
    section_names = _db.get_section_names_in_course(courseid)

    log_page_visit(f"Course {course_details['displayname']} ({courseid})", netid)

    notifs_status_data = get_notifs_status_data()

    html = render_template(
        "base.html",
        is_dashboard=False,
        is_admin=False,
        user_is_admin=is_admin(netid, _db),
        netid=netid,
        courseid=courseid,
        course_details=course_details,
        classes_list=classes_list,
        curr_waitlists=curr_waitlists,
        search_res=search_res,
        num_full=num_full,
        section_names=section_names,
        term_code=term_code,
        term_name=term_name,
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        is_course_disabled=_db.is_course_disabled(courseid),
        has_reserved_seats=_db.does_course_have_reserved_seats(courseid),
        is_top_n=_db.is_course_top_n_subscribed(course_details["displayname"]),
        using_auto_notifs_scheduler=AUTO_GENERATE_NOTIF_SCHEDULE,
    )

    return make_response(html)


@app.route("/logout", methods=["GET"])
def logout():
    _cas.logout()


# ----------------------------------------------------------------------
# ACCESSIBLE BY ALL, NOT VIA URL
# ----------------------------------------------------------------------


@app.route("/searchresults_placeholder", methods=["POST"])
def get_search_results_placeholder():
    html = render_template(
        "search/search_results.html",
        last_query=quote_plus(""),
        last_query_unquoted=unquote_plus(""),
        search_res=None,
    )
    return make_response(html)


@app.route("/searchresults", methods=["POST"])
@app.route("/searchresults/<query>", methods=["POST"])
def get_search_results(query=""):
    res, new_query = do_search(query, _db)
    html = render_template(
        "search/search_results.html",
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        search_res=res,
    )
    return make_response(html)


@app.route("/courseinfo/<courseid>", methods=["POST"])
def get_course_info(courseid):
    netid = _cas.authenticate()
    if not _db.is_user_created(netid):
        _db.create_user(netid)
        return redirect(url_for("tutorial"))

    course_details, classes_list = pull_course(courseid, _db)
    curr_waitlists = _db.get_user(netid, "waitlists")
    section_names = _db.get_section_names_in_course(courseid)

    num_full = sum(class_data["isFull"] for class_data in classes_list)
    term_code, term_name = _db.get_current_term_code()

    if courseid is not None:
        log_page_visit(f"Course {course_details['displayname']} ({courseid})", netid)

    notifs_status_data = get_notifs_status_data()

    html = render_template(
        "course/course.html",
        netid=netid,
        user_is_admin=is_admin(netid, _db),
        courseid=courseid,
        course_details=course_details,
        classes_list=classes_list,
        num_full=num_full,
        term_code=term_code,
        term_name=term_name,
        curr_waitlists=curr_waitlists,
        section_names=section_names,
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        is_course_disabled=_db.is_course_disabled(courseid),
        has_reserved_seats=_db.does_course_have_reserved_seats(courseid),
        is_top_n=_db.is_course_top_n_subscribed(course_details["displayname"]),
        using_auto_notifs_scheduler=AUTO_GENERATE_NOTIF_SCHEDULE,
    )
    return make_response(html)


@app.route("/add_to_waitlist/<classid>", methods=["POST"])
def add_to_waitlist(classid):
    netid = _cas.authenticate()
    waitlist = Waitlist(netid)
    return jsonify({"isSuccess": waitlist.add_to_waitlist(classid)})


@app.route("/remove_from_waitlist/<classid>", methods=["POST"])
def remove_from_waitlist(classid):
    netid = _cas.authenticate()
    waitlist = Waitlist(netid)
    return jsonify({"isSuccess": waitlist.remove_from_waitlist(classid)})


"""
Retired Trades method

@app.route(
    "/contact_trade/<course_name>/<match_netid>/<section_name>", methods=["POST"]
)
def contact_trade(course_name, match_netid, section_name):
    netid = _cas.authenticate()
    log_str = f"You contacted {match_netid} to swap into {course_name} {section_name}"
    log_str_alt = f"{netid} contacted you about swapping into your section {course_name} {section_name}"

    # protects against HTML injection
    if "<" in log_str or ">" in log_str or "script" in log_str:
        print("HTML code detected in", log_str, file=stderr)
        return jsonify({"isSuccess": False})

    try:
        _db.update_user_trade_log(netid, log_str)
        _db.update_user_trade_log(match_netid, log_str_alt)
        _db._add_system_log(
            "trade",
            {
                "message": f"{netid} contacted {match_netid} to swap into {course_name} {section_name}"
            },
            netid=netid,
        )
    except:
        return jsonify({"isSuccess": False})
    return jsonify({"isSuccess": True})
"""

# ----------------------------------------------------------------------
# ACCESSIBLE BY ADMIN ONLY, VIA URL
# ----------------------------------------------------------------------


@app.route("/admin", methods=["GET"])
def admin():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for(""))
    except:
        return redirect(url_for(""))

    _db._add_system_log(
        "admin", {"message": f"admin {netid} viewed admin panel"}, netid=netid
    )

    admin_logs = _db.get_admin_logs()
    try:
        admin_logs = admin_logs["logs"]
    except:
        admin_logs = None
    query = request.args.get("query-netid")

    if query is None:
        query = ""
    if len(query) > 100:
        query = query[:100]
    search_res, new_query, total_users = _db.search_for_user(query)

    term_code, term_name = _db.get_current_term_code()
    notifs_status_data = get_notifs_status_data()

    html = render_template(
        "base.html",
        is_dashboard=False,
        is_admin=True,
        user_is_admin=True,
        search_res=search_res[:20],
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        username=netid,
        admin_logs=admin_logs,
        blacklist=_db.get_blacklist(),
        notifs_online=notifs_status_data["notifs_online"],
        next_notifs=notifs_status_data["next_notifs"],
        current_term_code=term_code,
        term_name=term_name,
        total_users=total_users,
    )

    return make_response(html)


# ----------------------------------------------------------------------
# ACCESSIBLE BY ADMIN ONLY, NOT VIA URL
# ----------------------------------------------------------------------


@app.route("/disable_course/<courseid>", methods=["POST"])
def disable_course(courseid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")
    return jsonify({"isSuccess": _db.add_disabled_course(courseid.strip())})


@app.route("/enable_course/<courseid>", methods=["POST"])
def enable_course(courseid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")
    return jsonify({"isSuccess": _db.remove_disabled_course(courseid.strip())})


@app.route("/add_to_blacklist/<user>", methods=["POST"])
def add_to_blacklist(user):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"isSuccess": _db.add_to_blacklist(user.strip(), netid)})


@app.route("/remove_from_blacklist/<user>", methods=["POST"])
def remove_from_blacklist(user):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"isSuccess": _db.remove_from_blacklist(user.strip(), netid)})


@app.route("/get_notifications_status", methods=["POST"])
def get_notifications_status():
    if redirect_landing():
        return redirect("/")

    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"isOn": _db.get_cron_notification_status()})


@app.route("/clear_by_class/<classid>", methods=["POST"])
def clear_by_class(classid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"isSuccess": _db.clear_class_waitlist(classid, netid)})


@app.route("/clear_by_course/<courseid>", methods=["POST"])
def clear_by_course(courseid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"isSuccess": _db.clear_course_waitlists(courseid, netid)})


@app.route("/get_user_data/<netid>", methods=["POST"])
def get_user_data(netid):
    netid_ = _cas.authenticate()
    try:
        if not is_admin(netid_, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"data": _db.get_waited_sections(netid.strip())})


@app.route("/get_usage_summary", methods=["POST"])
def get_usage_summary():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"data": _db.get_usage_summary()})


@app.route("/get_all_subscriptions", methods=["POST"])
def get_all_subscriptions():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    return jsonify({"data": _db.get_all_subscriptions()})


@app.route("/fill_section/<classid>", methods=["POST"])
def fill_section(classid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect("/")
    except:
        return redirect("/")

    try:
        curr_enrollment = _db.get_class_enrollment(classid)
        if curr_enrollment is None:
            return jsonify({"isSuccess": False})
        _db.update_enrollment(
            classid,
            curr_enrollment["capacity"],
            curr_enrollment["capacity"],
            None,
            set_status_to_closed=True,
        )

        _db._add_admin_log(f"manually filled enrollments for class {classid}")
        _db._add_system_log(
            "admin",
            {"message": f"manually filled enrollments for class {classid}"},
            netid=netid,
        )
    except:
        return jsonify({"isSuccess": False})

    return jsonify({"isSuccess": True})


@app.template_filter("version")
def version_filter(file_path):
    """
    Filter used in HTML script tags in order to import
    the most up-to-date version of JS or CSS files.
    """

    # file_path is "/static/<file>"
    FOLDER = "static"
    file = file_path[len(f"/{FOLDER}/") :]

    file_split = file.split(".")
    FNAME = file_split[0]  # "app" or "styles"
    EXT = file_split[-1]  # "js" or "css"

    static_files = [f for f in listdir(FOLDER) if isfile(join(FOLDER, f))]
    VERSION = "."
    for f in static_files:
        if f[: len(FNAME)] == FNAME and f[-len(EXT) :] == EXT and f != f"{FNAME}.{EXT}":
            VERSION = f[len(FNAME) : -(len(EXT))]  # ".<version_num>."

    # "/static/app.<version_num>.js" or "/static/styles.<version_num>.css"
    return f"/{FOLDER}/{FNAME}{VERSION}{EXT}"


# ----------------------------------------------------------------------
# LIVE NOTIFICATIONS STATUS
# ----------------------------------------------------------------------


@app.route("/notifs_update_broadcast", methods=["GET"])
def notifs_update_broadcast():
    state, description, countdown = _db.get_live_notifs_status()
    if state == "countdown":
        description = countdown
    return jsonify(
        {
            "state": state,
            "description": description,
            "max_countdown": NOTIFS_INTERVAL_SECS,
        }
    )

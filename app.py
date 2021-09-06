# ----------------------------------------------------------------------
# api.py
# Defines endpoints for TigerSnatch app.
# ----------------------------------------------------------------------

from sys import path

path.append("src")  # noqa

from flask import Flask
from flask import render_template, make_response, request, redirect, url_for, jsonify
from database import Database
from CASClient import CASClient
from config import APP_SECRET_KEY
from waitlist import Waitlist
from _exec_update_all_courses import do_update_async
from app_helper import do_search, pull_course, is_admin
from urllib.parse import quote_plus, unquote_plus
from sys import stderr

app = Flask(__name__, template_folder="./views")
app.secret_key = APP_SECRET_KEY

_cas = CASClient()
_db = Database()


@app.errorhandler(Exception)
def handle_exception(e):
    # 404 errors simply clutter system logs
    if "404 Not Found" not in str(e):
        _db._add_system_log("error", {"message": request.path + ": " + str(e)})
    # uncomment the below two lines to force a print of the stack trace
    # import traceback
    # traceback.print_exc()
    return render_template("error.html")


@app.before_request
def enforceHttpsInHeroku():
    # always force redirect to HTTPS (secure connection)
    if request.headers.get("X-Forwarded-Proto") == "http":
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)


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
    if redirect_landing():
        return redirect(url_for("landing"))
    return redirect(url_for("dashboard"))


@app.route("/landing", methods=["GET"])
def landing():
    html = render_template("landing.html")
    return make_response(html)


@app.route("/login", methods=["GET"])
def login():
    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blacklisted user {netid} attempted to access the app")
        return make_response(render_template("blacklisted.html"))

    _db._add_system_log("user", {"message": f"user {netid} logged in"}, netid=netid)

    if not _db.is_user_created(netid):
        _db.create_user(netid)
        return redirect(url_for("tutorial"))

    return redirect(url_for("dashboard"))


@app.route("/tutorial", methods=["GET"])
def tutorial():
    if redirect_landing():
        html = render_template("tutorial.html", loggedin=False)
        return make_response(html)

    term_name = _db.get_current_term_code()[1]

    html = render_template(
        "tutorial.html",
        user_is_admin=is_admin(_cas.authenticate(), _db),
        loggedin=True,
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        term_name=term_name,
    )
    return make_response(html)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if redirect_landing():
        return redirect(url_for("landing"))

    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blacklisted user {netid} attempted to access the app")
        return make_response(render_template("blacklisted.html"))

    data = _db.get_dashboard_data(netid)
    email = _db.get_user(netid, "email")
    phone = _db.get_user(netid, "phone")

    query = request.args.get("query")
    new_email = request.form.get("new_email")
    new_phone = request.form.get("new_phone")

    if query is None:
        query = ""
    if len(query) > 100:
        query = query[:100]
    search_res, new_query = do_search(query, _db)

    if new_email is not None:
        if "<" in new_email or ">" in new_email or "script" in new_email:
            print("HTML code detected in", new_email, file=stderr)
            return redirect(url_for("dashboard"))

        _db.update_user(netid, new_email.strip())
        return redirect(url_for("dashboard"))

    if new_phone is not None:
        if "<" in new_phone or ">" in new_phone or "script" in new_phone:
            print("HTML code detected in", new_phone, file=stderr)
            return redirect(url_for("dashboard"))

        _db.update_user_phone(netid, new_phone.strip())
        return redirect(url_for("dashboard"))

    curr_sections = _db.get_current_sections(netid)
    term_name = _db.get_current_term_code()[1]

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
        curr_sections=curr_sections,
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        term_name=term_name,
    )

    return make_response(html)


@app.route("/about", methods=["GET"])
def about():
    if redirect_landing():
        html = render_template("about.html", loggedin=False)
        return make_response(html)

    term_name = _db.get_current_term_code()[1]

    html = render_template(
        "about.html",
        user_is_admin=is_admin(_cas.authenticate(), _db),
        loggedin=True,
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        term_name=term_name,
    )
    return make_response(html)


@app.route("/activity", methods=["GET"])
def activity():
    if redirect_landing():
        return redirect(url_for("landing"))

    netid = _cas.authenticate()

    waitlist_logs = _db.get_user_waitlist_log(netid)
    trade_logs = _db.get_user_trade_log(netid)
    term_name = _db.get_current_term_code()[1]

    html = render_template(
        "activity.html",
        user_is_admin=is_admin(_cas.authenticate(), _db),
        loggedin=True,
        waitlist_logs=waitlist_logs,
        trade_logs=trade_logs,
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        term_name=term_name,
    )

    return make_response(html)


@app.route("/course", methods=["GET"])
def get_course():
    if not _cas.is_logged_in():
        return redirect(url_for("landing"))

    netid = _cas.authenticate()
    if _db.is_blacklisted(netid):
        _db._add_admin_log(f"blacklisted user {netid} attempted to access the app")
        return make_response(render_template("blacklisted.html"))

    courseid = request.args.get("courseid")
    query = request.args.get("query")

    _db._add_system_log(
        "user",
        {"message": f"course page {courseid} visited by user {netid}"},
        netid=netid,
    )

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
    current_section = _db.get_current_section(netid, courseid)
    current_sectionname = (
        _db.classid_to_sectionname(current_section)
        if current_section is not None
        else ""
    )
    trade_unavailable = False
    if not section_names or len(section_names) < 2:
        trade_unavailable = True

    # change to check if updateSearch == 'false'
    # if updateSearch is None:
    html = render_template(
        "base.html",
        is_dashboard=False,
        is_admin=False,
        user_is_admin=is_admin(netid, _db),
        netid=netid,
        current_section=current_section,
        current_sectionname=current_sectionname,
        courseid=courseid,
        course_details=course_details,
        classes_list=classes_list,
        trade_unavailable=trade_unavailable,
        curr_waitlists=curr_waitlists,
        search_res=search_res,
        num_full=num_full,
        section_names=section_names,
        term_code=term_code,
        term_name=term_name,
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        is_course_disabled=_db.is_course_disabled(courseid),
    )

    return make_response(html)


@app.route("/logout", methods=["GET"])
def logout():
    _cas.logout()
    return redirect(url_for("landing"))


# ----------------------------------------------------------------------
# ACCESSIBLE BY ALL, NOT VIA URL
# ----------------------------------------------------------------------


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

    _db._add_system_log(
        "user",
        {"message": f"course page {courseid} visited by user {netid}"},
        netid=netid,
    )

    course_details, classes_list = pull_course(courseid, _db)
    curr_waitlists = _db.get_user(netid, "waitlists")
    section_names = _db.get_section_names_in_course(courseid)
    current_section = _db.get_current_section(netid, courseid)
    current_sectionname = (
        _db.classid_to_sectionname(current_section)
        if current_section is not None
        else ""
    )
    trade_unavailable = False
    if not section_names or len(section_names) < 2:
        trade_unavailable = True

    num_full = sum(class_data["isFull"] for class_data in classes_list)
    term_code, term_name = _db.get_current_term_code()

    html = render_template(
        "course/course.html",
        netid=netid,
        user_is_admin=is_admin(netid, _db),
        courseid=courseid,
        course_details=course_details,
        classes_list=classes_list,
        trade_unavailable=trade_unavailable,
        num_full=num_full,
        current_section=current_section,
        current_sectionname=current_sectionname,
        term_code=term_code,
        term_name=term_name,
        curr_waitlists=curr_waitlists,
        section_names=section_names,
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
        is_course_disabled=_db.is_course_disabled(courseid),
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


@app.route("/update_user_section/<courseid>/<classid>", methods=["POST"])
def update_user_section(courseid, classid):
    netid = _cas.authenticate()
    status = _db.update_current_section(netid, courseid, classid)
    return jsonify({"isSuccess": status})


@app.route("/remove_user_section/<courseid>", methods=["POST"])
def remove_user_section(courseid):
    netid = _cas.authenticate()
    status = _db.remove_current_section(netid, courseid)
    return jsonify({"isSuccess": status})


@app.route("/find_matches/<courseid>", methods=["POST"])
def find_matches(courseid):
    netid = _cas.authenticate()
    matches = _db.find_matches(netid, courseid)
    return jsonify({"data": matches})


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
    except:
        return jsonify({"isSuccess": False})
    return jsonify({"isSuccess": True})


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

    html = render_template(
        "base.html",
        is_dashboard=False,
        is_admin=True,
        user_is_admin=True,
        search_res=search_res,
        last_query=quote_plus(new_query),
        last_query_unquoted=unquote_plus(new_query),
        username=netid,
        admin_logs=admin_logs,
        blacklist=_db.get_blacklist(),
        notifs_online=_db.get_cron_notification_status(),
        next_notifs=_db.get_current_or_next_notifs_interval(),
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
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))
    return jsonify({"isSuccess": _db.add_disabled_course(courseid.strip())})


@app.route("/enable_course/<courseid>", methods=["POST"])
def enable_course(courseid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))
    return jsonify({"isSuccess": _db.remove_disabled_course(courseid.strip())})


@app.route("/add_to_blacklist/<user>", methods=["POST"])
def add_to_blacklist(user):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.add_to_blacklist(user.strip(), netid)})


@app.route("/remove_from_blacklist/<user>", methods=["POST"])
def remove_from_blacklist(user):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.remove_from_blacklist(user.strip(), netid)})


@app.route("/get_notifications_status", methods=["POST"])
def get_notifications_status():
    if redirect_landing():
        return redirect(url_for("landing"))

    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isOn": _db.get_cron_notification_status()})


@app.route("/set_notifications_status/<status>", methods=["POST"])
def set_notifications_status(status):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    _db.set_cron_notification_status(status == "true", admin_netid=netid)
    return jsonify({})


@app.route("/clear_all_trades", methods=["POST"])
def clear_all_trades():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.clear_all_trades(netid)})


@app.route("/clear_all_user_logs", methods=["POST"])
def clear_all_user_logs():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.clear_all_user_logs(netid)})


@app.route("/clear_all_waitlists", methods=["POST"])
def clear_all_waitlists():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.clear_all_waitlists(netid)})


@app.route("/clear_by_class/<classid>", methods=["POST"])
def clear_by_class(classid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.clear_class_waitlist(classid, netid)})


@app.route("/clear_by_course/<courseid>", methods=["POST"])
def clear_by_course(courseid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"isSuccess": _db.clear_course_waitlists(courseid, netid)})


@app.route("/get_user_data/<netid>/<isTrade>", methods=["POST"])
def get_user_data(netid, isTrade):
    netid_ = _cas.authenticate()
    try:
        if not is_admin(netid_, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify(
        {"data": _db.get_waited_sections(netid.strip(), trades=isTrade == "true")}
    )


@app.route("/get_usage_summary", methods=["POST"])
def get_usage_summary():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"data": _db.get_usage_summary()})


@app.route("/get_all_subscriptions", methods=["POST"])
def get_all_subscriptions():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    return jsonify({"data": _db.get_all_subscriptions()})


@app.route("/update_all_courses", methods=["POST"])
def update_all_courses():
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    do_update_async(netid)  # CAUTION: hard reset and update

    return jsonify({})


@app.route("/fill_section/<classid>", methods=["POST"])
def fill_section(classid):
    netid = _cas.authenticate()
    try:
        if not is_admin(netid, _db):
            return redirect(url_for("landing"))
    except:
        return redirect(url_for("landing"))

    try:
        curr_enrollment = _db.get_class_enrollment(classid)
        if curr_enrollment is None:
            return jsonify({"isSuccess": False})
        _db.update_enrollment(
            classid, curr_enrollment["capacity"], curr_enrollment["capacity"], None
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

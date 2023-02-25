const toastAdded = $(
  $.parseHTML(`
<div
    id="toast-added"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Successfully subscribed!</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastRemoved = $(
  $.parseHTML(`
<div
    id="toast-removed"
    class="toast align-items-center text-white bg-warning border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Successfully unsubscribed!</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastUserDoesNotExist = $(
  $.parseHTML(`
<div
    id="toast-user-does-not-exist"
    class="toast align-items-center text-white bg-danger border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">That netID does not exist.</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastEmailsOn = $(
  $.parseHTML(`
<div
    id="toast-emails-on"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Email notifications turned on! Reloading in a few seconds...</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastEmailsOff = $(
  $.parseHTML(`
<div
    id="toast-emails-off"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Email notifications turned off! Reloading in a few seconds...</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastClearSuccess = $(
  $.parseHTML(`
<div
    id="toast-clear-success"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Cleared sucessfully!</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastClearFail = $(
  $.parseHTML(`
<div
    id="toast-clear-fail"
    class="toast align-items-center text-white bg-danger border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Failed to clear. Check course/class ID or contact a TigerSnatch developer for assistance.</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastDisableEnableCourseSuccess = $(
  $.parseHTML(`
<div
    id="toast-disable-enable-course-success"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Successfully disabled/enabled course subscriptions!</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastDisableEnableCourseFail = $(
  $.parseHTML(`
<div
    id="toast-disable-enable-course-fail"
    class="toast align-items-center text-white bg-danger border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Failed to disable/enable course subscriptions. Check course ID or contact a TigerSnatch developer for assistance.</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastFillSuccess = $(
  $.parseHTML(`
<div
    id="toast-clear-success"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Filled section sucessfully!</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastFillFail = $(
  $.parseHTML(`
<div
    id="toast-clear-fail"
    class="toast align-items-center text-white bg-danger border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Failed to fill section. Check class ID or contact a TigerSnatch developer for assistance.</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastBlacklistFail = $(
  $.parseHTML(`
<div
    id="toast-blacklist-fail"
    class="toast align-items-center text-white bg-danger border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Failed to block/unblock user.</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

const toastBlacklistSuccess = $(
  $.parseHTML(`
<div
    id="toast-blacklist-success"
    class="toast align-items-center text-white bg-success border-0"
    role="alert"
    aria-live="assertive"
    aria-atomic="true"
    data-bs-delay="3000"
>
    <div class="d-flex">
        <div class="toast-body">Successfully blocked/unblocked user! Reloading in a few seconds...</div>
        <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            data-bs-dismiss="toast"
            aria-label="Close"
        ></button>
    </div>
</div>
`)
);

i = 0; // dummy variable used for toast ids

// scrolls to the bottom of id #dest
let scrollBottom = function (dest) {
  $(dest).animate(
    {
      scrollTop: $(dest)[0].scrollHeight - $(dest)[0].clientHeight,
    },
    500
  );
};

// scrolls to the top of id #dest
let resetScroll = function (dest) {
  $(dest).animate(
    {
      scrollTop: 0,
    },
    500
  );
};

// listens for submission of search form
let searchFormListener = function () {
  $("form#search-form").on("submit", function (e) {
    e.preventDefault();
    // close the keyboard
    $("#search-form-input").blur();
    // close the tooltip if open
    $("#search-form-input").tooltip("hide");
    return;
  });

  $("form#search-form").on("input", function (e) {
    e.preventDefault();

    // get search query
    query_raw = $("#search-form-input").prop("value");
    query = encodeURIComponent(query_raw);

    curr_path = location.pathname;
    params = location.search.replace("?", "").split("&");

    // close the tooltip if open
    $("#search-form-input").tooltip("hide");

    // add query to URL
    curr_path += `?query=${query}`;
    if (location.search !== "") {
      params.forEach((param) => {
        if (!param.startsWith("query")) curr_path += `&${param}`;
      });
    }

    // get search results
    if (query.trim() === "") {
      endpoint = "/searchresults";
    } else {
      endpoint = `/searchresults/${query}`;
    }

    $.post(endpoint, function (res) {
      $("div#search-results").html(res);
      window.history.pushState(
        { restore: "search", html: res },
        "restore search results",
        curr_path
      );
      // adds listener to new search results
      searchResultListener();
      resetScroll("#search-results");
      dashboardSkip();
    });
  });
};

// listens for selection of search result
let searchResultListener = function () {
  $(".search-results-link").on("click", function (e) {
    e.preventDefault();

    // blur frame while loading
    $("#main").css("pointer-events", "none");
    $("#main").css("filter", "blur(2px)");
    $("#loading-overlay").css("display", "flex");

    // remove gray background from currently selected course entry
    $("a.selected-course").css("background-color", "");
    $("a.selected-course").removeClass(
      "selected-course border border-3 border-warning"
    );

    closest_a = $(this).closest("a");

    // background: #C0BDBD;
    // add gray background to selected course
    closest_a.css("background-color", "#ffe58a");
    closest_a.addClass("selected-course border border-3 border-warning");

    course_link = closest_a.attr("href");
    courseid = closest_a.attr("data-courseid");

    scrollBottom("#main");

    // get course information
    $.post(`/courseinfo/${courseid}`, function (res) {
      // change search form to /course endpoint
      $("form#search-form").attr("action", "/course");
      $("input#search-form-courseid").attr("value", courseid);
      $("#right-wrapper").html(res);

      // unblur frame
      $("#loading-overlay").css("display", "none");
      $("#main").css("filter", "");
      $("#main").css("pointer-events", "");

      // update URL
      window.history.pushState(
        { restore: "right", html: res },
        "",
        course_link
      );

      // add listener to new switches & modals, and re-initialize
      // all tooltips and toasts
      switchListener();
      initTooltipsToasts();
      showAllListener();
      modalCancelListener();
      modalConfirmListener();
      searchSkip();
    });
  });
};

let disableSwitchFunctions = function () {
  $(".waitlist-switch").attr("disabled", true);
  $("#auto-resub-switch").attr("disabled", true);
  $("*").css("pointer-events", "none");
  $("*").css("cursor", "wait");
};

let enableSwitchFunctions = function () {
  $(".waitlist-switch").attr("disabled", false);
  $("#auto-resub-switch").attr("disabled", false);
  $("*").css("pointer-events", "");
  $("*").css("cursor", "");
};

// listens for toggle of waitlist notification switch
let switchListener = function () {
  $("input.waitlist-switch").change(function (e) {
    e.preventDefault();
    classid = e.target.getAttribute("data-classid");

    $("#confirm-remove-waitlist").attr("data-classid", classid);
    $("#close-waitlist-modal").attr("data-classid", classid);

    switchid = `#switch-${classid}`;
    n_tigers = $(this).closest("td").next("td");

    // if user is not on waitlist for this class, then add them
    if (!$(switchid).attr("checked")) {
      disableSwitchFunctions();
      $.post(`/add_to_waitlist/${classid}`, function (res) {
        // checks that user successfully added to waitlist on back-end
        if (res["isSuccess"] === 2) return;
        if (res["isSuccess"] === 0) {
          $("#close-waitlist-modal").modal("show");
          $(switchid).attr("checked", false);
          $(switchid).prop("checked", false);
          enableSwitchFunctions();
          return;
        }

        // increment # tigers and change tooltip message
        originalNumber = Number(n_tigers.text().trim());
        newNumber = originalNumber + 1;
        statsBadge = n_tigers.children()[0];
        if (statsBadge != null) {
          n_tigers.html(`${newNumber} ${statsBadge.outerHTML}`);
          $(n_tigers.children()[0]).attr(
            "data-bs-original-title",
            "Reload to see stats!"
          );
        } else {
          n_tigers.html(`${newNumber}`);
        }

        initTooltipsToasts();

        $(switchid).attr("checked", true);
        $(switchid).attr("data-bs-toggle", "modal");
        $(switchid).attr("data-bs-target", "#confirm-remove-waitlist");
        enableSwitchFunctions();

        $(".toast-container").prepend(
          toastAdded.clone().attr("id", "toast-added-" + ++i)
        );
        $("#toast-added-" + i).toast("show");
      });
    }
  });
};

let autoResubSwitchListener = function () {
  $("#auto-resub-switch").change(function (e) {
    e.preventDefault();
    disableSwitchFunctions();
    const checkedProp = $("#auto-resub-switch").prop("checked");
    $.post(`/update_auto_resub/${checkedProp}`, function (res) {
      if (res["isSuccess"]) {
        if (checkedProp) {
          alert(
            "Notification settings successfully changed: You have enabled the Stay Subscribed option."
          );
        } else {
          alert(
            "Notification settings successfully changed: You have disabled the Stay Subscribed option."
          );
        }
      } else {
        $("#auto-resub-switch").prop("checked", !checkedProp);
      }
      enableSwitchFunctions();
    });
  });
};

// listens for "Confirm" removal from waitlist
let modalConfirmListener = function () {
  $("#waitlist-modal-confirm").on("click", function (e) {
    e.preventDefault();
    classid = $("#confirm-remove-waitlist").attr("data-classid");
    switchid = `#switch-${classid}`;
    disableSwitchFunctions();

    n_tigers = $(switchid).closest("td").next("td");

    $.post(`/remove_from_waitlist/${classid}`, function (res) {
      // checks that user successfully removed from waitlist on back-end
      if (!res["isSuccess"]) return;

      // decrement # tigers and change tooltip message
      originalNumber = Number(n_tigers.text().trim());
      newNumber = originalNumber - 1;
      statsBadge = n_tigers.children()[0];
      if (statsBadge != null && newNumber !== 0) {
        n_tigers.html(`${newNumber} ${statsBadge.outerHTML}`);
        $(n_tigers.children()[0]).attr(
          "data-bs-original-title",
          "Reload to see stats!"
        );
      } else {
        n_tigers.html(`${newNumber}`);
      }

      initTooltipsToasts();

      $(`${switchid}.dashboard-switch`)
        .closest("tr.dashboard-course-row")
        .remove();
      $(switchid).removeAttr("checked");
      $(switchid).removeAttr("data-bs-toggle");
      $(switchid).removeAttr("data-bs-target");
      enableSwitchFunctions();

      $(".toast-container").prepend(
        toastRemoved.clone().attr("id", "toast-removed-" + ++i)
      );
      $("#toast-removed-" + i).toast("show");
    });
  });
};

// listens for "Cancel" removal from waitlist
let modalCancelListener = function () {
  $("#waitlist-modal-cancel").on("click", function (e) {
    e.preventDefault();
    classid = $("#confirm-remove-waitlist").attr("data-classid");
    $(`#switch-${classid}`).prop("checked", true);
  });
};

let showAllListener = function () {
  $("#show-all-check").on("click", function (e) {
    if ($(this).prop("checked")) {
      $(".available-section-row").removeClass("d-none");
      $("#no-full-message").addClass("d-none");
    } else {
      $(".available-section-row").addClass("d-none");
      $("#no-full-message").removeClass("d-none");
    }
  });
};

// listens for user to click back button on page
let pageBackListener = function () {
  $(window).on("popstate", function () {
    // for now, just reloads
    location.reload();
  });
};

// quick-skip to dashboard
let dashboardSkip = function () {
  $("#dashboard-skip").on("click", function (e) {
    e.preventDefault();
    scrollBottom("#main");
  });
  if (window.location.href.indexOf("skip") !== -1) $("#dashboard-skip").click();
};

// quick-skip to course search
let searchSkip = function () {
  $("#search-skip").on("click", function (e) {
    e.preventDefault();
    resetScroll("#main");
  });
};

// initialize all tooltips
let initTooltipsToasts = function () {
  let tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  let tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl, { html: true });
  });
  $("#status-indicator").on("click", function (e) {
    e.preventDefault();
  });
  $("#dev-warning").on("click", function (e) {
    e.preventDefault();
  });
};

// closes the navbar (mobile) on tap out
let navbarAutoclose = function () {
  $(document).click(function (event) {
    let click = $(event.target);
    if (
      $(".navbar-collapse").hasClass("show") &&
      !click.hasClass("navbar-toggler") &&
      !click.hasClass("nav-item") &&
      !click.hasClass("nav-button") &&
      !click.hasClass("nav-link")
    )
      $(".navbar-toggler").click();
  });
};

// listens for "Info" button on user list
let getUserInfoListener = function () {
  let helper = function (res, label) {
    if (res["data"] === "missing") {
      $(".toast-container").prepend(
        toastUserDoesNotExist
          .clone()
          .attr("id", "toast-user-does-not-exist-" + ++i)
      );
      $("#toast-user-does-not-exist-" + i).toast("show");
      enableAdminFunction();
      return;
    }
    let data = res["data"].split("{");
    $(`#get-${label}-input`).val("");

    dataHTML = "";
    for (let d of data) dataHTML += `<p class="my-1">&#8594; ${d}</p>`;

    $("#modal-body-user-data").html(dataHTML);
    $("#user-data-waitlist-modal").modal("show");
  };

  $("button.btn-user-info").on("click", function (e) {
    e.preventDefault();
    disableAdminFunction();
    netid = e.target.getAttribute("data-netid");
    $.post(`/get_user_data/${netid}`, function (res) {
      helper(res, "user-data");
      $("#staticBackdropLabelUserData").html(
        `Subscribed Sections for ${netid}`
      );
      enableAdminFunction();
    });
  });
};

// listens for Usage Summary button on admin panel
let getUsageSummaryListener = function () {
  let helper = function (res, label) {
    if (res["data"] === "error") {
      enableAdminFunction();
      return;
    }
    let data = res["data"].split("{");

    dataHTML = "";
    for (let d of data) dataHTML += `<p class="my-1">&#8594; ${d}</p>`;

    $("#modal-body-usage-summary").html(dataHTML);
    $("#usage-summary-modal").modal("show");
  };

  $("#usage-summary").on("click", function (e) {
    e.preventDefault();
    disableAdminFunction();
    $.post(`/get_usage_summary`, function (res) {
      helper(res, "usage-summary");
      enableAdminFunction();
    });
  });
};

// listens for All Subscriptions button on admin panel
let getAllSubscriptionsListener = function () {
  let helper = function (res, label) {
    if (res["data"] === "error") {
      enableAdminFunction();
      return;
    }
    let data = res["data"].split("{");

    dataHTML = "";
    for (let d of data) dataHTML += `<p class="my-1">&#8594; ${d}</p>`;

    $("#modal-body-all-subscriptions").html(dataHTML);
    $("#all-subscriptions-modal").modal("show");
  };

  $("#all-subscriptions").on("click", function (e) {
    e.preventDefault();
    disableAdminFunction();
    $.post(`/get_all_subscriptions`, function (res) {
      helper(res, "all-subscriptions");
      enableAdminFunction();
    });
  });
};

// enables all admin function buttons
let enableAdminFunction = function () {
  $(".btn-blacklist-removal").attr("disabled", false);
  $(".btn-user-info").attr("disabled", false);
  $("#notifs-sheet-link").attr("disabled", false);
  $("#usage-summary").attr("disabled", false);
  $("#all-subscriptions").attr("disabled", false);
  $("#disable-course-input").attr("disabled", false);
  $("#disable-course-submit").attr("disabled", false);
  $("#enable-course-input").attr("disabled", false);
  $("#enable-course-submit").attr("disabled", false);
  $("#classid-clear-input").attr("disabled", false);
  $("#classid-clear-submit").attr("disabled", false);
  $("#courseid-clear-input").attr("disabled", false);
  $("#courseid-clear-submit").attr("disabled", false);
  $("#get-user-data-input").attr("disabled", false);
  $("#get-user-data-submit").attr("disabled", false);
  $("#fill-section-input").attr("disabled", false);
  $("#fill-section-submit").attr("disabled", false);
  $("#block-user-input").attr("disabled", false);
  $("#block-user-submit").attr("disabled", false);
};

// disables all admin function buttons
let disableAdminFunction = function () {
  $(".btn-blacklist-removal").attr("disabled", true);
  $(".btn-user-info").attr("disabled", true);
  $("#notifs-sheet-link").attr("disabled", true);
  $("#usage-summary").attr("disabled", true);
  $("#all-subscriptions").attr("disabled", true);
  $("#disable-course-input").attr("disabled", true);
  $("#disable-course-submit").attr("disabled", true);
  $("#enable-course-input").attr("disabled", true);
  $("#enable-course-submit").attr("disabled", true);
  $("#classid-clear-input").attr("disabled", true);
  $("#classid-clear-submit").attr("disabled", true);
  $("#courseid-clear-input").attr("disabled", true);
  $("#courseid-clear-submit").attr("disabled", true);
  $("#get-user-data-input").attr("disabled", true);
  $("#get-user-data-submit").attr("disabled", true);
  $("#fill-section-input").attr("disabled", true);
  $("#fill-section-submit").attr("disabled", true);
  $("#block-user-input").attr("disabled", true);
  $("#block-user-submit").attr("disabled", true);
};

// listens for email notifications switch toggle
let toggleEmailNotificationsListener = function () {
  $("#notifs-sheet-link").on("click", function (e) {
    e.preventDefault();
    window.open(
      "https://docs.google.com/spreadsheets/d/1iSWihUcWa0yX8MsS_FKC-DuGH75AukdiuAigbSkPm8k/edit#gid=550138744",
      "_blank"
    );
  });
};

// helper method to display fail/success toasts for waitlist clearing
let clearWaitlistsToastHelper = function (res) {
  if (!res["isSuccess"]) {
    $(".toast-container").prepend(
      toastClearFail.clone().attr("id", "toast-clear-fail-" + ++i)
    );
    $("#toast-clear-fail-" + i).toast("show");
  } else {
    $(".toast-container").prepend(
      toastClearSuccess.clone().attr("id", "toast-clear-success-" + ++i)
    );
    $("#toast-clear-success-" + i).toast("show");
  }
};

// helper method to display fail/success toasts for course disabling/enabling
let disableEnableCourseToastHelper = function (res) {
  if (!res["isSuccess"]) {
    $(".toast-container").prepend(
      toastDisableEnableCourseFail
        .clone()
        .attr("id", "toast-disable-enable-course-fail-" + ++i)
    );
    $("#toast-disable-enable-course-fail-" + i).toast("show");
  } else {
    $(".toast-container").prepend(
      toastDisableEnableCourseSuccess
        .clone()
        .attr("id", "toast-disable-enable-course-success-" + ++i)
    );
    $("#toast-disable-enable-course-success-" + i).toast("show");
  }
};

// helper method to display fail/success toasts for waitlist clearing
let fillSectionToastHelper = function (res) {
  if (!res["isSuccess"]) {
    $(".toast-container").prepend(
      toastFillFail.clone().attr("id", "toast-clear-fail-" + ++i)
    );
    $("#toast-clear-fail-" + i).toast("show");
  } else {
    $(".toast-container").prepend(
      toastFillSuccess.clone().attr("id", "toast-clear-success-" + ++i)
    );
    $("#toast-clear-success-" + i).toast("show");
  }
};

// listens for clear class waitlist button
let clearClassWaitlistListener = function () {
  $("#classid-clear").on("submit", function (e) {
    e.preventDefault();
    classid = $("#classid-clear-input").val();
    disableAdminFunction();

    if (
      !confirm(
        `Are you sure you want to clear subscriptions for class ${classid}? This action is irreversible.`
      )
    ) {
      enableAdminFunction();
      return;
    }

    $.post(`/clear_by_class/${classid}`, function (res) {
      // checks that user successfully removed from waitlist on back-end
      clearWaitlistsToastHelper(res);
      $("#classid-clear-input").val("");
      enableAdminFunction();
    });
  });
};

let fillSectionListener = function () {
  $("#fill-section").on("submit", function (e) {
    e.preventDefault();
    classid = $("#fill-section-input").val();
    disableAdminFunction();

    $.post(`/fill_section/${classid}`, function (res) {
      // checks that user successfully removed from waitlist on back-end
      fillSectionToastHelper(res);
      $("#fill-section-input").val("");
      enableAdminFunction();
    });
  });
};

// listens for clear course waitlists button
let clearCourseWaitlistListener = function () {
  $("#courseid-clear").on("submit", function (e) {
    e.preventDefault();
    courseid = $("#courseid-clear-input").val();
    disableAdminFunction();

    if (
      !confirm(
        `Are you sure you want to clear subscriptions for course ${courseid}? This action is irreversible.`
      )
    ) {
      enableAdminFunction();
      return;
    }

    $.post(`/clear_by_course/${courseid}`, function (res) {
      // checks that user successfully removed from waitlist on back-end
      clearWaitlistsToastHelper(res);
      $("#courseid-clear-input").val("");
      enableAdminFunction();
    });
  });
};

// listens for disable course button
let disableCourseListener = function () {
  $("#disable-course").on("submit", function (e) {
    e.preventDefault();
    courseid = $("#disable-course-input").val();
    disableAdminFunction();

    if (
      !confirm(
        `Are you sure you want to disable course ${courseid}? This action will unsubscribe all users from the course's sections and is irreversible.`
      )
    ) {
      enableAdminFunction();
      return;
    }

    $.post(`/disable_course/${courseid}`, function (res) {
      // checks that course has successfully been disabled
      disableEnableCourseToastHelper(res);
      $("#disable-course-input").val("");
      enableAdminFunction();
    });
  });
};

// listens for enable course button
let enableCourseListener = function () {
  $("#enable-course").on("submit", function (e) {
    e.preventDefault();
    courseid = $("#enable-course-input").val();
    disableAdminFunction();

    $.post(`/enable_course/${courseid}`, function (res) {
      // checks that course has successfully been enable
      disableEnableCourseToastHelper(res);
      $("#enable-course-input").val("");
      enableAdminFunction();
    });
  });
};

// listens for a user data query
let getUserDataListener = function () {
  let helper = function (res, label) {
    if (res["data"] === "missing") {
      $(".toast-container").prepend(
        toastUserDoesNotExist
          .clone()
          .attr("id", "toast-user-does-not-exist-" + ++i)
      );
      $("#toast-user-does-not-exist-" + i).toast("show");
      enableAdminFunction();
      return;
    }
    let data = res["data"].split("{");
    $(`#get-${label}-input`).val("");

    dataHTML = "";
    for (let d of data) dataHTML += `<p class="my-1">&#8594; ${d}</p>`;

    $("#modal-body-user-data").html(dataHTML);
    $("#user-data-waitlist-modal").modal("show");
  };

  $("#get-user-data").on("submit", function (e) {
    e.preventDefault();
    netid = $(`#get-user-data-input`).val();
    disableAdminFunction();
    $.post(`/get_user_data/${netid}`, function (res) {
      helper(res, "user-data");
      $("#staticBackdropLabelUserData").html(
        `Subscribed Sections for ${netid}`
      );
      enableAdminFunction();
    });
  });
};

// listens for a user block or unblock query
let blockUserListener = function () {
  // helper method to show blacklist success/fail toast
  let blockToastHelper = function (type) {
    if (type === "success") {
      $(".toast-container").prepend(
        toastBlacklistSuccess
          .clone()
          .attr("id", "toast-blacklist-success-" + ++i)
      );
      $("#toast-blacklist-success-" + i).toast("show");
      $("*").css("pointer-events", "none");
      setTimeout(() => location.reload(), 3100);
    } else if (type === "fail") {
      $(".toast-container").prepend(
        toastBlacklistFail.clone().attr("id", "toast-blacklist-fail-" + ++i)
      );
      $("#toast-blacklist-fail-" + i).toast("show");
    }
  };

  $("#block-user").on("submit", function (e) {
    e.preventDefault();
    netid = $(`#block-user-input`).val();

    if (!confirm(`Are you sure you want to block user ${netid}?`)) return;

    disableAdminFunction();
    $.post(`/add_to_blacklist/${netid}`, function (res) {
      if (!res["isSuccess"]) {
        enableAdminFunction();
        blockToastHelper("fail");
        return;
      }
      blockToastHelper("success");
    });
  });

  $("button.btn-blacklist-removal").on("click", function (e) {
    e.preventDefault();
    netid = e.target.getAttribute("data-netid");

    if (!confirm(`Are you sure you want to unblock user ${netid}?`)) return;

    disableAdminFunction();
    $.post(`/remove_from_blacklist/${netid}`, function (res) {
      if (!res["isSuccess"]) {
        blockToastHelper("fail");
        enableAdminFunction();
        return;
      }
      blockToastHelper("success");
    });
  });
};

/**
 * Retired Trades functions

// helper function to build email link
let createEmail = function (
  match_netid,
  my_netid,
  match_section,
  my_section,
  course_name,
  match_email
) {
  const tradeEmailSubject = `TigerSnatch: Trade Sections for ${match_section} in ${course_name}?`;
  const tradeEmailBody = `Hi ${match_netid},\n\nFrom TigerSnatch, I saw that you're enrolled in ${course_name} ${match_section}. I'm currently in ${my_section}.\nWould you like to set up a time to trade sections with me? We should plan on swapping our sections simultaneously to prevent other TigerSnatch users from taking our spots.\n\nThank you,\n${my_netid}`;

  return encodeURI(
    `//mail.google.com/mail/?view=cm&fs=1&to=${match_email}&su=${tradeEmailSubject}&body=${tradeEmailBody}`
  );
};

// listens for find trades button
let findMatches = function () {
  $(".submit-trade").on("click", function (e) {
    e.preventDefault();
    courseid = e.target.getAttribute("courseid");
    netid = e.target.getAttribute("netid");
    coursename = e.target.getAttribute("coursename");

    disableTradeFunction();

    $.post(`/find_matches/${courseid}`, function (res) {
      // checks that user successfully updated section on back-end
      if (res["data"].length !== 0) {
        s = `<div>
                        <svg
                            id="dev-warning"
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            fill="currentColor"
                            class="bi bi-exclamation-triangle-fill text-primary"
                            viewBox="0 0 16 18"
                            >  
                            <path
                                d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"
                            />
                        </svg> Clicking 'Email' will add an entry for you and your match in Activity. Exchanging seats is your and your match's responsibilities. Instructors are not responsible if your seats are taken by other students during the exchange.
                    </div>
                    <div class="table-responsive">
                        <table class="table table-hover mt-2">
                        <thead class="table-white">
                            <tr>
                                <th scope="col">NetID</th>
                                <th scope="col">Current Section</th>
                                <th scopt="col">Contact</th>
                            </tr>
                        </thead>
                            <tbody>`;
        for (var i = 0; i < res["data"].length; i++) {
          match_netid = res["data"][i][0];
          match_section = res["data"][i][1];
          my_section = $(".submit-trade").attr("curr-section");
          coursename = $(".submit-trade").attr("coursename");
          match_email = res["data"][i][2];

          emailLink = createEmail(
            match_netid,
            netid,
            match_section,
            my_section,
            coursename,
            match_email
          );

          s += `<tr>
                        <td>${res["data"][i][0]}</td>
                        <td>${res["data"][i][1]}</td>
                        <td><a href=${emailLink} target='_blank' class='btn btn-outline-primary contact-button' match-netid=${res["data"][i][0]} match-section=${res["data"][i][1]}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-envelope me-1" viewBox="0 0 18 18">
                                <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1H2zm13 2.383-4.758 2.855L15 11.114v-5.73zm-.034 6.878L9.271 8.82 8 9.583 6.728 8.82l-5.694 3.44A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.739zM1 11.114l4.758-2.876L1 5.383v5.73z"/>
                            </svg>Email
                        </a>
                    </td>
                        </tr>`;
        }
        s += "</tbody></table></div>";
        $(`#match-${courseid}`).html(s);
        $(".contact-button").on("click", function (e) {
          e.preventDefault();
          $(".contact-button").attr("disabled", true);
          matchNetid = e.target.getAttribute("match-netid");
          matchSection = e.target.getAttribute("match-section");

          if (!matchNetid || !matchSection) return;

          if (
            !confirm(
              "Are you sure you want to email this user? They will be notified on their Activity page if you confirm!"
            )
          )
            return;

          window.open($(this).prop("href"), "_blank");

          $.post(
            `/contact_trade/${
              coursename.split("/")[0]
            }/${matchNetid}/${matchSection}`,
            function (res) {
              // checks that user successfully updated section on back-end
              $(".contact-button").attr("disabled", false);
            }
          );
        });
        initTooltipsToasts();
      } else {
        $(`#match-${courseid}`).html(
          "We're unable to find you a Trade! If you haven't already, make sure to Subscribe to one or more sections for this course. Your Subscribed sections are the ones you'd like to trade into!"
        );
      }
      $("#matches-modal").modal("show");
      enableTradeFunction();
    });
  });
};

*/

// change the name of this variable to force all users to see the tutorial and the alert banner
var doneKeyTutorial = "completed4";
var doneKeyBanner = "completed8";

// introJS tutorial
let initTutorial = function () {
  var tutorial = introJs();

  window.addEventListener("load", function () {
    if (window.location.pathname !== "/dashboard") return;
    if (window.innerWidth < 992) return;
    if (localStorage.getItem("EventTour") === doneKeyTutorial) return;
    tutorial
      .setOptions({
        showBullets: false,
        showProgress: true,
        tooltipClass: "tutorial-style",
        exitOnOverlayClick: false,
        exitOnEsc: false,
      })
      .start();

    tutorial.oncomplete(function () {
      localStorage.setItem("EventTour", doneKeyTutorial);
    });

    tutorial.onexit(function () {
      localStorage.setItem("EventTour", doneKeyTutorial);
    });
  });
};

// contact information change listeners
let initContactInfoChangeAlerts = function () {
  $("#new-email").submit(function (e) {
    alert(
      `Email address successfully changed to ${$("#new-email-input").val()}!`
    );
  });

  $("#new-phone").submit(function (e) {
    let newPhone = $("#new-phone-input").val();
    if (newPhone)
      alert(
        `Phone number successfully changed to ${$("#new-phone-input").val()}!`
      );
    else alert("Phone number successfully removed!");
  });

  let curr_email = $("#new-email-input").val();
  let curr_phone = $("#new-phone-input").val();

  $("#new-email-input").on("input", function (e) {
    if ($("#new-email-input").val() == curr_email) {
      $(this).next("button").attr("disabled", true);
      return;
    }
    $(this).next("button").attr("disabled", false);
  });

  $("#new-phone-input").on("input", function (e) {
    if ($("#new-phone-input").val() == curr_phone) {
      $(this).next("button").attr("disabled", true);
      return;
    }
    $(this).next("button").attr("disabled", false);
  });
};

// listens for account settings button and the account settings alert banner
let accountSettings = function () {
  $("#account-settings").submit(function (e) {
    e.preventDefault();
    $("#account-settings-modal").modal("show");
  });

  if (localStorage.getItem("NewFeaturesAlert") !== doneKeyBanner)
    $("#new-features-alert").removeClass("d-none");

  $("#new-features-alert-close").click(function (e) {
    localStorage.setItem("NewFeaturesAlert", doneKeyBanner);
  });
};

// handles functions that optimizes mobile view
let mobileViewFunctions = function () {
  dashboardSkip();
  searchSkip();
  navbarAutoclose();
};

// handles features on the admin panel
let adminFunctions = function () {
  blockUserListener();
  clearAllWaitlistsListener();
  clearAllLogsListener();
  clearClassWaitlistListener();
  clearCourseWaitlistListener();
  disableCourseListener();
  enableCourseListener();
  getUsageSummaryListener();
  getAllSubscriptionsListener();
  getUserDataListener();
  getUserInfoListener();
  initToggleEmailNotificationsButton();
  toggleEmailNotificationsListener();
  fillSectionListener();
};

// handles course search functions
let searchFunctions = function () {
  searchFormListener();
  searchResultListener();
};

// handles changes in course subscription
let subscriptionFunctions = function () {
  switchListener();
  modalConfirmListener();
  modalCancelListener();
};

// handles changes in account settings
let accountSettingsFunctions = function () {
  autoResubSwitchListener();
  initContactInfoChangeAlerts();
  accountSettings();
};

// jQuery 'on' only applies listeners to elements currently on DOM
// applies listeners to current elements when document is loaded
$(document).ready(function () {
  mobileViewFunctions();
  adminFunctions();
  searchFunctions();
  subscriptionFunctions();
  showAllListener();
  pageBackListener();
  initTooltipsToasts();
  initTutorial();
  accountSettingsFunctions();
});

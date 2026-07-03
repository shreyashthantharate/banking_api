frappe.listview_settings["Share Application"] = {
    refresh(listview) {
        hide_share_application_sidebar(listview);

        if (!listview.page.__share_report_button_added) {
            listview.page.__share_report_button_added = true;

            listview.page.add_inner_button(__("Download Report"), () => {
                const d = new frappe.ui.Dialog({
                    title: __("Download Share Application Report"),
                    fields: [
                        {
                            fieldname: "report_type",
                            label: __("Report Type"),
                            fieldtype: "Select",
                            options: [
                                "Success Report",
                                "Failed Report",
                                "Pending Report",
                                "Consolidated Report"
                            ].join("\n"),
                            reqd: 1
                        }
                    ],
                    primary_action_label: __("Download"),
                    primary_action(values) {
                        const report_map = {
                            "Success Report": "success",
                            "Failed Report": "failed",
                            "Pending Report": "pending",
                            "Consolidated Report": "consolidated"
                        };

                        const report_type = report_map[values.report_type];

                        if (!report_type) {
                            frappe.msgprint(__("Please select a valid report type."));
                            return;
                        }

                        window.open(
                            `/api/method/banking_api.banking_api.doctype.share_application.share_application.download_share_application_report?report_type=${report_type}`,
                            "_blank"
                        );

                        d.hide();
                    }
                });

                d.show();
            });
        }

        render_status_capsules(listview);
        setup_live_status_refresh(listview);

        setTimeout(() => {
            fix_share_application_header_layout(listview);
        }, 50);
    }
};

function render_status_capsules(listview) {
    const $custom_actions = listview.page.wrapper.find(".page-actions .custom-actions");

    if (!$custom_actions.length) return;

    if (!listview.page.$status_capsules) {
        listview.page.$status_capsules = $(`
            <div class="share-status-wrap" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                margin-right: 12px;
                flex: 0 0 auto;
                white-space: nowrap;
            ">

                <div class="share-status-capsules" style="
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    flex-wrap: nowrap;
                    white-space: nowrap;
                    flex: 0 0 auto;
                ">
                    <button type="button" class="share-capsule success" data-status="Success" style="
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        background: #ecfdf3;
                        color: #067647;
                        border: 1px solid #abefc6;
                        padding: 4px 10px;
                        border-radius: 999px;
                        font-size: 12px;
                        font-weight: 600;
                        line-height: 1.3;
                        white-space: nowrap;
                        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
                        cursor: pointer;
                    ">Success: 0</button>

                    <button type="button" class="share-capsule pending" data-status="Pending" style="
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        background: #fffaeb;
                        color: #b54708;
                        border: 1px solid #fedf89;
                        padding: 4px 10px;
                        border-radius: 999px;
                        font-size: 12px;
                        font-weight: 600;
                        line-height: 1.3;
                        white-space: nowrap;
                        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
                        cursor: pointer;
                    ">Pending: 0</button>

                    <button type="button" class="share-capsule failed" data-status="Failed" style="
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        background: #fef3f2;
                        color: #b42318;
                        border: 1px solid #fecdca;
                        padding: 4px 10px;
                        border-radius: 999px;
                        font-size: 12px;
                        font-weight: 600;
                        line-height: 1.3;
                        white-space: nowrap;
                        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
                        cursor: pointer;
                    ">Failed: 0</button>
                </div>
            </div>
        `);

        $custom_actions.prepend(listview.page.$status_capsules);
        bind_capsule_click_events(listview);
    }

    fetch_status_counts(listview);
}

function bind_capsule_click_events(listview) {
    listview.page.$status_capsules.find(".share-capsule").off("click").on("click", function () {
        const status = $(this).attr("data-status");
        apply_payment_status_filter(listview, status);
    });
}

function apply_payment_status_filter(listview, status) {
    if (!status) return;

    const doctype = "Share Application";
    const fieldname = "payment_status";
    const filter_area = listview.filter_area;
    const filter_list = filter_area && filter_area.filter_list;
    const page_field =
        listview.page &&
        listview.page.fields_dict &&
        listview.page.fields_dict[fieldname];

    try {
        if (filter_list && typeof filter_list.clear_filters === "function") {
            filter_list.clear_filters();
        }

        if (filter_list && typeof filter_list.add_filter === "function") {
            filter_list.add_filter(doctype, fieldname, "=", status);
        }

        if (page_field && typeof page_field.set_value === "function") {
            page_field.set_value(status);
        }

        if (filter_list && typeof filter_list.on_change === "function") {
            filter_list.on_change();
        } else if (listview && typeof listview.refresh === "function") {
            listview.refresh();
        }
    } catch (e) {
        console.error("Error while applying payment_status filter:", e);
    }
}

function fetch_status_counts(listview) {
    if (!listview.page.$status_capsules) return;

    frappe.call({
        method: "banking_api.banking_api.doctype.share_application.share_application.get_share_application_status_counts",
        callback(r) {
            if (!r.message) return;

            const counts = r.message;

            listview.page.$status_capsules.find(".success").text(`Success: ${counts.Success || 0}`);
            listview.page.$status_capsules.find(".pending").text(`Pending: ${counts.Pending || 0}`);
            listview.page.$status_capsules.find(".failed").text(`Failed: ${counts.Failed || 0}`);

            fix_share_application_header_layout(listview);
        }
    });
}

function setup_live_status_refresh(listview) {
    if (listview.page.__share_status_interval) {
        clearInterval(listview.page.__share_status_interval);
    }

    listview.page.__share_status_interval = setInterval(() => {
        if (
            listview.page &&
            listview.page.wrapper &&
            listview.page.wrapper.is(":visible")
        ) {
            fetch_status_counts(listview);
        }
    }, 15000);
}

function fix_share_application_header_layout(listview) {
    const $wrapper = listview.page.wrapper;

    $wrapper.find(".page-head-content").css({
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "nowrap"
    });

    $wrapper.find(".page-title").css({
        flex: "0 1 auto",
        minWidth: "0"
    });

    $wrapper.find(".page-actions").css({
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        flexWrap: "nowrap",
        whiteSpace: "nowrap",
        gap: "8px"
    });

    $wrapper.find(".page-actions .custom-actions").css({
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "flex-start",
        flexWrap: "nowrap",
        whiteSpace: "nowrap",
        gap: "10px",
        marginBottom: "0",
        flex: "0 0 auto"
    });

    $wrapper.find(".page-actions .standard-actions").css({
        display: "inline-flex",
        alignItems: "center",
        flexWrap: "nowrap",
        whiteSpace: "nowrap",
        flex: "0 0 auto"
    });

    $wrapper.find(".share-status-wrap").css({
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "flex-start",
        gap: "8px",
        flexWrap: "nowrap",
        whiteSpace: "nowrap",
        marginRight: "12px",
        flex: "0 0 auto"
    });

    $wrapper.find(".share-status-capsules").css({
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "flex-start",
        flexWrap: "nowrap",
        whiteSpace: "nowrap",
        gap: "6px",
        flex: "0 0 auto"
    });
}

function hide_share_application_sidebar(listview) {
    const $wrapper = listview.page.wrapper;
    const $side_section = $wrapper.find(".layout-side-section");
    const $main_section = $wrapper.find(".layout-main-section");

    if ($side_section.length) {
        $side_section.hide();
    }

    if ($main_section.length) {
        $main_section.removeClass("col-lg-10 col-md-10");
        $main_section.addClass("col-lg-12 col-md-12");
        $main_section.css({
            width: "100%",
            maxWidth: "100%",
            flex: "0 0 100%"
        });
    }

    $wrapper.find(".layout-main").css({
        width: "100%"
    });

    $wrapper.find(".list-row-container, .result, .frappe-list").css({
        width: "100%",
        maxWidth: "100%"
    });

    $wrapper.find(".sidebar-toggle-btn").hide();
}
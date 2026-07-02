frappe.listview_settings["Share Application"] = {
    refresh(listview) {
        console.log("Share Application list js loaded");

        if (listview.page.__share_report_button_added) return;
        listview.page.__share_report_button_added = true;

        listview.page.add_inner_button(__("Download Report"), () => {
            let d = new frappe.ui.Dialog({
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
};
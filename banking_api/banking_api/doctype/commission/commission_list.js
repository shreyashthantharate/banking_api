// frappe.listview_settings["Commission"] = {
//     onload(listview) {
//         listview.page.add_inner_button(__("Fetch Commission Data"), () => {
//             frappe.confirm(
//                 __("This will fetch commission records and create Commission documents. Do you want to continue?"),
//                 () => {
//                     frappe.call({
//                         method: "banking_api.banking_api.doctype.commission.commission.fetch_and_create_commission",
//                         freeze: true,
//                         freeze_message: __("Fetching commission data..."),
//                         callback: function (r) {
//                             if (r.message) {
//                                 frappe.msgprint({
//                                     title: __("Commission Fetch Result"),
//                                     indicator: r.message.error_count ? "orange" : "green",
//                                     message: `
// 										<div>
// 											<p><b>Status:</b> ${r.message.status || "Completed"}</p>
// 											<p><b>Query 1 Rows:</b> ${r.message.query_1_count || 0}</p>
// 											<p><b>Query 2 Rows:</b> ${r.message.query_2_count || 0}</p>
// 											<p><b>Inserted Docs:</b> ${r.message.inserted_count || 0}</p>
// 											<p><b>Errors:</b> ${r.message.error_count || 0}</p>
// 										</div>
// 									`
//                                 });
//                                 listview.refresh();
//                             }
//                         }
//                     });
//                 }
//             );
//         });
//     }
// };



frappe.listview_settings["Commission"] = {
    onload(listview) {
        // Row-level button example (optional – you can remove this whole block if not needed)
        // button: { ... } is shown here only as reference from your Share Application code.

    },

    refresh(listview) {
        // Avoid adding twice on refresh
        if (listview.page.__commission_actions_added) return;
        listview.page.__commission_actions_added = true;

        const action_label = __("Actions");

        // 1) Fetch Commission Data (under Actions)
        listview.page.add_inner_button(__("Fetch Commission Data"), () => {
            frappe.confirm(
                __("This will fetch commission records and create Commission documents. Do you want to continue?"),
                () => {
                    frappe.call({
                        method: "banking_api.banking_api.doctype.commission.commission.fetch_and_create_commission",
                        freeze: true,
                        freeze_message: __("Fetching commission data..."),
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint({
                                    title: __("Commission Fetch Result"),
                                    indicator: r.message.error_count ? "orange" : "green",
                                    message: `
                                        <div>
                                            <p><b>Status:</b> ${r.message.status || "Completed"}</p>
                                            <p><b>Query 1 Rows:</b> ${r.message.query_1_count || 0}</p>
                                            <p><b>Query 2 Rows:</b> ${r.message.query_2_count || 0}</p>
                                            <p><b>Inserted Docs:</b> ${r.message.inserted_count || 0}</p>
                                            <p><b>Errors:</b> ${r.message.error_count || 0}</p>
                                        </div>
                                    `,
                                });
                                listview.refresh();
                            }
                        },
                    });
                }
            );
        }, action_label);

        // 2) Calculate Commission (All Records) (under Actions)
        listview.page.add_inner_button(__("Calculate Commission (All Records)"), () => {
            frappe.confirm(
                __(
                    "This will calculate commission on ALL Commission documents. " +
                    "This may take some time. Do you want to continue?"
                ),
                () => {
                    frappe.call({
                        method: "banking_api.banking_api.doctype.commission.commission.calculate_commission_for_all",
                        freeze: true,
                        freeze_message: __("Calculating commission on all records..."),
                        callback: function (r) {
                            if (r.message) {
                                const data = r.message;
                                frappe.msgprint({
                                    title: __("Commission Calculation Result"),
                                    indicator: data.error_count ? "orange" : "green",
                                    message: `
                                        <div>
                                            <p><b>Status:</b> ${data.status || "Completed"}</p>
                                            <p><b>Total Processed:</b> ${data.total_processed || 0}</p>
                                            <p><b>Successful:</b> ${data.success_count || 0}</p>
                                            <p><b>Errors:</b> ${data.error_count || 0}</p>
                                        </div>
                                    `,
                                });
                                listview.refresh();
                            }
                        },
                    });
                }
            );
        }, action_label);

        listview.page.add_inner_button(__("Commission Dashboard (View Only)"), () => {
            window.open("http://shreyash.com:8000/commission", "_blank");
        }, action_label);
        listview.page.add_inner_button(__("Commission Reports"), () => {
            window.open("http://shreyash.com:8000/commission-report", "_blank");
        }, action_label);
    },
};



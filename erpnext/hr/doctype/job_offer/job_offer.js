
frappe.ui.form.on("Job Offer", {
    setup: function(frm) {
        frm.set_query("terms_and_conditions", function() {
            return {
                filters: {
                    hr: 1
                }
            };
        });
    },

	applicant_id: function(frm) {
        if (frm.doc.temp_applied_on) {
            frm.set_query('job_opening_id', function(doc) {
                return {
                        filters: {
                            "name": frm.doc.temp_applied_on
                        }
                    };
            });
        }
    }
});

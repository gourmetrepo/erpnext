
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

    onload: (frm) => {
        frm.set_query('applicant_id', () => {
			return {
				filters: {
					job_applicant_status: "Accepted"
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
    },

    terms_and_conditions: function(frm) {
        if (frm.doc.terms_and_conditions) {
            frappe.db.get_value('Terms and Conditions', {'name': frm.doc.terms_and_conditions}, 'terms', (r) => {
                if (r && r.terms) {
                    frm.set_value('terms_and_conditions_text', r.terms);
                }
            });
        }
    }
});

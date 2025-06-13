
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
    },
    select_job_offer_template: function(frm) {
        if (frm.doc.select_job_offer_template) {
            frm.clear_table(frm.doc.offer_terms);
            frm.refresh_field(frm.doc.offer_terms);
            
            return frappe.call({
                method: "erpnext.hr.doctype.job_offer.job_offer.apply_offer_term_template",
                args: {
                    job_offer: frm.doc.name,
                    template_name: frm.doc.select_job_offer_template,
                },
                    
                callback: function(r) {
                    if (r.message.status === "success") {
                        frm.reload_doc();
                    } else {
                        frappe.msgprint("Error: " + r.message.message);
                    }
                }
            });
        }
    },
});

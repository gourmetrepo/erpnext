
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
        if (frm.doc.applicant_id) {
            frappe.db.get_value('Job Applicant', frm.doc.applicant_id, ['first_name', 'middle_name', 'last_name', 'email', 'position_title'], (r) => {
                let full_name = [r.first_name, r.middle_name, r.last_name]
                            .filter(Boolean).join(' ');
                if (r) {
                    frm.set_value('full_name', full_name);
                    frm.set_value('position_title', r.position_title);
                }
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
        if (!frm.doc.select_job_offer_template) return;

        frappe.db.get_doc("Job Offer Term Template", frm.doc.select_job_offer_template)
            .then(template => {
                frm.clear_table("offer_terms");
                (template.terms || []).forEach(row => {

                    let child = frm.add_child("offer_terms", {
                        offer_term: row.offer_term,
                        value_description: row.description
                    });
                });

                frm.refresh_field("offer_terms");
            })
            .catch(err => {
                frappe.msgprint("Could not fetch template: " + err.message);
            });    
    },
});

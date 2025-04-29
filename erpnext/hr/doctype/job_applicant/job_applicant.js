
frappe.ui.form.on("Job Applicant", {
	setup: function(frm) {
		frm.fields_dict['core_skills'].grid.get_field('skill').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    'type': 'Functional'
                }
            };
        };

		frm.fields_dict['behavioral_competencies'].grid.get_field('skill').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    'type': 'Behavioral'
                }
            };
        };
	},	

	refresh: function(frm) {
		frappe.require("assets/nerp/js/jquery.maskedinput.min.js", () => {
            $.mask.definitions['3'] = null;
            $('input[data-fieldname="cnic"]').mask(frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9'),{autoclear: false});
            $('input[data-fieldname="contact"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
        });	
	},

    before_save: function(frm){
		validate_email(frm.doc.email);
		validate_contact_number(frm.doc.contact);

		frm.doc.references.forEach(reference => {
			validate_email(reference.reference_email, "References");
			validate_contact_number(reference.reference_contact, "References");
		});

		if (!frm.doc.truthful_information) {
			frappe.throw(__("Mandatory fields required - I confirm that the information provided is accurate and truthful."));
		}
		
		if (!frm.doc.personal_data_consent){
			frappe.throw(__("Mandatory fields required - I consent to the processing of my personal data for recruitment purposes in accordance with applicable data protection laws."));
		}

		var age = frappe.utils.get_age(frm.doc.date_of_birth);
        var allowed_age = frappe.utils.get_config_by_name("EMPLOYEE_ALLOWED_AGE", 18);
        if( age < allowed_age ) {
            frappe.throw("Applicant is underage.");
        }
	},

	first_name: function(frm){
		update_full_name(frm);
	},

	middle_name: function(frm){
		update_full_name(frm);
	},

	last_name: function(frm){
		update_full_name(frm);
	},

    nationality: function(frm) {
		if (frm.doc.nationality == 'Pakistan') {
			frm.set_df_property("cnic", "reqd", 1);
			frm.set_df_property("place_of_issue", "reqd", 1);
			frm.set_df_property("issue_date", "reqd", 1);
			frm.set_df_property("valid_upto", "reqd", 1);
			frm.set_df_property("passport", "reqd", 0);
			frm.set_df_property("passport_place_of_issue", "reqd", 0);
			frm.set_df_property("passport_issue_date", "reqd", 0);
			frm.set_df_property("passport_valid_upto", "reqd", 0);
		} else {
			frm.set_df_property("cnic", "reqd", 0);
			frm.set_df_property("place_of_issue", "reqd", 0);
			frm.set_df_property("issue_date", "reqd", 0);
			frm.set_df_property("valid_upto", "reqd", 0);
			frm.set_df_property("passport", "reqd", 1);
			frm.set_df_property("passport_place_of_issue", "reqd", 1);
			frm.set_df_property("passport_issue_date", "reqd", 1);
			frm.set_df_property("passport_valid_upto", "reqd", 1);
		}
	},
});


function update_full_name(frm){
	let fullName = "";

	if (frm.doc.first_name){
		fullName += frm.doc.first_name;
	}
	if (frm.doc.middle_name){
		fullName += " " + frm.doc.middle_name;
	}
	if (frm.doc.last_name){
		fullName += " " + frm.doc.last_name;
	}
	frm.set_value("full_name", fullName);
}

function validate_email(email_address, formPart="") {
    const validEmail = frappe.utils.validate_type(email_address, "email");
    if (!validEmail) {
		const msg = `in ${formPart}`;
        frappe.throw(__(`Please enter valid email address ${msg}`));
    }
}

function validate_contact_number(contact_number, formPart="") {
	const phoneRegex = /^03[0-9]{2}-[0-9]{7}$/;
    const isValid = phoneRegex.test(contact_number);
	if (!isValid) {
		const msg = `in ${formPart}`;
		frappe.throw(__(`Please enter valid contact number ${msg}`));
	}
}

frappe.ui.form.on('Job Applicant Education', {
	education_title: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.education_title) {
			frappe.meta.get_docfield("Job Applicant Education", "type", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Education", "specialization", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Education", "institute", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Education", "start_date", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).reqd = 1;
		}

		frm.refresh_field("education");
	},

    currently_enrolled: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.currently_enrolled) {
            frappe.model.set_value(cdt, cdn, 'completion_date', null); // optional: clear value
            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).hidden = 1;
            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).reqd = 0;
        } else {
            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).hidden = 0;
            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).reqd = 1;
        }

        frm.refresh_field("education");
    }
});


frappe.ui.form.on('Job Applicant Work Experience', {
	job_title: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.job_title) {
			frappe.meta.get_docfield("Job Applicant Work Experience", "company_name", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "location", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "joining_date", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "responsibilities_and_achievements", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "last_drawn_salary", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "perks_and_benifits", frm.doc.name).reqd = 1;
		}

		frm.refresh_field("work_experience");
	},

    currently_employed: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.currently_employed) {
            frappe.model.set_value(cdt, cdn, 'end_date', null); // optional: clear value
            frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).hidden = 1;
			frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).reqd = 0;
        } else {
            frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).hidden = 0;
			frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).reqd = 1;
        }

        frm.refresh_field("work_experience");
    }
});

frappe.ui.form.on('Job Applicant References', {
	reference_full_name: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.reference_full_name) {
			frappe.meta.get_docfield("Job Applicant References", "relationship", frm.doc.name).reqd = 1;
			frappe.meta.get_docfield("Job Applicant References", "reference_contact", frm.doc.name).reqd = 1;
		}

		frm.refresh_field("references");
	}
});
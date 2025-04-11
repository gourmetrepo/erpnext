
frappe.ui.form.on("Job Applicant", {
	
	refresh: function(frm) {
		frappe.require("assets/nerp/js/jquery.maskedinput.min.js", () => {
            $.mask.definitions['3'] = null;
            $('input[data-fieldname="cnic"]').mask(frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9'),{autoclear: false});
            $('input[data-fieldname="contact"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
        });	
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


frappe.ui.form.on('Job Applicant Education', {
    currently_enrolled: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.currently_enrolled) {
            frappe.model.set_value(cdt, cdn, 'completion_date', null); // optional: clear value

            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).hidden = 1;
        } else {
            frappe.meta.get_docfield("Job Applicant Education", "completion_date", frm.doc.name).hidden = 0;
        }

        frm.refresh_field("education");
    }
});


frappe.ui.form.on('Job Applicant Work Experience', {
    currently_employed: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.currently_employed) {
            frappe.model.set_value(cdt, cdn, 'end_date', null); // optional: clear value

            frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).hidden = 1;
        } else {
            frappe.meta.get_docfield("Job Applicant Work Experience", "end_date", frm.doc.name).hidden = 0;
        }

        frm.refresh_field("work_experience");
    }
});

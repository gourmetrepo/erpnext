// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Designation', {
	grade: function (frm) {
        if (frm.doc.grade) {
            frappe.db.get_value('Employee Grade', frm.doc.grade, 'cadre')
                .then(r => {
                    if (r && r.message) {
                        frm.set_value('internal_designation', r.message.cadre);
                    }
                });
        }
    }
});

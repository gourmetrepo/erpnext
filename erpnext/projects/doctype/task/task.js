// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Task", {
	setup: function (frm) {
		frm.set_query("project", function () {
			return {
				query: "erpnext.projects.doctype.task.task.get_project"
			}
		});

		frm.make_methods = {
			'Timesheet': () => frappe.model.open_mapped_doc({
				method: 'erpnext.projects.doctype.task.task.make_timesheet',
				frm: frm
			})
		}

		frm.set_query("parent_task", function() {
			return {
				filters: {
					"is_group": 1,
					"project": frm.doc.project
				}
			}
		});
	},

	onload: function (frm) {
		frm.set_query("task", "depends_on", function () {
			let filters = {
				name: ["!=", frm.doc.name]
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			};
		})

		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				filters: { user_id: frappe.session.user_email },
				fieldname: ["company", "designation"]
			},
			callback: function(r) {
				if (r.message) {
					if (r.message.company) {
						frm.set_query("project", function () {
							return {
								filters: {
									company: r.message.company
								}
							};
						})
					}


					if (r.message.designation) {
						const designation = r.message.designation;
						const allowedDesignations = ['Plant Engineer', 'Maintenance Engineer', 
											'Machine Supervisor', 'Manager Production', 
											'Manager Engineering', 'Asst. Manager Engineering'];
						if (allowedDesignations.includes(designation) && (frm.doc.progress == 100)) {
							frm.add_custom_button("Reopen", function() {
								frm.set_value("status", "Open");
								frm.set_value("progress", 0);
								frm.save();
							})
						}
					}
				}
			}
		});
	},

	is_group: function (frm) {
		frappe.call({
			method: "erpnext.projects.doctype.task.task.check_if_child_exists",
			args: {
				name: frm.doc.name
			},
			callback: function (r) {
				if (r.message.length > 0) {
					frappe.msgprint(__(`Cannot convert it to non-group. The following child Tasks exist: ${r.message.join(", ")}.`));
					frm.reload_doc();
				}
			}
		})
	},

	validate: function (frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project",
			frm.doc.project);
	}
});

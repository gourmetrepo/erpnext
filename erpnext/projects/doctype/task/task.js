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
		frm.fields_dict["assigned_users"].get_query = function() {
            return {

                query: "erpnext.projects.doctype.task.task.get_assigned_team_users"
            };
        };
		
	},

	refresh: function (frm) {
		frm.fields_dict["assigned_users"].grid.get_field("assigned_users").format_input = function(value, data) {
            return data ? `${data.team_member} - ${data.full_name}` : value;
        };
		if (!frm.is_new()) {
			frm.set_df_property("exp_start_date", "read_only", 1);
			frm.set_df_property("exp_end_date", "read_only", 1);

			frm.add_custom_button(__('Change Timeline'), () => {
				let change_timeline_dialogue = new frappe.ui.Dialog({
					title: 'Change Timeline',
					fields: [
						{
							label: 'Expected Start Date',
							fieldname: 'expected_start_date_dialogue',
							fieldtype: 'Date'
						},
						{
							label: 'Expected End Date',
							fieldname: 'expected_end_date_dialogue',
							fieldtype: 'Date'
						},
						{
							label: 'Reason for Timeline Change',
							fieldname: 'reason_timeline_change',
							fieldtype: 'Text'
						}
					],
					size: 'large', 
					primary_action_label: 'Submit',
					primary_action(values) {
						if (!values.reason_timeline_change) {
							frappe.msgprint(__("Please provide a reason for timeline change"), "Error");
							return;
						}
						if (!values.expected_start_date_dialogue && !values.expected_end_date_dialogue) {
							frappe.msgprint(__("No change in Dates"), "Error");
							return;
						}

						let comment_text = "<div>";
						if (values.expected_start_date_dialogue) {
							frm.doc.exp_start_date = values.expected_start_date_dialogue;
							comment_text += "<p>Expected Start Date changed to " + values.expected_start_date_dialogue + "</p>"
						}
						if (values.expected_end_date_dialogue) {
							frm.doc.exp_end_date = values.expected_end_date_dialogue;
							comment_text += "<p>Expected End Date changed to " + values.expected_end_date_dialogue + "</p>"
						}
						comment_text += "<p>Reason: " + values.reason_timeline_change + "</p></div>"

						frappe.call({
							method: "frappe.desk.form.utils.add_comment",
							args: {
								reference_doctype: frm.doc.doctype,
								reference_name: frm.doc.name,
								content: comment_text,
								comment_email: frappe.session.user
							},
							callback: function(r) {
								if(!r.exc) {
									frm.save();
									change_timeline_dialogue.hide();
								}
							}
						});
					}
				});
				change_timeline_dialogue.set_value('expected_start_date_dialogue', frm.doc.exp_start_date);
				change_timeline_dialogue.set_value('expected_end_date_dialogue', frm.doc.exp_end_date);
				change_timeline_dialogue.show();
			});
		}
		setup_assigned_team_users(frm);
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

					if (r.message.company) {
						frm.set_query("project", function () {
							return {
								filters: {
									company: r.message.company
								}
							};
						})
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



function setup_assigned_team_users(frm) {
    frm.fields_dict['assigned_users'].get_query = function() {
        return {
            query: "erpnext.projects.doctype.task.task.get_assigned_team_users"
        };
    };
}

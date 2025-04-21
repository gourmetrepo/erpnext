// Copyright (c) 2025, Shahzad Naser and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Opening', {
	job_requisition_id: (frm) => {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Job Requisition",
				name: frm.doc.job_requisition_id
			},
			callback: function (r) {
				frm.set_value("required_to_work_in_shifts", r.message.required_to_work_in_shifts);
				frm.refresh_field("required_to_work_in_shifts");
				frm.set_value("required_to_travel", r.message.required_to_travel);
				frm.refresh_field("required_to_travel");
			}
		});
	},

	position: (frm) => {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Position",
				name: frm.doc.position
			},
			callback: function (r) {
				frm.set_value("required_background_check", r.message.required_background_check);
				frm.refresh_field("required_background_check");

				frm.clear_table("required_core_skills");
				frm.clear_table("required_behavioral_competencies");

				r.message.required_core_skills.forEach(element => {
					debugger;
					let temp_skill = element.skill;
					let temp_proficiency = element.required_proficiency_level;

					frm.add_child('required_core_skills', {
						skill: temp_skill,
						required_proficiency_level: temp_proficiency,
					})
				})

				r.message.required_behavioral_competencies.forEach(element => {
					let temp_skill = element.skill;
					let temp_proficiency = element.required_proficiency_level;

					frm.add_child('required_behavioral_competencies', {
						skill: temp_skill,
						required_proficiency_level: temp_proficiency,
					})
				});

				frm.refresh_field('required_core_skills');
				frm.refresh_field('required_behavioral_competencies');
			}
		});
	}
});

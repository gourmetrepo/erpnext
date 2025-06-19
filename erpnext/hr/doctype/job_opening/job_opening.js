// Copyright (c) 2025, Shahzad Naser and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Opening', {
	onload: (frm) => {
		frm.set_query('job_requisition_id', () => {
			return {
				filters: {
					job_requisition_status: "Open & Approved"
				}
			};
		});

		frm.fields_dict.job_requisition_id.get_data = function(txt) {
            return frappe.db.get_list('Job Requisition', {
                fields: ['name', 'designation'],
                filters: {
                    job_requisition_status: 'Open & Approved',
                    name: ['like', `%${txt}%`]
                },
                limit: 10
            }).then(results => {
                return results.map(d => ({
                    value: d.name,
                    description: d.designation || ''
                }));
            });
        };
	},

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

				frm.clear_table("required_education");
				frm.clear_table("required_core_competencies");
				frm.clear_table("required_behavioral_competencies");

				r.message.required_education.forEach(element => {
					let education_title = element.education_title;
					let type = element.type;
					let specialization = element.specialization;

					frm.add_child('required_education', {
						education_title: education_title,
						type: type,
						specialization: specialization,
					})
				});

				r.message.required_core_competencies.forEach(element => {
					let temp_skill = element.competencies;
					let type = element.type;
					let temp_proficiency = element.proficiency_level;

					frm.add_child('required_core_competencies', {
						competencies: temp_skill,
						type: type,
						proficiency_level: temp_proficiency,
					})
				})

				r.message.required_behavioral_competencies.forEach(element => {
					let temp_skill = element.competencies;
					let type = element.type;
					let temp_proficiency = element.proficiency_level;

					frm.add_child('required_behavioral_competencies', {
						competencies: temp_skill,
						type: type,
						proficiency_level: temp_proficiency,
					})
				});

				frm.set_value("main_responsibilities", r.message.main_responsibilities);
				frm.refresh_field("main_responsibilities");

				frm.refresh_field('required_education');
				frm.refresh_field('required_core_competencies');
				frm.refresh_field('required_behavioral_competencies');
			}
		});
	}
});

frappe.listview_settings['Salary Structure Assignment'] = {

	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				// "employee_name":frappe.session.user_fullname,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -30),frappe.datetime.get_today()]]
			};
		}
		me.page.add_inner_button(__('Download Template'), function() {
            const filePath = "/assets/erpnext/csv/Salary_Structure_Assignment.csv";
            const baseUrl = window.location.origin;
            const fileUrl = baseUrl + filePath;
            window.open(fileUrl, '_blank');
        });
        me.page.add_inner_button(__('Import Data'), function() {
            new frappe.ui.FileUploader({
                allow_multiple: false,
                on_success: function(file) {
                    frappe.call({
                        method: 'nerp.modules.gourmet.salary_structure_assignment.salary_structure_assignment.create_ssa_doc_from_import',
                        args: {
                            file_url: file.file_url
                        },
                        freeze: true,
			            freeze_message: `<img src="/assets/erpnext/images/output-onlinegiftools.gif" style="width: 150px; height: 150px;" />`,
                        callback: function(response) {
                            if (response.message.success){
                                frappe.msgprint(__(response.message.success));
                            }
                            else{
                                frappe.msgprint(__(response.message.error));
                            }
                        }
                    });
                }
            });
        });
	}
};
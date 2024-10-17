frappe.listview_settings['Additional Salary'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Import Data'), function() {
            new frappe.ui.FileUploader({
                allow_multiple: false,
                on_success: function(file) {
                    frappe.call({
                        method: 'nerp.modules.gourmet.additional_salary.additional_salary.create_doc_from_import',
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

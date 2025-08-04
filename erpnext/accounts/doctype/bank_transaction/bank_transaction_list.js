// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Bank Transaction'] = {
	onload: function(listview) {
        listview.page.add_inner_button(__('Download Template'), function() {
            const filePath = "/assets/erpnext/csv/Bank Transaction.csv";
            const baseUrl = window.location.origin;
            const fileUrl = baseUrl + filePath;
            window.open(fileUrl, '_blank');
        });
        listview.page.add_inner_button(__('Import Data'), function() {
            new frappe.ui.FileUploader({
                allow_multiple: false,
                on_success: function(file) {
                    frappe.call({
                        method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction.create_doc_from_import',
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
    },
	add_fields: ["unallocated_amount"],
	get_indicator: function(doc) {
		if(flt(doc.unallocated_amount)>0) {
			return [__("Unreconciled"), "orange", "unallocated_amount,>,0"];
		} else if(flt(doc.unallocated_amount)<=0) {
			return [__("Reconciled"), "green", "unallocated_amount,=,0"];
		}
	}
};
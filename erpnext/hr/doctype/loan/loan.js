// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/hr/loan_common.js' %};

frappe.ui.form.on('Loan', {
	onload: function (frm) {
		frm.set_query("loan_application", function () {
			return {
				"filters": {
					"applicant": frm.doc.applicant,
					"docstatus": 1,
					"status": "Approved"
				}
			};
		});

		frm.set_query("interest_income_account", function () {
			return {
				"filters": {
					"company": frm.doc.company,
					"root_type": "Income",
					"is_group": 0
				}
			};
		});

		$.each(["payment_account", "loan_account"], function (i, field) {
			frm.set_query(field, function () {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": "Asset",
						"is_group": 0
					}
				};
			});
		})
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.doc.status == "Sanctioned") {
				frm.add_custom_button(__('Create Disbursement Entry'), function() {
					frm.trigger("make_jv");
				}).addClass("btn-primary");
			} else if (frm.doc.status == "Disbursed" && frm.doc.repayment_start_date && (frm.doc.applicant_type == 'Member' || frm.doc.repay_from_salary == 0)) {
				frm.add_custom_button(__('Create Repayment Entry'), function() {
					frm.trigger("make_repayment_entry");
				}).addClass("btn-primary");
			}
		}
		frm.trigger("toggle_fields");
	},
	posting_date: function(frm){
		frm.trigger("calculate_salary_fields");
        frm.trigger("toggle_fields");
	},
	applicant: function(frm){
        frm.trigger("calculate_salary_fields");
        frm.trigger("toggle_fields");
        if (frm.doc.applicant) {
			frappe.model.with_doc(frm.doc.applicant_type, frm.doc.applicant, function() {
				var applicant = frappe.model.get_doc(frm.doc.applicant_type, frm.doc.applicant);
				frm.set_value("company",applicant.company);
			});
		}
		else {
			frm.set_value("company", null);
		}
		frm.trigger("loan_type");
    },
	loan_type: function(frm){
		frm.trigger("calculate_salary_fields");
		frm.trigger("validate_loan_amount");
        frm.trigger("toggle_fields");
        frm.set_value("loan_account", "");
        frm.set_value("interest_income_account", "");
		if(frm.doc.loan_type){
		    frappe.call({
                method: "nerp.modules.gourmet.loan.loan.get_loan_type",
                args:
                    {   
                        'company':      frm.doc.company,
                        'loan_type':    frm.doc.loan_type
                    },
                callback: function(r){
                    if(r.message){
                        var data = r.message;
                        
                        if(data){
        					frm.set_query("loan_account", function () {
        						return {
        							"filters": {
        								"name": data.loan_account,
        								"company": frm.doc.company
        							}
        						};
        					});
        					frm.set_query("interest_income_account", function () {
        						return {
        							"filters": {
        								"name": data.interest_account,
        								"company": frm.doc.company
        							}
        						};
        					});
        					
        					if(data.loan_account){
        					    frm.set_value("loan_account", data.loan_account);
        					    }
        					
        					if(data.interest_account){
        					    frm.set_value("interest_income_account", data.interest_account);
        					    }
				        }
                    }
                }
		    });

		}
		frm.refresh_field('loan_account');
		frm.refresh_field('interest_income_account');
    },
	loan_amount: function(frm){
	    frm.trigger("validate_loan_amount");
	},
	calculate_salary_fields: function(frm){
		frappe.call({
			method: 'nerp.modules.gourmet.loan.loan.get_emp_salary_and_work_details',
			args: {
                loan: cur_frm.doc,
            },
			callback: function(r) {
			    frm.set_value('present_days', r.message.loan.present_days);
			    frm.set_value('current_salary', r.message.loan.current_salary);
			    frm.set_value('earned_salary', r.message.loan.earned_salary);
			    frm.set_value('repayment_periods', r.message.loan.repayment_periods);
			    frm.set_value('repayment_start_date', r.message.loan.repayment_start_date);
				frm.refresh();
			}
		});
	},
	validate_loan_amount: function(frm){
	    var max_percentage = frappe.utils.get_config_by_name('MAX_PERCENTAGE_FOR_ADV_SALARY_LOAN', 60);
	    if(frm.doc.loan_type == frappe.utils.get_config_by_name('ADVANCE_SALARY_LOAN_TYPE', 'Advance Against Salary')) {
	        var max_loan_amount = frm.doc.earned_salary * (max_percentage/100);
	        max_loan_amount = max_loan_amount.toFixed(2)
	        if(frm.doc.loan_amount > max_loan_amount){
	            frappe.msgprint(`Advance Against Salary Loan Amount cannot be more than ${max_percentage}% of Employee Earned Salary. Please enter (${max_loan_amount}) or less.`);
	        }
	    }
	},
	make_jv: function (frm) {
		frappe.call({
			args: {
				"loan": frm.doc.name,
				"company": frm.doc.company,
				"loan_account": frm.doc.loan_account,
				"applicant_type": frm.doc.applicant_type,
				"applicant": frm.doc.applicant,
				"loan_amount": frm.doc.loan_amount,
				"payment_account": frm.doc.payment_account
			},
			method: "erpnext.hr.doctype.loan.loan.make_jv_entry",
			callback: function (r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		})
	},
	make_repayment_entry: function(frm) {
		var repayment_schedule = $.map(frm.doc.repayment_schedule, function(d) { return d.paid ? d.payment_date : false; });
		if(repayment_schedule.length >= 1){
			frm.repayment_data = [];
			frm.show_dialog = 1;
			let title = "";
			let fields = [
			{fieldtype:'Section Break', label: __('Repayment Schedule')},
			{fieldname: 'payments', fieldtype: 'Table',
				fields: [
					{
						fieldtype:'Data',
						fieldname:'payment_date',
						label: __('Date'),
						read_only:1,
						in_list_view: 1,
						columns: 2
					},
					{
						fieldtype:'Currency',
						fieldname:'principal_amount',
						label: __('Principal Amount'),
						read_only:1,
						in_list_view: 1,
						columns: 3
					},
					{
						fieldtype:'Currency',
						fieldname:'interest_amount',
						label: __('Interest'),
						read_only:1,
						in_list_view: 1,
						columns: 2
					},
					{
						fieldtype:'Currency',
						read_only:1,
						fieldname:'total_payment',
						label: __('Total Payment'),
						in_list_view: 1,
						columns: 3
					},
				],
				data: frm.repayment_data,
				get_data: function() {
					return frm.repayment_data;
				}
			}
		]

		var dialog = new frappe.ui.Dialog({
			title: title, fields: fields,
		});
		if (frm.doc['repayment_schedule']) {
			frm.doc['repayment_schedule'].forEach((payment, index) => {
			if (payment.paid == 0 && payment.payment_date <= frappe.datetime.now_date()) {
					frm.repayment_data.push ({
						'id': index,
						'name': payment.name,
						'payment_date': payment.payment_date,
						'principal_amount': payment.principal_amount,
						'interest_amount': payment.interest_amount,
						'total_payment': payment.total_payment
					});
					dialog.fields_dict.payments.grid.refresh();
					$(dialog.wrapper.find(".grid-buttons")).hide();
					$(`.octicon.octicon-triangle-down`).hide();
				}

			})
		}

		dialog.show()
		dialog.set_primary_action(__('Create Repayment Entry'), function() {
			frm.values = dialog.get_values();
			if(frm.values) {
				_make_repayment_entry(frm, dialog.fields_dict.payments.grid.get_selected_children());
				dialog.hide()
				}
			});
		}

		dialog.get_close_btn().on('click', () => {
			dialog.hide();
		});
	},

	mode_of_payment: function (frm) {
		if (frm.doc.mode_of_payment && frm.doc.company) {
			frappe.call({
				method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
				args: {
					"mode_of_payment": frm.doc.mode_of_payment,
					"company": frm.doc.company
				},
				callback: function (r, rt) {
					if (r.message) {
						frm.set_value("payment_account", r.message.account);
					}
				}
			});
		}
	},

	loan_application: function (frm) {
	    if(frm.doc.loan_application){
            return frappe.call({
                method: "erpnext.hr.doctype.loan.loan.get_loan_application",
                args: {
                    "loan_application": frm.doc.loan_application
                },
                callback: function (r) {
                    if (!r.exc && r.message) {
                        frm.set_value("loan_type", r.message.loan_type);
                        frm.set_value("loan_amount", r.message.loan_amount);
                        frm.set_value("repayment_method", r.message.repayment_method);
                        frm.set_value("monthly_repayment_amount", r.message.repayment_amount);
                        frm.set_value("repayment_periods", r.message.repayment_periods);
                        frm.set_value("rate_of_interest", r.message.rate_of_interest);
                    }
                }
            });
        }
	},

	repayment_method: function (frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function (frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
		frm.set_df_property('repayment_start_date', 'read_only', frm.doc.loan_type==frappe.utils.get_config_by_name('ADVANCE_SALARY_LOAN_TYPE', 'Advance Against Salary'));
		frm.set_df_property('repayment_periods', 'read_only', frm.doc.loan_type==frappe.utils.get_config_by_name('ADVANCE_SALARY_LOAN_TYPE', 'Advance Against Salary'));
		frm.set_df_property('repayment_method', 'read_only', frm.doc.loan_type==frappe.utils.get_config_by_name('ADVANCE_SALARY_LOAN_TYPE', 'Advance Against Salary'));
	
	}
});

var _make_repayment_entry = function(frm, payment_rows) {
	frappe.call({
		method:"erpnext.hr.doctype.loan.loan.make_repayment_entry",
		args: {
			payment_rows: payment_rows,
			"loan": frm.doc.name,
			"company": frm.doc.company,
			"loan_account": frm.doc.loan_account,
			"applicant_type": frm.doc.applicant_type,
			"applicant": frm.doc.applicant,
			"payment_account": frm.doc.payment_account,
			"interest_income_account": frm.doc.interest_income_account
		},
		callback: function(r) {
			if (r.message)
				var doc = frappe.model.sync(r.message)[0];
			frappe.set_route("Form", doc.doctype, doc.name, {'payment_rows': payment_rows});
		}
	});
}
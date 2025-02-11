// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");
erpnext.hr.EmployeeController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.user_id.get_query = function(doc, cdt, cdn) {
			return {
				query: "frappe.core.doctype.user.user.user_query",
				filters: {ignore_user_type: 1}
			}
		}
		this.frm.fields_dict.reports_to.get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.employee_query"} }

	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
	},

	date_of_birth: function() {
		return cur_frm.call({
			method: "get_retirement_date",
			args: {date_of_birth: this.frm.doc.date_of_birth}
		});
	},

	salutation: function() {
		if(this.frm.doc.salutation) {
			this.frm.set_value("gender", {
				"Mr": "Male",
				"Ms": "Female"
			}[this.frm.doc.salutation]);
		}
	},

});
frappe.ui.form.on('Employee',{
	setup: function(frm) {
		frm.set_query("leave_policy", function() {
			return {
				"filters": {
					"docstatus": 1
				}
			};
		});
	},
	calculate_reporting_to: function(frm){
		frappe.call({
			method: "calculate_reporting_to",
			doc: frm.doc,
			freeze: true,
			callback: function(r) {
				if(!r.exc) {
					if(r.message) {
						// frappe.set_route("Form", "Account", r.message);
					} else {
						// frm.set_value("account_number", data.account_number);
						// frm.set_value("account_name", data.account_name);
					}
					// d.hide();
				}
			}
		});
	},
	refresh(frm) {
	    setTimeout(function() {
            frm.trigger("show_progress");
            frm.trigger("make_missing_field_dashboard");
            if(frappe.user.has_role(frappe.utils.get_config_by_name("ROLE_FOR_EMPLOYEE_DASHBOARD",["CEO"]))){
                frm.trigger("make_dashboard");
            }
        }, 100);
	    
	    setTimeout(function() {
            if (!($("#collapseThree3").find("[data-fieldname='education']").length) || !($("#collapseThree3").find("[data-fieldname='external_work_history']").length) || !($("#collapseThree3").find("[data-fieldname='internal_work_history']").length)){
                frm.trigger("make_missing_field_dashboard");
                if(frappe.user.has_role(frappe.utils.get_config_by_name("ROLE_FOR_EMPLOYEE_DASHBOARD",["CEO"]))){
                    frm.trigger("make_dashboard");
                }
    	    }
        }, 3000);
	    
	    if( frm.is_new() ){
	       cur_frm.set_value("status", "Pending");
	    }
        frappe.require("assets/nerp/js/jquery.maskedinput.min.js", () => {
            $.mask.definitions['3'] = null;
            $('input[data-fieldname="cnic_no"]').mask(frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9'),{autoclear: false});
            $('input[data-fieldname="cell_number"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
		    $('input[data-fieldname="emergency_phone_number"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
            $('input[data-fieldname="company_cell_number"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
        });
		frm.add_custom_button(__('Calculate Reporting To'), function () {
			frm.trigger("calculate_reporting_to");
		});
    },
	show_progress: function(frm) {
		let bars = [];
		let message = '';
		let title = '';
		let progress = 0;
	    let progress_class = 'progress-bar-danger progress-bar-striped active';
	   

        title = 'Profile Completion ' + frm.doc.progress + '%';
        message = title;
        
        if (frm.doc.progress){
            progress = frm.doc.progress; 
        }
        if (frm.doc.progress_class){
            progress_class = frm.doc.progress_class;
            progress_class = progress_class.concat(' progress-bar-striped active'); 
        }
        
        bars.push({
			'title': title,
			'width': progress + '%',
			'progress_class': progress_class
		    });

		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	},
	make_missing_field_dashboard: function(frm) {
	    let missing_fields;
	    if (frm.doc.employee) {
			frappe.call({
				method: "nerp.modules.gourmet.employee.employee.get_employee_profile_missing_fields",
				async: false,
				args: {
				    name: frm.doc.name,
					doctype: frm.doctype
				},
				callback: function(r) {
					if (!r.exc && r.message['missing_fields']) {
						missing_fields = r.message['missing_fields'];
					}
				}
			});
				
			var myvar = '{% if missing_fields %}'+
			'<div  id="missing" style="position: relative; right: 18px;" class="container missing">'+
            '<div class="panel-group" style="width: 77.5%; margin: 0px; padding:0px; margin-bottom: 5px;" role="tablist" aria-multiselectable="true">'+
            '   <div class="card panel panel-default">'+
            '       <div class="card-header panel-heading" role="tab" id="headingOne1">'+
            '       <h4 class="mb-0 panel-title"><a data-toggle="collapse" style="font-size: 14px;" href="#collapseOne1" aria-expanded="false" aria-controls="collapseOne1"> Profile Missing Fields<span style="padding-left: 15px;text-decoration: none;"></span><span style="font-size: 12px;" class="glyphicon glyphicon-menu-down js-rotate-if-collapsed"> </span></a></h4></div>'+
            '       <div id="collapseOne1" class="collapse panel-collapse" role="tabpanel" aria-labelledby="headingOne1" ><div class="card-body">'+
            '           <ul style="column-count: 2">'+
            '	            {% for missing_field in missing_fields %}'+
            '			        <li class="text-left">{{ missing_field }}</li>'+
            '               {% endfor %}'+
            '           </ul>'+
            '       </div></div>'+
            '       </div>'+
            '   </div>'+
            '</div>'+
            '{% endif %}';
            $("div").remove(".missing");
    		frm.dashboard.add_section(
    			frappe.render_template(myvar, {
    				missing_fields: missing_fields
    			},"missing")
    		);
            $(".progress-area").append( $(".missing") );

	    }
	},
	before_workflow_action: function(frm) {
	    if(frm.doc.workflow_state == "Active"){
    	    return new Promise(function(resolve, reject) {
                frappe.confirm(
                    'Do you really want to Mark Employee Left?',
                    function() {
                        if(frm.doc.status != "Active"){
                            frappe.throw("Employee status is not Active");
                        }
                        var negative = 'frappe.validated = false';
                        resolve(negative);
                    },
                    function() {
                        reject();
                    }
                );
            });
	    }
	},
	validate: function(frm) {
        if( frm.is_new() && cur_frm.doc.status != "Pending"){
            frappe.msgprint("You can create new employee with Pending status only.");
            validated = false;
        }
        if(frm.doc.cnic_no.length != frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9').length){
            frappe.msgprint("Please Enter valid CNIC No.");
            validated = false;
        }

        if(frm.doc.employee_address && frm.doc.employee_address.length){
            let primaryAddr = 0;
            frm.doc.employee_address.forEach(async function(element){
                if(element.address_type == "Primary")
                    primaryAddr++;
            });
            
            if(primaryAddr == 0){
                frappe.msgprint("Please add Primary address first");
                validated = false;
            }

            if(primaryAddr > 1){
                frappe.msgprint("You cannot add multiple Primary Addresses");
                validated = false;
            }

        }
        
        var age = frappe.utils.get_age(cur_frm.doc.date_of_birth);
        var allowed_age = frappe.utils.get_config_by_name("EMPLOYEE_ALLOWED_AGE", 18);
        if( age < allowed_age ) {
            frappe.msgprint("Employee is under age.");
            validated = false;
        }
    },
	
	onload:function(frm) {
		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
	},
	prefered_contact_email:function(frm){		
		frm.events.update_contact(frm)		
	},
	personal_email:function(frm){
		frm.events.update_contact(frm)
	},
	company_email:function(frm){
		frm.events.update_contact(frm)
	},
	user_id:function(frm){
		frm.events.update_contact(frm)
	},
	update_contact:function(frm){
		var prefered_email_fieldname = frappe.model.scrub(frm.doc.prefered_contact_email) || 'user_id';
		frm.set_value("prefered_email",
			frm.fields_dict[prefered_email_fieldname].value)
	},
	status: function(frm) {
		return frm.call({
			method: "deactivate_sales_person",
			args: {
				employee: frm.doc.employee,
				status: frm.doc.status
			}
		});
	},
	create_user: function(frm) {
		if (!frm.doc.prefered_email)
		{
			frappe.throw(__("Please enter Preferred Contact Email"))
		}
		frappe.call({
			method: "erpnext.hr.doctype.employee.employee.create_user",
			args: { employee: frm.doc.name, email: frm.doc.prefered_email },
			callback: function(r)
			{
				frm.set_value("user_id", r.message)
			}
		});
	}
});
cur_frm.cscript = new erpnext.hr.EmployeeController({frm: cur_frm});

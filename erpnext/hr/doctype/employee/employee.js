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

		frm.set_query('job_applicant', () => {
			return {
				filters: {
					job_applicant_status: "Offer Accepted"	
				}
			};
		});

		setTimeout(function() {
            if (!($("#collapseThree3").find("[data-fieldname='education']").length) || !($("#collapseThree3").find("[data-fieldname='external_work_history']").length) || !($("#collapseThree3").find("[data-fieldname='internal_work_history']").length)){
                frm.trigger("make_missing_field_dashboard");
                if(frappe.user.has_role(frappe.utils.get_config_by_name("ROLE_FOR_EMPLOYEE_DASHBOARD",["CEO"]))){
                    frm.trigger("make_dashboard");
                }
    	    }
        }, 3000);
        
        frm.fields_dict['employee_address'].grid.get_field('province').get_query = function(doc,dt, dn) {
            if(!locals[dt][dn].country){
                frappe.msgprint("Please select Country first");
            }
            return {
                filters:{"country": locals[dt][dn].country}
            }
        };
        
        frm.fields_dict['employee_address'].grid.get_field('city').get_query = function(doc,dt, dn) {
            if(!locals[dt][dn].province){
                frappe.msgprint("Please select Province first");
            }
            return {
                filters:{"province": locals[dt][dn].province}
            }
        };
        
        frm.set_query("room", function() {
            if(!frm.doc.residence){
                frappe.msgprint("Please select Residence Name first");
            }
            return {
                "filters": {
                    "residence": frm.doc.residence
                }
            };
        });
        
        frm.set_query("branch", function() {
            if(!frm.doc.department){
                frappe.msgprint("Please select Department first");
            }
            return {
                "filters": {
                    "department": frm.doc.department,
                    // "is_group":["=","0"]
                }
            };
        });
        
        frm.set_query("sub_branch", function() {
            if(!frm.doc.branch){
                frappe.msgprint("Please select Branch first");
            }
            return {
                "filters": {
                    "branch": frm.doc.branch
                }
            };
        });
	},
	designation: function(frm){
        frm.set_value('internal_designation', "");
	    frm.set_value('grade', "");
        if(frm.doc.designation){
            frappe.db.get_value("Designation", frm.doc.designation, "internal_designation", (r) => {
    			console.log(r.internal_designation,typeof r.internal_designation)
    			if (r && r.internal_designation){
	                frappe.db.get_value("Internal Designation", r.internal_designation, "employee_grade", (r) => {
            			if (r && r.employee_grade){
                		    frm.set_value('grade', r.employee_grade);
            			}
            		});
            		console.log(r);
            	    frm.set_value('internal_designation', r.internal_designation);
    			}
    		});
        }
    },
	date_of_birth: function(frm){
        var age = frappe.utils.get_age(cur_frm.doc.date_of_birth);
        var allowed_age = frappe.utils.get_config_by_name("EMPLOYEE_ALLOWED_AGE", 18);
        if( age < allowed_age ) {
            frappe.msgprint("Employee is under age.");
            return false;
        }
        return true;
    },
	make_dashboard: function(frm) {
		let employee_details_columns;
		let employee_details_data;
		let reports_to_details;
		let name_details;
		let head_count_details;
		let total_salary_details;
		if (frm.doc.employee) {
			frappe.call({
				method: "nerp.modules.gourmet.employee.employee.get_employee_details",
				async: false,
				args: {
					employee: frm.doc.name,
					reports_to: frm.doc.reports_to,
					department: frm.doc.department,
					branch: frm.doc.branch,
					sub_branch: frm.doc.sub_branch
				},
				callback: function(r) {
					if (!r.exc && r.message['employee_details_columns']) {
						employee_details_columns = r.message['employee_details_columns'];
					}
					if (!r.exc && r.message['employee_details_data']) {
						employee_details_data = r.message['employee_details_data'];
					}
					if (!r.exc && r.message['reports_to_details']) {
						reports_to_details = r.message['reports_to_details'];
					}
					if (!r.exc && r.message['name_details']) {
						name_details = r.message['name_details'];
					}
					if (!r.exc && r.message['head_count_details']) {
						head_count_details = r.message['head_count_details'];
					}
					if (!r.exc && r.message['total_salary_details']) {
						total_salary_details = r.message['total_salary_details'];
					}
				}
			});
			
			var myvar = 
			'<div id="summary" style="position: relative; right: 18px;" class="container summary">'+
			'<div style="width: 77.5%; margin: 0px; padding:0px;" class="panel-group" role="tablist" aria-multiselectable="true">'+
			'   {% if head_count_details && total_salary_details %}'+
			'   <div class="card panel panel-default">'+
			'       <div class="card-header panel-heading" role="tab" id="headingTwo2">'+
			'           <h4 class="mb-0 panel-title">'+
			'               <a data-toggle="collapse" style="font-size: 14px;" href="#collapseTwo2" aria-expanded="false" aria-controls="collapseTwo2"> Department Summary<span style="padding-left: 15px;text-decoration: none;"></span><span style="font-size: 12px;" class="glyphicon glyphicon-menu-down js-rotate-if-collapsed"> </span></a>'+
			'           </h4>'+
			'       </div>'+
			'       <div id="collapseTwo2" class="collapse panel-collapse" role="tabpanel" aria-labelledby="headingTwo2"><div class="card-body">'+
			'         <table style="width: 96.5%; margin-bottom:20px; margin-left:15px" class="table table-bordered small">'+
			'           <thead>'+
			'             <tr>'+
			'               <th style="width: 16%" class="text-left">{{ __("Description") }}</th>'+
			'               <th style="width: 16%" class="text-left">{{ __("Department") }}</th>'+
			'               <th style="width: 16%" class="text-left">{{ __("Branch") }}</th>'+
			'               <th style="width: 16%" class="text-left">{{ __("Sub Branch") }}</th>'+
			'             </tr>'+
			''+
			'           </thead>'+
			'           <tbody>'+
			'             {% for(const [key, value] of Object.entries(name_details)) { %}'+
			'               <tr>'+
			'                 <td class="text-left"> {%= value["field_name"] %} </td>'+
			'                 <td class="text-left"> {%= value["department_name"] %} </td>'+
			'                 <td class="text-left"> {%= value["branch_name"] %} </td>'+
			'                 <td class="text-left"> {%= value["sub_branch_name"] %} </td>'+
			'               </tr>'+
			'             {% } %}'+
			'             {% for(const [key, value] of Object.entries(head_count_details)) { %}'+
			'               <tr>'+
			'                 <td class="text-left"> {%= value["field_name"] %} </td>'+
			'                 <td class="text-right"> {%= value["department_head_count"] %} </td>'+
			'                 <td class="text-right"> {%= value["branch_head_count"] %} </td>'+
			'                 <td class="text-right"> {%= value["sub_branch_head_count"] %} </td>'+
			'               </tr>'+
			'             {% } %}'+
			'             {% for(const [key, value] of Object.entries(total_salary_details)) { %}'+
			'               <tr>'+
			'                 <td class="text-left"> {%= value["field_name"] %} </td>'+
			'                 <td class="text-right"> {%= value["department_total_salary"] %} </td>'+
			'                 <td class="text-right"> {%= value["branch_total_salary"] %} </td>'+
			'                 <td class="text-right"> {%= value["sub_branch_total_salary"] %} </td>'+
			'               </tr>'+
			'             {% } %}'+
			'           </tbody>'+
			'         </table>'+
			'       </div></div>'+
			'      </div>'+
			''+
			'       {% } else { %}'+
			'        <p style="margin-top: 30px;"> Department Analytics not found. </p>'+
			'        {% } %}'+
			''+
			''+
			''+
			'         {% if employee_details_columns && employee_details_data %}'+
			'         <div class="card panel panel-default">'+
			'           <div class="card-header panel-heading" role="tab" id="headingThree3">'+
			'               <h4 class="mb-0 panel-title">'+
			'                   <a data-toggle="collapse" style="font-size: 14px;" href="#collapseThree3" aria-expanded="false" aria-controls="collapseThree3"> Employee Summary<span style="padding-left: 15px;text-decoration: none;"></span><span style="font-size: 12px;" class="glyphicon glyphicon-menu-down js-rotate-if-collapsed"> </span></a>'+
			'               </h4>'+
			'           </div>'+
			'           <div id="collapseThree3" class="collapse panel-collapse" role="tabpanel" aria-labelledby="headingThree3"><div class="card-body">'+
			'           <h6 style="margin-top: 20px; padding-left: 15px;"> {{ __("Employee Salary and Allowances") }} </h6>'+
			'           <table style="width: 96.5%; margin-left:15px;" class="table table-bordered small">'+
			'             <thead>'+
			'               <tr>'+
			'                 {% for employee_column in employee_details_columns %}'+
			'                   <th style="width: 16%" class="text-left">{{ employee_column }}</th>'+
			'                 {% endfor %}'+
			'               </tr>'+
			''+
			'             </thead>'+
			'             <tbody>'+
			'               <tr>'+
			'                 {% for employee_data in employee_details_data %}'+
			'                   <td class="text-right"> {{ employee_data }} </td>'+
			'                 {% endfor %}'+
			'               </tr>'+
			'             </tbody>'+
			'           </table>'+
			'         {% } else { %}'+
			'           <p style="margin-top: 30px;"> Employee Salary Detail not found. </p>'+
			'         {% } %}'+
			''+
			''+
			''+
			'        {% if reports_to_details %}'+
			''+
			'        <h6 style="margin-top: 20px; padding-left: 15px;"> {{ __("Reports To Details") }} </h6>'+
			'        <table style="width: 96.5%; margin-left:15px; margin-bottom:20px;" class="table table-bordered small">'+
			'         <thead>'+
			'           <tr>'+
			'             <th style="width: 16%" class="text-left">{{ __("Employee No.") }}</th>'+
			'             <th style="width: 16%" class="text-left">{{ __("Employee Name") }}</th>'+
			'             <th style="width: 16%" class="text-left">{{ __("Designation") }}</th>'+
			'             <th style="width: 16%" class="text-left">{{ __("Department") }}</th>'+
			'             <th style="width: 16%" class="text-left">{{ __("Branch") }}</th>'+
			'             <th style="width: 16%" class="text-left">{{ __("Sub Branch") }}</th>'+
			'           </tr>'+
			''+
			'         </thead>'+
			'         <tbody>'+
			'                {% for(const [key, value] of Object.entries(reports_to_details)) { %}'+
			'             <tr>'+
			'               <td class="text-left"> <a href={%= value["redirect_url"] %}>{%= value["name"] %}</a> </td>'+
			'               <td class="text-left"> {%= value["employee_name"] %} </td>'+
			'               <td class="text-left"> {%= value["designation"] %} </td>'+
			'               <td class="text-left"> {%= value["department"] %} </td>'+
			'               <td class="text-left"> {%= value["branch"] %} </td>'+
			'               <td class="text-left"> {%= value["sub_branch"] %} </td>'+
			'             </tr>'+
			'                {% } %}'+
			'        </tbody>'+
			'        </table>'+
			''+
			'        {% } else { %}'+
			'        <p style="margin-top: 30px;"> Report Manager Detail not found. </p>'+
			'        {% } %}'+
			'       </div></div>'+
			'      </div>'+
			'   </div>'+
			'</div>';

	
			$("div").remove(".summary");
			frm.dashboard.add_section(
				frappe.render_template(myvar, {
					employee_details_columns: employee_details_columns,
					employee_details_data: employee_details_data,
					reports_to_details: reports_to_details,
					name_details: name_details,
					head_count_details: head_count_details,
					total_salary_details: total_salary_details
				}, "summary")
			);
			$(".progress-area").append( $("#summary") );

			// Append Education grid using jquery
			var education = $('div[data-fieldname="education"] .form-group').clone();
			education.find(".form-clickable-section").remove();
			education.find(".row-index").removeClass("col-xs-1").addClass("col-xs-2");
			education.find(".grid-heading-row").find(".row-index").append("<span> Sr. </span>").css('text-align','left');
			education.find(".col-xs-1").remove();
			education.find(".grid-row-check").remove();
			
			education.find(".control-label").css({"color": "#666666", "font-weight": "bold", "margin-bottom": "20px"});
			education.find(".data-row").css({"color": "#333333", "background-color": "white"});
			education.find(".grid-static-col").css({"color": "#333333", "background-color": "white"});
			education.css({"width": "96.5%", "margin-left": "15px", "margin-bottom": "20px"});

			// Append Employee External Experience grid using jquery
			var external_experience = $('div[data-fieldname="external_work_history"] .form-group').clone();
			external_experience.find(".form-clickable-section").remove();
			external_experience.find(".row-index").removeClass("col-xs-1").addClass("col-xs-2");
			external_experience.find(".col-xs-3").removeClass("col-xs-3").addClass("col-xs-4");
			external_experience.find(".grid-heading-row").find(".row-index").append("<span> Sr. </span>").css('text-align','left');
			external_experience.find(".col-xs-1").remove();
			external_experience.find(".grid-row-check").remove();
			
			external_experience.find(".control-label").css({"color": "#666666", "font-weight": "bold", "margin-bottom": "20px"});
			external_experience.find(".data-row").css({"color": "#333333", "background-color": "white"});
			external_experience.find(".grid-static-col").css({"color": "#333333", "background-color": "white"});
			external_experience.css({"width": "96.5%", "margin-left": "15px", "margin-bottom": "20px"});
			
			// Append Employee Internal Experience grid using jquery
			var internal_experience = $('div[data-fieldname="internal_work_history"] .form-group').clone();
			internal_experience.find(".form-clickable-section").remove();
			internal_experience.find(".row-index").removeClass("col-xs-1").addClass("col-xs-2");
			internal_experience.find(".grid-heading-row").find(".row-index").append("<span> Sr. </span>").css('text-align','left');
			internal_experience.find(".col-xs-1").remove();
			internal_experience.find(".grid-row-check").remove();
			
			internal_experience.find(".control-label").css({"color": "#666666", "font-weight": "bold", "margin-bottom": "20px"});
			internal_experience.find(".data-row").css({"color": "#333333", "background-color": "white"});
			internal_experience.find(".grid-static-col").css({"color": "#333333", "background-color": "white"});
			internal_experience.css({"width": "96.5%", "margin-left": "15px", "margin-bottom": "40px"});
			

			$( '#collapseThree3' ).append(education);
			$( '#collapseThree3' ).append(external_experience);
			$( '#collapseThree3' ).append(internal_experience);
		}
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

frappe.ui.form.on('Employee Address',{
    country: function(doc,cdt,cdn){
        frappe.model.set_value(cdt, cdn, "province", "");
        frappe.model.set_value(cdt, cdn, "city", "");
    },
    province: function(doc,cdt,cdn){
        frappe.model.set_value(cdt, cdn, "city", "");
    }
});
cur_frm.cscript = new erpnext.hr.EmployeeController({frm: cur_frm});

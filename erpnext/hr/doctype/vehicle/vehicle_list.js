frappe.listview_settings['Vehicle'] = {
	onload: function(me) {
        
		if (Object.values(frappe.route_options).length == 0){

            // var employeeCode;
            // frappe.call({
            //     method: "frappe.client.get_value",
            //     args: {
            //         doctype: "Employee",
            //         filters: {
            //             user_id: frappe.session.user
            //         },
            //         fieldname: ["name"]
            //     },
            //     callback: function(response) {
            //         employeeCode = response.message ? response.message.name : null;
                    
            //     }
            // });

            
            frappe.route_options = {
                // "employee": employeeCode,
                "creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -30),frappe.datetime.get_today()]]
            };

		}
	}
};

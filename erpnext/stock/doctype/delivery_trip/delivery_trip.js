// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Trip', {
	setup: function (frm) {
		frm.set_indicator_formatter('customer', (stop) => (stop.visited) ? "green" : "orange");

		frm.set_query("driver", function () {
			return {
				filters: {
					"status": "Active"
				}
			};
		});

		frm.set_query("address", "delivery_stops", function (doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (row.customer_name) {
				return {
					query: 'frappe.contacts.doctype.address.address.address_query',
					filters: {
						link_doctype: row.customer_type,
						link_name: row.customer_name
					}
				};
			}
		})

		frm.set_query("contact", "delivery_stops", function (doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (row.customer_name) {
				return {
					query: 'frappe.contacts.doctype.contact.contact.contact_query',
					filters: {
						link_doctype: row.customer_type,
						link_name: row.customer_name
					}
				};
			}
		})
	},
	notify_customers: function (frm) {
		$.each(frm.doc.delivery_stops || [], function (i, delivery_stop) {
			if (!delivery_stop.reference_id) {
				frappe.msgprint({
					"message": __("No Delivery Note selected for Customer {}", [delivery_stop.customer_name]),
					"title": __("Warning"),
					"indicator": "orange",
					"alert": 1
				});
			}
		});

		frappe.db.get_value("Delivery Settings", { name: "Delivery Settings" }, "dispatch_template", (r) => {
			if (!r.dispatch_template) {
				frappe.throw(__("Missing email template for dispatch. Please set one in Delivery Settings."));
			} else {
				frappe.confirm(__("Do you want to notify all the customers by email?"), function () {
					frappe.call({
						method: "erpnext.stock.doctype.delivery_trip.delivery_trip.notify_customers",
						args: {
							"delivery_trip": frm.doc.name
						},
						callback: function (r) {
							if (!r.exc) {
								frm.doc.email_notification_sent = true;
								frm.refresh_field('email_notification_sent');
							}
						}
					});
				});
			}
		});
	},
	show_map: function (frm) {
        var destinationLatlng = [];
        var wayPoints = [];
        var finalDestAddress;
        $.getScript("//maps.googleapis.com/maps/api/js?key=AIzaSyCZBPvWIhTmn6UCdjn4_6MdBqIPwg5ap9g", function () {
            frm.doc.delivery_stops.forEach(async function (element) {
                if (element.lat !== null && element.lat !== '' && element.lng !== null && element.lng !== '') {
                    var latLng = new google.maps.LatLng(element.lat, element.lng);
                    wayPoints.push({
                        location: latLng,
                        stopover: true
                    })
                    destinationLatlng.push(latLng);
                    finalDestAddress = {
                        lat: element.lat,
                        lng: element.lng
                    }
                }
                var originAddress = frm.doc.driver_address;
            });
            var originAddress = frm.doc.driver_address;
            var destAddress = finalDestAddress;
            var destAddressLatlng = destinationLatlng;
            wayPoints.pop()
            $('#map').css("display", "block");
            initMap(originAddress, destAddress, destinationLatlng, wayPoints);
        });
    },

	refresh: function (frm) {
		frm.remove_custom_button("Delivery Note", "Get customers from");

		if (frm.doc.docstatus == 1 && frm.doc.delivery_stops.length > 0) {
			frm.add_custom_button(__("Notify Customers via Email"), function () {
				frm.trigger('notify_customers');
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Delivery Note'), () => {
				erpnext.utils.map_current_doc({
					method: "nrp_manufacturing.modules.gourmet.delivery_note.delivery_note.make_delivery_trip",
					source_doctype: "Delivery Note",
					target: frm,
					date_field: "posting_date",
					setters: {
						company: frm.doc.company,
						vehicle: frm.doc.vehicle,
					},
					get_query_filters: {
						docstatus: 1,
						company: frm.doc.company,
						vehicle: frm.doc.vehicle,
					}
				})
			}, __("Get customers from"));
			


			frm.add_custom_button(__('Stock Entry'), () => {
				erpnext.utils.map_current_doc({
					method: "nrp_manufacturing.modules.gourmet.stock_entry.stock_entry.make_delivery_trip",
					source_doctype: "Stock Entry",
					target: frm,
					date_field: "posting_date",
					setters: {
						company: frm.doc.company,
						vehicle: frm.doc.vehicle,
					},
					get_query_filters: {
						docstatus: 1,
						company: frm.doc.company,
						vehicle: frm.doc.vehicle,
						purpose: "Send To Warehouse",
						per_transferred: ["<", 100],
						
					}
				})
			}, __("Get customers from"));
		}
	},

	calculate_arrival_time: function (frm) {
		if (!frm.doc.driver_address) {
			frappe.throw(__("Cannot Calculate Arrival Time as Driver Address is Missing."));
		}
		frappe.show_alert({
			message: "Calculating Arrival Times",
			indicator: 'orange'
		});
		frm.call("process_route", {
			optimize: false,
		}, () => {
			frm.reload_doc();
		});

	},

	optimize_route: function (frm) {
		if (!frm.doc.driver_address) {
			frappe.throw(__("Cannot Optimize Route as Driver Address is Missing."));
		}
		frappe.show_alert({
			message: "Optimizing Route",
			indicator: 'orange'
		});
		frm.call("process_route", {
			optimize: true,
		}, () => {
			frm.reload_doc();
		});
	},

	notify_customers: function (frm) {
		$.each(frm.doc.delivery_stops || [], function (i, delivery_stop) {
			if (!delivery_stop.delivery_note) {
				frappe.msgprint({
					"message": __("No Delivery Note selected for Customer {}", [delivery_stop.customer]),
					"title": __("Warning"),
					"indicator": "orange",
					"alert": 1
				});
			}
		});

		frappe.db.get_value("Delivery Settings", { name: "Delivery Settings" }, "dispatch_template", (r) => {
			if (!r.dispatch_template) {
				frappe.throw(__("Missing email template for dispatch. Please set one in Delivery Settings."));
			} else {
				frappe.confirm(__("Do you want to notify all the customers by email?"), function () {
					frappe.call({
						method: "erpnext.stock.doctype.delivery_trip.delivery_trip.notify_customers",
						args: {
							"delivery_trip": frm.doc.name
						},
						callback: function (r) {
							if (!r.exc) {
								frm.doc.email_notification_sent = true;
								frm.refresh_field('email_notification_sent');
							}
						}
					});
				});
			}
		});
	}
});

frappe.ui.form.on('Delivery Stop', {
	customer: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.customer) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_contact_and_address",
				args: { "name": row.customer },
				callback: function (r) {
					if (r.message) {
						if (r.message["shipping_address"]) {
							frappe.model.set_value(cdt, cdn, "address", r.message["shipping_address"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "address", '');
						}
						if (r.message["contact_person"]) {
							frappe.model.set_value(cdt, cdn, "contact", r.message["contact_person"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "contact", '');
						}
					}
					else {
						frappe.model.set_value(cdt, cdn, "address", '');
						frappe.model.set_value(cdt, cdn, "contact", '');
					}
				}
			});
		}
	},

	customer_name: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.customer_name) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_contact_and_address",
				args: { "name": row.customer_name, "customer_type": row.customer_type},
				callback: function (r) {
					if (r.message) {
						if (r.message["shipping_address"]) {
							frappe.model.set_value(cdt, cdn, "address", r.message["shipping_address"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "address", '');
						}
						if (r.message["contact_person"]) {
							frappe.model.set_value(cdt, cdn, "contact", r.message["contact_person"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "contact", '');
						}
					}
					else {
						frappe.model.set_value(cdt, cdn, "address", '');
						frappe.model.set_value(cdt, cdn, "contact", '');
					}
				}
			});
		}
	},

	address: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: { "address_dict": row.address },
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "customer_address", r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "customer_address", "");
		}
	},

	contact: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.contact) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_contact_display",
				args: { "contact": row.contact },
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "customer_contact", r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "customer_contact", "");
		}
	}
});
function initMap(originAddress, destAddress, destinationLatlng, wayPoints) {
    // Initiate map with the origin address
    var directionsService = new google.maps.DirectionsService;
    var directionsDisplay = new google.maps.DirectionsRenderer;
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 15,
        center: {
            lat: 31.5204,
            lng: 74.3587
        },
    });
    directionsDisplay.setMap(map);
    var i = 0;
    for (i = 0; i < destinationLatlng.length; i++) {
        console.log(destinationLatlng[i]);
    }
    calculateAndDisplayRoute(directionsService, directionsDisplay, originAddress, destAddress, wayPoints);
}

function calculateAndDisplayRoute(directionsService, directionsDisplay, originAddress, destAddress, wayPoints) {
    // For more customization on the route and distanceMatrix, please refer to the API
    // API Link: https://developers.google.com/maps/documentation/javascript/distancematrix
    var service = new google.maps.DistanceMatrixService();
    directionsService.route({
        origin: originAddress,
        destination: destAddress,
        waypoints: wayPoints,
        optimizeWaypoints: true,
        travelMode: google.maps.TravelMode.DRIVING
    }, function (response, status) {
        if (status === google.maps.DirectionsStatus.OK) {
            directionsDisplay.setDirections(response);
        } else {
            window.alert('Directions request failed due to ' + status);
            // Customize your own error here
        }
    });
    service.getDistanceMatrix({
        origins: [originAddress],
        destinations: [destAddress],
        travelMode: google.maps.TravelMode.DRIVING,
        unitSystem: google.maps.UnitSystem.METRIC,
        avoidHighways: false,
        avoidTolls: false
    }, function (response, status) {
        if (status == google.maps.DistanceMatrixStatus.OK && response.rows[0].elements[0].status != "ZERO_RESULTS") {
            var distance = response.rows[0].elements[0].distance.text;
            var time = response.rows[0].elements[0].duration.text;
            // Display the distance in an form input, replace distance2 as your field name
            // cur_frm.set_value("distance_map", distance);
            // The following line display to external div id instead of form input
            // Create an HTML field with the following option:
            //Total Distance between two location:

            // Uncomment the next 3 line to show the result in external div id
            var dvDistance = document.getElementById("total");
            dvDistance.innerHTML = "";
            dvDistance.innerHTML += " " + distance + ", Total Time: " + time;
        } else {
            alert("Unable To Find Distance Via Road.");
        }
    });
}

frappe.query_reports["Job Applicant Summary"] = {
	"filters": [
		{
			"fieldname": "job_opening",
			"label": __("Job Opening"),
			"fieldtype": "Link",
			"options": "Job Opening",
		}
	],

	"onload": function(report) {
		var styleElement = document.createElement('style');
		var cssStyles = `
			.dt-instance-1 .dt-cell--col-1 {position: sticky; left: 30px; z-index: 1 !important;}
			.dt-instance-1 .dt-cell--col-0 {position: sticky; left: 0px; z-index: 1 !important;}
			.custom-clickable-cell {cursor: pointer; }
	
		`;
		styleElement.innerHTML = cssStyles;
		document.head.appendChild(styleElement);
	},

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		console.log("data ", data);
		let dataValue = $(value).text().trim();

		let status_columns = [
			"applied",
			"longlisted",
			"shortlisted",
			"interview",
			"accepted",
			"rejected",
			"on_hold",
			"offered",
			"offer_accepted",
			"offer_rejected",
			"hired"
		];

		if (status_columns.includes(column.fieldname) && dataValue > 0) {
			let target_report = "Job Applicant Details";
			let job_opening = frappe.query_report.get_filter_value('job_opening');
			let status = column.fieldname.replace(/_/g, ' ').toLowerCase().split(' ')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
			let filters = `?job_opening=${job_opening}&status=${status}&platform=${data.platform}`;

			let url = `/desk#query-report/${target_report}${filters}`;

			value = `<a href="${url}" target="_blank" class="custom-clickable-cell">${value}</a>`;
		}

		return value;
	},
};

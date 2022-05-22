import frappe

from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True)
def handle():
	if frappe.request.method == "GET":
		return verify_token_and_fulfill_challenge()

	# TODO: Handle Post Request


def verify_token_and_fulfill_challenge():
	meta_challenge = frappe.form_dict.get("hub.challenge")
	expected_token = frappe.db.get_single_value("WABA Settings", "webhook_verify_token")

	if frappe.form_dict.get("hub.verify_token") != expected_token:
		frappe.throw("Verify token does not match")

	return Response(meta_challenge, status=200)

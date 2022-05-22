import frappe

from werkzeug.wrappers import Response

@frappe.whitelist(allow_guest=True)
def handle():
    if (frappe.request.method == "GET"):
        data = frappe.request.get_data()
        return Response(data, status=200)

    print("Webhook reached.")
    print(frappe.request.data)
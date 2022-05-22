import frappe

@frappe.whitelist(allow_guest=True)
def handle():
    if (frappe.request.method == "GET"):
        return frappe.request.data

    print("Webhook reached.")
    print(frappe.request.data)
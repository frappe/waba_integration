# Copyright (c) 2022, Hussain Nagaria and contributors
# For license information, please see license.txt

import frappe
import requests

from frappe.model.document import Document


class WABAWhatsAppMessage(Document):
	@frappe.whitelist()
	def send(self):
		# Get the API base URL
		access_token = frappe.utils.password.get_decrypted_password(
			"WABA Settings", "WABA Settings", "access_token"
		)
		api_base = frappe.db.get_single_value("WABA Settings", "api_base")
		phone_number_id = frappe.db.get_single_value("WABA Settings", "phone_number_id")

		endpoint = f"{api_base}/{phone_number_id}/messages"

		response = requests.post(
			endpoint,
			json={
				"messaging_product": "whatsapp",
				"recipient_type": "individual",
				"to": "919691048211",
				"type": "text",
				"text": {"preview_url": False, "body": self.message_body},
			},
			headers={
				"Authorization": "Bearer " + access_token,
				"Content-Type": "application/json",
			},
		)

		if response.ok:
			self.id = response.json().get("messages")[0]["id"]
			self.save(ignore_permissions=True)
			return response.json()
		else:
			frappe.throw(response.json().get("error").get("message"))

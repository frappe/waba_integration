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
			self.status = "Sent"
			self.save(ignore_permissions=True)
			return response.json()
		else:
			frappe.throw(response.json().get("error").get("message"))


def create_waba_whatsapp_message(message):
	message_type = message.get("type")
	message_data = frappe._dict(
		{
			"doctype": "WABA WhatsApp Message",
			"type": "Incoming",
			"from": message.get("from"),
			"id": message.get("id"),
			"message_type": message_type.title(),
		}
	)

	if message_type == "text":
		message_data["message_body"] = message.get("text").get("body")
	elif message_type in ("image", "sticker", "document"):
		message_data["media_id"] = message.get(message_type).get("id")
		message_data["media_mime_type"] = message.get(message_type).get("mime_type")
		message_data["media_hash"] = message.get(message_type).get("sha256")

	if message_type == "document":
		message_data["media_filename"] = message.get("document").get("filename")
		message_data["media_caption"] = message.get("document").get("caption")

	return frappe.get_doc(message_data).insert(ignore_permissions=True)


def process_status_update(status):
	message_id = status.get("id")
	status = status.get("status")

	frappe.db.set_value(
		"WABA WhatsApp Message", {"id": message_id}, "status", status.title()
	)

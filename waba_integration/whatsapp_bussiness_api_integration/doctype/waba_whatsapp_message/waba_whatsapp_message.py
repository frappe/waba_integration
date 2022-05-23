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

	@frappe.whitelist()
	def download_media(self):
		access_token = frappe.utils.password.get_decrypted_password(
			"WABA Settings", "WABA Settings", "access_token"
		)
		api_base = frappe.db.get_single_value("WABA Settings", "api_base")
		response = requests.get(
			f"{api_base}/{self.media_id}",
			headers={
				"Authorization": "Bearer " + access_token,
			},
		)

		if not response.ok:
			frappe.throw("Error fetching media URL")

		url = response.json().get("url")
		response = requests.get(
			url,
			headers={
				"Authorization": "Bearer " + access_token,
			},
		)

		file_name = self.media_filename or (
			"attachment_." + response.headers.get("Content-Type").split("/")[1]
		)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_name,
				"content": response.content,
				"attached_to_doctype": "WABA WhatsApp Message",
				"attached_to_name": self.name,
				"attached_to_field": "media_file",
			}
		).insert(ignore_permissions=True)

		self.set("media_file", file_doc.file_url)

		# Will be used to display image preview
		if self.message_type == "Image":
			self.set("media_image", file_doc.file_url)

		self.save()

		return file_doc.as_dict()


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

	message_doc = frappe.get_doc(message_data).insert(ignore_permissions=True)

	wants_automatic_image_downloads = frappe.db.get_single_value(
		"WABA Settings", "automatically_download_images"
	)
	if message_doc.message_type == "Image" and wants_automatic_image_downloads:
		message_doc.download_media()

	return message_doc


def process_status_update(status):
	message_id = status.get("id")
	status = status.get("status")

	frappe.db.set_value(
		"WABA WhatsApp Message", {"id": message_id}, "status", status.title()
	)

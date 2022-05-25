# Copyright (c) 2022, Hussain Nagaria and contributors
# For license information, please see license.txt

import frappe
import requests
import mimetypes

from typing import Dict
from functools import lru_cache
from frappe.model.document import Document


MEDIA_TYPES = ("image", "sticker", "document", "audio", "video")


class WABAWhatsAppMessage(Document):
	def validate(self):
		if self.message_type == "Audio" and self.media_file:
			self.preview_html = f"""
				<audio controls>
					<source src="{self.media_file}" type="{self.media_mime_type}">
					Your browser does not support the audio element.
				</audio>
			"""

		if self.message_type == "Video" and self.media_file:
			self.preview_html = f"""
				<video controls>
					<source src="{self.media_file}" type="{self.media_mime_type}">
					Your browser does not support the video element.
				</video>
			"""

	@frappe.whitelist()
	def send(self) -> Dict:
		if not self.to:
			frappe.throw("Recepient (`to`) is required to send message.")

		access_token = frappe.utils.password.get_decrypted_password(
			"WABA Settings", "WABA Settings", "access_token"
		)
		api_base = "https://graph.facebook.com/v13.0"
		phone_number_id = frappe.db.get_single_value("WABA Settings", "phone_number_id")

		endpoint = f"{api_base}/{phone_number_id}/messages"

		response_data = {
			"messaging_product": "whatsapp",
			"recipient_type": "individual",
			"to": self.to,
			"type": self.message_type.lower(),
		}

		if self.message_type == "Text":
			response_data["text"] = {"preview_url": False, "body": self.message_body}

		if self.message_type in ("Audio", "Image", "Video", "Document"):
			if not self.media_id:
				frappe.throw("Please attach and upload the media before sending this message.")

			response_data[self.message_type.lower()] = {
				"id": self.media_id,
			}

			if self.message_type == "Document":
				response_data[self.message_type.lower()]["filename"] = self.media_filename
				response_data[self.message_type.lower()]["caption"] = self.media_caption

		response = requests.post(
			endpoint,
			json=response_data,
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
	def download_media(self) -> Dict:
		url = self.get_media_url()
		access_token = self.get_access_token()
		response = requests.get(
			url,
			headers={
				"Authorization": "Bearer " + access_token,
			},
		)

		file_name = get_media_extention(self, response.headers.get("Content-Type"))
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

	def get_media_url(self) -> str:
		if not self.media_id:
			frappe.throw("`media_id` is missing.")

		api_base = "https://graph.facebook.com/v13.0"
		access_token = self.get_access_token()
		response = requests.get(
			f"{api_base}/{self.media_id}",
			headers={
				"Authorization": "Bearer " + access_token,
			},
		)

		if not response.ok:
			frappe.throw("Error fetching media URL")

		return response.json().get("url")

	@lru_cache
	def get_access_token(self) -> str:
		return frappe.utils.password.get_decrypted_password(
			"WABA Settings", "WABA Settings", "access_token"
		)

	@frappe.whitelist()
	def upload_media(self):
		if not self.media_file:
			frappe.throw("`media_file` is required to upload media.")

		media_file_path = frappe.get_doc(
			"File", {"file_url": self.media_file}
		).get_full_path()
		access_token = self.get_access_token()
		api_base = "https://graph.facebook.com/v13.0"
		phone_number_id = frappe.db.get_single_value("WABA Settings", "phone_number_id")

		if not self.media_mime_type:
			self.media_mime_type = mimetypes.guess_type(self.media_file)[0]

		# Way to send multi-part form data
		# Ref: https://stackoverflow.com/a/35974071
		form_data = {
			"file": (
				"file",
				open(media_file_path, "rb"),
				self.media_mime_type,
			),
			"messaging_product": (None, "whatsapp"),
			"type": (None, self.media_mime_type),
		}
		response = requests.post(
			f"{api_base}/{phone_number_id}/media",
			files=form_data,
			headers={
				"Authorization": "Bearer " + access_token,
			},
		)

		if response.ok:
			self.media_id = response.json().get("id")
			self.media_uploaded = True
			self.save(ignore_permissions=True)
		else:
			frappe.throw(response.json().get("error").get("message"))


def create_waba_whatsapp_message(message: Dict) -> WABAWhatsAppMessage:
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
	elif message_type in MEDIA_TYPES:
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

	wants_automatic_audio_downloads = frappe.db.get_single_value(
		"WABA Settings", "automatically_download_audio"
	)
	if (message_doc.message_type == "Image" and wants_automatic_image_downloads) or (
		message_doc.message_type == "Audio" and wants_automatic_audio_downloads
	):
		try:
			current_user = frappe.session.user
			frappe.set_user("Administrator")
			message_doc.download_media()
			frappe.set_user(current_user)
		except:
			frappe.log_error(
				f"WABA: Problem downloading {message_doc.message_type}", frappe.get_traceback()
			)

	return message_doc


def process_status_update(status: Dict):
	message_id = status.get("id")
	status = status.get("status")

	frappe.db.set_value(
		"WABA WhatsApp Message", {"id": message_id}, "status", status.title()
	)


def get_media_extention(message_doc: WABAWhatsAppMessage, content_type: str) -> str:
	return message_doc.media_filename or (
		"attachment_." + content_type.split(";")[0].split("/")[1]
	)

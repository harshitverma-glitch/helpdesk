"""
Helpdesk Call Recording Download API
Handles downloading and storing call recordings and transcripts from RingCentral using OAuth authentication
"""

import frappe
import requests
import re
from typing import Dict, Any, Optional


@frappe.whitelist()
def fetch_and_save_helpdesk_recording(call_log_name: str) -> Dict[str, Any]:
	"""
	Fetch recording for a Helpdesk call log and save to ERPNext
	Uses OAuth tokens from CRM RingCentral Settings (shared authentication)
	Handles both direct recording URLs and voicemail message URLs
	
	Args:
		call_log_name: Name of Helpdesk Call Log
		
	Returns:
		Dict with success status and file URL
	"""
	try:
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		
		if not call_log.recording_url:
			return {"success": False, "message": "No recording URL found"}
		
		recording_url = call_log.recording_url
		
		# Check if recording is already downloaded (local file path)
		if recording_url.startswith("/files/") or recording_url.startswith("/private/files/"):
			# Recording already stored locally
			existing_file = check_existing_file(call_log_name)
			if existing_file:
				return {"success": True, "cached": True, "file_url": existing_file}
		
		# Get OAuth access token from CRM RingCentral Settings
		try:
			from crm.api.ringcentral_auth import get_valid_access_token
			access_token = get_valid_access_token()
			
			if not access_token:
				return {"success": False, "message": "RingCentral OAuth authentication failed. Please authorize RingCentral in CRM Settings."}
		except Exception as auth_error:
			frappe.log_error(
				title="Helpdesk Recording - OAuth Token Error",
				message=f"Error getting OAuth token: {str(auth_error)}\n{frappe.get_traceback()}"
			)
			return {"success": False, "message": "Failed to get RingCentral OAuth token. Check CRM RingCentral Settings."}
		
		# Get RingCentral settings for account/extension info
		settings = frappe.get_single("CRM RingCentral Settings")
		if not settings or not settings.enabled:
			return {"success": False, "message": "RingCentral Settings not configured or disabled"}
		
		# Determine URL type and download recording
		recording_data = None
		identifier = None
		
		# Type 1: Voicemail Message URL
		# Format: https://app.ringcentral.com/messages/{messageId}
		message_match = re.search(r'/messages/(\d+)', recording_url)
		
		if message_match:
			message_id = message_match.group(1)
			identifier = f"msg_{message_id}"
			
			account_id = settings.account_id if settings.account_id else "~"
			extension_id = settings.extension_id if settings.extension_id else "~"
			
			recording_data = download_message_recording(access_token, message_id, account_id, extension_id)
		
		# Type 2: Direct Recording URL
		# Format: https://platform.ringcentral.com/restapi/v1.0/account/{accountId}/recording/{recordingId}/content
		else:
			recording_match = re.search(r'/recording/([^/]+)/content', recording_url)
			
			if recording_match:
				recording_id = recording_match.group(1)
				identifier = f"rec_{recording_id}"
				
				# Extract account ID from URL
				match_account = re.search(r'/account/([^/]+)/', recording_url)
				account_id = match_account.group(1) if match_account else settings.account_id or "~"
				
				recording_data = download_recording(access_token, recording_id, account_id)
			else:
				return {"success": False, "message": "Invalid recording URL format. Must be RingCentral message or recording URL."}
		
		if not recording_data:
			return {"success": False, "message": "Failed to download recording from RingCentral"}
		
		# Save recording to file
		file_url = save_recording_to_file(recording_data, identifier, call_log_name)
		
		if file_url:
			# Preserve original RingCentral URL for transcript fetching
			call_log.db_set('ringcentral_recording_url', recording_url, update_modified=False)
			# Update call log with local file URL
			call_log.db_set('recording_url', file_url, update_modified=True)
			frappe.db.commit()
			
			return {
				"success": True,
				"message": "Recording downloaded successfully",
				"file_url": file_url,
				"cached": False
			}
		else:
			return {"success": False, "message": "Failed to save recording to ERPNext"}
			
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Fetch Recording Error",
			message=f"Call Log: {call_log_name}\nError: {str(e)}\nTraceback: {frappe.get_traceback()}"
		)
		return {
			"success": False,
			"message": f"Error downloading recording: {str(e)}"
		}


def check_existing_file(call_log_name: str) -> Optional[str]:
	"""
	Check if recording file already exists in ERPNext
	
	Args:
		call_log_name: Name of Helpdesk Call Log
		
	Returns:
		str: File URL if exists, None otherwise
	"""
	try:
		files = frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Helpdesk Call Log",
				"attached_to_name": call_log_name,
			},
			fields=["file_url"],
			limit=1
		)
		
		if files and len(files) > 0:
			return files[0].file_url
		
		return None
		
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Recording - File Check Error",
			message=f"Call Log: {call_log_name}\nError: {str(e)}"
		)
		return None


def download_recording(access_token: str, recording_id: str, account_id: str) -> Optional[bytes]:
	"""
	Download call recording from RingCentral using OAuth token
	
	Args:
		access_token: OAuth access token
		recording_id: RingCentral recording ID
		account_id: Account ID (use "~" for current account)
		
	Returns:
		bytes: Recording file content (audio)
	"""
	try:
		server_url = "https://platform.ringcentral.com"
		
		headers = {
			"Authorization": f"Bearer {access_token}"
		}
		
		url = f"{server_url}/restapi/v1.0/account/{account_id}/recording/{recording_id}/content"
		
		response = requests.get(url, headers=headers, timeout=30)
		
		if response.status_code == 200:
			return response.content
		else:
			frappe.log_error(
				title="Helpdesk Recording Download Failed",
				message=f"Recording ID: {recording_id}\nStatus: {response.status_code}\n{response.text}"
			)
			return None
			
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Recording Download Error",
			message=f"Recording ID: {recording_id}\nError: {str(e)}"
		)
		return None


def download_message_recording(access_token: str, message_id: str, account_id: str, extension_id: str) -> Optional[bytes]:
	"""
	Download voicemail recording from RingCentral Messages using OAuth token
	
	Args:
		access_token: OAuth access token
		message_id: RingCentral message ID
		account_id: Account ID (use "~" for current account)
		extension_id: Extension ID (use "~" for current extension)
		
	Returns:
		bytes: Recording file content (audio)
	"""
	try:
		server_url = "https://platform.ringcentral.com"
		
		headers = {
			"Authorization": f"Bearer {access_token}"
		}
		
		# First, get the message to find the attachment ID
		msg_url = f"{server_url}/restapi/v1.0/account/{account_id}/extension/{extension_id}/message-store/{message_id}"
		msg_response = requests.get(msg_url, headers=headers, timeout=30)
		
		if msg_response.status_code != 200:
			frappe.log_error(
				title="Helpdesk Message Fetch Failed",
				message=f"Message ID: {message_id}\nStatus: {msg_response.status_code}\n{msg_response.text}"
			)
			return None
		
		message_data = msg_response.json()
		
		# Get the attachment (recording)
		attachments = message_data.get("attachments", [])
		if not attachments:
			frappe.log_error(
				title="Helpdesk No Recording Attachment",
				message=f"Message ID: {message_id}\nMessage has no attachments"
			)
			return None
		
		# Get the first audio attachment
		audio_attachment = None
		for att in attachments:
			if att.get("contentType", "").startswith("audio/"):
				audio_attachment = att
				break
		
		if not audio_attachment:
			return None
		
		# Download the attachment
		attachment_id = audio_attachment.get("id")
		content_url = f"{server_url}/restapi/v1.0/account/{account_id}/extension/{extension_id}/message-store/{message_id}/content/{attachment_id}"
		
		content_response = requests.get(content_url, headers=headers, timeout=60)
		
		if content_response.status_code == 200:
			return content_response.content
		else:
			frappe.log_error(
				title="Helpdesk Recording Content Download Failed",
				message=f"Message ID: {message_id}\nAttachment ID: {attachment_id}\nStatus: {content_response.status_code}"
			)
			return None
			
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Message Recording Error",
			message=f"Message ID: {message_id}\nError: {str(e)}"
		)
		return None


def save_recording_to_file(recording_data: bytes, identifier: str, call_log_name: str) -> Optional[str]:
	"""
	Save recording data as File in ERPNext
	
	Args:
		recording_data: Binary audio data
		identifier: Recording or message ID for filename
		call_log_name: Name of Helpdesk Call Log to attach to
		
	Returns:
		str: File URL in ERPNext
	"""
	try:
		if not recording_data:
			return None
		
		# Create File in ERPNext
		from frappe.utils.file_manager import save_file
		
		filename = f"helpdesk_call_recording_{identifier}.mp3"
		
		# Save as PUBLIC file (is_private=0) so HTML5 audio player can access it
		file_doc = save_file(
			fname=filename,
			content=recording_data,
			dt="Helpdesk Call Log",
			dn=call_log_name,
			is_private=0  # Makes file publicly accessible for audio player
		)
		
		return file_doc.file_url
		
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Recording Save Error",
			message=f"Identifier: {identifier}\nCall Log: {call_log_name}\nError: {str(e)}"
		)
		return None



"""
RingCentral Integration Utilities for Helpdesk
Handles parsing and processing of RingCentral webhook payloads
"""

import frappe
import json
import re
from typing import Dict, Any, Optional


def parse_ringcentral_payload(raw_payload: str) -> Dict[str, Any]:
	"""
	Parse RingCentral JSON payload and extract call details
	
	Args:
		raw_payload: JSON string or dict from RingCentral webhook (Body Parties array)
		
	Returns:
		dict with extracted fields: session_id, caller_number, 
		called_number, direction, duration, status, timestamps, etc.
	"""
	try:
		# Handle if already dict
		if isinstance(raw_payload, str):
			payload_data = json.loads(raw_payload)
		else:
			payload_data = raw_payload
			
		# RingCentral sends an array of parties - get the first one
		if isinstance(payload_data, list) and len(payload_data) > 0:
			party = payload_data[0]
		elif isinstance(payload_data, dict):
			party = payload_data
		else:
			frappe.throw("Invalid payload format")
			
		# Extract call details
		
		# Get caller name from uiCallInfo.additional if available (more accurate)
		caller_name = party.get("from", {}).get("name", "")
		from_ui_call_info = False
		
		ui_call_info = party.get("uiCallInfo", {})
		if ui_call_info and ui_call_info.get("additional", {}).get("type") == "CallerIdName":
			caller_name = ui_call_info.get("additional", {}).get("value", caller_name)
			from_ui_call_info = True  # Flag that this came from uiCallInfo
		
		# RingCentral sends names in "LAST FIRST" format from uiCallInfo.additional
		# Always swap if it came from there
		if from_ui_call_info and caller_name and " " in caller_name:
			parts = caller_name.strip().split()  # Split all parts
			if len(parts) >= 2:
				# Assume LAST word is FIRST name, everything before is LAST name
				# Examples:
				#   "BERG JOHN" → "JOHN BERG"
				#   "VON BERG JOHN" → "JOHN VON BERG"
				#   "SMITH MARY JANE" → "MARY JANE SMITH"
				first_name = parts[-1]  # Last word
				last_name = " ".join(parts[:-1])  # Everything before last word
				caller_name = f"{first_name} {last_name}"
		
		# Extract recording ID from recordings array
		recording_id = ""
		recordings = party.get("recordings", [])
		if recordings and isinstance(recordings, list) and len(recordings) > 0:
			recording_id = recordings[0].get("id", "")
		
		call_data = {
			"party_id": party.get("id", ""),
			"account_id": party.get("accountId", ""),
			"extension_id": party.get("extensionId", ""),
			"direction": party.get("direction", ""),
			"caller_number": party.get("from", {}).get("phoneNumber", ""),
			"caller_name": caller_name,  # Use cleaned caller name from uiCallInfo
			"caller_extension_id": party.get("from", {}).get("extensionId", ""),
			"caller_device_id": party.get("from", {}).get("deviceId", ""),
			"called_number": party.get("to", {}).get("phoneNumber", ""),
			"called_name": party.get("to", {}).get("name", ""),
			"called_extension_id": party.get("to", {}).get("extensionId", ""),
			"status_code": party.get("status", {}).get("code", ""),
			"status_rcc": party.get("status", {}).get("rcc", False),
			"missed_call": party.get("missedCall", False),
			"stand_alone": party.get("standAlone", False),
			"muted": party.get("muted", False),
			"park": party.get("park", []),
			# Extract voicemail/message data
			"message": party.get("message", {}),
			"vm_duration": party.get("message", {}).get("vmDuration", 0) if party.get("message") else 0,
			"message_id": party.get("message", {}).get("messageId", "") if party.get("message") else "",
			# Extract recording ID from recordings array
			"recording_id": recording_id,
		}
		
		return call_data
		
	except json.JSONDecodeError as e:
		frappe.log_error(
			title="RingCentral Payload Parse Error",
			message=f"Failed to parse JSON: {str(e)}\n\nPayload: {raw_payload[:500]}"
		)
		frappe.throw(f"Invalid JSON payload: {str(e)}")
	except Exception as e:
		frappe.log_error(
			title="RingCentral Payload Parse Error",
			message=f"Error: {str(e)}\n\nPayload: {raw_payload[:500] if isinstance(raw_payload, str) else str(raw_payload)[:500]}"
		)
		frappe.throw(f"Error parsing payload: {str(e)}")


def normalize_phone_number(phone: str) -> str:
	"""
	Normalize phone number for matching
	Removes +, spaces, dashes, parentheses
	
	Args:
		phone: Raw phone number string
		
	Returns:
		Normalized phone string (digits only)
	"""
	if not phone:
		return ""
	
	# Remove all non-digit characters
	normalized = re.sub(r'[^\d]', '', phone)
	
	return normalized


def format_duration(seconds: int) -> str:
	"""
	Format duration in human readable format
	
	Args:
		seconds: Duration in seconds (int)
		
	Returns:
		Formatted string like "2m 30s" or "1h 15m 30s"
	"""
	if not seconds or seconds == 0:
		return "0s"
		
	hours = seconds // 3600
	minutes = (seconds % 3600) // 60
	secs = seconds % 60
	
	parts = []
	if hours > 0:
		parts.append(f"{hours}h")
	if minutes > 0:
		parts.append(f"{minutes}m")
	if secs > 0 or not parts:  # Always show seconds if no other parts
		parts.append(f"{secs}s")
		
	return " ".join(parts)


def get_call_status_mapping(ringcentral_status: str) -> str:
	"""
	Map RingCentral call status to Helpdesk Call Log status options
	
	Args:
		ringcentral_status: Status from RingCentral (e.g., "Disconnected", "Connected")
		
	Returns:
		One of: Initiated, Ringing, In Progress, Completed, Failed, Busy, No Answer, Queued, Canceled
	"""
	status_map = {
		"Disconnected": "Completed",
		"Connected": "In Progress",
		"Gone": "No Answer",
		"Busy": "Busy",
		"NoAnswer": "No Answer",
		"Failed": "Failed",
		"Rejected": "Canceled",
		"Replied": "Completed",
		"Received": "Completed",
		"FaxOnDemand": "Completed",
		"VoiceMail": "No Answer",
		"Setup": "Initiated",
		"Proceeding": "Ringing",
	}
	
	return status_map.get(ringcentral_status, "Completed")


def get_call_type(direction: str) -> str:
	"""
	Map RingCentral direction to Helpdesk Call Log type
	
	Args:
		direction: "Inbound" or "Outbound"
		
	Returns:
		"Incoming" or "Outgoing"
	"""
	if direction and direction.lower() == "inbound":
		return "Incoming"
	elif direction and direction.lower() == "outbound":
		return "Outgoing"
	else:
		return "Incoming"  # Default


def find_contact_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
	"""
	Find an existing Contact by phone number
	
	Args:
		phone_number: Phone number to search for (will be normalized)
		
	Returns:
		Dict with contact details if found, None otherwise
	"""
	if not phone_number:
		return None
		
	normalized = normalize_phone_number(phone_number)
	
	if not normalized:
		return None
	
	# Try to find by phone field
	contact = frappe.db.get_value(
		"Contact",
		{"phone": ["like", f"%{normalized}%"]},
		["name", "full_name", "email_id", "phone"],
		as_dict=True
	)
	
	if contact:
		return contact
	
	# Try mobile_no field
	contact = frappe.db.get_value(
		"Contact",
		{"mobile_no": ["like", f"%{normalized}%"]},
		["name", "full_name", "email_id", "phone", "mobile_no"],
		as_dict=True
	)
	
	return contact


def create_ticket_from_call(call_data: Dict[str, Any], caller_number: str, existing_contact_name: str = None) -> Dict[str, Any]:
	"""
	Create a new HD Ticket from call data
	
	Args:
		call_data: Parsed call data from RingCentral
		caller_number: Normalized caller phone number
		existing_contact_name: Optional existing contact to link to ticket
		
	Returns:
		Dict with created ticket and contact details
	"""
	caller_name = call_data.get("caller_name") or "Unknown Caller"
	
	# If no existing contact, create one first
	contact_name = existing_contact_name
	raised_by_email = None
	
	if not contact_name:
		# Create new contact first (HD Ticket doesn't auto-create contacts)
		raised_by_email = f"{caller_number}@ringcentral.phone"
		
		try:
			new_contact = frappe.get_doc({
				"doctype": "Contact",
				"first_name": caller_name,
				"full_name": caller_name,
				"mobile_no": caller_number,
				"phone": caller_number,
				"email_id": raised_by_email,
			})
			new_contact.insert(ignore_permissions=True)
			frappe.db.commit()  # Commit contact so it's available for ticket fetch
			contact_name = new_contact.name
			frappe.logger().info(f"✅ Created new contact: {contact_name} - {caller_name} with phone: {caller_number}")
		except Exception as e:
			frappe.logger().error(f"❌ Failed to create contact: {str(e)}")
			# Continue anyway, ticket can be created without contact
			contact_name = None
	else:
		# Get email from existing contact and update phone if missing
		contact_email = frappe.db.get_value("Contact", existing_contact_name, "email_id")
		raised_by_email = contact_email if contact_email else f"{caller_number}@ringcentral.phone"
		
		# Update contact phone numbers if they're empty
		try:
			contact_doc = frappe.get_doc("Contact", existing_contact_name)
			updated = False
			
			if not contact_doc.phone:
				contact_doc.phone = caller_number
				updated = True
			
			if not contact_doc.mobile_no:
				contact_doc.mobile_no = caller_number
				updated = True
			
			if updated:
				contact_doc.save(ignore_permissions=True)
				frappe.db.commit()  # Commit contact updates
				frappe.logger().info(f"✅ Updated phone numbers for contact: {existing_contact_name} to: {caller_number}")
		except Exception as e:
			frappe.logger().error(f"❌ Failed to update contact phone: {str(e)}")
	
	# Create ticket with contact link
	ticket_data = {
		"doctype": "HD Ticket",
		"subject": f"Call from {caller_name}",
		"raised_by": raised_by_email,  # Must be valid email
		"status": "Open",
		"priority": "Medium",
		"description": f"Incoming call received at {frappe.utils.now()}\nCaller: {caller_name}\nPhone: {caller_number}",
		"contact_email": raised_by_email,
	}
	
	# Link contact to ticket
	if contact_name:
		ticket_data["contact"] = contact_name
	
	ticket = frappe.get_doc(ticket_data)
	ticket.insert(ignore_permissions=True)
	
	# Set contact_mobile AFTER insert to bypass the fetch_from logic
	# This ensures we use the call log's phone number, not the contact's mobile_no
	ticket.db_set('contact_mobile', caller_number, update_modified=False)
	
	frappe.db.commit()
	
	return {
		"ticket_name": ticket.name,
		"contact_name": contact_name,
		"subject": ticket.subject
	}


def create_call_log(call_data: Dict[str, Any], contact_name: str, ticket_name: Optional[str], session_id: str) -> str:
	"""
	Create a Helpdesk Call Log entry
	
	Args:
		call_data: Parsed call data from RingCentral
		contact_name: Name of the linked Contact
		ticket_name: Name of the linked HD Ticket (optional)
		session_id: RingCentral session ID
		
	Returns:
		Name of created call log
	"""
	# Find Customer linked to Contact (if exists)
	customer_name = None
	if contact_name:
		# Check if Contact has linked Customers
		customer_links = frappe.db.get_all(
			"Dynamic Link",
			filters={
				"link_doctype": "Contact",
				"link_name": contact_name,
				"parenttype": "Customer"
			},
			fields=["parent"],
			limit=1
		)
		if customer_links:
			customer_name = customer_links[0].parent
	
	# Check if we have vmDuration from voicemail, otherwise wait for background job
	vm_duration = call_data.get("vm_duration", 0)
	duration_text = format_duration(vm_duration) if vm_duration else "0s"
	
	# Build recording URL (same logic as CRM)
	recording_url = None
	recording_id = call_data.get("recording_id", "")
	message_id = call_data.get("message_id", "")
	account_id = call_data.get("account_id", "")
	extension_id = call_data.get("extension_id", "")
	
	# Option 1: Direct recording URL (if recording ID exists)
	if recording_id and account_id:
		recording_url = f"https://platform.ringcentral.com/restapi/v1.0/account/{account_id}/recording/{recording_id}/content"
	
	# Option 2: Voicemail message - Use RingCentral App deep link
	elif message_id and extension_id:
		# Deep link to voicemail in RingCentral app (most reliable)
		recording_url = f"https://app.ringcentral.com/messages/{message_id}"
	
	call_log = frappe.get_doc({
		"doctype": "Helpdesk Call Log",
		"call_id": call_data.get("party_id") or session_id,
		"from_number": call_data.get("caller_number", ""),
		"to_number": call_data.get("called_number", ""),
		"caller_name": call_data.get("caller_name", ""),
		"type": get_call_type(call_data.get("direction", "")),
		"status": get_call_status_mapping(call_data.get("status_code", "")),
		"duration": duration_text,  # Use vmDuration if available, otherwise wait for background job
		"telephony_medium": "RingCentral",
		"customer": customer_name,  # Link to Customer (not Contact)
		"ticket": ticket_name,
		"start_time": frappe.utils.now(),
		"recording_url": recording_url,  # RingCentral recording URL
		"ringcentral_recording_url": recording_url,  # Preserve original URL for transcript fetching
	})
	
	call_log.insert(ignore_permissions=True)
	frappe.db.commit()
	
	return call_log.name


def transcribe_recording(call_log_name: str) -> Dict[str, Any]:
	"""
	Transcribe call recording using RingCentral native transcription
	
	Args:
		call_log_name: Name of Helpdesk Call Log
		
	Returns:
		Dict with transcript text
	"""
	try:
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		
		# Check if transcript already exists
		if call_log.transcript:
			return {
				"success": True,
				"message": "Transcript already exists",
				"transcript": call_log.transcript,
				"cached": True
			}
		
		# Try to use preserved RingCentral URL first, fallback to recording_url
		url_to_use = getattr(call_log, 'ringcentral_recording_url', None) or call_log.recording_url
		
		if not url_to_use:
			return {"success": False, "message": "No recording URL found"}
		
		# Extract recording ID from URL
		import re
		
		# Check if it's a local file (already downloaded)
		if url_to_use.startswith("/files/") or url_to_use.startswith("/private/files/"):
			return {
				"success": False,
				"message": "Recording is stored locally. Transcripts can only be fetched from RingCentral URLs. Please try fetching before the recording is downloaded."
			}
		
		# Try direct recording URL format
		recording_match = re.search(r'/recording/([^/]+)/content', url_to_use)
		if recording_match:
			recording_id = recording_match.group(1)
		else:
			# Try message URL format (voicemail)
			message_match = re.search(r'/messages/(\d+)', url_to_use)
			if message_match:
				recording_id = f"message_{message_match.group(1)}"
			else:
				# Try alternative recording format without /content
				recording_match_alt = re.search(r'/recording/([^/]+)$', url_to_use)
				if recording_match_alt:
					recording_id = recording_match_alt.group(1)
				else:
					return {
						"success": False,
						"message": f"Could not extract recording ID from URL: {url_to_use}"
					}
		
		# Initialize and authenticate RingCentral client
		from crm.integrations.ringcentral_client import RingCentralClient
		
		client = RingCentralClient()
		
		# Get account ID from CRM settings
		settings = frappe.get_single("CRM RingCentral Settings")
		account_id = settings.account_id if settings and settings.account_id else "~"
		
		if not client.authenticate_auto(account_id=account_id):
			return {"success": False, "message": "Failed to authenticate with RingCentral"}
		
		# Get transcript from RingCentral
		transcript = client.get_ringcentral_transcript(recording_id, account_id)
		
		if transcript:
			# Save transcript directly to call log field
			call_log.db_set('transcript', transcript, update_modified=True)
			frappe.db.commit()
			
			frappe.logger().info(f"✅ RingCentral transcription successful for {call_log_name}")
			
			return {
				"success": True,
				"message": "Transcript generated successfully",
				"transcript": transcript,
				"cached": False
			}
		else:
			return {
				"success": False,
				"message": "RingCentral transcription not available for this recording. The recording may not have been transcribed yet, or transcription may not be enabled for your RingCentral account."
			}
			
	except Exception as e:
		frappe.log_error(
			title="Transcription Error",
			message=f"Call Log: {call_log_name}\nError: {str(e)}\n{frappe.get_traceback()}"
		)
		return {"success": False, "message": f"Error: {str(e)}"}


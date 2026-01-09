# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from helpdesk.integrations.ringcentral_utils import (
	parse_ringcentral_payload,
	normalize_phone_number,
	find_contact_by_phone,
	create_ticket_from_call,
	create_call_log
)


class RingCentralHelpdeskPayload(Document):
	def after_insert(self):
		"""Process payload immediately after creation"""
		# Enqueue processing to avoid blocking the webhook response
		frappe.enqueue(
			process_helpdesk_payload,
			queue='default',
			timeout=300,
			payload_name=self.name
		)


def process_helpdesk_payload(payload_name: str):
	"""
	Background job to process Helpdesk payload
	
	Args:
		payload_name: Name of the RingCentral Helpdesk Payload document
	"""
	try:
		payload = frappe.get_doc("RingCentral Helpdesk Payload", payload_name)
		
		# Skip if already processed
		if payload.processed:
			frappe.logger().info(f"Payload {payload_name} already processed, skipping")
			return
		
		# Mark as processing
		payload.db_set('processing_status', 'Processing', update_modified=False)
		frappe.db.commit()
		
		# Parse the raw payload
		if not payload.raw_payload:
			raise Exception("No raw_payload data found")
		
		call_data = parse_ringcentral_payload(payload.raw_payload)
		
		# Get caller phone number
		caller_number = call_data.get('caller_number', '')
		normalized_caller = normalize_phone_number(caller_number)
		
		if not normalized_caller:
			raise Exception("No valid caller number found in payload")
		
		# Search for existing contact by phone
		contact = find_contact_by_phone(normalized_caller)
		
		ticket_name = None
		contact_name = None
		
		# Always create ticket for inbound calls
		if contact:
			frappe.logger().info(f"Found existing contact: {contact['name']} for {normalized_caller}")
			contact_name = contact['name']
			# Create ticket with existing contact - use original caller_number (with formatting)
			ticket_result = create_ticket_from_call(call_data, caller_number, contact_name)
			ticket_name = ticket_result['ticket_name']
		else:
			# No contact found - create ticket (which auto-creates contact) - use original caller_number
			frappe.logger().info(f"No contact found for {normalized_caller}, creating ticket")
			ticket_result = create_ticket_from_call(call_data, caller_number)
			ticket_name = ticket_result['ticket_name']
			contact_name = ticket_result['contact_name']
		
		# Create Helpdesk Call Log
		call_log_name = create_call_log(
			call_data=call_data,
			contact_name=contact_name,
			ticket_name=ticket_name,
			session_id=payload.session_id or payload.uuid
		)
		
		# Update payload record with processing results
		payload.db_set('processed', 1, update_modified=False)
		payload.db_set('processing_status', 'Processed', update_modified=False)
		payload.db_set('processed_at', frappe.utils.now(), update_modified=False)
		payload.db_set('contact_created', contact_name, update_modified=False)
		payload.db_set('helpdesk_call_log_created', call_log_name, update_modified=False)
		
		processing_notes = f"Contact: {contact_name}, Call Log: {call_log_name}"
		if ticket_name:
			payload.db_set('ticket_created', ticket_name, update_modified=False)
			processing_notes += f", Ticket: {ticket_name}"
		
		payload.db_set('processing_notes', processing_notes, update_modified=False)
		
		frappe.db.commit()
		
		frappe.logger().info(f"Successfully processed payload {payload_name}: Contact={contact_name}, CallLog={call_log_name}, Ticket={ticket_name or 'None'}")
		
	except Exception as e:
		error_message = str(e)
		frappe.logger().error(f"Error processing Helpdesk payload {payload_name}: {error_message}")
		frappe.log_error(
			title=f"RingCentral Helpdesk Payload Processing Error - {payload_name}",
			message=frappe.get_traceback()
		)
		
		# Update payload with error status
		try:
			payload = frappe.get_doc("RingCentral Helpdesk Payload", payload_name)
			payload.db_set('processing_status', 'Error', update_modified=False)
			payload.db_set('error_message', error_message[:500], update_modified=False)
			frappe.db.commit()
		except:
			pass

"""
Utility functions for managing phone numbers and call logs across HD Tickets
"""

import frappe
from helpdesk.integrations.ringcentral_utils import normalize_phone_number


@frappe.whitelist()
def merge_call_logs_by_phone(ticket_name: str):
	"""
	Manually trigger call log merging for a ticket based on its phone number
	
	This is useful for:
	- Manually fixing historical tickets
	- Running bulk updates
	
	Args:
		ticket_name: Name of the HD Ticket to merge call logs into
		
	Returns:
		dict with status and count of transferred logs
	"""
	ticket = frappe.get_doc("HD Ticket", ticket_name)
	
	if not ticket.contact_mobile:
		return {
			"status": "error",
			"message": "Ticket has no phone number set"
		}
	
	# Normalize the phone number for matching
	normalized_phone = normalize_phone_number(ticket.contact_mobile)
	
	if not normalized_phone:
		return {
			"status": "error",
			"message": "Invalid phone number format"
		}
	
	# Find other tickets with the same phone number (excluding this ticket)
	filters = {
		"name": ["!=", ticket.name],
		"contact_mobile": ["like", f"%{normalized_phone}%"]
	}
	
	other_tickets = frappe.get_all(
		"HD Ticket",
		filters=filters,
		fields=["name", "contact_mobile", "subject", "creation"]
	)
	
	if not other_tickets:
		return {
			"status": "success",
			"message": "No other tickets found with this phone number",
			"transferred_count": 0,
			"source_tickets": []
		}
	
	# Get call logs from those tickets
	other_ticket_names = [t.name for t in other_tickets]
	
	call_logs = frappe.get_all(
		"Helpdesk Call Log",
		filters={
			"ticket": ["in", other_ticket_names]
		},
		fields=["name", "ticket", "from_number", "caller_name", "start_time"]
	)
	
	if not call_logs:
		return {
			"status": "success",
			"message": f"Found {len(other_tickets)} ticket(s) but no call logs to transfer",
			"transferred_count": 0,
			"source_tickets": [{"name": t.name, "subject": t.subject} for t in other_tickets]
		}
	
	# Transfer call logs to this ticket
	transferred_count = 0
	for call_log in call_logs:
		try:
			frappe.db.set_value(
				"Helpdesk Call Log",
				call_log.name,
				"ticket",
				ticket.name,
				update_modified=False
			)
			transferred_count += 1
		except Exception as e:
			frappe.log_error(
				title=f"Failed to transfer call log {call_log.name}",
				message=str(e)
			)
	
	frappe.db.commit()
	
	return {
		"status": "success",
		"message": f"Successfully transferred {transferred_count} call log(s)",
		"transferred_count": transferred_count,
		"source_tickets": [{"name": t.name, "subject": t.subject} for t in other_tickets],
		"call_logs": [{"name": cl.name, "caller_name": cl.caller_name, "from": cl.from_number} for cl in call_logs]
	}


@frappe.whitelist()
def find_duplicate_tickets_by_phone(phone_number: str):
	"""
	Find all tickets with a specific phone number
	
	Args:
		phone_number: Phone number to search for
		
	Returns:
		list of tickets with the phone number
	"""
	if not phone_number:
		return []
	
	normalized_phone = normalize_phone_number(phone_number)
	
	if not normalized_phone:
		return []
	
	tickets = frappe.get_all(
		"HD Ticket",
		filters={
			"contact_mobile": ["like", f"%{normalized_phone}%"]
		},
		fields=["name", "subject", "status", "contact_mobile", "raised_by", "creation"],
		order_by="creation desc"
	)
	
	# Also get call log counts for each ticket
	for ticket in tickets:
		call_log_count = frappe.db.count(
			"Helpdesk Call Log",
			{"ticket": ticket.name}
		)
		ticket["call_log_count"] = call_log_count
	
	return tickets


@frappe.whitelist()
def bulk_merge_duplicate_tickets():
	"""
	Find all phone numbers that have multiple tickets and merge call logs
	to the oldest ticket for each phone number
	
	This is useful for cleaning up historical data
	
	Returns:
		dict with summary of operations
	"""
	# Get all tickets with phone numbers
	tickets = frappe.get_all(
		"HD Ticket",
		filters={
			"contact_mobile": ["!=", ""]
		},
		fields=["name", "contact_mobile", "creation"],
		order_by="creation asc"
	)
	
	# Group by normalized phone number
	phone_groups = {}
	for ticket in tickets:
		normalized = normalize_phone_number(ticket.contact_mobile)
		if normalized:
			if normalized not in phone_groups:
				phone_groups[normalized] = []
			phone_groups[normalized].append(ticket)
	
	# Process groups with duplicates
	results = []
	total_transferred = 0
	
	for phone, ticket_list in phone_groups.items():
		if len(ticket_list) > 1:
			# Use the oldest ticket as the target
			target_ticket = ticket_list[0]  # Already sorted by creation asc
			source_tickets = [t.name for t in ticket_list[1:]]
			
			# Get call logs from source tickets
			call_logs = frappe.get_all(
				"Helpdesk Call Log",
				filters={
					"ticket": ["in", source_tickets]
				},
				fields=["name"]
			)
			
			if call_logs:
				# Transfer to target ticket
				for call_log in call_logs:
					frappe.db.set_value(
						"Helpdesk Call Log",
						call_log.name,
						"ticket",
						target_ticket.name,
						update_modified=False
					)
				
				total_transferred += len(call_logs)
				results.append({
					"phone": phone,
					"target_ticket": target_ticket.name,
					"source_tickets": source_tickets,
					"transferred_count": len(call_logs)
				})
	
	frappe.db.commit()
	
	return {
		"status": "success",
		"total_phone_numbers_processed": len(results),
		"total_call_logs_transferred": total_transferred,
		"details": results
	}


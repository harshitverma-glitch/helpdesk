import frappe
from frappe.utils import now
import uuid


@frappe.whitelist()
def create_manual_call_log(phone_number, contact_name=None, ticket_id=None):
	"""
	Create a manual call log when user clicks the RingCentral call button from Helpdesk
	
	Args:
		phone_number: Phone number being called
		contact_name: Name of contact (if available)
		ticket_id: HD Ticket ID if calling from a ticket
		
	Returns:
		Name of created call log
	"""
	try:
		# Generate unique ID for manual call
		call_id = f"manual-{uuid.uuid4().hex[:12]}"
		
		# Try to find associated ticket or customer
		ticket = None
		customer = None
		
		if ticket_id:
			ticket = ticket_id
			# Try to get customer from ticket
			customer = frappe.db.get_value("HD Ticket", ticket_id, "customer")
		
		# If no ticket provided, try to find ticket by phone number
		if not ticket:
			from helpdesk.helpdesk.integrations.ringcentral_utils import normalize_phone_number
			normalized_phone = normalize_phone_number(phone_number)
			
			# Check for existing contact with this phone
			existing_contact = frappe.db.get_value(
				"Contact",
				{"mobile_no": ["in", [phone_number, normalized_phone]]},
				["name", "full_name"],
				as_dict=True
			)
			
			# If contact found, try to find their most recent ticket
			if existing_contact:
				recent_ticket = frappe.db.get_value(
					"HD Ticket",
					{"contact": existing_contact.name},
					["name", "customer"],
					order_by="creation desc",
					as_dict=True
				)
				if recent_ticket:
					ticket = recent_ticket.name
					customer = recent_ticket.customer
		
		# Get current user's full name for caller name
		current_user = frappe.session.user
		caller_full_name = frappe.get_value("User", current_user, "full_name") or current_user
		
		# For receiver, use the contact name being called if provided
		receiver_name = contact_name or phone_number
		
		# Create call log
		call_log = frappe.get_doc({
			"doctype": "Helpdesk Call Log",
			"call_id": call_id,
			"from_number": current_user,  # Current user making the call
			"to_number": phone_number,
			"caller_name": receiver_name,  # The person being called
			"type": "Outgoing",
			"status": "Initiated",
			"duration": "0s",
			"telephony_medium": "RingCentral",
			"start_time": now(),
			"ticket": ticket,
			"customer": customer,
			"source": "Manual Call from Helpdesk",
			"created_by_user": current_user,
		})
		
		call_log.insert(ignore_permissions=True)
		frappe.db.commit()
		
		return {
			"success": True,
			"call_log_id": call_log.name,
			"message": "Call log created successfully"
		}
		
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Manual Call Log Error",
			message=f"Phone: {phone_number}\nError: {str(e)}\nTraceback: {frappe.get_traceback()}"
		)
		return {
			"success": False,
			"message": f"Error creating call log: {str(e)}"
		}


@frappe.whitelist()
def get_contact_by_phone(number):
	"""
	Get contact details by phone number for Helpdesk
	
	Args:
		number: Phone number to search
		
	Returns:
		Contact details or None
	"""
	try:
		from helpdesk.helpdesk.integrations.ringcentral_utils import normalize_phone_number
		
		normalized = normalize_phone_number(number)
		
		# Search for contact
		contact = frappe.db.get_value(
			"Contact",
			{"mobile_no": ["in", [number, normalized]]},
			["name", "full_name", "mobile_no", "image"],
			as_dict=True
		)
		
		if contact:
			return {
				"name": contact.name,
				"full_name": contact.full_name,
				"mobile_no": contact.mobile_no,
				"image": contact.image,
			}
		
		return None
		
	except Exception as e:
		frappe.log_error(
			title="Helpdesk Get Contact Error",
			message=f"Phone: {number}\nError: {str(e)}"
		)
		return None


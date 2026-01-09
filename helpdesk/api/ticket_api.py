"""
API endpoints for HD Ticket operations
"""

import frappe


@frappe.whitelist()
def update_ticket_mobile(ticket_name: str, mobile_no: str):
	"""
	Update the mobile number for a ticket and its linked contact
	
	This ensures the phone number persists correctly even with fetch_from field
	
	Args:
		ticket_name: Name of the HD Ticket
		mobile_no: New mobile number to set
		
	Returns:
		dict with success status and updated ticket data
	"""
	try:
		ticket = frappe.get_doc("HD Ticket", ticket_name)
		
		# Update ticket's contact_mobile
		ticket.contact_mobile = mobile_no
		
		# Save the ticket (this will trigger handle_phone_number_update)
		ticket.save(ignore_permissions=True)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": "Mobile number updated successfully",
			"ticket": {
				"name": ticket.name,
				"contact_mobile": ticket.contact_mobile
			}
		}
		
	except Exception as e:
		frappe.log_error(
			title=f"Failed to update mobile number for ticket {ticket_name}",
			message=str(e)
		)
		return {
			"success": False,
			"message": str(e)
		}


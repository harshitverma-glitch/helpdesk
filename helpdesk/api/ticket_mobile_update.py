"""
API endpoint for updating ticket mobile number with proper Contact sync
"""

import frappe


@frappe.whitelist()
def update_ticket_mobile(ticket_name: str, mobile_no: str):
	"""
	Update ticket mobile number and sync with Contact
	
	This endpoint ensures:
	1. Ticket's contact_mobile is updated
	2. Linked Contact's mobile_no is updated
	3. Both persist correctly across reloads
	
	Args:
		ticket_name: Name of HD Ticket
		mobile_no: New mobile number
		
	Returns:
		dict with success status
	"""
	try:
		# Get the ticket
		ticket = frappe.get_doc("HD Ticket", ticket_name)
		
		# Update the Contact first (if linked)
		if ticket.contact:
			contact = frappe.get_doc("Contact", ticket.contact)
			
			# Update mobile_no
			contact.mobile_no = mobile_no
			
			# Also update phone if empty
			if not contact.phone:
				contact.phone = mobile_no
			
			# Save contact
			contact.save(ignore_permissions=True)
			frappe.db.commit()
			
			frappe.logger().info(f"✅ Updated Contact {ticket.contact} mobile_no to {mobile_no}")
		
		# Now update the ticket
		# This will trigger handle_phone_number_update() hook
		ticket.contact_mobile = mobile_no
		ticket.save(ignore_permissions=True)
		frappe.db.commit()
		
		frappe.logger().info(f"✅ Updated Ticket {ticket_name} contact_mobile to {mobile_no}")
		
		return {
			"success": True,
			"message": "Mobile number updated successfully",
			"contact_mobile": ticket.contact_mobile,
			"contact_updated": bool(ticket.contact)
		}
		
	except Exception as e:
		frappe.log_error(
			title=f"Failed to update mobile for ticket {ticket_name}",
			message=str(e)
		)
		return {
			"success": False,
			"message": str(e)
		}


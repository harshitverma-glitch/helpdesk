import frappe


@frappe.whitelist()
def update_existing_contacts_from_payloads():
	"""
	Update existing contacts with phone numbers from their associated payloads
	This is a one-time script to fix contacts that were created before the phone update fix
	"""
	try:
		# Get all processed payloads that have contacts
		payloads = frappe.db.sql("""
			SELECT 
				name,
				contact_created,
				caller_number,
				caller_name
			FROM `tabRingCentral Helpdesk Payload`
			WHERE processed = 1
			AND contact_created IS NOT NULL
			AND contact_created != ''
			AND caller_number IS NOT NULL
			AND caller_number != ''
		""", as_dict=True)
		
		results = {
			"total": len(payloads),
			"updated": 0,
			"skipped": 0,
			"errors": []
		}
		
		for payload in payloads:
			try:
				contact_name = payload.contact_created
				caller_number = payload.caller_number
				
				# Get the contact
				contact = frappe.get_doc("Contact", contact_name)
				updated = False
				
				# Update phone if empty
				if not contact.phone:
					contact.phone = caller_number
					updated = True
				
				# Update mobile_no if empty
				if not contact.mobile_no:
					contact.mobile_no = caller_number
					updated = True
				
				if updated:
					contact.save(ignore_permissions=True)
					results["updated"] += 1
					frappe.logger().info(f"✅ Updated contact {contact_name} with phone {caller_number}")
				else:
					results["skipped"] += 1
					frappe.logger().info(f"⏭️  Skipped contact {contact_name} - phone already set")
				
			except Exception as e:
				results["errors"].append({
					"payload": payload.name,
					"contact": payload.contact_created,
					"error": str(e)
				})
				frappe.logger().error(f"❌ Failed to update contact {payload.contact_created}: {str(e)}")
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Updated {results['updated']} contacts, skipped {results['skipped']}, errors {len(results['errors'])}",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(
			title="Update Contacts from Payloads Error",
			message=str(e)
		)
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def reprocess_single_payload(payload_name):
	"""
	Reprocess a single payload to update contact phone numbers
	
	Args:
		payload_name: Name of the RingCentral Helpdesk Payload to reprocess
	"""
	try:
		from helpdesk.helpdesk.doctype.ringcentral_helpdesk_payload.ringcentral_helpdesk_payload import process_helpdesk_payload
		
		# Get the payload
		payload = frappe.get_doc("RingCentral Helpdesk Payload", payload_name)
		
		# If it has a contact, update the contact's phone
		if payload.contact_created and payload.caller_number:
			try:
				contact = frappe.get_doc("Contact", payload.contact_created)
				updated = False
				
				if not contact.phone:
					contact.phone = payload.caller_number
					updated = True
				
				if not contact.mobile_no:
					contact.mobile_no = payload.caller_number
					updated = True
				
				if updated:
					contact.save(ignore_permissions=True)
					frappe.db.commit()
					return {
						"success": True,
						"message": f"Updated contact {payload.contact_created} with phone {payload.caller_number}"
					}
				else:
					return {
						"success": True,
						"message": f"Contact {payload.contact_created} already has phone set"
					}
			except Exception as e:
				frappe.log_error(
					title="Update Contact from Payload Error",
					message=f"Payload: {payload_name}\nContact: {payload.contact_created}\nError: {str(e)}"
				)
				return {
					"success": False,
					"error": str(e)
				}
		else:
			return {
				"success": False,
				"message": "No contact or caller number found in payload"
			}
		
	except Exception as e:
		frappe.log_error(
			title="Reprocess Payload Error",
			message=f"Payload: {payload_name}\nError: {str(e)}"
		)
		return {
			"success": False,
			"error": str(e)
		}


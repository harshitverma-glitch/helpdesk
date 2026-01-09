"""
Demo/Test script for phone number call log merging feature

This can be run from bench console:
    bench console
    >>> from helpdesk.helpdesk.tests.test_phone_merge_demo import demo_phone_merge
    >>> demo_phone_merge()
"""

import frappe


def demo_phone_merge():
	"""
	Demonstrates the phone number call log merging feature
	Creates test tickets and call logs, then merges them
	"""
	print("\n" + "="*80)
	print("DEMO: Phone Number Call Log Merging")
	print("="*80)
	
	# Clean up any existing demo tickets
	cleanup_demo_tickets()
	
	# Step 1: Create first ticket (email) without phone number
	print("\n[Step 1] Creating Ticket #1 (Email - No Phone)")
	print("-" * 80)
	
	ticket1 = frappe.get_doc({
		"doctype": "HD Ticket",
		"subject": "Email: Need help with account",
		"raised_by": "john.kate@example.com",
		"status": "Open",
		"priority": "Medium",
		"description": "Customer sent email asking about account access"
	})
	ticket1.insert(ignore_permissions=True)
	frappe.db.commit()
	
	print(f"✓ Created Ticket: {ticket1.name}")
	print(f"  Subject: {ticket1.subject}")
	print(f"  Phone: {ticket1.contact_mobile or '(empty)'}")
	
	# Step 2: Create second ticket (call) with phone number
	print("\n[Step 2] Creating Ticket #2 (Call - With Phone)")
	print("-" * 80)
	
	ticket2 = frappe.get_doc({
		"doctype": "HD Ticket",
		"subject": "Call from John Kate",
		"raised_by": "john.kate@example.com",
		"status": "Open",
		"priority": "Medium",
		"description": "Customer called support line"
	})
	ticket2.insert(ignore_permissions=True)
	
	# Manually set phone number using db_set (simulating what RingCentral integration does)
	ticket2.db_set('contact_mobile', '+1-555-123-4567', update_modified=False)
	frappe.db.commit()
	
	print(f"✓ Created Ticket: {ticket2.name}")
	print(f"  Subject: {ticket2.subject}")
	print(f"  Phone: {ticket2.contact_mobile}")
	
	# Step 3: Add call log to ticket2
	print("\n[Step 3] Adding Call Log to Ticket #2")
	print("-" * 80)
	
	call_log = frappe.get_doc({
		"doctype": "Helpdesk Call Log",
		"call_id": "demo-call-12345",
		"from_number": "+1-555-123-4567",
		"to_number": "+1-800-SUPPORT",
		"caller_name": "John Kate",
		"type": "Incoming",
		"status": "Completed",
		"duration": "3m 45s",
		"ticket": ticket2.name,
		"telephony_medium": "RingCentral",
		"start_time": frappe.utils.now()
	})
	call_log.insert(ignore_permissions=True)
	frappe.db.commit()
	
	print(f"✓ Created Call Log: {call_log.name}")
	print(f"  From: {call_log.from_number}")
	print(f"  Linked to: {call_log.ticket}")
	print(f"  Duration: {call_log.duration}")
	
	# Step 4: Check current state
	print("\n[Step 4] Current State - BEFORE Merge")
	print("-" * 80)
	
	ticket1_logs = frappe.get_all("Helpdesk Call Log", filters={"ticket": ticket1.name})
	ticket2_logs = frappe.get_all("Helpdesk Call Log", filters={"ticket": ticket2.name})
	
	print(f"Ticket #1 ({ticket1.name}):")
	print(f"  Phone: {ticket1.contact_mobile or '(empty)'}")
	print(f"  Call Logs: {len(ticket1_logs)}")
	
	print(f"\nTicket #2 ({ticket2.name}):")
	print(f"  Phone: {ticket2.contact_mobile}")
	print(f"  Call Logs: {len(ticket2_logs)}")
	
	# Step 5: Update ticket1 with phone number (trigger merge)
	print("\n[Step 5] Updating Ticket #1 with Phone Number")
	print("-" * 80)
	print("This should trigger automatic call log merge...")
	
	ticket1.reload()
	ticket1.contact_mobile = "+1-555-123-4567"  # Same as ticket2
	ticket1.save(ignore_permissions=True)
	frappe.db.commit()
	
	print(f"✓ Updated {ticket1.name} with phone: {ticket1.contact_mobile}")
	
	# Step 6: Verify merge happened
	print("\n[Step 6] Final State - AFTER Merge")
	print("-" * 80)
	
	# Reload call log to see if it moved
	call_log.reload()
	
	ticket1_logs_after = frappe.get_all(
		"Helpdesk Call Log", 
		filters={"ticket": ticket1.name},
		fields=["name", "caller_name", "from_number", "duration"]
	)
	ticket2_logs_after = frappe.get_all("Helpdesk Call Log", filters={"ticket": ticket2.name})
	
	print(f"Ticket #1 ({ticket1.name}):")
	print(f"  Phone: {ticket1.contact_mobile}")
	print(f"  Call Logs: {len(ticket1_logs_after)}")
	
	if ticket1_logs_after:
		for log in ticket1_logs_after:
			print(f"    - {log.name}: {log.caller_name} ({log.from_number}) - {log.duration}")
	
	print(f"\nTicket #2 ({ticket2.name}):")
	print(f"  Phone: {ticket2.contact_mobile}")
	print(f"  Call Logs: {len(ticket2_logs_after)}")
	
	# Step 7: Results
	print("\n[Step 7] Results")
	print("=" * 80)
	
	if len(ticket1_logs_after) > 0 and call_log.ticket == ticket1.name:
		print("✅ SUCCESS! Call log was transferred from Ticket #2 to Ticket #1")
		print(f"   - Call log {call_log.name} now belongs to {ticket1.name}")
		print(f"   - Ticket #1 now has {len(ticket1_logs_after)} call log(s)")
		print(f"   - Ticket #2 now has {len(ticket2_logs_after)} call log(s)")
	else:
		print("❌ FAILED! Call log was not transferred")
		print(f"   - Call log {call_log.name} still belongs to {call_log.ticket}")
	
	print("\n" + "="*80)
	print("Demo Complete!")
	print("="*80)
	
	return {
		"ticket1": ticket1.name,
		"ticket2": ticket2.name,
		"call_log": call_log.name,
		"success": call_log.ticket == ticket1.name
	}


def cleanup_demo_tickets():
	"""Clean up any existing demo tickets"""
	try:
		# Find demo tickets
		demo_tickets = frappe.get_all(
			"HD Ticket",
			filters=[
				["subject", "like", "%Email: Need help with account%"],
				["OR", ["subject", "like", "%Call from John Kate%"]]
			]
		)
		
		for ticket in demo_tickets:
			# Delete associated call logs first
			call_logs = frappe.get_all("Helpdesk Call Log", filters={"ticket": ticket.name})
			for log in call_logs:
				frappe.delete_doc("Helpdesk Call Log", log.name, force=True)
			
			# Delete ticket
			frappe.delete_doc("HD Ticket", ticket.name, force=True)
		
		# Delete orphaned demo call logs
		orphan_logs = frappe.get_all(
			"Helpdesk Call Log",
			filters={"call_id": "demo-call-12345"}
		)
		for log in orphan_logs:
			frappe.delete_doc("Helpdesk Call Log", log.name, force=True)
		
		frappe.db.commit()
	except Exception as e:
		print(f"Note: Cleanup had issues (OK if first run): {str(e)}")


def test_manual_merge_api():
	"""
	Test the manual merge API function
	"""
	print("\n" + "="*80)
	print("TEST: Manual Merge API")
	print("="*80)
	
	# First run demo to create test data
	result = demo_phone_merge()
	
	print("\n[Testing Manual Merge API]")
	print("-" * 80)
	
	# Test find_duplicate_tickets_by_phone
	from helpdesk.helpdesk.api.ticket_phone_utils import find_duplicate_tickets_by_phone
	
	duplicates = find_duplicate_tickets_by_phone("+1-555-123-4567")
	print(f"\nFound {len(duplicates)} ticket(s) with phone +1-555-123-4567:")
	for dup in duplicates:
		print(f"  - {dup.name}: {dup.subject} (Call logs: {dup.call_log_count})")
	
	print("\n" + "="*80)


if __name__ == "__main__":
	demo_phone_merge()


# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HelpdeskCallLog(Document):
	def after_insert(self):
		"""Fetch call duration from RingCentral API if this is a RingCentral call"""
		# Only fetch duration for RingCentral calls
		if self.telephony_medium == "RingCentral" and self.call_id:
			# Enqueue background job with 10 second delay to allow call to complete
			frappe.enqueue(
				'helpdesk.helpdesk.doctype.helpdesk_call_log.helpdesk_call_log.update_call_duration_from_ringcentral',
				queue='default',
				timeout=300,
				call_log_name=self.name,
				session_id=self.call_id,
				enqueue_after_commit=True,
				at_front=False,
				now=False
			)
		
		# Sync to Unified Call Log
		self.sync_to_unified_call_log()
	
	def on_update(self):
		"""Sync to Unified Call Log on update"""
		self.sync_to_unified_call_log()
	
	def sync_to_unified_call_log(self):
		"""Sync this call log to Unified Call Log in ERPNext"""
		try:
			# Check if erpnext is installed
			if not frappe.db.exists("DocType", "Unified Call Log"):
				return
			
			frappe.enqueue(
				'erpnext.telephony.doctype.unified_call_log.unified_call_log.sync_helpdesk_call_log',
				queue='default',
				timeout=300,
				helpdesk_call_log_name=self.name,
				enqueue_after_commit=True,
				now=False
			)
		except Exception as e:
			# Don't fail the main operation if sync fails
			frappe.log_error(
				title=f"Failed to sync Helpdesk Call Log {self.name} to Unified Call Log",
				message=str(e)
			)


def update_call_duration_from_ringcentral(call_log_name: str, session_id: str):
	"""
	Background job to fetch and update call duration from RingCentral API
	
	Args:
		call_log_name: Name of the Helpdesk Call Log document
		session_id: RingCentral session ID (telephonySessionId)
	"""
	import time
	
	try:
		# Import here to avoid circular import
		from crm.integrations.ringcentral_client import RingCentralClient
		from frappe.utils import get_datetime, add_to_date
		
		# Wait 10 seconds to allow call to complete and appear in RingCentral API
		time.sleep(10)
		
		# Get the call log
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		
		# Skip if duration already set (manual update)
		if call_log.duration and call_log.duration != "0s":
			frappe.logger().info(f"Call log {call_log_name} already has duration, skipping")
			return
		
		# Initialize RingCentral client and authenticate
		client = RingCentralClient()
		if not client.authenticate_jwt():
			frappe.logger().error(f"Failed to authenticate with RingCentral for call log {call_log_name}")
			return
		
		# Fetch call log details from RingCentral
		call_details = client.get_call_log_details(session_id)
		
		if not call_details:
			frappe.logger().info(f"No call details found in RingCentral for session {session_id}")
			return
		
		# Extract duration and timestamps
		duration_seconds = call_details.get("duration", 0)
		start_time = call_details.get("startTime")  # ISO 8601 format
		
		# Update call log
		updates = {}
		if duration_seconds and duration_seconds > 0:
			# Format duration as human-readable
			from helpdesk.integrations.ringcentral_utils import format_duration
			updates["duration"] = format_duration(duration_seconds)
			
		if start_time:
			try:
				# Convert ISO 8601 to datetime
				start_dt = get_datetime(start_time)
				updates["start_time"] = start_dt
				
				# Calculate end time
				if duration_seconds:
					end_dt = add_to_date(start_dt, seconds=duration_seconds)
					updates["end_time"] = end_dt
			except:
				pass
		
		if updates:
			for field, value in updates.items():
				call_log.db_set(field, value, update_modified=False)
			frappe.db.commit()
			frappe.logger().info(f"✅ Updated Helpdesk call log {call_log_name} with duration: {updates.get('duration')}")
		else:
			frappe.logger().info(f"No duration data available for Helpdesk call log {call_log_name}")
			
	except Exception as e:
		frappe.log_error(
			title=f"Failed to update Helpdesk call duration for {call_log_name}",
			message=f"Session ID: {session_id}\nError: {str(e)}\n{frappe.get_traceback()}"
		)

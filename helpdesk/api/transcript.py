"""
API endpoints for call transcription
Handles on-demand transcription of call recordings
"""

import frappe
import re
import requests
from typing import Dict, Any, Optional


@frappe.whitelist()
def get_or_create_transcript(call_log_name: str) -> Dict[str, Any]:
	"""
	Get existing transcript or create new one on-demand
	
	This function:
	1. Checks if transcript already exists in call log
	2. If exists, returns immediately (cached)
	3. If not, uses preserved RingCentral URL
	4. Triggers transcription workflow
	5. Saves transcript to database
	6. Returns transcript text
	
	Args:
		call_log_name: Name of the Helpdesk Call Log
		
	Returns:
		dict with success status, transcript text, and cached flag
	"""
	try:
		# Get call log
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		
		# Check if transcript already exists
		if call_log.transcript:
			return {
				"success": True,
				"transcript": call_log.transcript,
				"cached": True,
				"message": "Transcript loaded from cache"
			}
		
		# Check if recording URL exists
		if not call_log.recording_url and not call_log.ringcentral_recording_url:
			return {
				"success": False,
				"message": "No recording available for this call"
			}
		
		# Transcribe the recording using RingCentral
		frappe.logger().info(f"Transcribing recording for {call_log_name}")
		
		# Use RingCentral native transcription (inline to avoid import issues)
		transcription_result = _transcribe_recording_internal(call_log)
		
		if transcription_result.get("success"):
			return {
				"success": True,
				"transcript": transcription_result.get("transcript"),
				"cached": False,
				"message": "Transcript generated successfully"
			}
		else:
			return {
				"success": False,
				"message": transcription_result.get("message", "Transcription failed")
			}
			
	except Exception as e:
		frappe.log_error(
			title=f"Get Transcript Error: {call_log_name}",
			message=f"Error: {str(e)}\n{frappe.get_traceback()}"
		)
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def refresh_transcript(call_log_name: str) -> Dict[str, Any]:
	"""
	Force refresh/regenerate transcript for a call log
	
	Args:
		call_log_name: Name of the Helpdesk Call Log
		
	Returns:
		dict with success status and new transcript
	"""
	try:
		# Get call log
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		
		# Clear existing transcript
		call_log.db_set('transcript', None, update_modified=False)
		frappe.db.commit()
		
		# Generate new transcript
		return get_or_create_transcript(call_log_name)
		
	except Exception as e:
		frappe.log_error(
			title=f"Refresh Transcript Error: {call_log_name}",
			message=f"Error: {str(e)}\n{frappe.get_traceback()}"
		)
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def debug_transcript_info(call_log_name: str) -> Dict[str, Any]:
	"""Debug endpoint to see call log data"""
	try:
		call_log = frappe.get_doc("Helpdesk Call Log", call_log_name)
		return {
			"success": True,
			"recording_url": call_log.recording_url,
			"ringcentral_recording_url": getattr(call_log, 'ringcentral_recording_url', None),
			"has_transcript": bool(call_log.transcript),
			"transcript_preview": call_log.transcript[:200] if call_log.transcript else None
		}
	except Exception as e:
		return {"success": False, "error": str(e)}


def _transcribe_recording_internal(call_log) -> Dict[str, Any]:
	"""
	Internal function to transcribe recording using RingCentral
	This is inline to avoid module import issues
	
	Args:
		call_log: Helpdesk Call Log document
		
	Returns:
		Dict with success status and transcript
	"""
	try:
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
		
		# Check if it's a local file (already downloaded)
		if url_to_use.startswith("/files/") or url_to_use.startswith("/private/files/"):
			return {
				"success": False,
				"message": "Recording is stored locally. Transcripts can only be fetched from RingCentral URLs. Please try fetching before the recording is downloaded."
			}
		
		# Extract recording ID from URL
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
		
		# Get transcript from RingCentral - Try multiple methods
		frappe.logger().info(f"Fetching transcript for recording_id: {recording_id}, account_id: {account_id}")
		
		# Method 1: Use RingCentralClient method
		transcript = client.get_ringcentral_transcript(recording_id, account_id)
		
		# Method 2: If that fails, try direct API call with different endpoints
		if not transcript:
			frappe.logger().info("Method 1 failed, trying alternative transcript endpoints...")
			transcript = _try_alternative_transcript_methods(client, recording_id, account_id, url_to_use)
		
		frappe.logger().info(f"Transcript result: {transcript[:200] if transcript else 'None'}")
		
		if transcript:
			# Save transcript directly to call log field
			call_log.db_set('transcript', transcript, update_modified=True)
			frappe.db.commit()
			
			frappe.logger().info(f"✅ RingCentral transcription successful for {call_log.name}")
			
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
			message=f"Call Log: {call_log.name}\nError: {str(e)}\n{frappe.get_traceback()}"
		)
		return {"success": False, "message": f"Error: {str(e)}"}


def _try_alternative_transcript_methods(client, recording_id: str, account_id: str, original_url: str) -> Optional[str]:
	"""
	Try alternative methods to fetch transcript from RingCentral
	
	Args:
		client: RingCentralClient instance
		recording_id: Recording ID
		account_id: Account ID
		original_url: Original recording URL
		
	Returns:
		Transcript text or None
	"""
	try:
		if not client.access_token:
			return None
			
		acc_id = account_id or "~"
		
		# Try different transcript API endpoints
		endpoints_to_try = [
			f"{client.base_url}/restapi/v1.0/account/{acc_id}/recording/{recording_id}/transcript",
			f"{client.base_url}/ai/audio/v1/async/speech-to-text/{recording_id}",
			f"{client.base_url}/restapi/v1.0/account/{acc_id}/call-log/{recording_id}/transcript"
		]
		
		headers = {
			"Authorization": f"Bearer {client.access_token}",
			"Accept": "application/json"
		}
		
		for endpoint in endpoints_to_try:
			try:
				frappe.logger().info(f"Trying transcript endpoint: {endpoint}")
				response = requests.get(endpoint, headers=headers, timeout=30)
				
				if response.status_code == 200:
					data = response.json()
					frappe.logger().info(f"Response data keys: {data.keys() if isinstance(data, dict) else type(data)}")
					
					# Try to extract transcript from various response formats
					if isinstance(data, dict):
						# Try common field names
						transcript = (
							data.get("transcript") or 
							data.get("text") or 
							data.get("content") or
							data.get("transcription") or
							data.get("body")
						)
						
						# Check for nested structures
						if not transcript and "data" in data:
							nested_data = data["data"]
							if isinstance(nested_data, dict):
								transcript = nested_data.get("transcript") or nested_data.get("text")
						
						# Check for array of segments
						if not transcript and "segments" in data:
							segments = data["segments"]
							if isinstance(segments, list):
								transcript = " ".join([seg.get("text", "") for seg in segments if seg.get("text")])
						
						if transcript:
							frappe.logger().info(f"✅ Found transcript using endpoint: {endpoint}")
							return transcript
							
					elif isinstance(data, str):
						frappe.logger().info(f"✅ Found transcript (string response) using endpoint: {endpoint}")
						return data
						
				elif response.status_code != 404:
					frappe.logger().info(f"Endpoint returned {response.status_code}: {response.text[:200]}")
					
			except Exception as e:
				frappe.logger().info(f"Endpoint {endpoint} failed: {str(e)}")
				continue
		
		return None
		
	except Exception as e:
		frappe.logger().error(f"Alternative transcript methods error: {str(e)}")
		return None


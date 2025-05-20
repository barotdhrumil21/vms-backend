import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
import json
import re

logger = logging.getLogger(__name__)

def schedule_calcom_booking(user_email, phone_number, user_name=""):
    """
    Schedule a booking on Cal.com for a demo after user signup
    
    Args:
        user_email (str): Email of the newly registered user
        user_name (str): Name of the user (can be derived from email if not provided)
        phone_number (str): Phone number of the user for follow-up
    
    Returns:
        dict: Response from Cal.com API with booking details or error information
    """
    try:
        # Cal.com API v2 endpoint for creating bookings
        cal_api_url = "https://api.cal.com/v2/bookings"
        
        # Get API key from settings
        api_key = getattr(settings, 'CALCOM_API_KEY', '').strip()
        
        # Enable debug logging if configured
        debug_mode = getattr(settings, 'DEBUG_CALCOM', False)
        
        # Validate API key
        if not api_key:
            logger.error("Cal.com API key not configured. Skipping booking creation.")
            return {"success": False, "message": "Cal.com API key not configured"}
        
        # Format name (use email username if no name provided)
        if not user_name or user_name.strip() == "":
            user_name = user_email.split('@')[0]
        
        # Format phone number to meet Cal.com requirements
        # Strip all non-numeric characters and ensure it starts with a plus
        if phone_number:
            # Remove all non-digit characters except plus sign
            formatted_phone = re.sub(r'[^\d+]', '', phone_number)
            # Ensure it starts with a plus sign if it doesn't already
            if not formatted_phone.startswith('+'):
                formatted_phone = '+' + formatted_phone
        else:
            formatted_phone = "+1234567890"  # Fallback default
        
        # Calculate booking time (48 hours from now)
        start_time = datetime.now() + timedelta(hours=48)
        # Round to nearest hour and format as ISO string with Z for UTC timezone
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        start_time_str = start_time.isoformat() + "Z"

        # Get event type ID or slug from settings
        event_type = getattr(settings, 'CALCOM_EVENT_TYPE_ID', '')
        
        if not event_type:
            logger.error("Cal.com event type not configured")
            return {"success": False, "error": "Event type not configured"}
        
        # Prepare payload according to Cal.com v2 API requirements
        payload = {
            "start": start_time_str,
            "attendee": {
                "name": user_name,
                "email": user_email,
                "timeZone": "Asia/Kolkata"
            },
            "bookingFieldsResponses": {
                "notes": "Auto-scheduled demo after signup",
                # Use proper field name that Cal.com expects
                "Phone-Number": "+917984627362"  # Changed from "phoneNumber" to "Phone-Number"
            },
            "metadata": {
                "source": "VMS Auto-signup"
            }
        }

        # Handle different ways event type can be specified (ID or slug)
        if event_type.isdigit():
            # It's a numeric ID
            payload["eventTypeId"] = int(event_type)
            logger.info(f"Using numeric event type ID: {event_type}")
        else:
            # It's a slug - need to specify it as eventTypeSlug with username
            payload["eventTypeSlug"] = event_type
            # For user events we need username
            username = getattr(settings, 'CALCOM_USERNAME', None)
            org_slug = getattr(settings, 'CALCOM_ORG_SLUG', None)
            
            if username:
                payload["username"] = username
                logger.info(f"Using username: {username} with event type slug: {event_type}")
            else:
                logger.error("Username not configured for event type slug")
                return {"success": False, "error": "Missing username for event type slug"}
                
            # Add org slug if specified
            if org_slug:
                payload["organizationSlug"] = org_slug
                logger.info(f"Using organization slug: {org_slug}")

        # Make the API request with the correct header format for Cal.com API v2
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "cal-api-version": "2024-08-13"  # Required by v2 API
        }
        
        if debug_mode:
            # Mask API key in logs
            debug_payload = payload.copy()
            logger.info(f"Cal.com API request payload: {json.dumps(debug_payload, indent=2)}")
        
        logger.info(f"Sending Cal.com booking request for {user_email}")
        
        response = requests.post(
            cal_api_url, 
            json=payload,
            headers=headers,
            timeout=20  # Increase timeout for better reliability
        )
        
        # Process the response
        if response.status_code in [200, 201]:
            logger.info(f"Successfully scheduled Cal.com booking for {user_email}")
            return {"success": True, "data": response.json()}
        else:
            # Log the full response for debugging
            error_message = f"Failed with status {response.status_code}: {response.text}"
            logger.error(f"Cal.com booking failed: {error_message}")
            return {"success": False, "error": error_message, "status_code": response.status_code}
            
    except requests.RequestException as e:
        logger.exception(f"Network error scheduling Cal.com booking: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Error scheduling Cal.com booking: {str(e)}")
        return {"success": False, "error": str(e)}

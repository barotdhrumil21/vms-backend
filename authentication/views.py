from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
import json, base64, logging, smtplib
from api.helper import check_string
from django.conf import settings
from authentication.utils import return_400, get_tokens_for_user
from api.models import Buyer
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from api.helper import EmailManager
from api.task import CeleryEmailManager
from api.ab_testing import pick_subscription_variant, calculate_initial_expiry
from datetime import datetime, timedelta
from api.calcom_helper import schedule_calcom_booking
from django.utils import timezone  # Add this import at the top

# Create your views here.

class Test(APIView):
    def get(self,request):
        try:
            return Response({"success":True})
        except Exception as error:
            return return_400({"success":False,"message":str(error)})

class LoginAPI(APIView):
    """
        Login API
    """
    permission_classes = (AllowAny,)
    def post(self,request):
        """
            API POST Method
        """
        try:
            data = request.data
            username = data.get("username").lower()
            password = data.get("password")
            if "@" not in username:
                buyer = Buyer.objects.filter(phone_no = username)
                if not buyer.exists():
                    raise Exception("Invalid phone number!")
                else:
                    buyer = buyer.last()
                    username = buyer.user.username
            decoded_bytes = base64.b64decode(password)
            decoded_password = decoded_bytes.decode('utf-8')
            user = authenticate(username=username, password=decoded_password)
            if not user:
                return return_400({"success":False, "error":"user doesn't exist"})
            data = get_tokens_for_user(user)
            data['email'] = user.email
            return Response({"success":True, "data":data})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"}) 

class GetUserDetailsAPI(APIView):
    '''
        This API is for fetching the details of the user on the basis of the JWT Token
    '''
    permission_classes = (IsAuthenticated,)

    def get(self,request):
        '''
            API GET Method
        '''
        try:
            user = request.user
            buyer = user.buyer
            if user and buyer:
                data = {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone_no": buyer.phone_no,
                    "company_name": buyer.company_name,
                    "gst_no": buyer.gst_no,
                    "address": buyer.address,
                    "currency": buyer.currency if hasattr(buyer, "currency") and buyer.currency else "USD",
                    "timezone": buyer.timezone if hasattr(buyer, "timezone") and buyer.timezone else "Asia/Kolkata",
                }
                return Response({"success":True, "data":data})
            else:
                return return_400({"success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"})
    
    def post(self,request):
        '''
            API POST Method
        '''
        try:
            user = request.user
            buyer = user.buyer
            data = request.data
            if buyer :
                if data.get("first_name"):
                    user.first_name = str(data.get("first_name"))
                if data.get("last_name"):
                    user.last_name = str(data.get("last_name"))
                if data.get("phone_no"):
                    buyer.phone_no = str(data.get("phone_no"))
                if data.get("company_name"):
                    buyer.company_name = str(data.get("company_name"))
                if data.get("gst_no"):
                    buyer.gst_no = str(data.get("gst_no"))
                if data.get("address"):
                    buyer.address = str(data.get("address"))
                if data.get("currency"):
                    buyer.currency = str(data.get("currency"))
                if data.get("timezone"):
                    buyer.timezone = str(data.get("timezone"))
                user.save()
                buyer.save()
                return Response({"success":True})
            else:
                return return_400({"success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"})
        
def send_signup_email(email_payload):
    """
    Safely send the welcome email without interrupting the signup flow.
    """
    try:
        if settings.USE_CELERY:
            CeleryEmailManager.new_user_signup.delay(email_payload)
            return
        EmailManager.new_user_signup(email_payload)
    except smtplib.SMTPException as smtp_error:
        logging.exception("SMTP error while dispatching signup email: %s", smtp_error)
    except Exception as error:
        logging.exception("Unexpected error while dispatching signup email: %s", error)


class SignUpView(APIView):
    def post(self, request):
        try:
            data = request.data
            email = data.get("email", "").lower()
            phone_no = data.get("phone_no", "")
            password = data.get("password", "")
            company_name = data.get("company_name", "")
            
            # Validate required fields
            if not all([email, phone_no, password]):
                return Response({
                    "success": False, 
                    "message": "Email, phone number and password are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(username=email).exists():
                return Response({
                    "success": False, 
                    "message": "User with this email already exists"
                }, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create_user(
                username=email, 
                email=email, 
                password=password,
            )
            variant = pick_subscription_variant(email)
            subscription_expiry = calculate_initial_expiry(variant)
            buyer_timezone = data.get("timezone") or "Asia/Kolkata"
            Buyer.objects.create(
                user=user,
                subscription_expiry_date=subscription_expiry,
                test_user=False,
                phone_no=phone_no,
                company_name=company_name,
                onboarding_variant=variant,
                timezone=buyer_timezone,
            )

            # Send welcome email
            email_obj = {
                "to": [email],
                "cc": [],
                "bcc": ["barotdhrumil21@gmail.com"],
                "subject": "Welcome to AuraVMS",
                "username": email,
                "password": password
            }
            try:
                if settings.USE_CELERY:
                    CeleryEmailManager.new_user_signup.delay(email_obj)
                else:
                    EmailManager.new_user_signup(email_obj)
            except smtplib.SMTPException as email_error:
                logging.error(
                    "SMTP delivery failed for welcome email to %s: %s",
                    email,
                    email_error,
                )
            except Exception as email_error:
                logging.error(
                    "Unexpected error while sending welcome email to %s: %s",
                    email,
                    email_error,
                )

            # Schedule a Cal.com booking for demo
            if getattr(settings, 'CALCOM_ENABLE_AUTO_BOOKING', False):
                try:
                    logging.info(f"Attempting to create Cal.com booking for {email}")
                    # Check if API key is present and properly formatted
                    api_key = getattr(settings, 'CALCOM_API_KEY', '').strip()
                    if not api_key:
                        logging.error("Cal.com API key not configured or empty")
                    
                    # Check for event type ID configuration
                    event_type = getattr(settings, 'CALCOM_EVENT_TYPE_ID', '')
                    if not event_type:
                        logging.error("Cal.com event type ID not configured")
                        
                    # Log the API key being used (mask it for security)
                    masked_key = f"{'*' * (len(api_key)-4)}{api_key[-4:]}" if api_key else "None"
                    logging.info(f"Using Cal.com API key ending in: {api_key[-4:] if api_key else 'None'}")
                    
                    # Format name for booking
                    user_name = f"{data.get('first_name', '')} {data.get('last_name', '')}"
                    if not user_name.strip():
                        user_name = email.split('@')[0]
                    
                    booking_result = schedule_calcom_booking(
                        user_email=email,
                        phone_number=phone_no,
                        user_name=user_name
                    )
                    
                    # Log detailed result
                    if booking_result.get('success'):
                        logging.info(f"Cal.com booking created successfully for {email}")
                    else:
                        logging.error(f"Failed to create Cal.com booking for {email}: {booking_result.get('error')}")
                        # Send notification about booking failure if needed
                        if settings.DEBUG_CALCOM:
                            email_obj = {
                                "to": ["barotdhrumil21@gmail.com"],
                                "subject": f"[DEBUG] Cal.com booking failed for {email}",
                                "message": f"Error: {booking_result.get('error')}"
                            }
                            try:
                                EmailManager().send_email(email_obj)
                            except:
                                logging.error("Failed to send Cal.com error notification")
                except Exception as cal_error:
                    logging.exception(f"Exception in Cal.com booking for {email}: {cal_error}")

            # Authenticate user and generate tokens
            authenticated_user = authenticate(username=email, password=password)
            if authenticated_user:
                refresh = RefreshToken.for_user(authenticated_user)
                return Response({
                    "success": True,
                    "message": "User created successfully",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "user": {
                        "email": authenticated_user.email,
                        "username": authenticated_user.username,
                        "phone": phone_no
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "success": True,
                    "message": "User created but login failed. Please login separately."
                }, status=status.HTTP_201_CREATED)

        except Exception as error:
            logging.exception(f"User creation failed: {error}")
            email_obj = {
                "to": ["barotdhrumil21@gmail.com"],
                "cc": [],
                "bcc": [""],
                "subject": "[ALERT] USER CREATION FAILED",
                "username": data.get("email", "unknown_email"),
                "error": str(error)
            }
            try:
                if settings.USE_CELERY:
                    CeleryEmailManager.user_create_failed.delay(email_obj)
                else:
                    EmailManager.user_create_failed(email_obj)
            except Exception as email_error:
                logging.error(f"Failed to send error notification: {email_error}")
                
            return Response({"success": False, "message": f"User creation failed: {str(error)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
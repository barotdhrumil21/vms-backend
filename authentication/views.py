from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
import json,base64
from api.helper import check_string
from django.conf import settings
from authentication.utils import return_400, get_tokens_for_user
from api.models import Buyer
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from api.helper import EmailManager
from api.task import CeleryEmailManager
from datetime import datetime, timedelta

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
                    "first_name":user.first_name,
                    "last_name":user.last_name,
                    "email":user.email,
                    "phone_no":buyer.phone_no,
                    "company_name": buyer.company_name,
                    "gst_no":buyer.gst_no,
                    "address":buyer.address,
                    "currency": buyer.currency if hasattr(buyer, 'currency') and buyer.currency else "USD"  # Default to INR if not set
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
                user.save()
                buyer.save()
                return Response({"success":True})
            else:
                return return_400({"success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"})
        
class SignUpView(APIView):
    def post(self, request):
        try:
            data = request.data
            email = data.get("email").lower()
            phone_no = data.get("phone_no")
            password = data.get("password")
            company_name = data.get("company_name")

            if User.objects.filter(username=email).exists():
                return Response({"success": False, "message": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create_user(username=email, email=email, password=password)
            renews_at = datetime.now() + timedelta(days=45)
            Buyer.objects.create(user=user, subscription_expiry_date=renews_at, test_user=False, phone_no=phone_no, company_name = company_name)

            # Send welcome email
            email_obj = {
                "to": [email],
                "cc": [],
                "bcc": ["barotdhrumil21@gmail.com"],
                "subject": "Welcome to AuraVMS",
                "username": email,
                "password":password
            }
            if settings.USE_CELERY:
                CeleryEmailManager.new_user_signup.delay(email_obj)
            else:
                EmailManager.new_user_signup(email_obj)

            # Authenticate user and generate tokens
            authenticated_user = authenticate(username=email, password=password)
            refresh = RefreshToken.for_user(authenticated_user)

            return Response({
                "success": True,
                "message": "User created successfully",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": {
                    "email": authenticated_user.email,
                    "username": authenticated_user.username,
                    "phone":phone_no
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as error:
            print(error)
            email_obj = {
                "to": ["barotdhrumil21@gmail.com"],
                "cc": [],
                "bcc": [""],
                "subject": "[ALERT] USER CREATION FAILED",
                "username": email,
                "error": str(error)
            }
            if settings.USE_CELERY:
                CeleryEmailManager.user_create_failed.delay(email_obj)
            else:
                EmailManager.user_create_failed(email_obj)
            return Response({"success": False, "message": "User creation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
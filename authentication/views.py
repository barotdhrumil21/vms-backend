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
            username = data.get("username")
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
            return Response({"success":True, "data":get_tokens_for_user(user)})
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
                    "address":buyer.address
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
                    user.first_name = check_string(data.get("first_name"),"first_name")
                if data.get("last_name"):
                    user.last_name = check_string(data.get("last_name"),"last_name")
                if data.get("phone_no"):
                    buyer.phone_no = check_string(data.get("phone_no"),"phone_no")
                if data.get("company_name"):
                    buyer.company_name = check_string(data.get("company_name"),"company_name")
                if data.get("gst_no"):
                    buyer.gst_no = check_string(data.get("gst_no"),"gst_no")
                if data.get("address"):
                    buyer.address = check_string(data.get("address"),"address")
                user.save()
                buyer.save()
                return Response({"success":True})
            else:
                return return_400({"success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"})       
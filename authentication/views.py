from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
import json,base64
from django.conf import settings
from authentication.utils import return_400, get_tokens_for_user


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
            decoded_bytes = base64.b64decode(password)
            decoded_password = decoded_bytes.decode('utf-8')
            user = authenticate(username=username, password=decoded_password)
            if not user:
                return return_400({"success":False, "error":"user doesn't exist"})
            return Response({"success":True, "data":get_tokens_for_user(user)})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"}) 

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
            if user:
                data = {
                    "name":f"{user.first_name} {user.last_name}",
                    "email":user.email
                }
                return Response({"success":True, "data":data})
            else:
                return return_400({"success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"success":False,"error":f"An unexpected error occured : {error}"})       
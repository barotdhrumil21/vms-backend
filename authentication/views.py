from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
import json
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
            user = authenticate(username=username, password=password)
            if user:
                print(get_tokens_for_user(user))
            else:
                return return_400({"Success":False, "error":"user doesn't exist"})
            return Response({"Success":True, "data":get_tokens_for_user(user)})
        except Exception as error:
            return return_400({"Success":False,"error":f"An unexpected error occured : {error}"}) 

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
                return Response({"Success":True, "data":data})
            else:
                return return_400({"Success": False, "error":"User details not found."})
        except Exception as error:
            return return_400({"Success":False,"error":f"An unexpected error occured : {error}"})       
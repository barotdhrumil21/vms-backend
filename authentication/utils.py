import json
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken

def return_400(data, request=None):
    response = HttpResponse(json.dumps(data), content_type='application/json')
    response.status_code = 400
    return response

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
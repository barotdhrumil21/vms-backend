import json
import logging
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)
def return_400(data, request=None):
    response = HttpResponse(json.dumps(data), content_type='application/json')
    response.status_code = 400

    # Log the error
    log_message = f"400 Bad Request: {json.dumps(data)}\n\n"
    if request:
        log_message = f"{request.method} {request.path} - {log_message}\n\n"
        if request.user.is_authenticated:
            log_message = f"User: {request.user.username} {request.method} {request.path} - {log_message}\n\n"

    logger.error(log_message)
    return response

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

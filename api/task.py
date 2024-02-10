
from .helper import EmailManager
from vms_backend.celery import app

class CeleryEmailManager:
    
    @app.task(queue="email_queue")
    def send_rfq_created_email(email_obj):
        EmailManager.send_rfq_created_email(email_obj)
    
    @app.task(queue="email_queue")
    def send_all_rfq_email(buyer_id):
        EmailManager.send_all_rfq_email(buyer_id)
        
        
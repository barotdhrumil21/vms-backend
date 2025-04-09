
from .helper import EmailManager
from vms_backend.celery import app

class CeleryEmailManager:
    
    @app.task(queue="email_queue")
    def send_rfq_created_email(email_obj):
        EmailManager.send_rfq_created_email(email_obj)
    
    @app.task(queue="email_queue")
    def send_all_rfq_email(buyer_id):
        EmailManager.send_all_rfq_email(buyer_id)
    
    @app.task(queue="email_queue")
    def send_email_with_body(email_obj):
        EmailManager.send_email_with_body(email_obj)
    
    @app.task(queue="email_queue")
    def new_user_signup(email_obj):
        EmailManager.new_user_signup(email_obj)
    
    @app.task(queue="email_queue")
    def user_create_failed(email_obj):
        EmailManager.user_create_failed(email_obj)
    
    @app.task(queue="email_queue")
    def new_rfq_response_alert(email_obj):
        EmailManager.new_rfq_response_alert(email_obj)

    @app.task(queue="email_queue")
    def send_rfq_reminder(email_obj):
        EmailManager.send_rfq_reminder(email_obj)

    @app.task(queue="email_queue")
    def send_purchase_order(email_obj):
        EmailManager.send_purchase_order(email_obj)   
        
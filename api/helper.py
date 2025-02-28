import re,os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from api.models import Buyer
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def check_string(string,variable_name=None):
    pattern = r"^[a-zA-Z0-9\s_.,%'-@]*$"
    if not bool(re.match(pattern, string)):
        raise Exception(f"Not a valid string value : {variable_name}")
    return string

def get_all_rfq_data(buyer):
    rfq_lists = buyer.request_for_quotations.all()
    data = []
    for rfq in rfq_lists:
        for supplier in rfq.suppliers.all():
            categories = supplier.categories.filter(active=True)
            categories = [category.name for category in categories]
            for item in rfq.request_for_quotation_items.all():
                res = item.request_for_quotation_item_response.filter(supplier=supplier)
                if res.exists():
                    res = res.last()
                else:
                    res = None
                obj = {
                    "RFQ Item Id" : rfq.id,
                    "Date" : rfq.created.strftime("%d-%b-%Y"),
                    "Terms & Conditions" : rfq.request_for_quotation_meta_data.last().payment_terms,
                    "Payment Terms" : rfq.request_for_quotation_meta_data.last().terms_conditions,
                    "Shipping Terms" : rfq.request_for_quotation_meta_data.last().shipping_terms,
                    "Product Name" : item.product_name,
                    "Quantity":item.quantity,
                    "UOM" : item.uom,
                    "Specification" : item.specifications,
                    "Expected Delivery" : item.expected_delivery_date.strftime("%d-%b-%Y") if item.expected_delivery_date else None,
                    "RFQ Status" :  item.get_status_display(),
                    "Supplier Name" : supplier.company_name,
                    "Supplier POC" : supplier.person_of_contact,
                    "Supplier Phone" : supplier.phone_no,
                    "Supplier Email" : supplier.email,
                    "Supplier Categories" : " , ".join(categories) if categories else "",
                    "Supplier Price" : res.price if res else None,
                    "Supplier Quantity" : res.quantity if res else None,
                    "Lead Time" : res.lead_time if (res and res.lead_time) else None,
                    "Seller Remarks" : res.remarks if (res and res.remarks) else None,
                    "Quote Received On" : res.created.strftime("%d-%b-%Y") if res else None,
                    "Order Status" : res.get_order_status_display() if res else None,
                    "Order Placed On" : res.updated.strftime("%d-%b-%Y") if (res and res.order_status==1)  else None,
                }
                data.append(obj)
    return data

class EmailManager:
    def send_rfq_created_email(email_obj):
        try:
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject=email_obj.get("subject",""), body=email_obj.get("body",""), 
            from_email=from_email, to=email_obj['to'], bcc=email_obj.get('bcc',[]) + 
                settings.DEFAULT_EMAIL_BCC_LIST,cc=email_obj.get('cc',[]) + settings.DEFAULT_EMAIL_CC_LIST)
            html_template = get_template(os.path.join(settings.BASE_DIR, 'templates/email/') +'RFQ_Created_Email_Template.html').render(email_obj)
            message.content_subtype = 'html'
            message.attach_alternative(html_template, "text/html")
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
    
    def new_user_signup(email_obj):
        try:
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject=email_obj.get("subject",""), body=email_obj.get("body",""), 
            from_email=from_email, to=email_obj['to'], bcc=email_obj.get('bcc',[]) + 
                settings.DEFAULT_EMAIL_BCC_LIST,cc=email_obj.get('cc',[]) + settings.DEFAULT_EMAIL_CC_LIST)
            html_template = get_template(os.path.join(settings.BASE_DIR, 'templates/email/') +'new_user_signup.html').render(email_obj)
            message.content_subtype = 'html'
            message.attach_alternative(html_template, "text/html")
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
    
    def new_rfq_response_alert(email_obj):
        try:
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject=email_obj.get("subject",""), body=email_obj.get("body",""), 
            from_email=from_email, to=email_obj['to'], bcc=email_obj.get('bcc',[]) + 
                settings.DEFAULT_EMAIL_BCC_LIST,cc=email_obj.get('cc',[]) + settings.DEFAULT_EMAIL_CC_LIST)
            html_template = get_template(os.path.join(settings.BASE_DIR, 'templates/email/') +'new_rfq_response.html').render(email_obj)
            message.content_subtype = 'html'
            message.attach_alternative(html_template, "text/html")
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
    
    def user_create_failed(email_obj):
        try:
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject=email_obj.get("subject",""), body=email_obj.get("body",""), 
            from_email=from_email, to=email_obj['to'], bcc=email_obj.get('bcc',[]) + 
                settings.DEFAULT_EMAIL_BCC_LIST,cc=email_obj.get('cc',[]) + settings.DEFAULT_EMAIL_CC_LIST)
            html_template = get_template(os.path.join(settings.BASE_DIR, 'templates/email/') +'user_create_failed.html').render(email_obj)
            message.content_subtype = 'html'
            message.attach_alternative(html_template, "text/html")
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
    
    def send_all_rfq_email(buyer_id):
        try:
            buyer = Buyer.objects.get(id=buyer_id)
            data = get_all_rfq_data(buyer=buyer)
            dataFrame = pd.DataFrame(data)
            file_name = f"media/templates/{buyer.user.first_name}_{buyer.id}.xlsx"
            dataFrame.to_excel(file_name,index=False)
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject="Request For Quotation File Available", body="Please find the below attached excel sheet.", 
            from_email=from_email, to=[buyer.user.email], bcc=settings.DEFAULT_EMAIL_BCC_LIST)
            message.attach_file(f"{settings.BASE_DIR}/{file_name}")
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
    
    def send_email_with_body(email_obj):
        try:
            from_email = settings.EMAIL_HOST_USER
            message = EmailMultiAlternatives(subject=email_obj.get("subject"), body=email_obj.get("body"), 
            from_email=from_email, to=email_obj.get("to",[]), cc=email_obj.get("cc",[]), bcc = settings.DEFAULT_EMAIL_BCC_LIST)
            if settings.SEND_EMAILS:
                message.send()
        except Exception as ex:
            logger.error(f"***** EMAIL ERROR : {ex}")
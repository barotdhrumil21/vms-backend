import random
import string
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from authentication.utils import return_400
from django.contrib.auth.models import User
import pandas as pd
import io, os
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import TemporaryUploadedFile
import re
from api.models import Buyer, Supplier,RequestForQuotation, RequestForQuotationItems, RequestForQuotationMetaData, SupplierCategory, RequestForQuotationItemResponse
from api.helper import check_string
from django.db.models import Count, Avg, Sum, F, ExpressionWrapper, FloatField, Q, DurationField
from datetime import datetime, timedelta
from django.db import transaction
from api.task import CeleryEmailManager
from .helper import EmailManager
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.functions import Cast
from django.core.validators import validate_email


class CreateSupplier(APIView):
    """
        Create Supplier API With Support of:
        1. POST => To create new instance
        2. PUT => To Update an existing instance
        3. DELETE => To delete an instance
    """
    permission_classes = (IsAuthenticated,)
    def post(self,request):
        """
            API POST Method
        """
        try:
            data = request.data
            company_name = data.get("company_name")
            person_of_contact = data.get("person_of_contact")
            phone_no = data.get("phone_no")
            email = data.get("email")
            categories = data.get("categories")
            remark = data.get("remark")
            buyer = request.user.buyer

            # Validations
            if not all([company_name, person_of_contact, phone_no, email]):
                raise ValidationError("Important parameters missing!")

            # Validate email
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Invalid email format")

            # Validate phone number
            if not re.match(r'^\+?[0-9-\s]{8,20}$', phone_no):
                raise ValidationError("Invalid phone number format")

            # Check if supplier with this email already exists
            if buyer.suppliers.filter(email=email).exists():
                raise ValidationError("Supplier with this email id already exists!")

            # Create supplier
            supplier_obj = Supplier(buyer=buyer)
            supplier_obj.company_name = company_name
            supplier_obj.person_of_contact = person_of_contact
            supplier_obj.phone_no = phone_no
            supplier_obj.email = email
            supplier_obj.remark = remark
            supplier_obj.save()

            # Add categories
            for category in categories:
                supplier_category = SupplierCategory(buyer=buyer, supplier=supplier_obj)
                supplier_category.name = category
                supplier_category.save()

            return Response({"success": True, "data": {"supplier_id": supplier_obj.id}})

        except ValidationError as ve:
            return return_400({"success": False, "error": str(ve)})
        except Exception as error:
            return return_400({"success": False, "error": str(error)})


    def put(self,request):
        """
            API PUT Method
        """
        try:
            data = request.data
            fields_updated = data.get("fields_updated",[])
            supplier_id = data.get("supplier_id")
            buyer = request.user.buyer
            # Validations
            if not fields_updated:
                raise Exception("No fields provided to update supplier data")
            if not supplier_id:
                raise Exception("Supplier ID not provided")
            supplier_obj = buyer.suppliers.filter(id=supplier_id).last()
            if not supplier_obj:
                raise Exception("This supplier doesn't exist in your suppliers list!")
            # Validations ends here
            for field in fields_updated:
                if field=="company_name" and bool(data.get("company_name")):
                    supplier_obj.company_name = check_string(data.get("company_name"),"Company Name")
                elif field=="person_of_contact" and bool(data.get("person_of_contact")):
                    supplier_obj.person_of_contact = check_string(data.get("person_of_contact"),"Person Of Contact")
                elif field=="phone_no" and bool(data.get("phone_no")):
                    phone_no = data.get("phone_no")
                    # Validate phone number
                    if not re.match(r'^\+?[0-9-\s]{8,20}$', phone_no):
                        raise ValidationError("Invalid phone number")
                    supplier_obj.phone_no = check_string(phone_no,"Phone No")
                elif field=="email" and bool(data.get("email")):
                    email = data.get("email")
                    # Validate email
                    try:
                        validate_email(email)
                    except ValidationError:
                        raise ValidationError("Invalid email format")
                    
                    # Check if another supplier with this email already exists (excluding current supplier)
                    if buyer.suppliers.filter(email=email).exclude(id=supplier_id).exists():
                        raise ValidationError("Another supplier with this email id already exists!")
                    
                    supplier_obj.email = check_string(email,"Email")
                elif field=="categories" and bool(data.get("categories")):
                    categories = data.get("categories")
                    prev_categories = supplier_obj.categories.all()
                    for prev_category in prev_categories:
                        if prev_category.name not in categories:
                            prev_category.active=False
                            prev_category.save()
                    for category in categories:
                        cat_obj = SupplierCategory.objects.filter(supplier=supplier_obj,name=category)
                        if cat_obj.exists():
                            cat_obj = cat_obj.last()
                            if cat_obj.active:
                                continue
                            cat_obj.active = True
                            cat_obj.save()
                        else:
                            supplier_category = SupplierCategory(buyer=buyer,supplier = supplier_obj)
                            supplier_category.name = check_string(category,"category")
                            supplier_category.save()
                elif field=="remark" and bool(data.get("remark")):
                    supplier_obj.remark = check_string(data.get("remark"),"Remark")
            supplier_obj.save()
            return Response({"success":True})
        except ValidationError as ve:
            return return_400({"success":False,"error":str(ve)})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})
        

    def delete(self,request):
        """
            API DELETE Method
        """
        try:
            data = request.data
            supplier_id = data.get("supplier_id")
            if not supplier_id:
                raise Exception("Supplier ID not provided")
            buyer = request.user.buyer
            supplier_obj = buyer.suppliers.filter(id=supplier_id).last()
            if not supplier_obj:
                raise Exception("This supplier doesn't exist in your suppliers list!")
            supplier_obj.delete()
            return Response({"success":True})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class CreateUser(APIView):
    """
        Create New Signup
    """
    def post(self,request):
        try:
            data = request.data
            event = data.get("meta").get("event_name")
            if event == "subscription_updated":

                email = data.get("data").get("attributes").get("user_email").lower()
                # user_name = data.get("data").get("attributes").get("user_name")
                renews_at = datetime.fromisoformat(data.get("data").get("attributes").get("renews_at").replace("Z", "+00:00"))
                test_mode = True if data.get("meta").get("test_mode") == "true" else False
                if not User.objects.filter(username=email).exists():
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    user = User.objects.create_user(username=email, email=email, password=password)
                    Buyer.objects.create(user=user, subscription_expiry_date = renews_at, test_user = test_mode)

                    email_obj = {
                        "to": [email],
                        "cc":[],
                        "bcc":["barotdhrumil21@gmail.com"],
                        "subject":f"Credentials for AuraVMS Login",
                        "username":email,
                        "password":password
                    }
                    if settings.USE_CELERY:
                        CeleryEmailManager.new_user_signup.delay(email_obj)
                    else:
                        EmailManager.new_user_signup(email_obj)
                else:
                    buyer = Buyer.objects.get(user=User.objects.get(username=email))
                    buyer.subscription_expiry_date = renews_at
                    buyer.save()
            return Response({"success":True})  
        except Exception as error:
            print(error)
            email_obj = {
                        "to": ["barotdhrumil21@gmail.com"],
                        "cc":[],
                        "bcc":[""],
                        "subject":f"[ALERT] USER CREATION FAILED",
                        "username":email,
                        "error":error
                    }
            if settings.USE_CELERY:
                CeleryEmailManager.user_create_failed.delay(email_obj)
            else:
                EmailManager.user_create_failed(email_obj)  
            return Response({"success":False}) 

class FramerCreateUser(APIView):
    """
        Create New Signup From Framer
    """
    def post(self,request):
        try:
            data = request.data
            email = data.get("Email").lower()
            phone = data.get("Phone Number").lower()
            test_mode = False
            renews_at = datetime.now() + timedelta(days=45)
            if not User.objects.filter(username=email).exists():
                password = data.get("Password")
                user = User.objects.create_user(username=email, email=email, password=password)
                Buyer.objects.create(user=user, subscription_expiry_date = renews_at, test_user = test_mode, phone_no=phone)

                email_obj = {
                    "to": [email],
                    "cc":[],
                    "bcc":["barotdhrumil21@gmail.com"],
                    "subject":f"Credentials for AuraVMS Login",
                    "username":email,
                    "password":password
                }
                if settings.USE_CELERY:
                    CeleryEmailManager.new_user_signup.delay(email_obj)
                else:
                    EmailManager.new_user_signup(email_obj)
            return Response({"success":True})
        except Exception as error:
            print(error)
            email_obj = {
                        "to": ["barotdhrumil21@gmail.com"],
                        "cc":[],
                        "bcc":[""],
                        "subject":f"[ALERT] USER CREATION FAILED",
                        "username":email,
                        "error":error
                    }
            if settings.USE_CELERY:
                CeleryEmailManager.user_create_failed.delay(email_obj)
            else:
                EmailManager.user_create_failed(email_obj)  
            return Response({"success":False}) 


class CreateRFQ(APIView):
    """
        Create RFQ API With Support of:
        1. POST => To create RQF
    """
    permission_classes = (IsAuthenticated,)
    @transaction.atomic
    def post(self,request):
        """
            API POST Method
        """
        try:
            data = request.data
            items = data.get("items")
            suppliers = data.get("suppliers")
            terms_and_condition = data.get("terms_and_condition")
            payment_terms = data.get("payment_terms")
            shipping_terms = data.get("shipping_terms")
            buyer = request.user.buyer
            rfq = RequestForQuotation(buyer=buyer)
            rfq.save()
            meta_data = {
                "terms_conditions" : str(terms_and_condition) if terms_and_condition else None,
                "payment_terms" : str(payment_terms) if payment_terms else None,
                "shipping_terms" : str(shipping_terms) if shipping_terms else None
            }
            RequestForQuotationMetaData(**meta_data,request_for_quotation = rfq).save()
            for item in items:
                rfq_item = RequestForQuotationItems(request_for_quotation = rfq)
                rfq_item.product_name = str(item.get("product_name"))
                rfq_item.quantity = float(item.get("quantity"))
                rfq_item.uom = str(item.get("uom"))
                rfq_item.specifications = str(item.get("specifications")) if item.get("specifications") else ""
                rfq_item.expected_delivery_date = datetime.strptime(item.get("expected_delivery_date"),"%d/%m/%Y")
                rfq_item.save()
            email_obj = {
                "to": [],
                "cc":[],
                "bcc":[],
                "subject":f"New Quotation Requested From {rfq.buyer.company_name if rfq.buyer.company_name else rfq.buyer.user.first_name} ",
                "items":items,
                "rfq_id" : rfq.id,
                "total_no_of_items":len(items)
            }
            for supplier in suppliers:
                sup = buyer.suppliers.filter(id=supplier)
                if sup.exists():
                    sup = sup.last()
                    rfq.suppliers.add(sup)
                    email_obj["to"] = [sup.email]
                    email_obj["url"] = f"{settings.FRONTEND_URL}/rfq-response/{rfq.id}/{sup.id}"
                    email_obj["supplier_name"] = sup.company_name
                    email_obj["company_name"] = rfq.buyer.company_name
                    if settings.USE_CELERY:
                        CeleryEmailManager.send_rfq_created_email.delay(email_obj)
                    else:
                        EmailManager.send_rfq_created_email(email_obj)
            return Response({"success":True})  
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetRFQ(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To create RQF
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        """
            API GET Method
        """
        try:
            buyer = request.user.buyer
            search = request.GET.get("q", None)
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 10))

            rfq_item_query = RequestForQuotationItems.objects.filter(
                request_for_quotation__buyer=buyer
            ).select_related(
                'request_for_quotation'
            ).annotate(
                quotes_count=Count('request_for_quotation_item_response')
            ).order_by("-created")

            if search:
                rfq_item_query = rfq_item_query.filter(
                    Q(product_name__icontains=check_string(search, "Search parameter")) |
                    Q(request_for_quotation__id=int(search) if search.isdigit() else None)
                )

            rfq_item_query = rfq_item_query.values(
                'request_for_quotation__id',
                'id',
                'product_name',
                'quantity',
                'uom',
                'status',
                'specifications',
                'expected_delivery_date',
                'quotes_count',
                'created'
            )

            paginator = Paginator(rfq_item_query, limit)
            rfq_items = paginator.get_page(page)

            data = [
                {
                    "rfq_id": item['request_for_quotation__id'],
                    "rfq_item_id": item['id'],
                    "product_name": item['product_name'],
                    "quantity": {
                        "amount": item['quantity'],
                        "uom": item['uom'],
                    },
                    "status": RequestForQuotationItems.STATUS_CHOICE[item['status']-1][1],
                    "specifications": item['specifications'],
                    "expected_delivery_date": item['expected_delivery_date'].strftime("%d/%b") if item['expected_delivery_date'] else None,
                    "quotes": item['quotes_count'],
                    "created": item['created'].strftime("%d/%b/%Y")
                }
                for item in rfq_items
            ]

            return Response({
                "success": True,
                "data": data,
                "pagination": {
                    "max_page": paginator.num_pages,
                    "page_number": page
                }
            })

        except Exception as error:
            return return_400({"success": False, "error": f"{error}"})

class GetRFQResponsePageData(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To get data for RFQ response page
    """
    permission_classes = (AllowAny,)
    def get(self,request,rfq_id,supplier_id):
        """
            API GET Method
        """
        try:
            rfq = RequestForQuotation.objects.get(id=rfq_id)
            supplier = rfq.suppliers.filter(id=supplier_id)
            if not supplier.exists():
                raise Exception("Invalid Supplier ID")
            supplier = supplier.last()
            buyer = rfq.buyer
            metadata = rfq.request_for_quotation_meta_data.last()
            data = {
                "buyer":{
                    "company_name":buyer.company_name,
                    "first_name":buyer.user.first_name,
                    "last_name":buyer.user.last_name,
                    "gst_no":buyer.gst_no,
                    "address": buyer.address,
                    "currency":buyer.currency if buyer.currency else "USD",
                },
                "supplier":{
                    "supplier_id":supplier.id,
                    "company_name":supplier.company_name,
                    "person_of_contact":supplier.person_of_contact,
                    "phone_no":supplier.phone_no,
                    "email":supplier.email,
                    "categories": [category.name for category in supplier.categories.filter(active=True)]
                },
                "terms_conditions":metadata.terms_conditions,
                "payment_terms":metadata.payment_terms,
                "shipping_terms":metadata.shipping_terms,
                "items":[]
            }
            for item in rfq.request_for_quotation_items.all():
                request_response = RequestForQuotationItemResponse.objects.filter(request_for_quotation_item=item,supplier=supplier)
                item_obj = {
                        "item_id": item.id,
                        "product_name":item.product_name,
                        "quantity":item.quantity,
                        "specifications":item.specifications,
                        "uom":item.uom,
                        "responded": True if request_response.exists() else False,
                        "supplier_price": request_response.last().price if request_response.exists() else None,
                        "supplier_quantity": request_response.last().quantity if request_response.exists() else None,
                        "supplier_lead_time": request_response.last().lead_time if request_response.exists() else None,
                        "supplier_remarks": request_response.last().remarks if request_response.exists() else None,
                        "status":item.get_status_display(),
                        "expected_delivery_date":item.expected_delivery_date.strftime("%d/%b/%Y") if item.expected_delivery_date else None,
                    }
                data["items"].append(item_obj)
            return Response({"success":True,"data":data})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class BulkImportSuppliers(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = ['.csv', '.xls', '.xlsx']
    REQUIRED_COLUMNS = ['Company Name', 'Person Of Contact', 'Phone No', 'Email']


    def validate_file(self, file):
        # Check file size
        if file.size > self.MAX_UPLOAD_SIZE:
            raise ValidationError(f"File size must be no more than {self.MAX_UPLOAD_SIZE/(1024*1024)} MB")

        # Check file extension
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError("Unsupported file format. Please upload a CSV or Excel file.")
        
    def validate_columns(self, df):
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValidationError(f"Columns not found in file: {', '.join(missing_columns)}")
        
    def validate_phone_number(self, phone_number):
        # Regex for phone number validation
        regex = r'^\+?[0-9-\s]{8,200}$'
        if not re.match(regex, phone_number):
            raise ValidationError(f"Invalid phone number format: {phone_number}")

    def validate_email(self, email):
        """
        Validate an email address.
        """
        # Regular expression for email validation
        valid_regex = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$"
        
        if not re.match(valid_regex, email.strip()):
            raise ValidationError(f"Invalid email format: {email}")
        
    def post(self, request):
        try:
            file = request.FILES.get('file')

            if not file:
                return return_400({"success": False, "message": "No file was uploaded"})

            # Validate the file
            self.validate_file(file)

            # Use TemporaryUploadedFile for secure file handling
            with TemporaryUploadedFile(file.name, file.content_type, file.size, file.charset, file.content_type_extra) as temp_file:
                temp_file.write(file.read())
                temp_file.flush()

                if file.name.endswith('.csv'):
                    df = pd.read_csv(temp_file.temporary_file_path())
                elif file.name.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(temp_file.temporary_file_path())

            # Validate required columns
            self.validate_columns(df)
            
            # Convert all columns to string
            df = df.astype(str).fillna("")
            buyer=request.user.buyer

            # Process the dataframe
            with transaction.atomic():
                for index, row in df.iterrows():
                    row_num = index + 1
                     # Extract values
                    company_name = row.get('Company Name', '')
                    person_of_contact = row.get('Person Of Contact', '')
                    email = row.get('Email', '')
                    phone_no = row.get('Phone No', '')
                    
                    # Validate required fields
                    if not company_name:
                        raise ValidationError(f"Row {row_num}: Company Name is required")
                    
                    if not person_of_contact:
                        raise ValidationError(f"Row {row_num}: Person Of Contact is required")
                    
                    if not email:
                        raise ValidationError(f"Row {row_num}: Email is required")
                    
                    if not phone_no:
                        raise ValidationError(f"Row {row_num}: Phone No is required")
                    
                    # Validate phone number
                    try:
                        self.validate_phone_number(phone_no)
                    except ValidationError as e:
                        raise ValidationError(f"Row {row_num}: {str(e)}")
                    
                    # Validate email
                    try:
                        self.validate_email(email)
                    except ValidationError as e:
                        raise ValidationError(f"Row {row_num}: {str(e)}")



                    if not Supplier.objects.filter(email=email, buyer = buyer).exists():
                        supplier_obj = Supplier(buyer=buyer)
                        supplier_obj.company_name = row['Company Name']
                        supplier_obj.person_of_contact = row['Person Of Contact']
                        supplier_obj.phone_no = phone_no
                        supplier_obj.email = email
                        supplier_obj.remark = row['Remark'] if 'Remark' in row else None
                        supplier_obj.save()

            return Response({"success": True, "message": "Suppliers imported successfully"})
        except ValidationError as ve:
            return return_400({"success": False, "error": str(ve)})
        except Exception as error:
            return return_400({"success": False, "error": f"{error}"})

class GetMetaData(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To last RFQ metadata
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            last_rfq = buyer.request_for_quotations.last()
            if last_rfq:
                last_meta = last_rfq.request_for_quotation_meta_data.last()
                if last_meta:
                    data = {
                        "terms_and_conditions":last_meta.terms_conditions,
                        "payment_terms":last_meta.payment_terms,
                        "shipping_terms":last_meta.shipping_terms,
                    }
                else:
                    data = {
                        "terms_and_conditions":"",
                        "payment_terms":"",
                        "shipping_terms":"",
                        }
                return Response({"success":True,"data":data})
            raise Exception("No last RFQ metadata found")
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetSuppliers(APIView):
    """
        API to get all suppliers associated with a buyer
        1. GET => To retrieve all suppliers associated with the buyer
    """
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        try:
            buyer = request.user.buyer
            search = request.GET.get("q", "")
            
            # Get all suppliers for the buyer
            all_suppliers = buyer.suppliers.all()
            
            # Define time thresholds
            now = datetime.now()
            recent_supplier_threshold = now - timedelta(hours=1)  # Suppliers added in the last hour
            recent_rfq_threshold = now - timedelta(days=5)        # RFQs from the last 5 days
            
            # Create a dictionary to track processed suppliers
            processed_suppliers = {}
            result_data = []
            
            # STEP 1: First prioritize very recently added suppliers (last hour)
            recent_suppliers = all_suppliers.filter(created__gte=recent_supplier_threshold).order_by('-created')
            
            if search:
                recent_suppliers = recent_suppliers.filter(
                    Q(company_name__icontains=search) |
                    Q(person_of_contact__icontains=search) |
                    Q(phone_no__icontains=search) |
                    Q(email__icontains=search)
                )
                
            for supplier in recent_suppliers:
                result_data.append({
                    "supplier_id": supplier.id,
                    "company": supplier.company_name,
                    "person": supplier.person_of_contact,
                    "phone": supplier.phone_no,
                    "email": supplier.email,
                    "categories": [
                        {"category_id": category.id, "category_name": category.name} 
                        for category in supplier.categories.filter(active=True)
                    ],
                    "remark": supplier.remark
                })
                processed_suppliers[supplier.id] = True
            
            # STEP 2: Then process suppliers from recent RFQs
            rfq_list = RequestForQuotation.objects.filter(
                created__gte=recent_rfq_threshold, 
                buyer=buyer
            ).order_by('-created')
            
            for rfq in rfq_list:
                # Filter suppliers based on search query if provided
                if search:
                    suppliers_rfq = rfq.suppliers.filter(
                        Q(company_name__icontains=search) |
                        Q(person_of_contact__icontains=search) |
                        Q(phone_no__icontains=search) |
                        Q(email__icontains=search)
                    )
                else:
                    suppliers_rfq = rfq.suppliers.all().order_by('-created')
                
                # Add each supplier to the result if not already added
                for supplier in suppliers_rfq:
                    if not processed_suppliers.get(supplier.id, False):
                        result_data.append({
                            "supplier_id": supplier.id,
                            "company": supplier.company_name,
                            "person": supplier.person_of_contact,
                            "phone": supplier.phone_no,
                            "email": supplier.email,
                            "categories": [
                                {"category_id": category.id, "category_name": category.name} 
                                for category in supplier.categories.filter(active=True)
                            ],
                            "remark": supplier.remark
                        })
                        processed_suppliers[supplier.id] = True
            
            # STEP 3: Finally process any remaining suppliers
            if search:
                remaining_suppliers = all_suppliers.filter(
                    Q(company_name__icontains=search) |
                    Q(person_of_contact__icontains=search) |
                    Q(phone_no__icontains=search) |
                    Q(email__icontains=search)
                )
            else:
                remaining_suppliers = all_suppliers
                
            for supplier in remaining_suppliers:
                if not processed_suppliers.get(supplier.id, False):
                    result_data.append({
                        "supplier_id": supplier.id,
                        "company": supplier.company_name,
                        "person": supplier.person_of_contact,
                        "phone": supplier.phone_no,
                        "email": supplier.email,
                        "categories": [
                            {"category_id": category.id, "category_name": category.name} 
                            for category in supplier.categories.filter(active=True)
                        ],
                        "remark": supplier.remark
                    })
                    processed_suppliers[supplier.id] = True
            
            return Response({"success": True, "data": result_data})
            
        except Exception as error:
            return return_400({"success": False, "error": str(error)})
        
class GetSupplierCategories(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To all suppliers categories associated with buyer
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            if not buyer:
                raise Exception("This Buyer doesn't exists")
            categories = buyer.supplier_categories.filter()
            data = set()
            for category in categories:
                data.add(category.name)
            return Response({"success":True,"data":[{"label":category,"value":category} for category in list(data)]})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetRfqUom(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To all suppliers categories associated with buyer
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            if not buyer:
                raise Exception("This Buyer doesn't exists")
            uom_dic = RequestForQuotationItems.objects.filter(request_for_quotation__buyer=buyer).values("uom")
            data = set()
            for uom in uom_dic:
                data.add(uom.get("uom"))
            return Response({"success":True,"data":[{"label":uom,"value":uom} for uom in list(data)]})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetRfqProduct(APIView):
    """
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            if not buyer:
                raise Exception("This Buyer doesn't exists")
            product_dic = RequestForQuotationItems.objects.filter(request_for_quotation__buyer=buyer).values("product_name")
            data = set()
            for product in product_dic:
                data.add(product.get("product_name"))
            return Response({"success":True,"data":[{"label":uom,"value":uom} for uom in list(data)]})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class CreateRFQResponse(APIView):
    """
        Create RFQ Item Response API With Support of:
        1. POST => To Create RFQ Item Response
    """
    permission_classes = (AllowAny,)
    def post(self,request):
        """
            API POST Method
        """
        try:
            data = request.data
            rfq = RequestForQuotation.objects.filter(id=data.get("rfq_id"))
            if rfq.exists():
                rfq = rfq.last()
            else:
                raise Exception("Invalid RFQ id")
            supplier = rfq.buyer.suppliers.filter(id=data.get("supplier_id"))
            if supplier.exists():
                supplier = supplier.last()
            else:
                raise Exception("Invalid supplier id")
            items = data.get("items")
            if not items:
                raise Exception("Items not provided")
            body = []
            for _,item in enumerate(items):
                rfq_item = rfq.request_for_quotation_items.filter(id=item.get("rfq_item_id"))
                if not rfq_item.exists():
                   raise Exception("Invalid RFQ item id!")
                rfq_item = rfq_item.last()
                if rfq_item.request_for_quotation_item_response.filter(supplier=supplier).exists():
                    continue
                # body.append(f"{index+1}.{rfq_item.product_name}({item.get('quantity')} {rfq_item.uom})\tPrice : ₹{item.get('price')} \t Lead Time : {item.get('supplier_lead_time')}\t Remarks : {item.get('supplier_remarks')}\n")
                rfq_response = RequestForQuotationItemResponse(request_for_quotation_item=rfq_item,supplier=supplier)
                rfq_response.quantity = item.get("quantity")
                rfq_response.price = item.get("price")
                rfq_response.bought_quantity = item.get("quantity")
                rfq_response.bought_price = item.get("price")
                rfq_response.lead_time = item.get("supplier_lead_time")
                rfq_response.remarks = item.get("supplier_remarks")
                rfq_response.save()
            email_obj = {
                "to" : [supplier.buyer.user.email],
                "cc" : [supplier.email],
                "subject": "New quotation received",
                "supplier_name":str(supplier.company_name),
                "url":f"{settings.FRONTEND_URL}"
            }
            if settings.USE_CELERY:
                CeleryEmailManager.new_rfq_response_alert.delay(email_obj)
            else:
                EmailManager.new_rfq_response_alert(email_obj)
            return Response({"success":True})    
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class RFQItemData(APIView):
    """
        API to get and update RFQ Item responses
        1. GET => Get all responses for the RFQ Item from the suppliers
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request,rfq_item_id):
        """
            API POST Method
        """
        try:
            buyer = request.user.buyer
            rfq_item = RequestForQuotationItems.objects.get(id=rfq_item_id)
            if rfq_item.request_for_quotation.buyer!=buyer:
                raise Exception("Invalid RFQ Item ID for this buyer")
            rfq = rfq_item.request_for_quotation
            meta_data = rfq.request_for_quotation_meta_data.last()
            data = {
                "item_id":rfq_item.id,
                "product_name": rfq_item.product_name,
                "buyer":{
                    "quantity":rfq_item.quantity,
                    "address": buyer.address,
                    "gst_no": buyer.gst_no,
                    "uom":rfq_item.uom,
                    "company_name": buyer.company_name,
                    "specification": rfq_item.specifications,
                    "expected_delivery":rfq_item.expected_delivery_date.strftime("%d %b") if rfq_item.expected_delivery_date else None,
                    "terms_and_conditions" : meta_data.terms_conditions,
                    "payment_terms": meta_data.payment_terms,
                    "shipping_terms": meta_data.shipping_terms,
                    "currency":buyer.currency,
                },
                "status": "Closed" if rfq_item.request_for_quotation_item_response.filter(order_status=RequestForQuotationItemResponse.ORDER_PLACED).exists() else "Open",
                "suppliers":[]
            }
            for supplier in rfq.suppliers.all():
                res = rfq_item.request_for_quotation_item_response.filter(supplier=supplier)
                if res.exists():
                    res = res.last()
                    data["suppliers"].insert(0,{
                        "company_name":supplier.company_name,
                        "supplier_id": supplier.id,
                        "price":res.price if res else None,
                        "response_id": res.id if res else None,
                        "quantity":res.quantity if res else None,
                        "bought_quantity":res.bought_quantity if res.bought_quantity else res.quantity if res.quantity else None,
                        "bought_price":res.bought_price if res.bought_price else res.price if res.price else None,
                        "supplier_lead_time":res.lead_time if res else None,
                        "supplier_remarks":res.remarks if res else None,
                        "order_status":res.get_order_status_display() if res else None,
                        "created_at":res.created.strftime("%d/%b/%Y") if res else None,
                    })
                    continue
                else:
                    res = None
                    data["suppliers"].append({
                            "company_name":supplier.company_name,
                            "supplier_id": supplier.id,
                            "price":None,
                            "response_id": None,
                            "quantity":None,
                            "supplier_lead_time":res.lead_time if res else None,
                            "supplier_remarks":res.remarks if res else None,
                            "order_status": None
                        })
            return Response({"success":True,"data":data})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

    def post(self,request,rfq_item_id):
        """
            API POST Method
        """
        try:
            buyer = request.user.buyer
            data = request.data
            rfq_item = RequestForQuotationItems.objects.get(id=rfq_item_id)
            if rfq_item.request_for_quotation.buyer!=buyer:
                raise Exception("Invalid RFQ Item ID for this buyer")
            if not data.get("response_id"):
                raise Exception("Response ID not provided!")
            response = RequestForQuotationItemResponse.objects.get(id=data.get("response_id"))
            meta_data = rfq_item.request_for_quotation.request_for_quotation_meta_data.last()

            # Update quantity and price if provided in the request
            if data.get("bought_quantity"):
                response.bought_quantity = data.get("bought_quantity")
            if data.get("bought_price"):
                response.bought_price = data.get("bought_price")
            
            email_obj = {
                "to" : [response.supplier.email],
                "cc" : [buyer.user.email],
                "subject" : f"Purchase order from {buyer.company_name}",
                "product_name": rfq_item.product_name,
                "supplier_name": response.supplier.company_name,
                "purchase_price": "{0} {1}".format(response.bought_price ,
                                                   buyer.currency if buyer.currency else "(currency not set)"),
                "quantity": str(response.bought_quantity) + ' ' + str(rfq_item.uom),
                "lead_time": response.lead_time if response.lead_time else "",
                "buyer_name": buyer.company_name,
                "order_date": datetime.now().strftime("%d %b %Y"),
                "shipping_terms": meta_data.shipping_terms,
                "currency": buyer.currency,
                "terms_and_conditions": meta_data.terms_conditions,
                "payment_terms": meta_data.payment_terms,
            }
            if settings.USE_CELERY:
                CeleryEmailManager.send_purchase_order.delay(email_obj)
            else:
                EmailManager.send_purchase_order(email_obj)
            
            response.order_status = RequestForQuotationItemResponse.ORDER_PLACED
            response.save()
            rfq_item.status = RequestForQuotationItems.CLOSE
            rfq_item.save()
            return Response({"success":True})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetAllRFQDataEmail(APIView):
    """
        Get the all the rfq and create an csv of the same
        1. GET
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            if settings.USE_CELERY:
                CeleryEmailManager.send_all_rfq_email.delay(buyer.id)
            else:
                EmailManager.send_all_rfq_email(buyer.id)
            return Response({"success":True})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetSuppliersStatsData(APIView):
    """
        Get the all the rfq and create an csv of the same
        1. GET
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            suppliers_list = buyer.suppliers.all()
            data = []
            total_suppliers_order_value = 0
            for supplier in suppliers_list:
                 # Count the total number of RFQ items requested from this supplier
                quotes_requested_count = RequestForQuotationItems.objects.filter(
                    request_for_quotation__suppliers=supplier,
                    request_for_quotation__buyer=buyer
                ).count()
                
                quotes_received = supplier.request_for_quotation_responses.all()
                order_placed = quotes_received.filter(order_status=RequestForQuotationItemResponse.ORDER_PLACED)
                quotes_value = supplier.request_for_quotation_responses.aggregate(total=Sum(F('price') * F('quantity')))['total']
                total_order_value = supplier.request_for_quotation_responses.filter(order_status=RequestForQuotationItemResponse.ORDER_PLACED).aggregate(total=Sum(F('price') * F('quantity')))['total']
                if total_order_value:
                    total_suppliers_order_value = total_suppliers_order_value + total_order_value
                data.append({
                    "supplier_id":supplier.id,
                    "company_name":supplier.company_name,
                    "quotes_requested":quotes_requested_count,
                    "quotes_received":quotes_received.count(),
                    "quotes_value":quotes_value if quotes_value else "--",
                    "order_placed":order_placed.count(),
                    "total_order_value":total_order_value if total_order_value else 0.00,
                    "success_percent":f"{round(((order_placed.count()/quotes_received.count())*100),2) if quotes_received.count() else 0.00}%",
                })
            if total_suppliers_order_value>0:
                for d in data:
                    if d['total_order_value']:
                        d["contribution_percent"] = f"{round((d['total_order_value']/total_suppliers_order_value),2)*100}%"
                    else:
                        d["contribution_percent"] = "--"
            return Response({"success":True, "data":data})

        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class SendRFQReminder(APIView):
    """
    Send reminders to suppliers who haven't quoted for a specific RFQ item.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            rfq_item_id = request.data.get('rfq_item_id')
            if not rfq_item_id:
                raise ValueError("RFQ item ID is required")

            rfq_item = RequestForQuotationItems.objects.get(id=rfq_item_id)
            rfq = rfq_item.request_for_quotation
            buyer = request.user.buyer

            if rfq.buyer != buyer:
                raise ValueError("You don't have permission to send reminders for this RFQ")

            suppliers_to_remind = []
            for supplier in rfq.suppliers.all():
                if not RequestForQuotationItemResponse.objects.filter(
                    request_for_quotation_item=rfq_item,
                    supplier=supplier
                ).exists():
                    suppliers_to_remind.append(supplier)

            if not suppliers_to_remind:
                return Response({"success": True, "message": "All suppliers have already quoted for this item."})

            rfq_response_url = f"{settings.FRONTEND_URL}/rfq-response/{rfq.id}/"

            for supplier in suppliers_to_remind:
                email_obj = {
                    "to": [supplier.email],
                    "cc": [buyer.user.email],
                    "subject": f"Reminder: Quote Request for {rfq_item.product_name}",
                    "company_name": buyer.company_name,
                    "supplier_name": supplier.person_of_contact,
                    "product_name": rfq_item.product_name,
                    "quantity": rfq_item.quantity,
                    "uom": rfq_item.uom,
                    "specifications": rfq_item.specifications,
                    "expected_delivery_date": rfq_item.expected_delivery_date.strftime("%d %b %Y") if rfq_item.expected_delivery_date else "Not specified",
                    "rfq_response_url": rfq_response_url + str(supplier.id)
                }

                if settings.USE_CELERY:
                    CeleryEmailManager.send_rfq_reminder.delay(email_obj)
                else:
                    EmailManager.send_rfq_reminder(email_obj)

            return Response({
                "success": True,
                "message": f"Reminders sent to {len(suppliers_to_remind)} suppliers."
            })

        except RequestForQuotationItems.DoesNotExist:
            return return_400({"success": False, "error": "Invalid RFQ item ID"})
        except Exception as error:
            return return_400({"success": False, "error": str(error)})

class DashboardStats(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            filter_type = request.GET.get('filter', 'all')
            buyer = request.user.buyer

            # Define the date range based on the filter
            end_date = timezone.now()
            if filter_type == 'today':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif filter_type == '7days':
                start_date = end_date - timezone.timedelta(days=7)
            elif filter_type == '30days':
                start_date = end_date - timezone.timedelta(days=30)
            elif filter_type == '90days':
                start_date = end_date - timezone.timedelta(days=90)
            else:  # 'all'
                start_date = None

            # Apply date filter if applicable
            date_filter = Q() if start_date is None else Q(created__gte=start_date, created__lte=end_date)

            # 1. RFQs
            rfqs = RequestForQuotation.objects.filter(buyer=buyer).filter(date_filter)
            rfq_items = RequestForQuotationItems.objects.filter(request_for_quotation__in=rfqs)
            
            # 1.1 Open RFQs count
            open_rfqs_count = rfqs.filter(request_for_quotation_items__status=RequestForQuotationItems.OPEN).distinct().count()

            # 1.2 Total RFQs count
            total_rfqs_count = rfqs.count()

            # 1.3 Average item SLA
            avg_sla = rfq_items.filter(status=RequestForQuotationItems.CLOSE).annotate(
                sla=ExpressionWrapper(
                    F('request_for_quotation_item_response__updated') - F('created'),
                    output_field=DurationField()
                )
            ).aggregate(avg_sla=Avg('sla'))['avg_sla']

            # 1.4 RFQs count by product
            rfqs_by_product = rfq_items.values('product_name').annotate(count=Count('id'))

            # 1.5 Total purchase value
            total_purchase_value = RequestForQuotationItemResponse.objects.filter(
                request_for_quotation_item__in=rfq_items,
                order_status=RequestForQuotationItemResponse.ORDER_PLACED
            ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

            # 2. Suppliers
            suppliers = Supplier.objects.filter(buyer=buyer)

            # 2.1 Total suppliers count
            total_suppliers_count = suppliers.count()

            # 2.2 Suppliers by tag - count
            suppliers_by_tag = suppliers.values('categories__name').annotate(count=Count('id'))

            # 2.3 Suppliers by product count
            suppliers_by_product = RequestForQuotationItemResponse.objects.filter(
                request_for_quotation_item__in=rfq_items
            ).values('request_for_quotation_item__product_name').annotate(
                supplier_count=Count('supplier', distinct=True)
            ).values('request_for_quotation_item__product_name', 'supplier_count')

            # 2.4 Suppliers by response%
            suppliers_response = suppliers.annotate(
                total_rfqs=Count('request_for_quotations'),
                responded_rfqs=Count('request_for_quotation_responses')
            ).annotate(
                response_rate=ExpressionWrapper(
                    F('responded_rfqs') * 100.0 / F('total_rfqs'),
                    output_field=FloatField()
                )
            )

            # 2.5 & 2.6 Purchase count and value by supplier
            supplier_purchases = RequestForQuotationItemResponse.objects.filter(
                request_for_quotation_item__in=rfq_items,
                order_status=RequestForQuotationItemResponse.ORDER_PLACED
            ).values('supplier__company_name').annotate(
                count=Count('id'),
                value=Sum(F('price') * F('quantity'))
            ).order_by('-value')

            # 2.7 Lead time by suppliers
            lead_time_by_suppliers = suppliers.annotate(
                avg_lead_time=Avg(
                    Cast('request_for_quotation_responses__lead_time', output_field=FloatField())
                )
            ).exclude(avg_lead_time__isnull=True).order_by('avg_lead_time').values('company_name', 'avg_lead_time')



            total_purchase_count = sum(item['count'] for item in supplier_purchases)
            for item in supplier_purchases:
                item['count_percentage'] = (item['count'] / total_purchase_count) * 100 if total_purchase_count else 0
                item['value_percentage'] = (item['value'] / total_purchase_value) * 100 if total_purchase_value else 0

            response_data = {
                "rfqs": {
                    "open_rfqs_count": open_rfqs_count,
                    "total_rfqs_count": total_rfqs_count,
                    "average_item_sla_in_hours": avg_sla.total_seconds() / 3600 if avg_sla else None,  # in hours
                    "rfqs_by_product": list(rfqs_by_product),
                    "total_purchase_value": total_purchase_value
                },
                "suppliers": {
                    "total_suppliers_count": total_suppliers_count,
                    "suppliers_by_tag": list(suppliers_by_tag),
                    "suppliers_by_product": list(suppliers_by_product),
                    "suppliers_by_response_rate": list(suppliers_response.values('company_name', 'response_rate')),
                    "purchase_by_supplier": list(supplier_purchases),
                    "lead_time_by_suppliers": [
                        {
                            "company_name": item['company_name'],
                            "avg_lead_time_days": item['avg_lead_time']
                        }
                        for item in lead_time_by_suppliers
                    ]
                }
            }

            return Response({"success": True, "data": response_data})

        except Exception as error:
            return return_400({"success": False, "error": str(error)})

def TestEmail(request):
    obj={
        'items': [
            {'product_name': 
             'Test product 1', 
             'quantity': 1, 
             'uom': 'Boxes', 
             'specification': '', 
             'expected_delivery_date': '15/02/2024', 
             'specifications': 'Specs 1'
            }, 
            {'product_name': 'Test Product 2', 
             'quantity': 2, 
             'uom': 'Pack', 
             'specifications': 'Specs 2', 
             'expected_delivery_date': '16/02/2024'
            }], 
        'rfq_id': 19, 
        'total_no_of_items': 2, 
        'url': 'http://localhost:3000/rfq-response/19/11bd8451-163f-47c8-b380-c904eac3a234',
        'supplier_name':"Sunrise Stock",
        }
    rfq_lists = RequestForQuotation.objects.all()
    data = []
    for rfq in rfq_lists:
        for supplier in rfq.suppliers.all():
            categories = supplier.categories.filter(active=True)
            categories = [category.name for category in categories]
            print(categories)
            for item in rfq.request_for_quotation_items.all():
                res = item.request_for_quotation_item_response.filter(supplier=supplier)
                if res.exists():
                    res = res.last()
                else:
                    res = None
                obj = {
                    "RFQ Item Id" : rfq.id,
                    "Date-Time" : rfq.created.strftime("%d-%b-%Y"),
                    "Terms & Conditions" : rfq.request_for_quotation_meta_data.last().payment_terms,
                    "Payment Terms" : rfq.request_for_quotation_meta_data.last().terms_conditions,
                    "Shipping Terms" : rfq.request_for_quotation_meta_data.last().shipping_terms,
                    "Product Name" : item.product_name,
                    "Quantity":item.quantity,
                    "UOM" : item.uom,
                    "Specification" : item.specifications,
                    "Expected Delivery" : item.expected_delivery_date.strftime("%d-%b-%Y") if item.expected_delivery_date else None,
                    "RFQ Status" : "",
                    "Supplier Name" : supplier.company_name,
                    "Supplier POC" : supplier.person_of_contact,
                    "Supplier Phone" : supplier.phone_no,
                    "Supplier Email" : supplier.email,
                    "Supplier Categories" : "|".join(categories) if categories else "",
                    "Supplier Price" : res.price if res else None,
                    "Supplier Quantity" : res.quantity if res else None,
                    "Lead Time" : res.delivery_date.strftime("%d-%b-%Y") if (res and res.delivery_date) else None,
                    "Quote Received On" : res.created.strftime("%d-%b-%Y") if res else None,
                    "Order Status" : res.get_order_status_display() if res else None,
                    "Order Placed On" : res.updated.strftime("%d-%b-%Y") if (res and res.order_status==1)  else None,
                }
                data.append(obj)
    print(data,len(data))
    return render(request,"email/RFQ_Created_Email_Template.html",obj)

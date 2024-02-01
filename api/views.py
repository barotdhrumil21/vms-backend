from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from authentication.utils import return_400
from api.models import Supplier,RequestForQuotation, RequestForQuotationItems, RequestForQuotationMetaData, SupplierCategory, RequestForQuotationItemResponse
from api.helper import check_string
from django.db.models import Q
from datetime import datetime
from django.db import transaction

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
            company_name = data.get("company_name") #IMPORTANT
            person_of_contact = data.get("person_of_contact") #IMPORTANT
            phone_no = data.get("phone_no") #IMPORTANT
            email = data.get("email") #IMPORTANT
            categories = data.get("categories")
            remark = data.get("remark")
            buyer = request.user.buyer
            if not (company_name and person_of_contact and phone_no and email):
                raise Exception("Important parameters missing!")
            if buyer.suppliers.filter(email=email).exists():
                raise Exception("Supplier with this email id already exists!")
            supplier_obj = Supplier(buyer=buyer)
            supplier_obj.company_name = check_string(company_name,"Company Name")
            supplier_obj.person_of_contact = check_string(person_of_contact,"Person Of Contact")
            supplier_obj.phone_no = check_string(phone_no,"Phone No")
            supplier_obj.email = check_string(email,"Email")
            supplier_obj.remark = check_string(remark,"Remark") if remark else None
            supplier_obj.save()
            for category in categories:
                supplier_category = SupplierCategory(buyer=buyer,supplier = supplier_obj)
                supplier_category.name = check_string(category,"category")
                supplier_category.save()
            return Response({"success":True, "data":{"supplier_id":supplier_obj.id}})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})
    
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
                    supplier_obj.phone_no = check_string(data.get("phone_no"),"Phone No")
                elif field=="email" and bool(data.get("email")):
                    supplier_obj.email = check_string(data.get("email"),"Email")
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
                "terms_conditions" : check_string(terms_and_condition,"terms_and_conditions") if terms_and_condition else None,
                "payment_terms" : check_string(payment_terms,"payment_terms") if payment_terms else None,
                "shipping_terms" : check_string(shipping_terms,"shipping_terms") if shipping_terms else None
            }
            RequestForQuotationMetaData(**meta_data,request_for_quotation = rfq).save()
            for item in items:
                rfq_item = RequestForQuotationItems(request_for_quotation = rfq)
                rfq_item.product_name = check_string(item.get("product_name"),"item_product_name")
                rfq_item.quantity = float(item.get("quantity"))
                rfq_item.uom = check_string(item.get("uom"),"item_uom")
                rfq_item.specifications = check_string(item.get("specifications"),"item_specifications") if item.get("specifications") else None
                rfq_item.expected_delivery_date = datetime.strptime(item.get("expected_delivery_date"),"%d/%m/%Y")
                rfq_item.save()
            for supplier in suppliers:
                sup = buyer.suppliers.filter(id=supplier)
                if sup.exists():
                    rfq.suppliers.add(sup.last())
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
            search = request.GET.get("q",None)
            rfq_item_list = RequestForQuotationItems.objects.filter(request_for_quotation__buyer=buyer)
            if search and rfq_item_list.exists():
                rfq_item_list = rfq_item_list.filter(Q(product_name__icontains=check_string(search,"Search parameter"))|Q(request_for_quotation__id=int(search) if search.isdigit() else None))
            data = []
            for item in rfq_item_list:
                obj_json= {
                    "rfq_id":item.request_for_quotation.id,
                    "rfq_item_id": item.id,
                    "product_name": item.product_name,
                    "quantity" : {
                            "amount":item.quantity,
                            "uom": item.uom,
                        },
                    "status": item.get_status_display(),
                    "specifications": item.specifications,
                    "expected_delivery_date": item.expected_delivery_date.strftime("%d/%b") if item.expected_delivery_date else None,
                    "quotes": item.request_for_quotation_item_response.all().count()                       
                }
                data.append(obj_json)
            return Response({"success":True,"data":data})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

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
                    "address": buyer.address
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
                "items":[
                    {
                        "item_id": item.id,
                        "product_name":item.product_name,
                        "quantity":item.quantity,
                        "specifications":item.specifications,
                        "uom":item.uom,
                        "responded": True if RequestForQuotationItemResponse.objects.filter(request_for_quotation_item=item,supplier=supplier).exists() else False,
                        "status":item.get_status_display(),
                        "expected_delivery_date":item.expected_delivery_date.strftime("%d/%b") if item.expected_delivery_date else None,
                    }
                    for item in rfq.request_for_quotation_items.all()
                ]
            }
            return Response({"success":True,"data":data})
            
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})
            
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
                last_rfq = last_rfq.request_for_quotation_meta_data.last()
                data = {
                    "terms_and_conditions":last_rfq.terms_conditions,
                    "payment_terms":last_rfq.payment_terms,
                    "shipping_terms":last_rfq.shipping_terms,
                }
                return Response({"success":True,"data":data})
            raise Exception("No last RFQ metadata found")
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

class GetSuppliers(APIView):
    """
        Create RFQ API With Support of:
        1. GET => To all suppliers associated buyer
    """
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        try:
            buyer = request.user.buyer
            suppliers = buyer.suppliers.all()
            data = []
            for supplier in suppliers:
                sup_dic = {
                    "supplier_id":supplier.id,
                    "company":supplier.company_name,
                    "person":supplier.person_of_contact,
                    "phone":supplier.phone_no,
                    "email":supplier.email,
                    "categories": [{"category_id":category.id,"category_name":category.name} for category in supplier.categories.filter(active=True).all()],
                    "remark": supplier.remark
                }
                data.append(sup_dic)
            return Response({"success":True,"data":data})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})

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
            for item in items:
                rfq_item = rfq.request_for_quotation_items.filter(id=item.get("rfq_item_id"))
                if not rfq_item.exists():
                   raise Exception("Invalid RFQ item id!")
                rfq_item = rfq_item.last()
                if rfq_item.request_for_quotation_item_response.filter(supplier=supplier).exists():
                    continue
                rfq_response = RequestForQuotationItemResponse(request_for_quotation_item=rfq_item,supplier=supplier)
                rfq_response.quantity = item.get("quantity")
                rfq_response.price = item.get("price")
                rfq_response.delivery_date = datetime.strptime(item.get("delivery_date"),"%d/%m/%Y") if item.get("delivery_date") else None
                rfq_response.save()
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
                    "shipping_terms": meta_data.shipping_terms
                },
                "status": "Closed" if rfq_item.request_for_quotation_item_response.filter(order_status=RequestForQuotationItemResponse.ORDER_PLACED).exists() else "Open",
                "suppliers":[
                        {
                            "company_name":response.supplier.company_name,
                            "price":response.price,
                            "response_id": response.id,
                            "quantity":response.quantity,
                            "delivery_by":response.delivery_date.strftime("%d / %b") if response.delivery_date else None,
                            "order_status":response.get_order_status_display()
                        }
                    for response in rfq_item.request_for_quotation_item_response.all()
                    ]
            }
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
            response.order_status = RequestForQuotationItemResponse.ORDER_PLACED
            response.save()
            rfq_item.status = RequestForQuotationItems.CLOSE
            rfq_item.save()
            return Response({"success":True})
        except Exception as error:
            return return_400({"success":False,"error":f"{error}"})



from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from authentication.utils import return_400
from api.models import Supplier,RequestForQuotation, RequestForQuotationItems, RequestForQuotationMetaData, SupplierCategory
from api.helper import check_string
import json
from django.db.models import Q
from datetime import datetime
from django.core.paginator import Paginator
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
                "terms_conditions" : check_string(terms_and_condition,"terms_and_conditions"),
                "payment_terms" : check_string(payment_terms,"payment_terms"),
                "shipping_terms" : check_string(shipping_terms,"shipping_terms")
            }
            RequestForQuotationMetaData(**meta_data,request_for_quotation = rfq).save()
            for item in items:
                rfq_item = RequestForQuotationItems(request_for_quotation = rfq)
                rfq_item.product_name = check_string(item.get("product_name"),"item_product_name")
                rfq_item.quantity = float(item.get("quantity"))
                rfq_item.uom = check_string(item.get("uom"),"item_uom")
                rfq_item.specifications = check_string(item.get("specifications"),"item_specifications")
                rfq_item.specifications = check_string(item.get("specifications"),"item_specifications")
                rfq_item.expected_delivery_date = datetime.strptime(item.get("expected_delivery_date"),"%Y-%m-%d")
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
            limit = request.GET.get("limit",10)
            page = request.GET.get("page",1)
            search = request.GET.get("q",None)
            rfq_item_list = RequestForQuotationItems.objects.filter(request_for_quotation__buyer=buyer)
            if search and rfq_item_list.exists():
                rfq_item_list = rfq_item_list.filter(Q(product_name__icontains=check_string(search,"Search parameter"))|Q(request_for_quotation__id=search if search.isdigit() else None))
            data = []
            for item in rfq_item_list:
                obj_json= {
                    "rfq_id":item.request_for_quotation.id,
                    "rfq_item_id": item.id,
                    "product_name": item.product_name,
                    "quantity" : item.quantity,
                    "uom": item.uom,
                    "status": item.get_status_display(),
                    "specifications": item.specifications,
                    "expected_delivery_date": item.expected_delivery_date.strftime("%d/%b") if item.expected_delivery_date else None,
                    "quotes": 10                        
                }
                data.append(obj_json)
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
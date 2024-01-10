from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from authentication.utils import return_400
from api.models import Supplier
from api.helper import check_string
import json

class CreateSupplier(APIView):
    """
        Create Supplier API
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
            supplier_obj.categories = categories
            supplier_obj.remark = check_string(remark,"Remark")
            supplier_obj.save()
            return Response({"Success":True, "data":{"supplier_id":supplier_obj.id}})
        except Exception as error:
            return return_400({"Success":False,"error":f"{error}"})
    
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
                    supplier_obj.categories = data.get("categories")
                elif field=="remark" and bool(data.get("remark")):
                    supplier_obj.remark = check_string(data.get("remark"),"Remark")
            supplier_obj.save()
            return Response({"Success":True})
        except Exception as error:
            return return_400({"Success":False,"error":f"{error}"})
        
from authentication import views
from django.urls import path

urlpatterns = [
    path('test/', views.Test.as_view(),name="test"),
    path('login/', views.LoginAPI.as_view(),name="login"),   
    path('signup/', views.SignUpView.as_view(),name="signup"),   
    path('user-details/',views.GetUserDetailsAPI.as_view(),name='user-details'),
       
]

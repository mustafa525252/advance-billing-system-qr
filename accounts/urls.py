from django.urls import path
from . import views


urlpatterns = [
    path('admin-login/',views.admin_login,name='admin_login'),
    path('',views.distributor_login,name='distributor_login'),
    path('admin-dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('distributor-dashboard/',views.distributor_dashboard,name='distributor_dashboard'),
    path('logout/',views.logout_view,name='logout'),
    path('distributor-register/',views.distributor_register,name='distributor_register'),
    path('forgot-password/',views.forgot_password,name='forgot_password'),
    path('verify-otp/',views.verify_otp,name='verify_otp'),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path('reset-password/',views.reset_password,name='reset_password'),
    path('distributor-profile/',views.distributor_profile,name='distributor_profile'),
    path('edit-profile/',views.edit_distributor_profile,name='edit_distributor_profile'),
    path('add-customer/',views.add_customer,name='add_customer'),
    path('customers/',views.customer_list,name='customer_list'),
    path('customer/<int:customer_id>/edit/',views.edit_customer,name='edit_customer'),
    path('customer/<int:customer_id>/delete/',views.delete_customer,name='delete_customer'),
    path('products/add/',views.add_product,name='add_product'),
    path('products/',views.product_list,name='product_list'),
    path('products/<int:product_id>/edit/',views.edit_product,name='edit_product'),
    path('products/<int:product_id>/delete/',views.delete_product,name='delete_product'),
    path('logout/',views.logout_view,name='logout'),
]
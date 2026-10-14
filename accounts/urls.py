from django.urls import path
from . import views
from .views import admin_reports_pdf, qr_decoder

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
    path('invoices/create/',views.create_invoice,name='create_invoice'),
    path('invoices/',views.invoice_list,name='invoice_list'),
    path('invoices/<int:invoice_id>/',views.invoice_detail,name='invoice_detail'),
    path('invoices/<int:invoice_id>/print/',views.print_invoice,name='print_invoice'),
    path('invoice/<int:invoice_id>/download/',views.download_invoice_pdf,name='download_invoice_pdf'),
    #admin register api
    path('accounts/admin/register/',views.admin_register,name='admin_register'),
    path('api/admin/register/',views.admin_register_api,name='admin_register_api'),
    path('accounts/admin/forgot-password/',views.admin_forgot_password,name='admin_forgot_password'),
    path('accounts/admin/verify-otp/',views.admin_verify_otp,name='admin_verify_otp'),
    path('accounts/admin/reset-password/',views.admin_reset_password,name='admin_reset_password'),
    path('api/customer/register/',views.customer_register_api,name='customer_register_api'),
    # admin report
    path('admin-reports/', views.admin_reports, name='admin_reports'),
    path('admin-distributors/',views.view_distributors,name='view_distributors'),
    path('admin-customers/',views.view_customers,name='view_customers'),
    path('admin-products/',views.view_products,name='view_products'),
    # Add inside urlpatterns:
    path('admin-reports/pdf/',views.admin_reports_pdf,name='admin_reports_pdf'),
    # Add inside your existing urlpatterns list:
    path('qr-decoder/', qr_decoder, name='qr_decoder'),
    path('logout/',views.logout_view,name='logout'),
]
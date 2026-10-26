from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
import random
from datetime import timedelta
from django.utils import timezone
from .models import OTPVerification, DistributorProfile
from .models import Customer, Product, Invoice, InvoiceItem
from django.contrib.auth.models import User, Group
from django.db import transaction   
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Sum
from .qr_utils import generate_invoice_qr
from django.http import HttpResponse, request
from xhtml2pdf import pisa
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.validators import validate_email
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.template.loader import get_template
import cv2
import numpy as np
from django.db.models import ProtectedError

# Create your views here.


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')

        logout(request)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Enter your username and password.')
            return render(request, 'accounts/admin_login.html')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            messages.error(request, 'Invalid username or password.')

        elif not user.is_staff or not user.is_active:
            messages.error(request, 'This account does not have Admin access.')

        else:
            login(request, user)
            return redirect('admin_dashboard')

    return render(request, 'accounts/admin_login.html')


def distributor_login(request):

    if request.user.is_authenticated:
        return redirect('distributor_dashboard')

    if request.method == 'POST':

        email = request.POST.get(
            'email',
            ''
        ).strip().lower()

        password = request.POST.get(
            'password',
            ''
        )

        # -------------------------
        # Validate fields
        # -------------------------

        if not email or not password:

            messages.error(
                request,
                'Please enter email and password.'
            )

            return render(
                request,
                'accounts/distributor_login.html'
            )

        # -------------------------
        # Find user by email
        # -------------------------

        try:

            user_obj = User.objects.get(
                email__iexact=email
            )

        except User.DoesNotExist:

            messages.error(
                request,
                'Invalid email or password.'
            )

            return render(
                request,
                'accounts/distributor_login.html'
            )

        # -------------------------
        # Authenticate user
        # -------------------------

        user = authenticate(
            request,
            username=user_obj.username,
            password=password
        )

        if user is None:

            messages.error(
                request,
                'Invalid email or password.'
            )

            return render(
                request,
                'accounts/distributor_login.html'
            )

        # -------------------------
        # Check Distributor role
        # -------------------------

        if not user.groups.filter(
            name='Distributor'
        ).exists():

            messages.error(
                request,
                'This account is not registered as a Distributor.'
            )

            return render(
                request,
                'accounts/distributor_login.html'
            )

        # -------------------------
        # Login
        # -------------------------

        login(request, user)

        print(
            'DISTRIBUTOR LOGIN SUCCESS:',
            user.email
        )

        return redirect(
            'distributor_dashboard'
        )

    return render(
        request,
        'accounts/distributor_login.html'
    )


@login_required
def admin_dashboard(request):

    if not request.user.is_staff:

        messages.error(
            request,
            'Admin access required.'
        )

        return redirect('distributor_login')


    distributors = DistributorProfile.objects.select_related(
        'user'
    ).all().order_by('-created_at')


    customers = Customer.objects.all()


    products = Product.objects.all().order_by(
        '-created_at'
    )


    context = {

        'distributors': distributors,

        'customers': customers,

        'products': products,

        'distributor_count': distributors.count(),

        'customer_count': customers.count(),

        'product_count': products.count(),

    }


    return render(
        request,
        'accounts/admin_dashboard.html',
        context
    )


@login_required
def distributor_dashboard(request):

    if not request.user.is_authenticated:
        return redirect('distributor_login')

    if not request.user.groups.filter(
        name='Distributor'
    ).exists():

        return redirect('distributor_login')

    return render(
        request,
        'accounts/distributor_dashboard.html'
    )


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')

import re

from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect


def distributor_register(request):

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        # -------------------------
        # Name validation
        # -------------------------

        if not name:
            messages.error(
                request,
                'Full name is required.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        if len(name) < 3:
            messages.error(
                request,
                'Name must contain at least 3 characters.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        if not re.match(
            r'^[A-Za-z ]+$',
            name
        ):
            messages.error(
                request,
                'Name can contain only letters and spaces.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Email validation
        # -------------------------

        if not email:
            messages.error(
                request,
                'Email address is required.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(
            email_pattern,
            email
        ):
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Phone validation
        # -------------------------

        if not phone:
            messages.error(
                request,
                'Phone number is required.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        if not phone.isdigit():
            messages.error(
                request,
                'Phone number must contain only digits.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        if len(phone) != 10:
            messages.error(
                request,
                'Phone number must contain exactly 10 digits.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Password validation
        # -------------------------

        if not password:
            messages.error(
                request,
                'Password is required.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        if len(password) < 8:
            messages.error(
                request,
                'Password must contain at least 8 characters.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # At least one letter
        if not re.search(
            r'[A-Za-z]',
            password
        ):
            messages.error(
                request,
                'Password must contain at least one letter.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # At least one number
        if not re.search(
            r'\d',
            password
        ):
            messages.error(
                request,
                'Password must contain at least one number.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Confirm password
        # -------------------------

        if password != confirm_password:
            messages.error(
                request,
                'Passwords do not match.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Duplicate email
        # -------------------------

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                'This email is already registered.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Duplicate phone
        # -------------------------

        if DistributorProfile.objects.filter(
            phone=phone
        ).exists():

            messages.error(
                request,
                'This phone number is already registered.'
            )
            return render(
                request,
                'accounts/distributor_register.html'
            )

        # -------------------------
        # Create username
        # -------------------------

        username = email.split('@')[0]

        original_username = username
        counter = 1

        while User.objects.filter(
            username=username
        ).exists():

            username = (
                f'{original_username}{counter}'
            )

            counter += 1

        # -------------------------
        # Create User
        # -------------------------

        user = User.objects.create_user(
            username=username,
            first_name=name,
            email=email,
            password=password
        )

        # -------------------------
        # Distributor Group
        # -------------------------

        distributor_group, created = (
            Group.objects.get_or_create(
                name='Distributor'
            )
        )

        user.groups.add(distributor_group)

        # -------------------------
        # Distributor Profile
        # -------------------------

        DistributorProfile.objects.create(
            user=user,
            phone=phone
        )

        # -------------------------
        # Success
        # -------------------------

        messages.success(
            request,
            'Registration successful! Please login.'
        )

        return redirect(
            'distributor_login'
        )

    return render(
        request,
        'accounts/distributor_register.html'
    )
    
    
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

    if not email:
        messages.error(
            request,
            'Please enter your email address.'
        )
        return render(
            request,
            'accounts/forgot_password.html'
        )

    # Find users matching this email
    users = User.objects.filter(email__iexact=email)

    if not users.exists():
        messages.error(
            request,
            'No account found with this email address.'
        )
        return render(
            request,
            'accounts/forgot_password.html'
        )

    # Prevent ambiguity when multiple accounts share an email
    if users.count() > 1:
        messages.error(
            request,
            'Multiple accounts use this email. Please contact the administrator.'
        )
        return render(
            request,
            'accounts/forgot_password.html'
        )

    user = users.first()

    # Generate OTP
    otp = generate_reset_otp(email)

    # Store email in session
    request.session['reset_email'] = email

    # Reset verification status
    request.session['otp_verified'] = False

    # Send OTP
    send_mail(
        subject='Password Reset OTP',
        message=(
            f'Your password reset OTP is: {otp}\n\n'
            'This OTP will expire in 5 minutes.'
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )

    messages.success(
        request,
        'OTP has been sent to your email.'
    )
    return redirect('verify_otp')

    return render(
        request,
        'accounts/forgot_password.html'
    )

    
def generate_otp():
    return str(random.randint(100000, 999999))


def verify_otp(request):

    email = request.session.get('reset_email')

    if not email:
        messages.error(
            request,
            'Please request a new OTP.'
        )
        return redirect('forgot_password')

    if request.method == 'POST':

        otp = request.POST.get('otp', '').strip()

        print("================================")
        print("RESET EMAIL:", email)
        print("ENTERED OTP:", repr(otp))

        # Get latest OTP for this email
        verification = OTPVerification.objects.filter(
            email__iexact=email,
            is_verified=False
        ).order_by('-id').first()

        if verification:

            print("DATABASE EMAIL:", verification.email)
            print("DATABASE OTP:", repr(verification.otp_code))
            print("EXPIRED:", verification.is_expired())
            print("VERIFIED:", verification.is_verified)

        else:

            print("NO OTP FOUND IN DATABASE")

        print("================================")

        if not verification:
            messages.error(
                request,
                'Invalid OTP.'
            )
            return render(
                request,
                'accounts/verify_otp.html'
            )

        # Check OTP
        if verification.otp_code != otp:

            messages.error(
                request,
                'Invalid OTP.'
            )
            return render(
                request,
                'accounts/verify_otp.html'
            )

        # Check expiry
        if verification.is_expired():

            messages.error(
                request,
                'OTP has expired. Please request a new OTP.'
            )
            return render(
                request,
                'accounts/verify_otp.html'
            )

        # OTP is correct
        verification.is_verified = True
        verification.save()

        request.session['otp_verified'] = True

        return redirect('reset_password')

    return render(
        request,
        'accounts/verify_otp.html'
    )   
    
    
def generate_reset_otp(email):

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Delete existing OTPs
    OTPVerification.objects.filter(
        email__iexact=email
    ).delete()

    # Expire after 5 minutes
    expires_at = (
        timezone.now()
        + timedelta(minutes=5)
    )

    # Create new OTP
    OTPVerification.objects.create(
        email=email,
        otp_code=otp,
        expires_at=expires_at,
        is_verified=False
    )

    return otp    
        
def logout_view(request):

    logout(request)

    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return redirect('distributor_login')

def resend_otp(request):

    email = request.session.get('reset_email')

    if not email:
        messages.error(
            request,
            'Your password reset session has expired.'
        )

        return redirect('forgot_password')

    # Generate OTP
    otp = generate_reset_otp(email)

    # Send new OTP
    send_mail(
        subject='Password Reset OTP',
        message=(
            f'Your new password reset OTP is: {otp}\n\n'
            'This OTP will expire in 5 minutes.'
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )

    messages.success(
        request,
        'A new OTP has been sent to your email.'
    )

    return redirect('verify_otp')

def reset_password(request):

    email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')

    if not email or not otp_verified:
        messages.error(
            request,
            'Please verify your OTP first.'
        )
        return redirect('forgot_password')

    if request.method == 'POST':

        password = request.POST.get('password', '')
        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        if not password:
            messages.error(
                request,
                'Please enter a new password.'
            )
            return render(
                request,
                'accounts/reset_password.html'
            )

        if password != confirm_password:
            messages.error(
                request,
                'Passwords do not match.'
            )
            return render(
                request,
                'accounts/reset_password.html'
            )

        try:
            user = User.objects.get(
                email__iexact=email
            )
        except User.DoesNotExist:
            messages.error(
                request,
                'User account not found.'
            )
            return redirect('forgot_password')

        user.set_password(password)
        user.save()

        # Clear password reset session
        request.session.pop('reset_email', None)
        request.session.pop('otp_verified', None)

        messages.success(
            request,
            'Your password has been reset successfully. You can now login.'
        )

        return redirect('distributor_login')

    return render(
        request,
        'accounts/reset_password.html'
    )
    
@login_required(login_url='distributor_login')
def distributor_profile(request):

    user = request.user

    # Only distributors can access this page
    if not user.groups.filter(name='Distributor').exists():
        return redirect('distributor_login')

    profile = user.distributor_profile

    return render(
        request,
        'accounts/distributor_profile.html',
        {
            'user': user,
            'profile': profile,
        }
    )
    
@login_required(login_url='distributor_login')
def add_customer(request):

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        # -------------------------
        # Name Validation
        # -------------------------

        if not name:
            messages.error(
                request,
                'Customer name is required.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if len(name) < 3:
            messages.error(
                request,
                'Customer name must contain at least 3 characters.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if not re.match(r'^[A-Za-z ]+$', name):
            messages.error(
                request,
                'Customer name can contain only letters and spaces.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        # -------------------------
        # Email Validation
        # -------------------------

        if not email:
            messages.error(
                request,
                'Customer email is required.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(email_pattern, email):
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        # -------------------------
        # Phone Validation
        # -------------------------

        if not phone:
            messages.error(
                request,
                'Customer phone number is required.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if not phone.isdigit():
            messages.error(
                request,
                'Phone number must contain only digits.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if len(phone) != 10:
            messages.error(
                request,
                'Phone number must contain exactly 10 digits.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        # -------------------------
        # Address Validation
        # -------------------------

        if not address:
            messages.error(
                request,
                'Customer address is required.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if len(address) < 5:
            messages.error(
                request,
                'Address must contain at least 5 characters.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        # -------------------------
        # Duplicate Validation
        # -------------------------

        if Customer.objects.filter(
            distributor=request.user,
            email__iexact=email
        ).exists():

            messages.error(
                request,
                'A customer with this email already exists.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        if Customer.objects.filter(
            distributor=request.user,
            phone=phone
        ).exists():

            messages.error(
                request,
                'A customer with this phone number already exists.'
            )
            return render(
                request,
                'accounts/add_customer.html'
            )

        # -------------------------
        # Save Customer
        # -------------------------

        Customer.objects.create(
            distributor=request.user,
            name=name,
            email=email,
            phone=phone,
            address=address
        )

        # -------------------------
        # Success Message
        # -------------------------

        messages.success(
            request,
            'Customer added successfully!'
        )

        return redirect('add_customer')

    return render(
        request,
        'accounts/add_customer.html'
    )
    
@login_required(login_url='distributor_login')
def edit_distributor_profile(request):

    user = request.user
    profile = user.distributor_profile

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()

        # -------------------------
        # Name Validation
        # -------------------------

        if not name:
            messages.error(
                request,
                'Full name is required.'
            )
            return redirect('edit_distributor_profile')

        if len(name) < 3:
            messages.error(
                request,
                'Name must contain at least 3 characters.'
            )
            return redirect('edit_distributor_profile')

        if not re.match(r'^[A-Za-z ]+$', name):
            messages.error(
                request,
                'Name can contain only letters and spaces.'
            )
            return redirect('edit_distributor_profile')

        # -------------------------
        # Email Validation
        # -------------------------

        if not email:
            messages.error(
                request,
                'Email address is required.'
            )
            return redirect('edit_distributor_profile')

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(email_pattern, email):
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return redirect('edit_distributor_profile')

        # Check duplicate email excluding current user
        if User.objects.filter(
            email__iexact=email
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                'This email is already registered.'
            )
            return redirect('edit_distributor_profile')

        # -------------------------
        # Phone Validation
        # -------------------------

        if not phone:
            messages.error(
                request,
                'Phone number is required.'
            )
            return redirect('edit_distributor_profile')

        if not phone.isdigit():
            messages.error(
                request,
                'Phone number must contain only digits.'
            )
            return redirect('edit_distributor_profile')

        if len(phone) != 10:
            messages.error(
                request,
                'Phone number must contain exactly 10 digits.'
            )
            return redirect('edit_distributor_profile')

        # Check duplicate phone excluding current profile
        if DistributorProfile.objects.filter(
            phone=phone
        ).exclude(
            id=profile.id
        ).exists():

            messages.error(
                request,
                'This phone number is already registered.'
            )
            return redirect('edit_distributor_profile')

        # -------------------------
        # Save Updated Data
        # -------------------------

        user.first_name = name
        user.email = email
        user.save()

        profile.phone = phone
        profile.save()

        messages.success(
            request,
            'Profile updated successfully!'
        )

        return redirect('distributor_profile')

    return render(
        request,
        'accounts/edit_distributor_profile.html',
        {
            'user': user,
            'profile': profile,
        }
    )
    
    
@login_required(login_url='distributor_login')
def customer_list(request):

    search_query = request.GET.get('search', '').strip()

    customers = Customer.objects.filter(
        distributor=request.user
    )

    if search_query:

        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    customers = customers.order_by('-created_at')

    return render(
        request,
        'accounts/customer_list.html',
        {
            'customers': customers,
            'search_query': search_query,
        }
    )
    
@login_required(login_url='distributor_login')
def edit_customer(request, customer_id):

    customer = Customer.objects.filter(
        id=customer_id,
        distributor=request.user
    ).first()

    if not customer:
        messages.error(
            request,
            'Customer not found.'
        )
        return redirect('customer_list')

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        # Name validation
        if not name:
            messages.error(request, 'Customer name is required.')
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        if len(name) < 3:
            messages.error(
                request,
                'Customer name must contain at least 3 characters.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        if not re.match(r'^[A-Za-z ]+$', name):
            messages.error(
                request,
                'Customer name can contain only letters and spaces.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Email validation
        if not email:
            messages.error(request, 'Email is required.')
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(email_pattern, email):
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Duplicate email excluding current customer
        if Customer.objects.filter(
            distributor=request.user,
            email__iexact=email
        ).exclude(id=customer.id).exists():

            messages.error(
                request,
                'Another customer with this email already exists.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Phone validation
        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        if not phone.isdigit() or len(phone) != 10:
            messages.error(
                request,
                'Phone number must contain exactly 10 digits.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Duplicate phone excluding current customer
        if Customer.objects.filter(
            distributor=request.user,
            phone=phone
        ).exclude(id=customer.id).exists():

            messages.error(
                request,
                'Another customer with this phone number already exists.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Address validation
        if not address:
            messages.error(request, 'Address is required.')
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        if len(address) < 5:
            messages.error(
                request,
                'Address must contain at least 5 characters.'
            )
            return redirect(
                'edit_customer',
                customer_id=customer.id
            )

        # Update customer
        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.address = address
        customer.save()

        messages.success(
            request,
            'Customer updated successfully!'
        )

        return redirect('customer_list')

    return render(
        request,
        'accounts/edit_customer.html',
        {
            'customer': customer
        }
    )
    
@login_required(login_url='distributor_login')
@require_POST
def delete_customer(request, customer_id):

    customer = Customer.objects.filter(
        id=customer_id,
        distributor=request.user
    ).first()

    if not customer:
        messages.error(
            request,
            'Customer not found or you do not have permission.'
        )
        return redirect('customer_list')

    customer_name = customer.name

    customer.delete()

    messages.success(
        request,
        f'{customer_name} was deleted successfully!'
    )

    return redirect('customer_list')

@login_required(login_url='distributor_login')
def add_product(request):
    if request.method == 'POST':
        data = validate_product_data(request)

        if data is None:
            return render(request, 'accounts/add_product.html')

        Product.objects.create(
            distributor=request.user,
            **data
        )

        messages.success(request, 'Product added successfully.')
        return redirect('product_list')

    return render(request, 'accounts/add_product.html')
    
    
@login_required(login_url='distributor_login')
def product_list(request):
    search_query = request.GET.get('search', '').strip()

    products = Product.objects.filter(
        distributor=request.user
    ).order_by('-created_at')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
        )

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(
        request,
        'accounts/product_list.html',
        context
    )
    
    
@login_required(login_url='distributor_login')
def edit_product(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        distributor=request.user
    )

    if request.method == 'POST':
        data = validate_product_data(request)

        if data is None:
            return render(
                request,
                'accounts/edit_product.html',
                {'product': product}
            )

        product.name = data['name']
        product.category = data['category']
        product.price = data['price']
        product.stock = data['stock']
        product.gst_rate = data['gst_rate']
        product.save()

        messages.success(request, 'Product updated successfully.')
        return redirect('product_list')

    return render(
        request,
        'accounts/edit_product.html',
        {'product': product}
    )
    
    
@login_required(login_url='distributor_login')
def delete_product(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        distributor=request.user
    )

    if request.method == 'POST':
        try:
            product.delete()

        except ProtectedError:
            messages.error(
                request,
                'This product cannot be deleted because it is '
                'linked to an existing invoice. You can keep it '
                'and set its stock to 0 instead.'
            )
            return redirect('product_list')

        messages.success(request, 'Product deleted successfully.')
        return redirect('product_list')

    return render(
        request,
        'accounts/delete_product.html',
        {'product': product}
    )
    
@login_required
def create_invoice(request):

    customers = Customer.objects.filter(
        distributor=request.user
    )

    products = Product.objects.filter(
        distributor=request.user
    )

    if request.method == 'POST':

        customer_id = request.POST.get('customer')

        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        gst_rates = request.POST.getlist('gst_rate[]')
        discounts = request.POST.getlist('discount[]')


        # Validate customer

        if not customer_id:

            messages.error(
                request,
                'Please select a customer.'
            )

            return redirect('create_invoice')


        customer = get_object_or_404(
            Customer,
            id=customer_id,
            distributor=request.user
        )


        # Check at least one product exists

        valid_products = [
            product_id
            for product_id in product_ids
            if product_id
        ]

        if not valid_products:

            messages.error(
                request,
                'Please select at least one product.'
            )

            return redirect('create_invoice')


        try:

            with transaction.atomic():

                # Generate invoice number

                invoice_number = (
                    f"INV-"
                    f"{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
                )


                # Create invoice first

                invoice = Invoice.objects.create(
                    distributor=request.user,
                    customer=customer,
                    invoice_number=invoice_number,
                    total_amount=Decimal('0.00')

                )


                grand_total = Decimal('0.00')


                # Create invoice items

                for index, product_id in enumerate(product_ids):

                    # Skip empty product rows

                    if not product_id:
                        continue


                    product = get_object_or_404(
                        Product,
                        id=product_id,
                        distributor=request.user
                    )


                    quantity = int(
                        quantities[index]
                    )


                    # Validate quantity

                    if quantity < 1:

                        raise ValueError(
                            'Quantity must be at least 1.'
                        )


                    price = Decimal(
                        prices[index]
                    )


                    gst_rate = Decimal(
                        gst_rates[index] or '0'
                    )


                    discount = Decimal(
                        discounts[index] or '0'
                    )


                    # Validation

                    if price < 0:

                        raise ValueError(
                            'Product price cannot be negative.'
                        )


                    if gst_rate < 0:

                        raise ValueError(
                            'GST rate cannot be negative.'
                        )


                    if discount < 0 or discount > 100:

                        raise ValueError(
                            'Discount must be between 0 and 100.'
                        )


                    # Create InvoiceItem
                    # Its save() method automatically calculates total

                    invoice_item = InvoiceItem.objects.create(

                        invoice=invoice,

                        product=product,

                        quantity=quantity,

                        price=price,

                        gst_rate=gst_rate,

                        discount=discount

                    )


                    grand_total += invoice_item.total


                # Update final invoice amount

                invoice.total_amount = grand_total

                invoice.save()


            messages.success(
                request,
                f'Invoice {invoice.invoice_number} '
                f'created successfully.'
            )


            return redirect('invoice_list')


        except (ValueError, IndexError) as error:

            messages.error(
                request,
                str(error)
            )

            return redirect('create_invoice')


        except Exception:

            messages.error(
                request,
                'Unable to create invoice. Please try again.'
            )

            return redirect('create_invoice')


    context = {
        'customers': customers,
        'products': products
    }

    return render(
        request,
        'accounts/create_invoice.html',
        context
    )
    
    

@login_required
def invoice_list(request):
    invoices = (
        Invoice.objects
        .select_related('customer', 'distributor')
        .prefetch_related('items__product')
    )

    # Admins can see all invoices.
    # Distributors can see only their own invoices.
    if not request.user.is_staff:
        invoices = invoices.filter(distributor=request.user)

    invoices = invoices.order_by('-created_at')

    total_billing = invoices.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    latest_invoice = invoices.first()

    paginator = Paginator(invoices, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'total_billing': total_billing,
        'latest_invoice': latest_invoice,
    }

    return render(
        request,
        'accounts/invoice_list.html',
        context
    )

    
    
@login_required
def invoice_detail(request, invoice_id):
    invoices = (
        Invoice.objects
        .select_related('customer', 'distributor')
        .prefetch_related('items__product')
    )

    # Admins can view every invoice.
    # Distributors can view only their own invoices.
    if request.user.is_staff:
        invoice = get_object_or_404(
            invoices,
            id=invoice_id
        )
    else:
        invoice = get_object_or_404(
            invoices,
            id=invoice_id,
            distributor=request.user
        )

    qr_code = generate_invoice_qr(invoice)

    context = {
        'invoice': invoice,
        'qr_code': qr_code,
    }

    return render(
        request,
        'accounts/invoice_detail.html',
        context
    )
    

@login_required
def invoice_qr_preview(request, invoice_id):
    invoices = (
        Invoice.objects
        .select_related('customer', 'distributor')
        .prefetch_related('items__product')
    )

    if request.user.is_staff:
        invoice = get_object_or_404(invoices, id=invoice_id)
    else:
        invoice = get_object_or_404(
            invoices,
            id=invoice_id,
            distributor=request.user
        )

    qr_code = generate_invoice_qr(invoice)

    return render(
        request,
        'accounts/invoice_qr_preview.html',
        {
            'invoice': invoice,
            'qr_code': qr_code,
        }
    )

    
@login_required
def print_invoice(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'customer'
        ).prefetch_related(
            'items__product'
        ),
        id=invoice_id
    )

    qr_code = generate_invoice_qr(invoice)

    context = {
        'invoice': invoice,
        'qr_code': qr_code,
    }

    return render(
        request,
        'accounts/print_invoice.html',
        context
    )
    

# @login_required
# def download_invoice_pdf(request, invoice_id):
#     invoices = (
#         Invoice.objects
#         .select_related('customer', 'distributor')
#         .prefetch_related('items__product')
#     )

#     # Admins can download every invoice.
#     # Distributors can download only their own invoicess.
#     if request.user.is_staff:
#         invoice = get_object_or_404(
#             invoices,
#             id=invoice_id
#         )
#     else:
#         invoice = get_object_or_404(
#             invoices,
#             id=invoice_id,
#             distributor=request.user
#         )

#     response = HttpResponse(content_type='application/pdf')

#     response['Content-Disposition'] = (
#         f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
#     )

#     pdf = canvas.Canvas(response, pagesize=A4)
#     width, height = A4

#     # Invoice Header
#     pdf.setFont('Helvetica-Bold', 18)
#     pdf.drawString(50, height - 50, 'INVOICE')

#     pdf.setFont('Helvetica', 10)
#     pdf.drawString(
#         50, height - 75,
#         f'Invoice No: {invoice.invoice_number}'
#     )
#     pdf.drawString(
#         50, height - 90,
#         f'Date: {invoice.created_at.strftime("%d-%m-%Y")}'
#     )

#     # Customer Details
#     y = height - 130
#     pdf.setFont('Helvetica-Bold', 12)
#     pdf.drawString(50, y, 'Customer Details')

#     y -= 20
#     pdf.setFont('Helvetica', 10)

#     for label, value in [
#         ('Name', invoice.customer.name),
#         ('Email', invoice.customer.email),
#         ('Phone', invoice.customer.phone),
#         ('Address', invoice.customer.address),
#     ]:
#         pdf.drawString(50, y, f'{label}: {value}')
#         y -= 15

#     # Product Table
#     y -= 25
#     pdf.setFont('Helvetica-Bold', 10)

#     pdf.drawString(50, y, 'Product')
#     pdf.drawString(250, y, 'Qty')
#     pdf.drawString(300, y, 'Price')
#     pdf.drawString(380, y, 'GST')
#     pdf.drawString(440, y, 'Discount')
#     pdf.drawString(510, y, 'Total')

#     y -= 15
#     pdf.line(50, y, 550, y)
#     y -= 20

#     pdf.setFont('Helvetica', 9)

#     for item in invoice.items.all():
#         # Start a new page before writing beyond the page.
#         if y < 80:
#             pdf.showPage()
#             y = height - 50
#             pdf.setFont('Helvetica-Bold', 10)
#             pdf.drawString(50, y, 'Product')
#             pdf.drawString(250, y, 'Qty')
#             pdf.drawString(300, y, 'Price')
#             pdf.drawString(380, y, 'GST')
#             pdf.drawString(440, y, 'Discount')
#             pdf.drawString(510, y, 'Total')
#             y -= 25
#             pdf.setFont('Helvetica', 9)

#         pdf.drawString(50, y, str(item.product.name)[:30])
#         pdf.drawString(250, y, str(item.quantity))
#         pdf.drawString(300, y, f'{item.price:.2f}')
#         pdf.drawString(380, y, f'{item.gst_rate:.2f}%')
#         pdf.drawString(440, y, f'{item.discount:.2f}%')
#         pdf.drawString(510, y, f'{item.total:.2f}')

#         y -= 20

#     # Grand Total
#     if y < 100:
#         pdf.showPage()
#         y = height - 60

#     y -= 5
#     pdf.line(400, y, 550, y)
#     y -= 25

#     pdf.setFont('Helvetica-Bold', 12)
#     pdf.drawString(400, y, 'Grand Total:')
#     pdf.drawRightString(550, y, f'{invoice.total_amount:.2f}')

#     pdf.save()
#     return response


@login_required
def download_invoice_pdf(request, invoice_id):
    invoices = (
        Invoice.objects
        .select_related('customer', 'distributor')
        .prefetch_related('items__product')
    )

    if request.user.is_staff:
        invoice = get_object_or_404(
            invoices,
            id=invoice_id
        )
    else:
        invoice = get_object_or_404(
            invoices,
            id=invoice_id,
            distributor=request.user
        )

    qr_code = generate_invoice_qr(invoice)

    template = get_template('accounts/invoice_pdf.html')
    html = template.render({
        'invoice': invoice,
        'qr_code': qr_code,
    }, request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    )

    result = pisa.CreatePDF(
        html,
        dest=response,
        encoding='utf-8',
    )

    if result.err:
        return HttpResponse(
            'Unable to generate the invoice PDF. '
            'Please check the PDF template and server logs.',
            status=500,
        )

    return response



@csrf_exempt
def admin_register_api(request):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Only POST requests are allowed.'
        }, status=405)

    try:
        data = json.loads(request.body)

        name = data.get('name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Name validation
        if not name:
            return JsonResponse({
                'success': False,
                'message': 'Full name is required.'
            }, status=400)

        if len(name) < 3:
            return JsonResponse({
                'success': False,
                'message': 'Name must contain at least 3 characters.'
            }, status=400)

        if not re.match(r'^[A-Za-z ]+$', name):
            return JsonResponse({
                'success': False,
                'message': 'Name can contain only letters and spaces.'
            }, status=400)

        # Username validation
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Username is required.'
            }, status=400)

        if len(username) < 4:
            return JsonResponse({
                'success': False,
                'message': 'Username must contain at least 4 characters.'
            }, status=400)

        if not re.match(r'^[A-Za-z0-9_]+$', username):
            return JsonResponse({
                'success': False,
                'message': 'Username can contain only letters, numbers, and underscores.'
            }, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({
                'success': False,
                'message': 'This username is already taken.'
            }, status=400)

        # Email validation
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Email address is required.'
            }, status=400)

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(email_pattern, email):
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            }, status=400)

        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'This email is already registered.'
            }, status=400)

        # Password validation
        if not password:
            return JsonResponse({
                'success': False,
                'message': 'Password is required.'
            }, status=400)

        if len(password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must contain at least 8 characters.'
            }, status=400)

        if not re.search(r'[A-Za-z]', password):
            return JsonResponse({
                'success': False,
                'message': 'Password must contain at least one letter.'
            }, status=400)

        if not re.search(r'\d', password):
            return JsonResponse({
                'success': False,
                'message': 'Password must contain at least one number.'
            }, status=400)

        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Passwords do not match.'
            }, status=400)

        # Create admin user
        user = User.objects.create_user(
            username=username,
            first_name=name,
            email=email,
            password=password,
            is_staff=True
        )

        return JsonResponse({
            'success': True,
            'message': 'Admin user registered successfully.',
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.first_name,
                'email': user.email
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data.'
        }, status=400)

    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'Unable to register admin user.'
        }, status=500)

        
def admin_register(request):
    return render(
        request,
        'accounts/admin_register.html'
    )
    
#admin forgot password view
def admin_forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email.')
            return redirect('admin_forgot_password')

        user = User.objects.filter(
            email__iexact=email,
            is_staff=True
        ).first()

        # Use a generic message to avoid revealing
        # whether an admin email exists.
        if user:
            otp = str(random.randint(100000, 999999))

            OTPVerification.objects.filter(
                email__iexact=email
            ).delete()

            OTPVerification.objects.create(
                email=email,
                otp_code=otp,
                expires_at=timezone.now() + timedelta(minutes=5),
                is_verified=False
            )

            request.session['admin_reset_email'] = email
            request.session['admin_otp_verified'] = False

            try:
                send_mail(
                    subject='Admin Password Reset OTP',
                    message=(
                        f'Your OTP is {otp}. '
                        'It expires in 5 minutes.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                OTPVerification.objects.filter(
                    email__iexact=email
                ).delete()

                request.session.pop('admin_reset_email', None)
                messages.error(
                    request,
                    'Unable to send the OTP. Please try again.'
                )
                return redirect('admin_forgot_password')

        messages.success(
            request,
            'If the email belongs to an admin account, '
            'a password reset OTP has been sent.'
        )
        return redirect('admin_verify_otp')

    return render(request, 'accounts/admin_forgot_password.html')

#admin verify otp view
def admin_verify_otp(request):
    email = request.session.get('admin_reset_email')

    if not email:
        messages.error(request, 'Please request a new OTP.')
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()

        verification = OTPVerification.objects.filter(
            email__iexact=email,
            is_verified=False
        ).order_by('-id').first()

        if not verification or verification.otp_code != otp:
            messages.error(request, 'Invalid OTP.')
            return redirect('admin_verify_otp')

        if verification.is_expired():
            messages.error(
                request,
                'OTP expired. Please request a new one.'
            )
            return redirect('admin_forgot_password')

        # Confirm this is still an Admin account.
        if not User.objects.filter(
            email__iexact=email,
            is_staff=True
        ).exists():
            messages.error(request, 'Admin account not found.')
            return redirect('admin_forgot_password')

        verification.is_verified = True
        verification.save(update_fields=['is_verified'])

        request.session['admin_otp_verified'] = True

        return redirect('admin_reset_password')

    return render(request, 'accounts/admin_verify_otp.html')

#admin reset password view
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def admin_reset_password(request):
    email = request.session.get('admin_reset_email')
    verified = request.session.get('admin_otp_verified', False)

    if not email or not verified:
        messages.error(request, 'Please verify your OTP first.')
        return redirect('admin_forgot_password')

    user = User.objects.filter(
        email__iexact=email,
        is_staff=True
    ).first()

    if not user:
        request.session.pop('admin_reset_email', None)
        request.session.pop('admin_otp_verified', None)
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_reset_password')

        try:
            validate_password(password, user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect('admin_reset_password')

        user.set_password(password)
        user.save()

        # Consume the verified OTP.
        OTPVerification.objects.filter(
            email__iexact=email,
            is_verified=True
        ).delete()

        request.session.pop('admin_reset_email', None)
        request.session.pop('admin_otp_verified', None)

        messages.success(
            request,
            'Password reset successfully. Please log in.'
        )
        return redirect('admin_login')

    return render(request, 'accounts/admin_reset_password.html')


@login_required(login_url='distributor_login')
@require_POST
def customer_register_api(request):
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    phone = request.POST.get('phone', '').strip()

    street_address = request.POST.get('street_address', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    pincode = request.POST.get('pincode', '').strip()
    country = request.POST.get('country', 'India').strip() or 'India'

    if not all([name, email, phone, street_address, city, state, pincode]):
        return JsonResponse({
            'success': False,
            'message': 'Please fill in all required fields.'
        }, status=400)

    if len(name) > 100 or len(email) > 254 or len(phone) > 15:
        return JsonResponse({
            'success': False,
            'message': 'Name, email, or phone exceeds the allowed length.'
        }, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid email address.'
        }, status=400)

    address = (
        f"{street_address}, {city}, {state}, "
        f"{pincode}, {country}"
    )

    customer = Customer.objects.create(
        distributor=request.user,
        name=name,
        email=email,
        phone=phone,
        address=address
    )

    return JsonResponse({
        'success': True,
        'message': 'Customer registered successfully.',
        'customer_id': customer.id
    }, status=201)
    
    
def validate_product_data(request):
    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', '').strip()
    raw_price = request.POST.get('price', '').strip()
    raw_stock = request.POST.get('stock', '').strip()
    raw_gst = request.POST.get('gst_rate', '').strip()

    if not name:
        messages.error(request, 'Product name is required.')
        return None

    if not category:
        messages.error(request, 'Category is required.')
        return None

    try:
        price = Decimal(raw_price)

        if not price.is_finite() or price <= 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError):
        messages.error(
            request,
            'Enter a valid price greater than 0.'
        )
        return None

    try:
        stock = int(raw_stock)

        if stock < 0:
            messages.error(request, 'Stock cannot be negative.')
            return None

    except (ValueError, TypeError):
        messages.error(
            request,
            'Enter a valid whole-number stock quantity.'
        )
        return None

    try:
        gst_rate = Decimal(raw_gst)

        if (
            not gst_rate.is_finite()
            or gst_rate < 0
            or gst_rate > 100
        ):
            raise InvalidOperation

    except (InvalidOperation, ValueError):
        messages.error(
            request,
            'GST rate must be a valid number between 0 and 100.'
        )
        return None

    return {
        'name': name,
        'category': category,
        'price': price,
        'stock': stock,
        'gst_rate': gst_rate,
    }
    

@login_required(login_url='admin_login')
def admin_reports(request):
    if not request.user.is_staff:
        messages.error(request, 'Admin access required.')
        return redirect('distributor_login')

    today = timezone.localdate()
    default_start = today - timedelta(days=29)

    # Defaults for the initial page load
    start_date = default_start.isoformat()
    end_date = today.isoformat()

    # Track whether the user actually submitted date filters
    has_date_filter = (
        'start_date' in request.GET
        or 'end_date' in request.GET
    )

    if has_date_filter:
        start_date = request.GET.get('start_date', '').strip()
        end_date = request.GET.get('end_date', '').strip()

        try:
            if not start_date or not end_date:
                raise ValueError(
                    'Both start date and end date are required.'
                )

            start = timezone.datetime.strptime(
                start_date, '%Y-%m-%d'
            ).date()

            end = timezone.datetime.strptime(
                end_date, '%Y-%m-%d'
            ).date()

            # Reject impossible dates and reversed ranges
            if start.isoformat() != start_date:
                raise ValueError('Invalid start date.')

            if end.isoformat() != end_date:
                raise ValueError('Invalid end date.')

            if start > end:
                raise ValueError(
                    'Start date cannot be after end date.'
                )

        except (ValueError, TypeError):
            messages.error(
                request,
                'Select both valid dates. The start date must '
                'be on or before the end date.'
            )
            start = default_start
            end = today
            start_date = start.isoformat()
            end_date = end.isoformat()
    else:
        start = default_start
        end = today

    # Filter invoices using the validated date range
    invoices = (
        Invoice.objects.filter(
            created_at__date__range=(start, end)
        )
        .select_related('customer', 'distributor')
        .order_by('-created_at')
    )

    sales_summary = invoices.aggregate(
        total_sales=Sum('total_amount'),
        invoice_count=Count('id'),
    )

    daily_sales = (
        invoices.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(
            sales=Sum('total_amount'),
            invoice_count=Count('id'),
        )
        .order_by('day')
    )

    distributor_sales = (
        invoices.values(
            'distributor__username',
            'distributor__first_name',
        )
        .annotate(
            total_sales=Sum('total_amount'),
            invoice_count=Count('id'),
        )
        .order_by('-total_sales')
    )

    products = Product.objects.select_related(
        'distributor'
    ).order_by('name')

    low_stock_products = products.filter(stock__lte=5)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'invoices': invoices,
        'total_sales': (
            sales_summary['total_sales'] or Decimal('0.00')
        ),
        'invoice_count': sales_summary['invoice_count'] or 0,
        'daily_sales': daily_sales,
        'distributor_sales': distributor_sales,
        'total_products': products.count(),
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
    }

    return render(
        request,
        'accounts/admin_reports.html',
        context
    )


@login_required(login_url='admin_login')
def admin_reports_pdf(request):
    if not request.user.is_staff:
        messages.error(request, 'Admin access required.')
        return redirect('distributor_login')

    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    try:
        if not start_date or not end_date:
            raise ValueError

        start = timezone.datetime.strptime(
            start_date, '%Y-%m-%d'
        ).date()

        end = timezone.datetime.strptime(
            end_date, '%Y-%m-%d'
        ).date()

        if (
            start.isoformat() != start_date
            or end.isoformat() != end_date
            or start > end
        ):
            raise ValueError

    except (ValueError, TypeError):
        messages.error(
            request,
            'Please select a valid date range before downloading.'
        )
        return redirect('admin_reports')

    invoices = (
        Invoice.objects.filter(
            created_at__date__range=(start, end)
        )
        .select_related('customer', 'distributor')
        .order_by('-created_at')
    )

    summary = invoices.aggregate(
        total_sales=Sum('total_amount'),
        invoice_count=Count('id'),
    )

    context = {
        'start_date': start,
        'end_date': end,
        'invoices': invoices,
        'total_sales': (
            summary['total_sales'] or Decimal('0.00')
        ),
        'invoice_count': summary['invoice_count'] or 0,
    }

    template = get_template('accounts/admin_reports_pdf.html')
    html = template.render(context, request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="invoice_report.pdf"'
    )

    result = pisa.CreatePDF(
        html,
        dest=response,
        encoding='utf-8',
    )

    if result.err:
        return HttpResponse(
            'Unable to generate the PDF report.',
            status=500,
        )

    return response




# VIEW ALL DISTRIBUTORS
@login_required(login_url='admin_login')
def view_distributors(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('distributor_login')

    search = request.GET.get('q', '').strip()

    distributors = DistributorProfile.objects.select_related('user')

    if search:
        distributors = distributors.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search)
        )

    distributors = distributors.order_by('-created_at')

    paginator = Paginator(distributors, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/view_distributors.html', {
        'page_obj': page_obj,
        'search': search,
    })


# VIEW ALL CUSTOMERS
@login_required(login_url='admin_login')
def view_customers(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('distributor_login')

    search = request.GET.get('q', '').strip()

    customers = Customer.objects.all()

    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(address__icontains=search)
        )

    customers = customers.order_by('-id')

    paginator = Paginator(customers, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/view_customers.html', {
        'page_obj': page_obj,
        'search': search,
    })


# VIEW ALL PRODUCTS
@login_required(login_url='admin_login')
def view_products(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('distributor_login')

    search = request.GET.get('q', '').strip()

    products = Product.objects.select_related('distributor')

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(category__icontains=search) |
            Q(distributor__username__icontains=search) |
            Q(distributor__first_name__icontains=search)
        )

    products = products.order_by('-created_at')

    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/view_products.html', {
        'page_obj': page_obj,
        'search': search,
    })
    



@login_required(login_url='admin_login')
def qr_decoder(request):
    decoded_data = None
    invoice = None
    error = None

    if request.method == 'POST':
        uploaded_file = request.FILES.get('qr_image')

        if not uploaded_file or uploaded_file.size == 0:
            error = 'Please select a QR code image.'

        elif uploaded_file.size > 5 * 1024 * 1024:
            error = 'Image size must be 5 MB or less.'

        else:
            try:
                image_bytes = uploaded_file.read()
                image_array = np.frombuffer(
                    image_bytes,
                    dtype=np.uint8
                )
                image = cv2.imdecode(
                    image_array,
                    cv2.IMREAD_COLOR
                )

                if image is None:
                    error = 'The uploaded file is not a valid image.'
                else:
                    detector = cv2.QRCodeDetector()
                    decoded_data, points, _ = (
                        detector.detectAndDecode(image)
                    )

                    if not decoded_data or not decoded_data.strip():
                        decoded_data = None
                        error = (
                            'No readable QR code was found. '
                            'Try a clearer image.'
                        )
                    else:
                        invoice_number = decoded_data.strip()

                        try:
                            qr_payload = json.loads(decoded_data)
                            if isinstance(qr_payload, dict):
                                invoice_number = str(
                                    qr_payload.get(
                                        'invoice_number', ''
                                    )
                                ).strip()
                        except (json.JSONDecodeError, TypeError):
                            pass

                        if not invoice_number:
                            error = (
                                'The QR code does not contain '
                                'an invoice number.'
                            )
                        else:
                            invoices = (
                                Invoice.objects
                                .select_related(
                                    'customer', 'distributor'
                                )
                                .prefetch_related('items__product')
                            )

                            # Staff admins can find any invoice.
                            # Other users can find only their own.
                            if not request.user.is_staff:
                                invoices = invoices.filter(
                                    distributor=request.user
                                )

                            invoice = invoices.filter(
                                invoice_number=invoice_number
                            ).first()

                            if invoice is None:
                                error = (
                                    'No accessible invoice was found '
                                    'for the decoded QR data.'
                                )

            except (cv2.error, ValueError, TypeError):
                decoded_data = None
                invoice = None
                error = (
                    'Unable to read this image. '
                    'Please try another.'
                )

        if error:
            messages.error(request, error)
        elif invoice:
            messages.success(
                request,
                f'QR code decoded successfully. '
                f'Invoice {invoice.invoice_number} found.'
            )

    return render(
        request,
        'accounts/qr_decoder.html',
        {
            'decoded_data': decoded_data,
            'invoice': invoice,
            'error': error,
        }
    )




@login_required(login_url='admin_login')
def admin_invoice_list(request):
    if not request.user.is_staff:
        messages.error(request, 'Admin access required.')
        return redirect('distributor_login')

    search = request.GET.get('q', '').strip()

    invoices = (
        Invoice.objects
        .select_related('customer', 'distributor')
        .order_by('-created_at')
    )

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(distributor__username__icontains=search)
            | Q(distributor__first_name__icontains=search)
            | Q(distributor__last_name__icontains=search)
        )

    paginator = Paginator(invoices, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'accounts/admin_invoice_list.html',
        {
            'page_obj': page_obj,
            'search': search,
        }
    )



@login_required
def admin_invoice_detail(request, invoice_id):
    # Only staff/admin users can access this page.
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect('distributor_login')

    invoice = get_object_or_404(
        Invoice.objects
        .select_related('customer', 'distributor')
        .prefetch_related('items__product'),
        id=invoice_id
    )

    qr_code = generate_invoice_qr(invoice)

    context = {
        'invoice': invoice,
        'qr_code': qr_code,
    }

    return render(
        request,
        'accounts/admin_invoice_detail.html',
        context
    )

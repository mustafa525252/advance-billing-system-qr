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

# Create your views here.


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        logout(request)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')

            messages.error(
                request,
                'This account does not have Admin access.'
            )
        else:
            messages.error(
                request,
                'Invalid username or password.'
            )

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


def add_product(request):

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', '').strip()
        price = request.POST.get('price', '').strip()
        stock = request.POST.get('stock', '').strip()
        gst_rate = request.POST.get('gst_rate', '').strip()


        # PRODUCT NAME VALIDATION

        if not name:
            messages.error(
                request,
                'Product name is required.'
            )

            return render(
                request,
                'accounts/add_product.html'
            )


        # CATEGORY VALIDATION

        if not category:
            messages.error(
                request,
                'Category is required.'
            )

            return render(
                request,
                'accounts/add_product.html'
            )


        # PRICE VALIDATION

        try:

            price = Decimal(price)

            if price <= 0:

                messages.error(
                    request,
                    'Price must be greater than 0.'
                )

                return render(
                    request,
                    'accounts/add_product.html'
                )

        except InvalidOperation:

            messages.error(
                request,
                'Please enter a valid price.'
            )

            return render(
                request,
                'accounts/add_product.html'
            )


        # STOCK VALIDATION

        try:

            stock = int(stock)

            if stock < 0:

                messages.error(
                    request,
                    'Stock cannot be negative.'
                )

                return render(
                    request,
                    'accounts/add_product.html'
                )

        except ValueError:

            messages.error(
                request,
                'Please enter a valid stock quantity.'
            )

            return render(
                request,
                'accounts/add_product.html'
            )


        # GST VALIDATION

        try:

            gst_rate = Decimal(gst_rate)

            if gst_rate < 0:

                messages.error(
                    request,
                    'GST rate cannot be negative.'
                )

                return render(
                    request,
                    'accounts/add_product.html'
                )

        except InvalidOperation:

            messages.error(
                request,
                'Please enter a valid GST rate.'
            )

            return render(
                request,
                'accounts/add_product.html'
            )


        # CREATE PRODUCT

        Product.objects.create(
            distributor=request.user,
            name=name,
            category=category,
            price=price,
            stock=stock,
            gst_rate=gst_rate
        )


        messages.success(
            request,
            'Product added successfully.'
        )

        return redirect('product_list')


    return render(
        request,
        'accounts/add_product.html'
    )
    
    
def product_list(request):

    search_query = request.GET.get('search', '')

    products = Product.objects.filter(distributor=request.user).order_by('-created_at')

    if search_query:

        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    paginator = Paginator(products, 5)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(
        request,
        'accounts/product_list.html',
        context
    )
    
    
@login_required
def edit_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        distributor=request.user
    )

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        category = request.POST.get(
            'category',
            ''
        ).strip()

        price = request.POST.get(
            'price',
            ''
        ).strip()

        stock = request.POST.get(
            'stock',
            ''
        ).strip()

        gst_rate = request.POST.get(
            'gst_rate',
            ''
        ).strip()


        # VALIDATION

        if not name:

            messages.error(
                request,
                'Product name is required.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        if not category:

            messages.error(
                request,
                'Category is required.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        try:

            price = float(price)

            stock = int(stock)

            gst_rate = float(gst_rate)

        except ValueError:

            messages.error(
                request,
                'Please enter valid product values.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        if price <= 0:

            messages.error(
                request,
                'Price must be greater than 0.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        if stock < 0:

            messages.error(
                request,
                'Stock cannot be negative.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        if gst_rate < 0:

            messages.error(
                request,
                'GST rate cannot be negative.'
            )

            return redirect(
                'edit_product',
                product_id=product.id
            )


        # UPDATE PRODUCT

        product.name = name
        product.category = category
        product.price = price
        product.stock = stock
        product.gst_rate = gst_rate

        product.save()


        messages.success(
            request,
            'Product updated successfully.'
        )

        return redirect('product_list')


    context = {
        'product': product
    }

    return render(
        request,
        'accounts/edit_product.html',
        context
    )
    
    
@login_required
def delete_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        distributor=request.user
    )

    if request.method == 'POST':

        product.delete()

        messages.success(
            request,
            'Product deleted successfully.'
        )

        return redirect('product_list')

    context = {
        'product': product
    }

    return render(
        request,
        'accounts/delete_product.html',
        context
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
    .filter(distributor=request.user)
    .select_related('customer')
    .prefetch_related('items__product')
    .order_by('-created_at')
)

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

    invoice = get_object_or_404(
        Invoice.objects
        .select_related('customer')
        .prefetch_related('items__product'),
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
    
@login_required
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects
        .select_related('customer')
        .prefetch_related('items__product'),
        id=invoice_id,
        distributor=request.user
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4

    # -------------------------
    # Invoice Header
    # -------------------------
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(
        50,
        height - 50,
        'INVOICE'
    )

    pdf.setFont('Helvetica', 10)

    pdf.drawString(
        50,
        height - 75,
        f'Invoice No: {invoice.invoice_number}'
    )

    pdf.drawString(
        50,
        height - 90,
        f'Date: {invoice.created_at.strftime("%d-%m-%Y")}'
    )

    # -------------------------
    # Customer Details
    # -------------------------
    y = height - 130

    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(
        50,
        y,
        'Customer Details'
    )

    y -= 20

    pdf.setFont('Helvetica', 10)

    pdf.drawString(
        50,
        y,
        f'Name: {invoice.customer.name}'
    )

    y -= 15

    pdf.drawString(
        50,
        y,
        f'Email: {invoice.customer.email}'
    )

    y -= 15

    pdf.drawString(
        50,
        y,
        f'Phone: {invoice.customer.phone}'
    )

    y -= 15

    pdf.drawString(
        50,
        y,
        f'Address: {invoice.customer.address}'
    )

    # -------------------------
    # Product Table Header
    # -------------------------
    y -= 40

    pdf.setFont('Helvetica-Bold', 10)

    pdf.drawString(50, y, 'Product')
    pdf.drawString(250, y, 'Qty')
    pdf.drawString(300, y, 'Price')
    pdf.drawString(380, y, 'GST')
    pdf.drawString(440, y, 'Discount')
    pdf.drawString(510, y, 'Total')

    y -= 15

    pdf.line(
        50,
        y,
        550,
        y
    )

    y -= 20

    # -------------------------
    # Invoice Items
    # -------------------------
    pdf.setFont('Helvetica', 9)

    for item in invoice.items.all():

        pdf.drawString(
            50,
            y,
            str(item.product.name)[:30]
        )

        pdf.drawString(
            250,
            y,
            str(item.quantity)
        )

        pdf.drawString(
            300,
            y,
            f'{item.price:.2f}'
        )

        pdf.drawString(
            380,
            y,
            f'{item.gst_rate:.2f}%'
        )

        pdf.drawString(
            440,
            y,
            f'{item.discount:.2f}%'
        )

        pdf.drawString(
            510,
            y,
            f'{item.total:.2f}'
        )

        y -= 20

        # Start a new page if necessary
        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 9)

    # -------------------------
    # Grand Total
    # -------------------------
    y -= 15

    pdf.line(
        400,
        y,
        550,
        y
    )

    y -= 25

    pdf.setFont(
        'Helvetica-Bold',
        12
    )

    pdf.drawString(
        400,
        y,
        'Grand Total:'
    )

    pdf.drawString(
        510,
        y,
        f'{invoice.total_amount:.2f}'
    )

    # -------------------------
    # Finish PDF
    # -------------------------
    pdf.showPage()
    pdf.save()

    return response


@csrf_exempt
def admin_register_api(request):

    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'message': 'Only POST requests are allowed.'
            },
            status=405
        )

    try:
        data = json.loads(request.body)

        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # -------------------------
        # Name validation
        # -------------------------
        if not name:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Full name is required.'
                },
                status=400
            )

        if len(name) < 3:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Name must contain at least 3 characters.'
                },
                status=400
            )

        if not re.match(r'^[A-Za-z ]+$', name):
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Name can contain only letters and spaces.'
                },
                status=400
            )

        # -------------------------
        # Email validation
        # -------------------------
        if not email:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Email address is required.'
                },
                status=400
            )

        email_pattern = (
            r'^[A-Za-z0-9._%+-]+@'
            r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        )

        if not re.match(email_pattern, email):
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Please enter a valid email address.'
                },
                status=400
            )

        # -------------------------
        # Password validation
        # -------------------------
        if not password:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Password is required.'
                },
                status=400
            )

        if len(password) < 8:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Password must contain at least 8 characters.'
                },
                status=400
            )

        if not re.search(r'[A-Za-z]', password):
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Password must contain at least one letter.'
                },
                status=400
            )

        if not re.search(r'\d', password):
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Password must contain at least one number.'
                },
                status=400
            )

        # -------------------------
        # Confirm password
        # -------------------------
        if password != confirm_password:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Passwords do not match.'
                },
                status=400
            )

        # -------------------------
        # Duplicate email
        # -------------------------
        if User.objects.filter(
            email__iexact=email
        ).exists():
            return JsonResponse(
                {
                    'success': False,
                    'message': 'This email is already registered.'
                },
                status=400
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
            username = f'{original_username}{counter}'
            counter += 1

        # -------------------------
        # Create Admin User
        # -------------------------
        user = User.objects.create_user(
            username=username,
            first_name=name,
            email=email,
            password=password,
            is_staff=True
        )

        return JsonResponse(
            {
                'success': True,
                'message': 'Admin user registered successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'name': user.first_name,
                    'email': user.email
                }
            },
            status=201
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid JSON data.'
            },
            status=400
        )

    except Exception as error:
        return JsonResponse(
            {
                'success': False,
                'message': 'Unable to register admin user.'
            },
            status=500
        )
        
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
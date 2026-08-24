from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
import random
from datetime import timedelta
from django.utils import timezone
from .models import OTPVerification, DistributorProfile
from .models import Customer
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.views.decorators.http import require_POST

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
        messages.error(request, 'Admin access required.')
        return redirect('distributor_login')

    return render(request, 'accounts/admin_dashboard.html')


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

from .models import DistributorProfile


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

        email = request.POST.get(
            'email',
            ''
        ).strip().lower()

        if not email:
            messages.error(
                request,
                'Please enter your email address.'
            )

            return render(
                request,
                'accounts/forgot_password.html'
            )

        try:
            user = User.objects.get(
                email__iexact=email
            )
        except User.DoesNotExist:

            messages.error(
                request,
                'No account found with this email address.'
            )

            return render(
                request,
                'accounts/forgot_password.html'
            )

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
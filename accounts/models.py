from django.db import models
from django.contrib.auth.models import User


class DistributorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='distributor_profile'
    )

    phone = models.CharField(
        max_length=20,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.first_name


class OTPVerification(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.otp_code}"
    
class Customer(models.Model):

    distributor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customers'
    )

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        max_length=254
    )

    phone = models.CharField(
        max_length=15
    )

    address = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name
from django.contrib import admin
from .models import Product, DistributorProfile
from .models import Invoice, InvoiceItem

# Register your models here.


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'name',
        'category',
        'price',
        'stock',
        'gst_rate',
        'created_at',
    )

    search_fields = (
        'name',
        'category',
    )

    list_filter = (
        'category',
    )
    
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
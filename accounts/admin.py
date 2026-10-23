
from django.contrib import admin
from .models import (
    Product,
    DistributorProfile,
    Customer,
    Invoice,
    InvoiceItem,
)


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

    search_fields = ('name', 'category')
    list_filter = ('category',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone')
    search_fields = ('name', 'email', 'phone')


admin.site.register(Invoice)
admin.site.register(InvoiceItem)

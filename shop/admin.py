from django.contrib import admin
from .models import Customer, Invoice, Product, Category


admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Invoice)

class InvoiceAdmin:
   list_display = ('UNPAID', 'PAID', 'PROCESSING', 'CONFIRMED', 'REJECTED', 'CANCELED', 'DONE')
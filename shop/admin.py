from django.contrib import admin
from .models import (
   Address,
   Cart,
   CartItem,
   Category,
   Customer,
   InventoryReservation,
   Invoice,
   InvoiceItem,
   LegacyInvoice,
   Order,
   OrderItem,
   OrderStatusHistory,
   PaymentAttempt,
   Product,
   ProductImage,
   Refund,
   StockMovement,
)


class InvoiceAdmin(admin.ModelAdmin):
   list_display = ('invoice_number', 'order', 'status', 'document_type', 'total_amount', 'created_at')


admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(LegacyInvoice)
admin.site.register(Address)
admin.site.register(ProductImage)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceItem)
admin.site.register(PaymentAttempt)
admin.site.register(Refund)
admin.site.register(StockMovement)
admin.site.register(InventoryReservation)
admin.site.register(OrderStatusHistory)

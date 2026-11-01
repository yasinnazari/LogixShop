from django.contrib import admin
from .models import (
   Address,
   Cart,
   CartItem,
   Category,
   EmailVerificationChallenge,
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


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
   list_display = ('product_title', 'image', 'is_primary', 'sort_order', 'created_at')
   list_filter = ('is_primary', 'created_at')
   search_fields = ('product__title', 'product__id', 'alt_text')
   list_select_related = ('product',)

   @admin.display(ordering='product__title', description='Product title')
   def product_title(self, obj):
      return obj.product.title


@admin.register(EmailVerificationChallenge)
class EmailVerificationChallengeAdmin(admin.ModelAdmin):
   list_display = ('id', 'user', 'purpose', 'target_email', 'expires_at', 'attempts', 'max_attempts', 'consumed_at', 'sent_at')
   list_filter = ('purpose', 'consumed_at')
   search_fields = ('user__username', 'user__email', 'target_email')
   readonly_fields = ('user', 'purpose', 'target_email', 'expires_at', 'attempts', 'max_attempts', 'sent_at', 'consumed_at', 'created_at')
   exclude = ('code_digest',)

   def has_add_permission(self, request):
      return False

   def has_change_permission(self, request, obj=None):
      return False

   def has_delete_permission(self, request, obj=None):
      return False


admin.site.register(Product)
admin.site.register(Category)
admin.site.register(LegacyInvoice)
admin.site.register(Address)
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

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.db import transaction
from django.utils import timezone


def new_public_number(prefix):
   return f"{prefix}-{uuid.uuid4().hex[:20].upper()}"


def new_idempotency_key():
   return uuid.uuid4().hex


def new_order_number():
   return new_public_number('LS')


def new_invoice_number():
   return new_public_number('INV')


class Category(models.Model):
   title = models.CharField(max_length=40, unique=True)
   slug = models.SlugField(max_length=50, unique=True, null=True, blank=True)
   description = models.TextField(null=True, blank=True)
   category_image = models.ImageField(upload_to='upload/category/')
   parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.PROTECT)
   display_order = models.PositiveIntegerField(default=0)
   created_at = models.DateTimeField(default=timezone.now)
   updated_at = models.DateTimeField(default=timezone.now)
   deleted_at = models.DateTimeField(null=True, blank=True)

   class Meta:
      ordering = ('display_order', 'title')
      indexes = [
         models.Index(fields=('deleted_at', 'display_order'), name='category_active_order_idx'),
      ]

   def clean(self):
      super().clean()
      if self.parent_id == self.pk:
         raise ValidationError({'parent': 'category cannot be its own parent'})

      ancestor = self.parent
      visited = set()
      while ancestor is not None:
         if ancestor.pk in visited or ancestor.pk == self.pk:
            raise ValidationError({'parent': 'Category hierarchy cycles are not allowed.'})
         visited.add(ancestor.pk)
         ancestor = ancestor.parent

   def __str__(self):
      return self.title


class Product(models.Model):
   id = models.AutoField(primary_key=True, unique=True)
   title = models.CharField(max_length=80)
   description = models.TextField(max_length=1000, default='', blank=True, null=True)
   slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
   price = models.DecimalField(max_digits=12, decimal_places=0, default=0)
   discounted_price = models.DecimalField(max_digits=12, decimal_places=0, default=None, null=True, blank=True)
   category_title = models.ForeignKey(Category, verbose_name="category_title", on_delete=models.PROTECT)
   is_sale = models.BooleanField(default=False)
   stock = models.IntegerField(default=0)
   has_stock = models.BooleanField(default=False)
   rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
   rating_count = models.PositiveBigIntegerField(default=0)
   status = models.CharField(max_length=20, choices=(
      ('DRAFT', 'Draft'),
      ('PUBLISHED', 'Published'),
      ('ARCHIVED', 'Archived'),
   ), default='DRAFT')
   image = models.ImageField(upload_to='upload/product/')
   created_at = models.DateTimeField(default=timezone.now)
   updated_at = models.DateTimeField(default=timezone.now)
   deleted_at = models.DateTimeField(null=True, blank=True)

   class Meta:
      indexes = [
         models.Index(fields=('status', 'deleted_at'), name='product_publish_idx'),
         models.Index(fields=('category_title', 'status'), name='product_category_status_idx'),
      ]
      constraints = [
         models.CheckConstraint(condition=Q(price__gte=0), name='product_price_nonnegative'),
         models.CheckConstraint(
            condition=Q(discounted_price__isnull=True) | (Q(discounted_price__gt=0) & Q(discounted_price__lt=models.F('price'))),
            name='product_discount_valid',
         ),
         models.CheckConstraint(condition=Q(stock__gte=0), name='product_stock_nonnegative'),
         models.CheckConstraint(condition=Q(rating__gte=0) & Q(rating__lte=5), name='product_rating_range'),
      ]

   def clean(self):
      super().clean()
      if self.discounted_price is not None and not (0 < self.discounted_price < self.price):
         raise ValidationError({'discounted_price': 'Discounted price must be positive and lower than price.'})

   @property
   def effective_price(self):
      return self.discounted_price if self.discounted_price is not None else self.price

   def __str__(self):
      return self.title


class LegacyInvoice(models.Model):
   """The original one-product invoice table, retained without reinterpretation."""

   class InvoiceStatus(models.TextChoices):
      UNPAID = ('UNPAID', 'Awaiting Payment')
      PAID = ('PAID', 'Paid')
      PROCESSING = ('PROCESSING', 'Processing')
      REJECTED = ('REJECTED', 'Rejected')
      CONFIRMED = ('CONFIRMED', 'Confirmed')
      CANCELED = ('CANCELED', 'Canceled')
      DONE = ('DONE', 'Done')


   id = models.AutoField(primary_key=True, unique=True)
   product_id = models.ForeignKey(Product, verbose_name="product_id", on_delete=models.PROTECT)
   customer_id = models.ForeignKey(Customer, verbose_name="customer_id", on_delete=models.PROTECT)
   count = models.SmallIntegerField()
   address = models.CharField(max_length=300, blank=False)
   created_at = models.DateField(auto_now=False, auto_now_add=True)
   status = models.CharField(max_length=30, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

   def __str__(self):
      return f"Legacy invoice {self.id}"


class Address(models.Model):
   user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='addresses', on_delete=models.PROTECT)
   title = models.CharField(max_length=80)
   recipient_name = models.CharField(max_length=120)
   recipient_phone = models.CharField(max_length=32)
   country_code = models.CharField(max_length=8, default='IR')
   province = models.CharField(max_length=100)
   city = models.CharField(max_length=100)
   district = models.CharField(max_length=100, blank=True, default='')
   street_address = models.CharField(max_length=300)
   building_number = models.CharField(max_length=30, blank=True, default='')
   unit = models.CharField(max_length=30, blank=True, default='')
   postal_code = models.CharField(max_length=20)
   latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
   longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
   is_default = models.BooleanField(default=False)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(
            fields=('user',),
            condition=Q(is_default=True),
            name='one_default_address_per_user',
         ),
      ]
      indexes = [models.Index(fields=('user', 'created_at'), name='address_user_created_idx')]

   def clean(self):
      super().clean()
      if self.user_id and Address.objects.filter(user_id=self.user_id).exclude(pk=self.pk).count() >= 3:
         raise ValidationError('A user may have at most three saved addresses.')

   def save(self, *args, **kwargs):
      if self.user_id:
         with transaction.atomic():
            type(self.user).objects.select_for_update().get(pk=self.user_id)
            if Address.objects.filter(user_id=self.user_id).exclude(pk=self.pk).count() >= 3:
               raise ValidationError('A user may have at most three saved addresses.')
            return super().save(*args, **kwargs)
      return super().save(*args, **kwargs)


class ProductImage(models.Model):
   product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
   image = models.ImageField(upload_to='upload/product/gallery/')
   alt_text = models.CharField(max_length=160, null=True, blank=True)
   sort_order = models.PositiveIntegerField(default=0)
   is_primary = models.BooleanField(default=False)
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      ordering = ('sort_order', 'id')
      constraints = [
         models.UniqueConstraint(
            fields=('product',),
            condition=Q(is_primary=True),
            name='one_primary_image_per_product',
         ),
      ]


class Cart(models.Model):
   class Status(models.TextChoices):
      ACTIVE = 'ACTIVE', 'Active'
      CONVERTED = 'CONVERTED', 'Converted'
      ABANDONED = 'ABANDONED', 'Abandoned'

   user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='carts', on_delete=models.PROTECT)
   status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(
            fields=('user',),
            condition=Q(status='ACTIVE'),
            name='one_active_cart_per_user',
         ),
      ]


class CartItem(models.Model):
   cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
   product = models.ForeignKey(Product, related_name='cart_items', on_delete=models.PROTECT)
   quantity = models.PositiveIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(fields=('cart', 'product'), name='unique_cart_product'),
         models.CheckConstraint(condition=Q(quantity__gt=0), name='cart_item_quantity_positive'),
      ]


class Order(models.Model):
   class Status(models.TextChoices):
      PENDING = 'PENDING', 'Pending'
      CONFIRMED = 'CONFIRMED', 'Confirmed'
      PROCESSING = 'PROCESSING', 'Processing'
      COMPLETED = 'COMPLETED', 'Completed'
      CANCELED = 'CANCELED', 'Canceled'

   class PaymentStatus(models.TextChoices):
      UNPAID = 'UNPAID', 'Unpaid'
      PENDING = 'PENDING', 'Pending'
      PAID = 'PAID', 'Paid'
      FAILED = 'FAILED', 'Failed'
      PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially refunded'
      REFUNDED = 'REFUNDED', 'Refunded'

   order_number = models.CharField(max_length=32, unique=True, default=new_order_number)
   user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.PROTECT)
   address = models.ForeignKey(Address, null=True, blank=True, related_name='orders', on_delete=models.SET_NULL)
   buyer_name = models.CharField(max_length=160)
   buyer_email = models.EmailField(max_length=254)
   buyer_phone = models.CharField(max_length=32)
   recipient_name = models.CharField(max_length=120)
   recipient_phone = models.CharField(max_length=32)
   shipping_country = models.CharField(max_length=8)
   shipping_province = models.CharField(max_length=100)
   shipping_city = models.CharField(max_length=100)
   shipping_district = models.CharField(max_length=100, blank=True, default='')
   shipping_address = models.CharField(max_length=300)
   shipping_building_number = models.CharField(max_length=30, blank=True, default='')
   shipping_unit = models.CharField(max_length=30, blank=True, default='')
   shipping_postal_code = models.CharField(max_length=20)
   subtotal_amount = models.BigIntegerField()
   discount_amount = models.BigIntegerField(default=0)
   shipping_amount = models.BigIntegerField(default=0)
   tax_amount = models.BigIntegerField(default=0)
   total_amount = models.BigIntegerField()
   currency = models.CharField(max_length=12, default='TOMAN')
   status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
   payment_status = models.CharField(max_length=24, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
   notes = models.TextField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)
   paid_at = models.DateTimeField(null=True, blank=True)
   canceled_at = models.DateTimeField(null=True, blank=True)
   completed_at = models.DateTimeField(null=True, blank=True)

   class Meta:
      indexes = [
         models.Index(fields=('user', '-created_at'), name='order_user_created_idx'),
         models.Index(fields=('status', '-created_at'), name='order_status_created_idx'),
      ]
      constraints = [
         models.CheckConstraint(condition=Q(subtotal_amount__gte=0), name='order_subtotal_nonnegative'),
         models.CheckConstraint(condition=Q(discount_amount__gte=0), name='order_discount_nonnegative'),
         models.CheckConstraint(condition=Q(shipping_amount__gte=0), name='order_shipping_nonnegative'),
         models.CheckConstraint(condition=Q(tax_amount__gte=0), name='order_tax_nonnegative'),
         models.CheckConstraint(condition=Q(total_amount__gte=0), name='order_total_nonnegative'),
      ]


class OrderItem(models.Model):
   order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
   product = models.ForeignKey(Product, null=True, blank=True, related_name='order_items', on_delete=models.SET_NULL)
   product_title = models.CharField(max_length=160)
   sku_snapshot = models.CharField(max_length=100, null=True, blank=True)
   external_product_id_snapshot = models.CharField(max_length=160, null=True, blank=True)
   unit_price = models.BigIntegerField()
   original_unit_price = models.BigIntegerField()
   discount_amount = models.BigIntegerField(default=0)
   quantity = models.PositiveIntegerField()
   line_total = models.BigIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      constraints = [
         models.CheckConstraint(condition=Q(quantity__gt=0), name='order_item_quantity_positive'),
         models.CheckConstraint(condition=Q(unit_price__gte=0), name='order_item_unit_price_nonnegative'),
         models.CheckConstraint(condition=Q(original_unit_price__gte=0), name='order_item_original_price_nonnegative'),
         models.CheckConstraint(condition=Q(discount_amount__gte=0), name='order_item_discount_nonnegative'),
         models.CheckConstraint(condition=Q(line_total__gte=0), name='order_item_line_total_nonnegative'),
      ]


class Invoice(models.Model):
   class DocumentType(models.TextChoices):
      STANDARD = 'STANDARD', 'Standard'
      CREDIT_NOTE = 'CREDIT_NOTE', 'Credit note'

   class Status(models.TextChoices):
      DRAFT = 'DRAFT', 'Draft'
      ISSUED = 'ISSUED', 'Issued'
      VOID = 'VOID', 'Void'

   order = models.ForeignKey(Order, related_name='invoices', on_delete=models.PROTECT)
   invoice_number = models.CharField(max_length=40, unique=True, default=new_invoice_number)
   document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.STANDARD)
   related_invoice = models.ForeignKey('self', null=True, blank=True, related_name='correction_invoices', on_delete=models.PROTECT)
   status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
   issued_at = models.DateTimeField(null=True, blank=True)
   currency = models.CharField(max_length=12, default='TOMAN')
   seller_name = models.CharField(max_length=160)
   seller_tax_id = models.CharField(max_length=80, null=True, blank=True)
   seller_phone = models.CharField(max_length=32)
   seller_address = models.CharField(max_length=300)
   buyer_name = models.CharField(max_length=160)
   buyer_email = models.EmailField(max_length=254)
   buyer_phone = models.CharField(max_length=32)
   buyer_tax_id = models.CharField(max_length=80, null=True, blank=True)
   billing_address = models.CharField(max_length=300)
   subtotal_amount = models.BigIntegerField()
   discount_amount = models.BigIntegerField(default=0)
   shipping_amount = models.BigIntegerField(default=0)
   tax_amount = models.BigIntegerField(default=0)
   total_amount = models.BigIntegerField()
   notes = models.TextField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.CheckConstraint(condition=Q(subtotal_amount__gte=0), name='invoice_subtotal_nonnegative'),
         models.CheckConstraint(condition=Q(discount_amount__gte=0), name='invoice_discount_nonnegative'),
         models.CheckConstraint(condition=Q(shipping_amount__gte=0), name='invoice_shipping_nonnegative'),
         models.CheckConstraint(condition=Q(tax_amount__gte=0), name='invoice_tax_nonnegative'),
         models.CheckConstraint(condition=Q(total_amount__gte=0), name='invoice_total_nonnegative'),
      ]


class InvoiceItem(models.Model):
   invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
   order_item = models.ForeignKey(OrderItem, null=True, blank=True, related_name='invoice_items', on_delete=models.SET_NULL)
   description = models.CharField(max_length=300)
   quantity = models.PositiveIntegerField()
   unit_price = models.BigIntegerField()
   discount_amount = models.BigIntegerField(default=0)
   tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
   tax_amount = models.BigIntegerField(default=0)
   line_total = models.BigIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      constraints = [
         models.CheckConstraint(condition=Q(quantity__gt=0), name='invoice_item_quantity_positive'),
         models.CheckConstraint(condition=Q(unit_price__gte=0), name='invoice_item_unit_price_nonnegative'),
         models.CheckConstraint(condition=Q(discount_amount__gte=0), name='invoice_item_discount_nonnegative'),
         models.CheckConstraint(condition=Q(tax_amount__gte=0), name='invoice_item_tax_nonnegative'),
         models.CheckConstraint(condition=Q(line_total__gte=0), name='invoice_item_line_total_nonnegative'),
      ]


class PaymentAttempt(models.Model):
   class Status(models.TextChoices):
      CREATED = 'CREATED', 'Created'
      PENDING = 'PENDING', 'Pending'
      SUCCEEDED = 'SUCCEEDED', 'Succeeded'
      FAILED = 'FAILED', 'Failed'
      CANCELED = 'CANCELED', 'Canceled'
      EXPIRED = 'EXPIRED', 'Expired'

   order = models.ForeignKey(Order, related_name='payment_attempts', on_delete=models.PROTECT)
   gateway = models.CharField(max_length=40)
   amount = models.BigIntegerField()
   currency = models.CharField(max_length=12, default='TOMAN')
   status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
   authority = models.CharField(max_length=160, null=True, blank=True)
   reference_id = models.CharField(max_length=160, null=True, blank=True)
   idempotency_key = models.CharField(max_length=64, unique=True, default=new_idempotency_key)
   failure_code = models.CharField(max_length=80, null=True, blank=True)
   failure_reason = models.TextField(null=True, blank=True)
   requested_at = models.DateTimeField(auto_now_add=True)
   verified_at = models.DateTimeField(null=True, blank=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(fields=('gateway', 'authority'), condition=Q(authority__isnull=False), name='unique_gateway_authority'),
         models.UniqueConstraint(fields=('gateway', 'reference_id'), condition=Q(reference_id__isnull=False), name='unique_gateway_reference'),
         models.CheckConstraint(condition=Q(amount__gte=0), name='payment_amount_nonnegative'),
      ]


class Refund(models.Model):
   class Status(models.TextChoices):
      CREATED = 'CREATED', 'Created'
      PENDING = 'PENDING', 'Pending'
      SUCCEEDED = 'SUCCEEDED', 'Succeeded'
      FAILED = 'FAILED', 'Failed'
      CANCELED = 'CANCELED', 'Canceled'

   payment_attempt = models.ForeignKey(PaymentAttempt, related_name='refunds', on_delete=models.PROTECT)
   amount = models.BigIntegerField()
   currency = models.CharField(max_length=12, default='TOMAN')
   status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
   provider_refund_id = models.CharField(max_length=160, null=True, blank=True)
   idempotency_key = models.CharField(max_length=64, unique=True, default=new_idempotency_key)
   reason = models.TextField(null=True, blank=True)
   requested_at = models.DateTimeField(auto_now_add=True)
   processed_at = models.DateTimeField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(fields=('provider_refund_id',), condition=Q(provider_refund_id__isnull=False), name='unique_provider_refund'),
         models.CheckConstraint(condition=Q(amount__gt=0), name='refund_amount_positive'),
      ]


class StockMovement(models.Model):
   class MovementType(models.TextChoices):
      RESTOCK = 'RESTOCK', 'Restock'
      SALE = 'SALE', 'Sale'
      RETURN = 'RETURN', 'Return'
      ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'

   product = models.ForeignKey(Product, related_name='stock_movements', on_delete=models.PROTECT)
   quantity_delta = models.IntegerField()
   movement_type = models.CharField(max_length=16, choices=MovementType.choices)
   order_item = models.ForeignKey(OrderItem, null=True, blank=True, related_name='stock_movements', on_delete=models.SET_NULL)
   created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='stock_movements', on_delete=models.SET_NULL)
   idempotency_key = models.CharField(max_length=64, unique=True, default=new_idempotency_key)
   note = models.TextField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      constraints = [
         models.CheckConstraint(condition=~Q(quantity_delta=0), name='stock_movement_nonzero'),
      ]


class InventoryReservation(models.Model):
   class Status(models.TextChoices):
      ACTIVE = 'ACTIVE', 'Active'
      CONSUMED = 'CONSUMED', 'Consumed'
      RELEASED = 'RELEASED', 'Released'
      EXPIRED = 'EXPIRED', 'Expired'

   order_item = models.ForeignKey(OrderItem, related_name='inventory_reservations', on_delete=models.PROTECT)
   product = models.ForeignKey(Product, related_name='inventory_reservations', on_delete=models.PROTECT)
   quantity = models.PositiveIntegerField()
   status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
   expires_at = models.DateTimeField()
   created_at = models.DateTimeField(auto_now_add=True)
   consumed_at = models.DateTimeField(null=True, blank=True)
   released_at = models.DateTimeField(null=True, blank=True)

   class Meta:
      constraints = [
         models.UniqueConstraint(fields=('order_item',), condition=Q(status='ACTIVE'), name='one_active_reservation_per_item'),
         models.CheckConstraint(condition=Q(quantity__gt=0), name='reservation_quantity_positive'),
      ]


class OrderStatusHistory(models.Model):
   order = models.ForeignKey(Order, related_name='status_history', on_delete=models.CASCADE)
   old_status = models.CharField(max_length=24, null=True, blank=True)
   new_status = models.CharField(max_length=24)
   changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='order_status_changes', on_delete=models.SET_NULL)
   note = models.TextField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      ordering = ('created_at', 'id')
      indexes = [models.Index(fields=('order', '-created_at'), name='order_status_history_idx')]


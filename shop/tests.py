from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import (
   Address,
   Cart,
   CartItem,
   Category,
   InventoryReservation,
   Order,
   OrderItem,
   PaymentAttempt,
   Product,
   ProductImage,
   Refund,
   StockMovement,
)


class DomainConstraintTests(TestCase):
   def setUp(self):
      self.user = get_user_model().objects.create_user(username='domain-user', password='test-password')
      self.category = Category.objects.create(title='Test', slug='test', category_image='upload/category/test.jpg')
      self.product = Product.objects.create(
         title='Test product',
         slug='test-product',
         category_title=self.category,
         price=1000,
         discounted_price=900,
         stock=10,
         image='upload/product/test.jpg',
      )

   def assert_integrity_error(self, callback):
      with self.assertRaises(IntegrityError):
         with transaction.atomic():
            callback()

   def order(self):
      return Order.objects.create(
         user=self.user,
         buyer_name='Test User',
         buyer_email='test@example.com',
         buyer_phone='09120000000',
         recipient_name='Test User',
         recipient_phone='09120000000',
         shipping_country='IR',
         shipping_province='Tehran',
         shipping_city='Tehran',
         shipping_address='Main street',
         shipping_postal_code='1234567890',
         subtotal_amount=900,
         total_amount=900,
      )

   def test_address_limit_and_one_default(self):
      Address.objects.create(
         user=self.user,
         title='Home',
         recipient_name='Test User',
         recipient_phone='09120000000',
         province='Tehran',
         city='Tehran',
         street_address='Main street',
         postal_code='1234567890',
         is_default=True,
      )
      self.assert_integrity_error(lambda: Address.objects.create(
         user=self.user,
         title='Second default',
         recipient_name='Test User',
         recipient_phone='09120000000',
         province='Tehran',
         city='Tehran',
         street_address='Second street',
         postal_code='1234567890',
         is_default=True,
      ))
      for number in (2, 3):
         Address.objects.create(
            user=self.user,
            title=f'Address {number}',
            recipient_name='Test User',
            recipient_phone='09120000000',
            province='Tehran',
            city='Tehran',
            street_address=f'Street {number}',
            postal_code='1234567890',
         )
      with self.assertRaises(ValidationError):
         Address.objects.create(
            user=self.user,
            title='Fourth',
            recipient_name='Test User',
            recipient_phone='09120000000',
            province='Tehran',
            city='Tehran',
            street_address='Fourth street',
            postal_code='1234567890',
         )

   def test_category_hierarchy_cycle_is_rejected_by_validation(self):
      parent = Category.objects.create(title='Parent', slug='parent', category_image='upload/category/parent.jpg')
      child = Category.objects.create(title='Child', slug='child', parent=parent, category_image='upload/category/child.jpg')
      parent.parent = child
      with self.assertRaises(ValidationError):
         parent.full_clean()

   def test_cart_has_one_active_instance_and_unique_product_lines(self):
      Cart.objects.create(user=self.user)
      self.assert_integrity_error(lambda: Cart.objects.create(user=self.user))
      cart = Cart.objects.get(user=self.user, status=Cart.Status.ACTIVE)
      CartItem.objects.create(cart=cart, product=self.product, quantity=1)
      self.assert_integrity_error(lambda: CartItem.objects.create(cart=cart, product=self.product, quantity=1))

   def test_product_image_has_one_primary_image(self):
      ProductImage.objects.create(product=self.product, image='upload/product/gallery/one.jpg', is_primary=True)
      self.assert_integrity_error(lambda: ProductImage.objects.create(
         product=self.product,
         image='upload/product/gallery/two.jpg',
         is_primary=True,
      ))

   def test_order_item_keeps_product_snapshot(self):
      order = self.order()
      item = OrderItem.objects.create(
         order=order,
         product=self.product,
         product_title=self.product.title,
         unit_price=900,
         original_unit_price=1000,
         quantity=1,
         line_total=900,
      )
      self.product.title = 'Changed product'
      self.product.save(update_fields=['title'])
      item.refresh_from_db()
      self.assertEqual(item.product_title, 'Test product')

   def test_payment_attempt_and_refund_idempotency(self):
      order = self.order()
      attempt = PaymentAttempt.objects.create(order=order, gateway='test', amount=900, idempotency_key='payment-1')
      self.assert_integrity_error(lambda: PaymentAttempt.objects.create(
         order=order, gateway='test', amount=900, idempotency_key='payment-1'
      ))
      self.assert_integrity_error(lambda: Refund.objects.create(
         payment_attempt=attempt, amount=0, idempotency_key='refund-1'
      ))

   def test_stock_movement_and_reservation_quantities_are_valid(self):
      self.assert_integrity_error(lambda: StockMovement.objects.create(
         product=self.product,
         quantity_delta=0,
         movement_type=StockMovement.MovementType.ADJUSTMENT,
         idempotency_key='movement-1',
      ))
      item = OrderItem.objects.create(
         order=self.order(),
         product=self.product,
         product_title=self.product.title,
         unit_price=900,
         original_unit_price=1000,
         quantity=1,
         line_total=900,
      )
      self.assert_integrity_error(lambda: InventoryReservation.objects.create(
         order_item=item,
         product=self.product,
         quantity=0,
         expires_at=timezone.now() + timedelta(minutes=10),
      ))

from datetime import timedelta
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .authentication.authorization import get_owned_object_or_404, require_permission
from .authentication.services import ChallengeError, issue_email_challenge, verify_email_challenge
from .models import (
   Address,
   Cart,
   CartItem,
   Category,
   EmailVerificationChallenge,
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
      ProductImage.objects.create(product=self.product, image='upload/product/one.jpg', is_primary=True)

      self.assert_integrity_error(lambda: ProductImage.objects.create(
         product=self.product,
         image='upload/product/two.jpg',
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


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationTests(TestCase):
   password = 'A-strong-password-987!'

   def setUp(self):
      cache.clear()

   def _register(self, **overrides):
      data = {
         'first_name': 'Ada',
         'last_name': 'Lovelace',
         'email': 'ada@example.com',
         'password': self.password,
         'password_confirmation': self.password,
      }
      data.update(overrides)
      return self.client.post('/register/', data)

   def _code(self):
      match = re.search(r'\b(\d{6})\b', mail.outbox[-1].body)
      self.assertIsNotNone(match)
      return match.group(1)

   def _active_user(self, email='active@example.com'):
      return get_user_model().objects.create_user(
         username=f'user-{email}', email=email, password=self.password, is_active=True,
      )

   def test_registration_hashes_password_and_creates_inactive_user(self):
      response = self._register()
      self.assertEqual(response.status_code, 302)
      user = get_user_model().objects.get(email='ada@example.com')
      self.assertFalse(user.is_active)
      self.assertTrue(user.check_password(self.password))
      self.assertNotEqual(user.password, self.password)
      challenge = EmailVerificationChallenge.objects.get(user=user)
      self.assertNotIn(self._code(), challenge.code_digest)

   def test_registration_rejects_case_insensitive_duplicate_email(self):
      self._active_user('Ada@Example.com')
      response = self._register(email='ada@example.com')
      self.assertEqual(response.status_code, 302)
      self.assertEqual(get_user_model().objects.filter(email__iexact='ada@example.com').count(), 1)

   def test_database_rejects_case_insensitive_duplicate_email(self):
      self._active_user('unique@example.com')
      with self.assertRaises(IntegrityError):
         with transaction.atomic():
            self._active_user('UNIQUE@example.com')

   def test_email_verification_activates_user_and_prevents_replay(self):
      self._register()
      code = self._code()
      response = self.client.post('/verify-email/', {'email': 'ADA@example.com', 'code': code})
      self.assertEqual(response.status_code, 302)
      user = get_user_model().objects.get(email='ada@example.com')
      self.assertTrue(user.is_active)
      challenge = EmailVerificationChallenge.objects.get(user=user)
      self.assertIsNotNone(challenge.consumed_at)
      self.client.logout()
      replay = self.client.post('/verify-email/', {'email': 'ada@example.com', 'code': code})
      self.assertEqual(replay.status_code, 400)

   def test_expired_or_exhausted_code_is_rejected(self):
      self._register()
      user = get_user_model().objects.get(email='ada@example.com')
      challenge = EmailVerificationChallenge.objects.get(user=user)
      challenge.expires_at = timezone.now() - timedelta(seconds=1)
      challenge.save(update_fields=['expires_at'])
      self.assertEqual(self.client.post('/verify-email/', {'email': user.email, 'code': self._code()}).status_code, 400)
      self.assertFalse(user.is_active)

      challenge.expires_at = timezone.now() + timedelta(minutes=5)
      challenge.save(update_fields=['expires_at', 'consumed_at'])
      for _ in range(5):
         with self.assertRaises(ChallengeError):
            verify_email_challenge(
               email=user.email,
               code='000000',
               purpose=EmailVerificationChallenge.Purpose.REGISTRATION,
            )
      challenge.refresh_from_db()
      self.assertEqual(challenge.attempts, 5)
      self.assertIsNotNone(challenge.consumed_at)

   def test_resend_cooldown_does_not_issue_a_second_code(self):
      self._register()
      self.assertEqual(EmailVerificationChallenge.objects.count(), 1)
      response = self.client.post('/verify-email/resend/', {'email': 'ada@example.com'})
      self.assertEqual(response.status_code, 302)
      self.assertEqual(EmailVerificationChallenge.objects.count(), 1)

   def test_login_rejects_unverified_or_disabled_users_and_rotates_session(self):
      self._register()
      self.assertEqual(self.client.post('/login/', {'email': 'ada@example.com', 'password': self.password}).status_code, 400)
      active_user = self._active_user()
      active_user.is_active = False
      active_user.save(update_fields=['is_active'])
      self.assertEqual(self.client.post('/login/', {'email': active_user.email, 'password': self.password}).status_code, 400)
      active_user.is_active = True
      active_user.save(update_fields=['is_active'])
      session = self.client.session
      session['pre_login'] = 'value'
      session.save()
      old_session_key = session.session_key
      response = self.client.post('/login/', {'email': active_user.email, 'password': self.password})
      self.assertEqual(response.status_code, 302)
      self.assertNotEqual(self.client.session.session_key, old_session_key)

   def test_password_change_updates_password_and_keeps_current_session(self):
      user = self._active_user()
      self.client.force_login(user)
      response = self.client.post('/password/change/', {
         'old_password': self.password,
         'new_password1': 'Another-strong-password-123!',
         'new_password2': 'Another-strong-password-123!',
      })
      self.assertEqual(response.status_code, 302)
      user.refresh_from_db()
      self.assertTrue(user.check_password('Another-strong-password-123!'))
      self.assertIn('_auth_user_id', self.client.session)

   def test_password_reset_uses_django_single_use_token_flow(self):
      user = self._active_user()
      response = self.client.post('/password/reset/', {'email': user.email})
      self.assertEqual(response.status_code, 302)
      self.assertEqual(len(mail.outbox), 1)
      reset_path = re.search(r'https?://testserver([^\s]+)', mail.outbox[0].body).group(1)
      response = self.client.get(reset_path, follow=True)
      self.assertEqual(response.status_code, 200)
      response = self.client.post(response.request['PATH_INFO'], {
         'new_password1': 'Reset-strong-password-123!',
         'new_password2': 'Reset-strong-password-123!',
      }, follow=True)
      self.assertEqual(response.status_code, 200)
      user.refresh_from_db()
      self.assertTrue(user.check_password('Reset-strong-password-123!'))

   def test_email_change_requires_a_verified_otp(self):
      user = self._active_user()
      self.client.force_login(user)
      response = self.client.post('/email/change/', {
         'email': 'changed@example.com', 'current_password': self.password,
      })
      self.assertEqual(response.status_code, 302)
      response = self.client.post('/email/change/verify/', {
         'email': 'changed@example.com', 'code': self._code(),
      })
      self.assertEqual(response.status_code, 302)
      user.refresh_from_db()
      self.assertEqual(user.email, 'changed@example.com')

   def test_csrf_is_required_for_login_post(self):
      user = self._active_user()
      csrf_client = Client(enforce_csrf_checks=True)
      response = csrf_client.post('/login/', {'email': user.email, 'password': self.password})
      self.assertEqual(response.status_code, 403)

   def test_login_rate_limit_and_pydantic_unexpected_field(self):
      for _ in range(5):
         self.client.post('/login/', {'email': 'nobody@example.com', 'password': self.password})
      response = self.client.post('/login/', {'email': 'nobody@example.com', 'password': self.password})
      self.assertEqual(response.status_code, 429)
      invalid = self.client.post('/register/', {
         'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'new@example.com',
         'password': self.password, 'password_confirmation': self.password, 'unexpected': 'no',
      })
      self.assertEqual(invalid.status_code, 400)

   def test_permission_and_ownership_helpers_deny_by_default(self):
      owner = self._active_user('owner@example.com')
      other = self._active_user('other@example.com')
      address = Address.objects.create(
         user=owner, title='Home', recipient_name='Owner', recipient_phone='09120000000',
         province='Tehran', city='Tehran', street_address='Street', postal_code='1234567890',
      )
      with self.assertRaises(Exception):
         require_permission(other, 'shop.change_order')
      with self.assertRaises(Http404):
         get_owned_object_or_404(Address, user=other, pk=address.pk)

   def test_business_groups_are_created_without_assigning_them_to_users(self):
      self.assertEqual(
         set(Group.objects.filter(name__in={'Admin', 'Manager', 'Product Creator', 'Order Manager', 'Support'}).values_list('name', flat=True)),
         {'Admin', 'Manager', 'Product Creator', 'Order Manager', 'Support'},
      )
      self.assertTrue(Group.objects.get(name='Admin').permissions.filter(content_type__app_label='shop').exists())
      self.assertTrue(Group.objects.get(name='Manager').permissions.filter(codename='change_order').exists())

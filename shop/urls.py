from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from .authentication import views as authentication_views

app_name = 'shop'

urlpatterns = [
   path('', views.home, name='home'),
   path('about/', views.about, name='about'),
   path('products/', views.products, name='products'),
   path('products/<int:product_id>/', views.product_detail, name='product_detail'),
   path('cart/summary/', views.cart_summary, name='cart_summary'),
   path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
   path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

   path('register/', authentication_views.register, name='register'),
   path('login/', authentication_views.login_view, name='login'),
   path('logout/', authentication_views.logout_view, name='logout'),
   path('verify-email/', authentication_views.verify_email, name='verify_email'),
   path('verify-email/resend/', authentication_views.resend_verification, name='resend_verification'),

   path('password/reset/', authentication_views.password_reset_request, name='password_reset'),
   path('password/change/', authentication_views.password_change, name='password_change'),
   path(
      'password/reset/<uidb64>/<token>/',
      authentication_views.ValidatedPasswordResetConfirmView.as_view(),
      name='password_reset_confirm',
   ),
   path(
      'password/reset/complete/',
      auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),
      name='password_reset_complete',
   ),

   path('dashboard/', authentication_views.dashboard, name='dashboard'),
   path('dashboard/account_security', authentication_views.account_security, name='account_security'),
   path('dashboard/admin/', authentication_views.admin_panel, name='admin_panel'),

   path('email/change/', authentication_views.email_change, name='email_change'),
   path('email/change/verify/', authentication_views.verify_email_change, name='verify_email_change'),
]

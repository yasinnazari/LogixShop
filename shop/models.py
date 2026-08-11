from django.db import models


class Category(models.Model):
   title = models.CharField(max_length=30)

   def __str__(self):
      return self.name
   

class Customer(models.Model):
   id = models.AutoField(primary_key=True, unique=True)
   first_name = models.CharField(max_length=30)
   last_name = models.CharField(max_length=30)
   phone_number = models.CharField(max_length=20)
   email = models.EmailField(max_length=254)
   password = models.CharField(max_length=20)

   def __str__(self):
      return self.name

class Product(models.Model):
   id = models.AutoField(primary_key=True, unique=True)
   title = models.CharField(max_length=80)
   description = models.TextField(max_length=1000)
   price = models.IntegerField()
   category_title = models.ForeignKey(Category, verbose_name="category_title", on_delete=models.CASCADE)
   image = models.ImageField(upload_to=None, height_field=None, width_field=None, max_length=None)

   def __str__(self):
      return self.name

class Invoice(models.Model):
   class InvoiceStatus(models.TextChoices):
      UNPAID = 'در انتظار پرداخت'
      PAID = 'پرداخت شده'
      PROCESSING = 'در حال بررسی'
      REJECTED = 'رد شده'
      CONFIRMED = 'تایید شده'
      CANCELED = 'لغو شده'
      DONE = 'انجام شده'

   product_id = models.ForeignKey(Product, verbose_name="product_id", on_delete=models.CASCADE)
   customer_id = models.ForeignKey(Customer, verbose_name="customer_id", on_delete=models.CASCADE)
   count = models.SmallIntegerField()
   address = models.CharField(max_length=300)
   created_at = models.DateField(auto_now=False, auto_now_add=True)
   status = models.CharField(max_length=15, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

   def __str__(self):
      return self.name

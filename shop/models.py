from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
   title = models.CharField(max_length=30)
   # image = models.ImageField(upload_to='upload/category/')

   def __str__(self):
      return self.title


class Customer(models.Model):
   id = models.AutoField(primary_key=True, unique=True)
   first_name = models.CharField(max_length=30)
   last_name = models.CharField(max_length=30)
   phone_number = models.CharField(max_length=20)
   email = models.EmailField(max_length=254)
   password = models.CharField(max_length=20)


   def __str__(self):
      return f"{self.first_name} {self.last_name}"



class Product(models.Model):
   id = models.AutoField(primary_key=True, unique=True)
   title = models.CharField(max_length=80)
   description = models.TextField(max_length=1000, default='', blank=True, null=True)
   price = models.DecimalField(max_digits=12, decimal_places=0, default=0)
   discounted_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)
   category_title = models.ForeignKey(Category, verbose_name="category_title", on_delete=models.CASCADE)
   is_sale = models.BooleanField(default=False)
   rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
   image = models.ImageField(upload_to='upload/product/')

   def __str__(self):
      return self.title


class Invoice(models.Model):
   class InvoiceStatus(models.TextChoices):
      UNPAID = ('UNPAID', 'در انتظار پرداخت')
      PAID = ('PAID', 'پرداخت شده')
      PROCESSING = ('PROCESSING', 'در حال بررسی')
      REJECTED = ('REJECTED', 'رد شده')
      CONFIRMED = ('CONFIRMED', 'تایید شده')
      CANCELED = ('CANCELED', 'لغو شده')
      DONE = ('DONE', 'انجام شده')

   id = models.AutoField(primary_key=True, unique=True)
   product_id = models.ForeignKey(Product, verbose_name="product_id", on_delete=models.CASCADE)
   customer_id = models.ForeignKey(Customer, verbose_name="customer_id", on_delete=models.CASCADE)
   count = models.SmallIntegerField()
   address = models.CharField(max_length=300, blank=False)
   created_at = models.DateField(auto_now=False, auto_now_add=True)
   status = models.CharField(max_length=30, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

   def __str__(self):
      return "Invoice" + self.id


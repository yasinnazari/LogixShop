from django.db import models


class Category(models.Model):
   title = models.CharField(max_length=30)

   def __str__(self):
      return self.name
   

class Customer(models.Model):
   first_name = models.CharField(max_length=30)
   last_name = models.CharField(max_length=30)
   phone_number = models.CharField(max_length=20)
   email = models.EmailField(max_length=254)
   password = models.CharField(max_length=20)

   def __str__(self):
      return self.name

class Product(models.Model):
   title = models.CharField(max_length=80)
   description = models.TextField(max_length=1000)
   price = models.IntegerField()
   category_title = models.ForeignKey(Category, verbose_name="category_title")
   image = models.ImageField(upload_to=None, height_field=None, width_field=None, max_length=None)

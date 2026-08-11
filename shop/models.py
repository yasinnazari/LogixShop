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
   
from django.db import models


class Brand(models.Model):
    id = models.AutoField(primary_key=True, db_column="BrandID")
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "Brand"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    id = models.AutoField(primary_key=True, db_column="LocationID")
    brand = models.ForeignKey(Brand, models.PROTECT, db_column="BrandID", related_name="locations")
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Location"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Perfume(models.Model):
    id = models.AutoField(primary_key=True, db_column="PerfumeID")
    brand = models.ForeignKey(Brand, models.PROTECT, db_column="BrandID", related_name="perfumes")
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    price_per_spray = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "Perfume"
        ordering = ["brand_id", "name"]

    def __str__(self):
        return f"{self.name} ({self.brand})"

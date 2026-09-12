from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files import File
from django.db import models


# Extended User Model for Role-Based Control
class User(AbstractUser):
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("AUDIT", "Audit"),
        ("IT", "IT"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="IT")


class Asset(models.Model):
    # 1. Choices / Constants
    ASSET_TYPES = (
        ("LAPTOP", "Laptop"),
        ("MONITOR", "Monitor"),
        ("CELLPHONE", "Cellphone"),
        ("OTHERS", "Others"),
    )
    STATUS_CHOICES = (
        ("AVAILABLE", "Available"),
        ("ASSIGNED", "Assigned"),
        ("UNDER_REPAIR", "Under Repair"),
        ("DISPOSED", "Disposed"),
    )

    # 2. Database Fields
    unit_name = models.CharField(max_length=100)
    company_tag = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, unique=True)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)

    # DJ001 Fix: String-based fields should use default="" or blank=True without null=True
    assigned_to = models.CharField(max_length=100, blank=True, default="")

    # File/Image fields (null=True is allowed on FileField when file can be absent)
    accountability_scan = models.FileField(
        upload_to="accountability_scans/", blank=True, null=True
    )
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="AVAILABLE"
    )
    date_purchased = models.DateField()
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    # Tracking user relationships
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets_updated",
    )

    # 3. Magic Methods (DJ012 Fix: Put __str__ before custom methods and save())
    def __str__(self):
        return f"{self.company_tag} - {self.unit_name}"

    # 4. Custom save() Method
    def save(self, *args, **kwargs):
        # 1. Structure the scanner payload containing Company Tag, Serial Number, and Unit Name
        qr_content = f"{self.company_tag} | {self.serial_number} | {self.unit_name}"

        # 2. Configure high-scannability parameters
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% error tolerance
            box_size=10,  # High resolution output
            border=4,  # Standard margin required by hardware scanners
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        # 3. Build image buffer and write file stream
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        file_name = f"qr_{self.company_tag}.png"

        # Save to Model ImageField without triggering recursive save loop
        self.qr_code.save(file_name, File(buffer), save=False)

        super().save(*args, **kwargs)


# Specs Models linked via OneToOne field
class LaptopSpec(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="laptop_spec")
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    ram = models.CharField(max_length=20)
    cpu = models.CharField(max_length=50)
    gpu = models.CharField(max_length=50, blank=True, null="")

    def __str__(self):
        return f"{self.brand} {self.model} ({self.asset})"


class MonitorSpec(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="monitor_spec")
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.brand} {self.model} ({self.asset})"


class CellphoneSpec(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="cellphone_spec")
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.brand} {self.model} ({self.asset})"


class OtherSpec(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="other_spec")
    brand = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.brand} Spec ({self.asset})"


class AuditLog(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="audit_logs")
    auditor = models.ForeignKey(User, on_delete=models.CASCADE)
    remarks = models.TextField()
    audit_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit log for {self.asset} by {self.auditor}"

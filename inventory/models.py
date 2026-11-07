from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files import File
from django.db import models, router


# Extended User Model for Role-Based Control
class User(AbstractUser):
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("AUDIT", "Audit"),
        ("IT", "IT"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="IT")


class Asset(models.Model):
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

    unit_name = models.CharField(max_length=100)
    company_tag = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, unique=True)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    assigned_to = models.CharField(max_length=100, blank=True, default="")

    accountability_scan = models.FileField(
        upload_to="accountability_scans/",
        blank=True,
        null=True,
    )
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")
    date_purchased = models.DateField()
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

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

    def __str__(self):
        return f"{self.company_tag} - {self.unit_name}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        using = using or router.db_for_write(type(self), instance=self)

        if update_fields is not None:
            update_fields = set(update_fields)
            if not update_fields:
                return

        qr_fields = ("company_tag", "serial_number", "unit_name")
        previous = None

        if self.pk is not None and not force_insert:
            previous = type(self).objects.using(using).filter(pk=self.pk).values(*qr_fields, "qr_code").first()

        qr_values = {field: getattr(self, field) for field in qr_fields}
        qr_name = self.qr_code.name

        if previous is not None and update_fields is not None:
            # Partial saves use the stored values for fields outside update_fields.
            for field in qr_fields:
                if field not in update_fields:
                    qr_values[field] = previous[field]

            if "qr_code" not in update_fields:
                qr_name = previous["qr_code"]

        payload_changed = previous is None or any(qr_values[field] != previous[field] for field in qr_fields)
        qr_missing = not qr_name or not self.qr_code.storage.exists(qr_name)

        if payload_changed or qr_missing:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(" | ".join(qr_values[field] for field in qr_fields))
            qr.make(fit=True)

            image = qr.make_image(fill_color="black", back_color="white")
            filename = f"qr_{qr_values['company_tag']}.png"

            with BytesIO() as buffer:
                image.save(buffer, format="PNG")
                buffer.seek(0)
                self.qr_code.save(filename, File(buffer), save=False)

            if update_fields is not None:
                update_fields.add("qr_code")

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


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

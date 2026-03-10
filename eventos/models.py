import os
import re
import uuid
import qrcode

from io import BytesIO
from datetime import datetime

from django.core.files import File
from django.db import models
from django.urls import reverse


def generate_token():
    return uuid.uuid4().hex


def sanitize_filename_part(value):
    if not value:
        return "Invitado"

    value = value.strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9_áéíóúÁÉÍÓÚñÑ-]", "", value)

    return value or "Invitado"


def media_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower() or ".jpg"

    guest = sanitize_filename_part(instance.guest_name)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    new_filename = f"{guest}_{timestamp}{extension}"

    event_slug = instance.event.slug
    table_number = instance.table.number

    return f"{event_slug}/mesa_{table_number}/{new_filename}"


class Event(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Table(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="tables"
    )
    number = models.PositiveIntegerField()
    token = models.CharField(
        max_length=48,
        default=generate_token,
        unique=True
    )
    qr_image = models.ImageField(
        upload_to="qrs/",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.event.name} - Mesa {self.number}"

    def get_upload_url(self):
        return reverse(
            "table_upload",
            kwargs={
                "event_slug": self.event.slug,
                "table_number": self.number,
                "token": self.token,
            }
        )

    def get_full_upload_url(self):
        return f"http://127.0.0.1:8000{self.get_upload_url()}"

    def generate_qr(self):
        qr = qrcode.make(self.get_full_upload_url())
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        filename = f"evento_{self.event.slug}_mesa_{self.number}.png"
        self.qr_image.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.qr_image:
            self.generate_qr()
            super().save(update_fields=["qr_image"])


class Media(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_APPROVED, "Aprobada"),
        (STATUS_REJECTED, "Rechazada"),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="media_items"
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="media_items"
    )
    guest_name = models.CharField(max_length=150, blank=True, null=True)
    image = models.ImageField(upload_to=media_upload_path)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto {self.id} - Mesa {self.table.number} - {self.status}"
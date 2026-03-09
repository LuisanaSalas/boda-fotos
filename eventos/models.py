import uuid
from django.db import models


def generate_token():
    return uuid.uuid4().hex


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.event.name} - Mesa {self.number}"


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
    image = models.ImageField(upload_to="uploads/")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto {self.id} - Mesa {self.table.number} - {self.status}"
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Event, Table, Media


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "pdf_qr_link", "created_at")
    prepopulated_fields = {"slug": ("name",)}

    def pdf_qr_link(self, obj):
        url = reverse("event_qr_pdf", kwargs={"event_slug": obj.slug})
        return format_html('<a href="{}" target="_blank">Descargar PDF QR</a>', url)

    pdf_qr_link.short_description = "PDF de QR"


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("event", "number", "token", "upload_link", "qr_preview", "created_at")
    list_filter = ("event",)
    search_fields = ("event__name", "number", "token")
    readonly_fields = ("qr_preview_large",)

    def upload_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">Abrir enlace</a>',
            obj.get_upload_url()
        )
    upload_link.short_description = "Link de subida"

    def qr_preview(self, obj):
        if obj.qr_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius:8px;" />',
                obj.qr_image.url
            )
        return "Sin QR"
    qr_preview.short_description = "QR"

    def qr_preview_large(self, obj):
        if obj.qr_image:
            return format_html(
                '<img src="{}" width="250" height="250" style="border-radius:12px;" />',
                obj.qr_image.url
            )
        return "Sin QR"
    qr_preview_large.short_description = "Vista previa QR"


@admin.action(description="Aprobar fotos seleccionadas")
def approve_selected(modeladmin, request, queryset):
    queryset.update(status=Media.STATUS_APPROVED)


@admin.action(description="Rechazar fotos seleccionadas")
def reject_selected(modeladmin, request, queryset):
    queryset.update(status=Media.STATUS_REJECTED)


@admin.action(description="Marcar como pendientes")
def mark_pending(modeladmin, request, queryset):
    queryset.update(status=Media.STATUS_PENDING)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_preview",
        "event",
        "table",
        "guest_name",
        "status_badge",
        "uploaded_at",
    )
    list_filter = ("event", "status", "table")
    search_fields = ("guest_name", "table__number", "event__name")
    actions = [approve_selected, reject_selected, mark_pending]
    readonly_fields = ("image_preview_large", "uploaded_at")
    list_per_page = 50

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )
        return "Sin imagen"
    image_preview.short_description = "Vista previa"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="300" style="max-height:300px;object-fit:contain;border-radius:12px;" />',
                obj.image.url
            )
        return "Sin imagen"
    image_preview_large.short_description = "Imagen"

    def status_badge(self, obj):
        if obj.status == Media.STATUS_APPROVED:
            color = "#198754"
            text = "Aprobada"
        elif obj.status == Media.STATUS_REJECTED:
            color = "#dc3545"
            text = "Rechazada"
        else:
            color = "#ffc107"
            text = "Pendiente"

        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{};color:#fff;font-size:12px;font-weight:600;">{}</span>',
            color,
            text
        )
    status_badge.short_description = "Estado"

    fieldsets = (
        ("Información general", {
            "fields": ("event", "table", "guest_name", "status", "uploaded_at")
        }),
        ("Imagen", {
            "fields": ("image", "image_preview_large")
        }),
    )
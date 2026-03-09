from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Table, Media


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("event", "number", "token", "upload_link", "created_at")
    list_filter = ("event",)
    search_fields = ("event__name", "number", "token")

    def upload_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">Abrir enlace</a>',
            obj.get_upload_url()
        )

    upload_link.short_description = "Link de subida"


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "table", "guest_name", "status", "uploaded_at")
    list_filter = ("event", "status")
    search_fields = ("guest_name", "table__number", "event__name")
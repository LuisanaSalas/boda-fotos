from django.contrib import admin
from .models import Event, Table, Media


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("event", "number", "token", "created_at")
    list_filter = ("event",)
    search_fields = ("event__name", "number", "token")


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "table", "guest_name", "status", "uploaded_at")
    list_filter = ("event", "status")
    search_fields = ("guest_name", "table__number", "event__name")
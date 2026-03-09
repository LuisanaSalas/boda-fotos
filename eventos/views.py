from django.shortcuts import render, get_object_or_404
from .models import Table


def home(request):
    return render(request, "home.html")


def table_upload(request, event_slug, table_number, token):
    table = get_object_or_404(
        Table,
        event__slug=event_slug,
        number=table_number,
        token=token,
        event__is_active=True
    )

    context = {
        "table": table,
        "event": table.event,
    }
    return render(request, "table_upload.html", context)
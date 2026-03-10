from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from .google_drive import upload_file_to_drive
from .models import Table, Event, Media
from .forms import MediaUploadForm


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

    if request.method == "POST":

        form = MediaUploadForm(request.POST, request.FILES)

        if form.is_valid():

            guest_name = form.cleaned_data.get("guest_name")
            images = request.FILES.getlist("images")

            for image in images:
                Media.objects.create(
                    event=table.event,
                    table=table,
                    guest_name=guest_name,
                    image=image
                )

                image.seek(0)

                upload_file_to_drive(
                    image,
                    image.name,
                    table.number,
                    guest_name
                )
            return redirect(request.path)

    else:
        form = MediaUploadForm()

    context = {
        "table": table,
        "event": table.event,
        "form": form
    }

    return render(request, "table_upload.html", context)


def event_qr_pdf(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    tables = event.tables.all().order_by("number")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    for table in tables:
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawCentredString(width / 2, height - 3 * cm, event.name)

        pdf.setFont("Helvetica-Bold", 28)
        pdf.drawCentredString(width / 2, height - 4.5 * cm, f"Mesa {table.number}")

        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(
            width / 2,
            height - 5.5 * cm,
            "Escanea este código para subir tus fotos de la boda"
        )

        if table.qr_image:
            qr_path = table.qr_image.path
            qr_reader = ImageReader(qr_path)

            qr_size = 9 * cm
            x = (width - qr_size) / 2
            y = height - 15 * cm

            pdf.drawImage(
                qr_reader,
                x,
                y,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask='auto'
            )

        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(
            width / 2,
            4 * cm,
            "Abre la cámara de tu celular y escanea el código QR"
        )

        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawCentredString(
            width / 2,
            3.3 * cm,
            "Podrás subir tus fotos directamente desde tu teléfono"
        )

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    filename = f"{event.slug}_qrs_mesas.pdf"
    return HttpResponse(buffer, content_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{filename}"'
    })

def event_gallery(request, event_slug):

    event = get_object_or_404(Event, slug=event_slug)

    media_items = Media.objects.filter(
        event=event
    ).order_by("-uploaded_at")

    context = {
        "event": event,
        "media_items": media_items
    }

    return render(request, "event_gallery.html", context)
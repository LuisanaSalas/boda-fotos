from io import BytesIO
import os

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from .google_drive import upload_file_to_drive
from .models import Table, Event, Media
from .forms import MediaUploadForm


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_FILE_SIZE_MB = 10


def home(request):
    event = Event.objects.filter(is_active=True).order_by("-created_at").first()

    context = {
        "event": event,
    }

    return render(request, "home.html", context)

def validate_uploaded_image(image):
    extension = os.path.splitext(image.name)[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return False, (
            f"El archivo '{image.name}' no tiene un formato permitido. "
            "Solo se aceptan JPG, JPEG, PNG, WEBP y HEIC."
        )

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if image.size > max_size_bytes:
        return False, (
            f"El archivo '{image.name}' excede el tamaño máximo permitido "
            f"de {MAX_FILE_SIZE_MB} MB."
        )

    content_type = getattr(image, "content_type", "")
    if not content_type.startswith("image/"):
        return False, f"El archivo '{image.name}' no es una imagen válida."

    return True, None


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

            if not images:
                messages.error(request, "Debes seleccionar al menos una imagen.")
                return redirect(request.path)

            uploaded_count = 0
            drive_error_count = 0
            validation_errors = []

            for image in images:
                is_valid, error_message = validate_uploaded_image(image)

                if not is_valid:
                    validation_errors.append(error_message)
                    continue

                media_item = Media.objects.create(
                    event=table.event,
                    table=table,
                    guest_name=guest_name,
                    image=image
                )

                uploaded_count += 1

                try:
                    image.seek(0)
                    upload_file_to_drive(
                        image,
                        os.path.basename(media_item.image.name),
                        table.number,
                        guest_name
                    )
                except Exception:
                    drive_error_count += 1

            for error in validation_errors:
                messages.error(request, error)

            if uploaded_count > 0 and drive_error_count == 0:
                messages.success(
                    request,
                    f"Se subieron correctamente {uploaded_count} foto(s)."
                )
            elif uploaded_count > 0 and drive_error_count > 0:
                messages.warning(
                    request,
                    f"Se guardaron {uploaded_count} foto(s), "
                    f"pero {drive_error_count} no se pudieron sincronizar con Google Drive."
                )
            elif uploaded_count == 0 and validation_errors:
                messages.error(
                    request,
                    "No se pudo subir ninguna foto. Revisa los archivos seleccionados."
                )
            else:
                messages.error(
                    request,
                    "Ocurrió un problema al procesar las imágenes."
                )

            return redirect(request.path)

        messages.error(request, "No se pudo procesar el formulario.")
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
        event=event,
        status=Media.STATUS_APPROVED
    ).order_by("-uploaded_at")

    slideshow = request.GET.get("slideshow") == "1"

    context = {
        "event": event,
        "media_items": media_items,
        "slideshow": slideshow,
    }

    return render(request, "event_gallery.html", context)

def event_gallery_api(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    media_items = Media.objects.filter(
        event=event,
        status=Media.STATUS_APPROVED
    ).order_by("-uploaded_at")[:100]

    data = []

    for m in media_items:
        data.append({
            "image": m.image.url,
            "guest_name": m.guest_name or "Invitado",
            "table_number": m.table.number,
            "uploaded_at": m.uploaded_at.strftime("%d/%m/%Y %H:%M"),
        })

    return JsonResponse({"items": data})
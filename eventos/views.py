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
import zipfile
from django.utils.text import slugify


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

                try:
                    media_item = Media.objects.create(
                        event=table.event,
                        table=table,
                        guest_name=guest_name,
                        image=image
                    )

                    uploaded_count += 1

                    try:
                        upload_file_to_drive(
                            media_item.image.path,
                            os.path.basename(media_item.image.name),
                            table.number,
                            guest_name
                        )
                    except Exception as e:
                        print("Error subiendo a Google Drive:", e)
                        drive_error_count += 1

                except Exception as e:
                    print("Error guardando imagen en Django:", e)
                    validation_errors.append(
                        f"No se pudo guardar el archivo '{image.name}'."
                    )

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

    form = MediaUploadForm()

    context = {
        "table": table,
        "event": table.event,
        "form": form
    }

    return render(request, "table_upload.html", context)

def upload_general(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug, is_active=True)

    if request.method == "POST":
        form = MediaUploadForm(request.POST, request.FILES)

        if form.is_valid():
            guest_name = form.cleaned_data.get("guest_name")
            images = request.FILES.getlist("images")

            for image in images:
                is_valid, _ = validate_uploaded_image(image)
                if not is_valid:
                    continue

                Media.objects.create(
                    event=event,
                    table=None, 
                    guest_name=guest_name,
                    image=image
                )

            messages.success(request, "Fotos subidas correctamente.")
            return redirect(request.path)

    else:
        form = MediaUploadForm()

    return render(request, "table_upload.html", {
        "event": event,
        "table": None,  
        "form": form
    })

def event_qr_pdf(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    tables = event.tables.all().order_by("number")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    cols = 2
    rows = 2

    card_width = width / cols
    card_height = height / rows

    padding = 1 * cm
    qr_size = 6.5 * cm  

    wine = (122/255, 45/255, 47/255)
    gold = (185/255, 150/255, 70/255)

    positions = [
        (0, height/2),
        (width/2, height/2),
        (0, 0),
        (width/2, 0),
    ]

    pos_index = 0

    for table in tables:

        if pos_index == 0:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(0, 0, width, height, fill=1)

        x_offset, y_offset = positions[pos_index]
        center_x = x_offset + card_width / 2

        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(1)
        pdf.roundRect(
            x_offset + padding,
            y_offset + padding,
            card_width - padding*2,
            card_height - padding*2,
            20,
            fill=0
        )

        pdf.setFillColorRGB(*wine)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(center_x, y_offset + card_height - 2.5*cm, event.name)

        pdf.setStrokeColorRGB(*gold)
        pdf.setLineWidth(1)
        pdf.line(
            center_x - 2.5*cm,
            y_offset + card_height - 2.9*cm,
            center_x + 2.5*cm,
            y_offset + card_height - 2.9*cm
        )

        pdf.setFont("Helvetica-Bold", 18)
        pdf.setFillColorRGB(*wine)
        pdf.drawCentredString(center_x, y_offset + card_height - 4*cm, f"Mesa {table.number}")

        if table.qr_image:
            qr_reader = ImageReader(table.qr_image.path)

            pdf.drawImage(
                qr_reader,
                center_x - qr_size/2,
                y_offset + card_height/2 - qr_size/2,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask='auto'
            )

        pdf.setFont("Helvetica-Oblique", 8.5)
        pdf.setFillColorRGB(*gold)

        pdf.drawCentredString(center_x, y_offset + 2.5*cm,
            "Escanea el código QR"
        )

        pdf.drawCentredString(center_x, y_offset + 2*cm,
            "y sube tus fotos"
        )

        pdf.setFont("Helvetica", 7.5)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)

        pdf.drawCentredString(center_x, y_offset + 1.3*cm,
            "Forma parte de nuestra historia ✨"
        )

        pos_index += 1

        if pos_index == 4:
            pdf.showPage()
            pos_index = 0

    if pos_index != 0:
        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    return HttpResponse(
        buffer,
        content_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename=\"{event.slug}_qrs_mesas.pdf\"'
        }
    )

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
            "id": m.id,
            "image": m.image.url,
            "guest_name": m.guest_name or "Invitado",
            "table_number": m.table.number if m.table else "General",
            "uploaded_at": m.uploaded_at.strftime("%d/%m/%Y %H:%M"),
        })

    return JsonResponse({"items": data})

def download_all_photos(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    media_items = Media.objects.filter(
        event=event,
        status=Media.STATUS_APPROVED
    ).order_by("-uploaded_at")

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for media in media_items:
            if not media.image:
                continue

            file_path = media.image.path
            extension = os.path.splitext(file_path)[1].lower()

            guest_name = media.guest_name or "invitado"
            guest_slug = slugify(guest_name) or "invitado"

            filename = (
                f"{'mesa_' + str(media.table.number) if media.table else 'general'}/"
                f"{guest_slug}_{media.uploaded_at.strftime('%Y%m%d_%H%M%S')}{extension}"
            )

            if os.path.exists(file_path):
                zip_file.write(file_path, arcname=filename)

    buffer.seek(0)

    zip_filename = f"{event.slug}_galeria_completa.zip"

    return HttpResponse(
        buffer.getvalue(),
        content_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


def download_selected_photos(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    selected_ids = request.GET.getlist("ids")

    media_items = Media.objects.filter(
        event=event,
        status=Media.STATUS_APPROVED,
        id__in=selected_ids
    ).order_by("-uploaded_at")

    if not media_items.exists():
        return HttpResponse("No se seleccionaron fotos válidas.", status=400)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for media in media_items:
            if not media.image:
                continue

            file_path = media.image.path
            extension = os.path.splitext(file_path)[1].lower()

            guest_name = media.guest_name or "invitado"
            guest_slug = slugify(guest_name) or "invitado"

            folder = f"mesa_{media.table.number}" if media.table else "general"

            filename = (
                f"{folder}/"
                f"{guest_slug}_{media.uploaded_at.strftime('%Y%m%d_%H%M%S')}{extension}"
            )

            if os.path.exists(file_path):
                zip_file.write(file_path, arcname=filename)

    buffer.seek(0)

    zip_filename = f"{event.slug}_seleccion.zip"

    return HttpResponse(
        buffer.getvalue(),
        content_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
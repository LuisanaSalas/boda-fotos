from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'evento/<slug:event_slug>/mesa/<int:table_number>/<str:token>/',
        views.table_upload,
        name='table_upload'
    ),
    path(
        'evento/<slug:event_slug>/qrs/pdf/',
        views.event_qr_pdf,
        name='event_qr_pdf'
    ),
    path(
        'evento/<slug:event_slug>/galeria/',
        views.event_gallery,
        name='event_gallery'
    ),
    path(
        "evento/<slug:event_slug>/galeria/api/",
        views.event_gallery_api,
        name="event_gallery_api"
    ),
    path(
        "evento/<slug:event_slug>/galeria/descargar/todas/",
        views.download_all_photos,
        name="download_all_photos"
    ),
    path(
        "evento/<slug:event_slug>/galeria/descargar/seleccion/",
        views.download_selected_photos,
        name="download_selected_photos"
    ),
]
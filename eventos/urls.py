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
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'evento/<slug:event_slug>/mesa/<int:table_number>/<str:token>/',
        views.table_upload,
        name='table_upload'
    ),
]
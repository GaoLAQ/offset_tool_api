"""URL configuration for the offset tool API project."""
from django.urls import path

from cad.views import offset_view

urlpatterns = [
    path("offset", offset_view, name="offset"),
]

from django.urls import path

from apps.core.views import saude

urlpatterns = [
    path("saude/", saude, name="saude"),
]

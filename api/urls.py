from django.urls import path

from . import views


urlpatterns = [
    path("auth/session", views.session_view, name="api-session"),
]

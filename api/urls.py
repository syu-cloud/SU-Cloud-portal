from django.urls import path

from . import views


urlpatterns = [
    path("auth/session", views.session_view, name="api-session"),
    path("vms", views.vm_list_view, name="api-vms"),
    path("images", views.image_list_view, name="api-images"),
]

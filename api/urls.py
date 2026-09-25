from django.urls import path

from . import views


urlpatterns = [
    path("auth/session", views.session_view, name="api-session"),
    path("vms", views.vm_list_view, name="api-vms"),
    path(
        "vms/reclaim-requests",
        views.vm_reclaim_view,
        name="api-vm-reclaim",
    ),
    path("images", views.image_list_view, name="api-images"),
    path("flavors", views.flavor_list_view, name="api-flavors"),
]

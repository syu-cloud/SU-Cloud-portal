"""이미지 관리 UI 라우팅."""

from django.urls import path

from . import image_views


app_name = "imagebuild"


urlpatterns = [
    path(
        "",
        image_views.list_view,
        name="list",
    ),
    path(
        "create/",
        image_views.create_view,
        name="create",
    ),
    path(
        "<int:build_id>/publish/",
        image_views.publish_view,
        name="publish",
    ),
    path(
        "<int:build_id>/cancel/",
        image_views.cancel_view,
        name="cancel",
    ),
]

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from portal import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.index, name="index"),
    path("portal/", include("portal.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="portal/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
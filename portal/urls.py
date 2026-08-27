# ============================================================
# /portal/ 아래 라우팅. config/urls.py의 include("portal.urls")로 연결됨.
# 실제 로그인 분기(index)와 /accounts/login/ 등은 config/urls.py에 있음.
# ============================================================

from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.list_view, name="list"),          # 목록 화면
    path("create/", views.create_view, name="create"),  # 생성 처리
]
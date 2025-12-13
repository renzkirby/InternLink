from django.urls import path
from .views import DashboardView, register_view

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("register/", register_view, name="register"),
]

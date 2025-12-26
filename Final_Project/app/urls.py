from django.urls import path
from .views import register_view
from app import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="app/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", auth_views.LoginView.as_view(template_name="app/login.html"), name="home"),
    path(
        "profile/update/", views.student_profile_update, name="student_profile_update"
    ),
    path("log/add/", views.add_daily_log, name="add_daily_log"),
]

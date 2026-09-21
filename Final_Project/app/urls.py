from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", auth_views.LoginView.as_view(template_name="app/login.html"), name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="app/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),

    path("profile/update/", views.student_profile_update, name="student_profile_update"),

    path("log/add/", views.add_daily_log, name="add_daily_log"),
    path("log/approve/<int:log_id>/", views.approve_log, name="approve_log"),

    path(
        "evaluate/<int:internship_id>/",
        views.evaluate_student,
        name="evaluate_student",
    ),

    path("documents/upload/", views.upload_document, name="upload_document"),
    path(
        "documents/<int:report_id>/",
        views.download_document,
        name="document_download",
    ),

    path(
        "coordinator/student/<int:internship_id>/",
        views.coordinator_student_detail,
        name="coordinator_student_detail",
    ),
    path(
        "coordinator/deploy/",
        views.coordinator_deploy_intern,
        name="coordinator_deploy_intern",
    ),
    path(
        "coordinator/company/add/",
        views.coordinator_add_company,
        name="coordinator_add_company",
    ),
    path(
        "coordinator/setup/",
        views.complete_coordinator_profile,
        name="complete_coordinator_profile",
    ),

    path(
        "supervisor/setup/",
        views.complete_supervisor_profile,
        name="complete_supervisor_profile",
    ),

    path(
        "export/dtr/<int:internship_id>/",
        views.generate_dtr_pdf,
        name="generate_dtr_pdf",
    ),
    path(
        "my-evaluation/",
        views.student_evaluation_detail,
        name="student_evaluation_detail",
    ),

    path(
        "ajax/get-supervisors/",
        views.get_supervisors_for_company,
        name="get_supervisors",
    ),
]

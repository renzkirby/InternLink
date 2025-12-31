from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .forms import *
from .models import *


# Create your views here.


def register_view(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = StudentRegistrationForm()

    return render(request, "app/register.html", {"form": form})


@login_required
def dashboard_view(request):
    user = request.user

    if user.role == User.Role.STUDENT:
        student_profile = user.student_profile
        active_internship = Internship.objects.filter(
            student=student_profile, status="ongoing"
        ).first()

        total_hours = 0
        recent_logs = []
        required_hours = 600
        completion_percent = 0
        documents_count = 0

        if active_internship:
            documents_count = active_internship.student_reports.count()
            required_hours = active_internship.required_hours
            hours_data = active_internship.daily_logs.filter(
                is_verified=True
            ).aggregate(Sum("hours_rendered"))
            total_hours = hours_data["hours_rendered__sum"] or 0

            if required_hours > 0:
                completion_percent = (total_hours / required_hours) * 100

            recent_logs = active_internship.daily_logs.order_by("-date")[:5]

        context = {
            "profile": student_profile,
            "internship": active_internship,
            "total_hours": total_hours,
            "required_hours": required_hours,
            "completion_percent": round(completion_percent, 1),
            "recent_logs": recent_logs,
            "documents_uploaded": documents_count,
        }

        return render(request, "app/student_dashboard.html", context)

    elif user.role == User.Role.COORDINATOR:
        total_students = StudentProfile.objects.count()
        ongoing_internships = Internship.objects.filter(status="ongoing").count()
        total_companies = Company.objects.count()

        recent_deployments = (
            Internship.objects.select_related("student__user", "company")
            .all()
            .order_by("-start_date")
        )

        context = {
            "total_students": total_students,
            "ongoing_internships": ongoing_internships,
            "total_companies": total_companies,
            "deployments": recent_deployments,
        }

        return render(request, "app/coordinator_dahsboard.html", context)

    elif user.role == User.Role.SUPERVISOR:
        supervisor_profile = user.supervisor_profile

        pending_logs = DailyLog.objects.filter(
            internship__supervisor=supervisor_profile, is_verified=False
        ).order_by("date")

        my_internships = Internship.objects.filter(
            supervisor=supervisor_profile, status="ongoing"
        )

        context = {
            "supervisor": supervisor_profile,
            "pending_logs": pending_logs,
            "my_internships": my_internships,
        }

        return render(request, "app/supervisor_dashboard.html", context)

    return render(request, "app/error_dashboard.html")


@login_required
def student_profile_update(request):
    profile = request.user.student_profile

    if request.method == "POST":
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("dashboard")
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, "app/student_profile_update.html", {"form": form})


@login_required
def add_daily_log(request):
    active_internship = Internship.objects.filter(
        student__user=request.user, status="ongoing"
    ).first()

    if not active_internship:
        messages.error(request, "You do not have an active internship.")
        return redirect("dashboard")

    if request.method == "POST":
        form = DailyLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.internship = active_internship
            log.save()
            messages.success(request, "Time log submitted successfully!")
    else:
        form = DailyLogForm()

    return render(request, "app/add_daily_log.html", {"form": form})


@login_required
def approve_log(request, log_id):
    log = get_object_or_404(DailyLog, id=log_id)

    if request.user.supervisor_profile != log.internship.supervisor:
        messages.error(request, "You are not authorized to approve this log.")
        return redirect("dashboard")

    log.is_verified = True
    log.save()

    messages.success(
        request, f"Log for {log.internship.student.user.first_name} approved."
    )
    return redirect("dashboard")


@login_required
def evaluate_student(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)

    if (
        not hasattr(request.user, "supervisor_profile")
        or internship.supervisor != request.user.supervisor_profile
    ):
        messages.error(request, "You are not authorized to evaluate this student.")
        return redirect("dashboard")

    if request.method == "POST":
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.internship = internship
            evaluation.evaluator = request.user
            evaluation.evaluator_role = "supervisor"
            evaluation.save()

            messages.success(
                request,
                f"Evaluation submitted for {internship.student.user.first_name}.",
            )
            return redirect("dashboard")

    else:
        form = EvaluationForm()

    return render(
        request, "app/evaluate_student.html", {"form": form, "internship": internship}
    )


@login_required
def upload_document(request):
    if not hasattr(request.user, "student_profile"):
        return redirect("dashboard")

    active_internship = Internship.objects.filter(
        student=request.user.student_profile, status="ongoing"
    ).first()

    if not active_internship:
        messages.error(
            request, "You must have an active internship to upload documents."
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = StudentReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.internship = active_internship
            report.save()

            messages.success(request, "Document uploaded successfully!")
            return redirect("dashboard")

    else:
        form = StudentReportForm()

    existing_reports = active_internship.student_reports.all().order_by("-submitted_at")

    return render(
        request,
        "app/upload_document.html",
        {"form": form, "existing_reports": existing_reports},
    )

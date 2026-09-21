from datetime import timedelta

from mimetypes import guess_type

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CompanyForm,
    CoordinatorProfileForm,
    DailyLogForm,
    EvaluationForm,
    InternshipDeploymentForm,
    RegistrationForm,
    StudentProfileForm,
    StudentReportForm,
    SupervisorProfileForm,
)
from .models import (
    Company,
    CoordinatorProfile,
    DailyLog,
    Evaluation,
    Internship,
    StudentProfile,
    StudentReport,
    SupervisorProfile,
    User,
)
from .permissions import (
    can_access_internship,
    can_manage_internship,
    is_coordinator,
    is_student,
    is_supervisor,
)
from .utils import render_to_pdf


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = RegistrationForm()

    return render(request, "app/register.html", {"form": form})


@login_required
def dashboard_view(request):
    user = request.user

    if is_student(user):
        student_profile = getattr(user, "student_profile", None)
        if student_profile is None:
            messages.error(request, "Your student profile is missing.")
            return redirect("logout")

        active_internship = (
            Internship.objects.select_related("company", "supervisor__user")
            .filter(student=student_profile, status="ongoing")
            .first()
        )

        total_hours = 0
        recent_logs = []
        required_hours = 0
        completion_percent = 0
        remaining_hours = 0
        days_remaining = 0
        documents_count = 0
        has_evaluation = False

        if active_internship:
            documents_count = active_internship.student_reports.count()
            required_hours = active_internship.required_hours
            hours_data = active_internship.daily_logs.filter(
                is_verified=True
            ).aggregate(Sum("hours_rendered"))
            total_hours = hours_data["hours_rendered__sum"] or 0

            if required_hours > 0:
                completion_percent = min(
                    (float(total_hours) / required_hours) * 100,
                    100,
                )

            remaining_hours = max(required_hours - total_hours, 0)
            days_remaining = max(
                (active_internship.end_date - timezone.localdate()).days,
                0,
            )

            recent_logs = active_internship.daily_logs.order_by("-date")[:5]
            has_evaluation = active_internship.has_evaluation

        return render(
            request,
            "app/student_dashboard.html",
            {
                "profile": student_profile,
                "internship": active_internship,
                "total_hours": total_hours,
                "required_hours": required_hours,
                "completion_percent": round(completion_percent, 1),
                "remaining_hours": remaining_hours,
                "days_remaining": days_remaining,
                "recent_logs": recent_logs,
                "documents_uploaded": documents_count,
                "has_evaluation": has_evaluation,
            },
        )

    if is_coordinator(user):
        coordinator_profile = getattr(user, "coordinator_profile", None)
        if coordinator_profile is None:
            return redirect("complete_coordinator_profile")

        current_school = coordinator_profile.school

        school_internships = Internship.objects.filter(
            student__school=current_school,
            company__school=current_school,
        )

        total_students = StudentProfile.objects.filter(
            school=current_school
        ).count()
        ongoing_internships = school_internships.filter(
            status="ongoing"
        ).count()
        completed_internships = school_internships.filter(
            status="completed"
        ).count()
        total_companies = Company.objects.filter(
            school=current_school
        ).count()
        submitted_documents = StudentReport.objects.filter(
            internship__student__school=current_school,
            internship__company__school=current_school,
        ).count()
        pending_evaluations = school_internships.filter(
            status="ongoing"
        ).exclude(
            evaluations__evaluator_role="supervisor"
        ).count()

        recent_deployments = (
            school_internships
            .select_related(
                "student__user",
                "company",
                "supervisor__user",
            )
            .prefetch_related("daily_logs")
            .order_by("-start_date", "-id")[:12]
        )

        for internship in recent_deployments:
            approved_hours = sum(
                (
                    log.hours_rendered or 0
                    for log in internship.daily_logs.all()
                    if log.is_verified
                ),
                0,
            )
            internship.approved_hours = approved_hours
            internship.progress_percent = (
                min(
                    round((float(approved_hours) / internship.required_hours) * 100, 1),
                    100,
                )
                if internship.required_hours
                else 0
            )

        return render(
            request,
            "app/coordinator_dahsboard.html",
            {
                "total_students": total_students,
                "ongoing_internships": ongoing_internships,
                "completed_internships": completed_internships,
                "total_companies": total_companies,
                "submitted_documents": submitted_documents,
                "pending_evaluations": pending_evaluations,
                "deployments": recent_deployments,
                "current_school": current_school,
            },
        )

    if is_supervisor(user):
        supervisor_profile = getattr(user, "supervisor_profile", None)
        if supervisor_profile is None:
            return redirect("complete_supervisor_profile")

        my_internships = (
            Internship.objects.select_related("student__user", "company")
            .prefetch_related("daily_logs")
            .filter(supervisor=supervisor_profile, status="ongoing")
            .order_by("start_date", "id")
        )

        pending_logs = (
            DailyLog.objects.select_related(
                "internship__student__user",
                "internship__company",
            )
            .filter(
                internship__supervisor=supervisor_profile,
                is_verified=False,
            )
            .order_by("date", "id")
        )

        pending_logs_count = pending_logs.count()
        pending_hours = sum(
            (log.hours_rendered or 0 for log in pending_logs),
            0,
        )
        pending_evaluations = 0

        for internship in my_internships:
            approved_hours = sum(
                (
                    log.hours_rendered or 0
                    for log in internship.daily_logs.all()
                    if log.is_verified
                ),
                0,
            )
            internship.approved_hours = approved_hours
            internship.progress_percent = (
                min(
                    round(
                        (float(approved_hours) / internship.required_hours) * 100,
                        1,
                    ),
                    100,
                )
                if internship.required_hours
                else 0
            )

            if not internship.has_evaluation:
                pending_evaluations += 1

        total_approved_hours = sum(
            (internship.approved_hours for internship in my_internships),
            0,
        )

        return render(
            request,
            "app/supervisor_dashboard.html",
            {
                "supervisor": supervisor_profile,
                "pending_logs": pending_logs[:10],
                "pending_logs_count": pending_logs_count,
                "pending_hours": pending_hours,
                "my_internships": my_internships,
                "pending_evaluations": pending_evaluations,
                "total_approved_hours": total_approved_hours,
            },
        )

    return render(request, "app/error_dashboard.html")


@login_required
def student_profile_update(request):
    if not is_student(request.user):
        return redirect("dashboard")

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
def complete_coordinator_profile(request):
    if not is_coordinator(request.user):
        return redirect("dashboard")

    if hasattr(request.user, "coordinator_profile"):
        return redirect("dashboard")

    if request.method == "POST":
        form = CoordinatorProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Coordinator profile set up!")
            return redirect("dashboard")
    else:
        form = CoordinatorProfileForm()

    return render(request, "app/complete_coordinator_profile.html", {"form": form})


@login_required
def add_daily_log(request):
    if not is_student(request.user):
        return redirect("dashboard")

    active_internship = (
        Internship.objects.select_related("student")
        .filter(student__user=request.user, status="ongoing")
        .first()
    )

    if not active_internship:
        messages.error(request, "You do not have an active internship.")
        return redirect("dashboard")

    if request.method == "POST":
        form = DailyLogForm(
            request.POST,
            internship=active_internship,
            instance=DailyLog(internship=active_internship),
        )
        if form.is_valid():
            log = form.save()
            messages.success(request, "Time log submitted successfully!")
            return redirect("dashboard")
    else:
        form = DailyLogForm(internship=active_internship)

    return render(request, "app/add_daily_log.html", {"form": form})


@login_required
@require_POST
def approve_log(request, log_id):
    if not is_supervisor(request.user):
        messages.error(request, "Only assigned supervisors can approve daily logs.")
        return redirect("dashboard")

    log = get_object_or_404(
        DailyLog.objects.select_related("internship__student__user"),
        id=log_id,
    )

    if not can_manage_internship(request.user, log.internship):
        messages.error(request, "You are not authorized to approve this log.")
        return redirect("dashboard")

    if log.is_verified:
        messages.info(request, "This log has already been approved.")
        return redirect("dashboard")

    log.is_verified = True
    log.save(update_fields=["is_verified"])

    messages.success(
        request,
        f"Log for {log.internship.student.user.first_name} approved.",
    )
    return redirect("dashboard")


@login_required
def evaluate_student(request, internship_id):
    internship = get_object_or_404(
        Internship.objects.select_related(
            "student__user",
            "supervisor__company",
        ),
        id=internship_id,
    )

    if not can_manage_internship(request.user, internship) or not is_supervisor(
        request.user
    ):
        messages.error(request, "You are not authorized to evaluate this student.")
        return redirect("dashboard")

    existing_evaluation = Evaluation.objects.filter(
        internship=internship,
        evaluator_role="supervisor",
    ).first()

    if existing_evaluation:
        messages.warning(
            request,
            "You have already submitted an evaluation for this student.",
        )
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
        request,
        "app/evaluate_student.html",
        {"form": form, "internship": internship},
    )


@login_required
def upload_document(request):
    if not is_student(request.user):
        return redirect("dashboard")

    active_internship = (
        Internship.objects.select_related("company")
        .filter(student=request.user.student_profile, status="ongoing")
        .first()
    )

    if not active_internship:
        messages.error(
            request,
            "You must have an active internship to upload documents.",
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

    existing_reports = active_internship.student_reports.order_by("-submitted_at")

    return render(
        request,
        "app/upload_document.html",
        {"form": form, "existing_reports": existing_reports},
    )


@login_required
def download_document(request, report_id):
    report = get_object_or_404(
        StudentReport.objects.select_related(
            "internship__student__user",
            "internship__company",
            "internship__supervisor",
            "internship__coordinator",
        ),
        id=report_id,
    )

    if not can_access_internship(request.user, report.internship):
        messages.error(request, "You are not authorized to access this document.")
        return redirect("dashboard")

    if not report.file:
        messages.error(request, "This document is no longer available.")
        return redirect("dashboard")

    content_type, _ = guess_type(report.file.name)
    try:
        file_handle = report.file.open("rb")
    except OSError:
        messages.error(request, "The requested document could not be opened.")
        return redirect("dashboard")

    return FileResponse(
        file_handle,
        as_attachment=False,
        filename=report.title,
        content_type=content_type or "application/octet-stream",
    )


@login_required
def coordinator_student_detail(request, internship_id):
    internship = get_object_or_404(
        Internship.objects.select_related(
            "student__user",
            "company",
            "supervisor__user",
            "coordinator__user",
        ),
        id=internship_id,
    )

    if not is_coordinator(request.user) or not can_access_internship(
        request.user, internship
    ):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    documents = internship.student_reports.order_by("-submitted_at")
    recent_logs = internship.daily_logs.order_by("-date")[:10]
    approved_hours = (
        internship.daily_logs.filter(is_verified=True).aggregate(
            Sum("hours_rendered")
        )["hours_rendered__sum"]
        or 0
    )
    total_logs = internship.daily_logs.count()
    pending_logs = internship.daily_logs.filter(is_verified=False).count()
    progress_percent = (
        min(
            round((float(approved_hours) / internship.required_hours) * 100, 1),
            100,
        )
        if internship.required_hours
        else 0
    )
    supervisor_evaluation = (
        internship.evaluations.filter(evaluator_role="supervisor")
        .select_related("evaluator")
        .first()
    )
    coordinator_evaluation = (
        internship.evaluations.filter(evaluator_role="coordinator")
        .select_related("evaluator")
        .first()
    )

    return render(
        request,
        "app/coordinator_student_detail.html",
        {
            "internship": internship,
            "student": internship.student,
            "documents": documents,
            "recent_logs": recent_logs,
            "approved_hours": approved_hours,
            "progress_percent": progress_percent,
            "total_logs": total_logs,
            "pending_logs": pending_logs,
            "supervisor_evaluation": supervisor_evaluation,
            "coordinator_evaluation": coordinator_evaluation,
        },
    )


@login_required
def generate_dtr_pdf(request, internship_id):
    internship = get_object_or_404(
        Internship.objects.select_related(
            "student__user",
            "company",
            "supervisor__user",
        ),
        id=internship_id,
    )

    if not can_access_internship(request.user, internship):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    logs = internship.daily_logs.filter(is_verified=True).order_by("date")
    total_hours = logs.aggregate(Sum("hours_rendered"))["hours_rendered__sum"] or 0

    return render_to_pdf(
        "app/pdf/dtr_template.html",
        {
            "internship": internship,
            "logs": logs,
            "total_hours": total_hours,
            "generated_at": timezone.now(),
        },
    )


@login_required
def student_evaluation_detail(request):
    if not is_student(request.user):
        return redirect("dashboard")

    internship = (
        Internship.objects.select_related("company")
        .filter(
            student=request.user.student_profile,
            status="ongoing",
        )
        .first()
    )

    if not internship:
        messages.error(request, "No active internship found.")
        return redirect("dashboard")

    evaluation = (
        Evaluation.objects.select_related("evaluator")
        .filter(
            internship=internship,
            evaluator_role="supervisor",
        )
        .first()
    )

    if not evaluation:
        messages.warning(
            request,
            "Your supervisor has not submitted an evaluation yet.",
        )
        return redirect("dashboard")

    return render(
        request,
        "app/student_evaluation_detail.html",
        {
            "evaluation": evaluation,
            "internship": internship,
        },
    )


@login_required
def coordinator_deploy_intern(request):
    if not is_coordinator(request.user):
        return redirect("dashboard")

    coordinator_profile = getattr(request.user, "coordinator_profile", None)
    if coordinator_profile is None:
        return redirect("complete_coordinator_profile")

    if request.method == "POST":
        form = InternshipDeploymentForm(
            request.POST,
            school=coordinator_profile.school,
        )
        if form.is_valid():
            internship = form.save(commit=False)
            internship.coordinator = coordinator_profile
            internship.status = "ongoing"

            estimated_days = max(
                int((internship.required_hours + 7) / 8) + 20,
                1,
            )
            internship.end_date = internship.start_date + timedelta(days=estimated_days)
            internship.save()

            messages.success(
                request,
                f"Successfully deployed {internship.student.user.get_full_name()}!",
            )
            return redirect("dashboard")
    else:
        form = InternshipDeploymentForm(school=coordinator_profile.school)

    return render(
        request,
        "app/coordinator_deploy_intern.html",
        {"form": form},
    )


@login_required
def coordinator_add_company(request):
    if not is_coordinator(request.user):
        return redirect("dashboard")

    coordinator_profile = getattr(request.user, "coordinator_profile", None)
    if coordinator_profile is None:
        return redirect("complete_coordinator_profile")

    if request.method == "POST":
        form = CompanyForm(
            request.POST,
            school=coordinator_profile.school,
        )
        if form.is_valid():
            company = form.save(commit=False)
            company.school = coordinator_profile.school
            company.save()
            messages.success(request, f"Successfully added {company.name}!")
            return redirect("dashboard")
    else:
        form = CompanyForm(school=coordinator_profile.school)

    return render(request, "app/coordinator_add_company.html", {"form": form})


@login_required
def complete_supervisor_profile(request):
    if not is_supervisor(request.user):
        return redirect("dashboard")

    if hasattr(request.user, "supervisor_profile"):
        return redirect("dashboard")

    if request.method == "POST":
        form = SupervisorProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Profile completed successfully!")
            return redirect("dashboard")
    else:
        form = SupervisorProfileForm()

    return render(request, "app/complete_supervisor_profile.html", {"form": form})


@login_required
def get_supervisors_for_company(request):
    if not is_coordinator(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    coordinator_profile = getattr(request.user, "coordinator_profile", None)
    if coordinator_profile is None:
        return JsonResponse(
            {"detail": "Coordinator profile required"},
            status=403,
        )

    company_id = request.GET.get("company_id")
    if not company_id:
        return JsonResponse([], safe=False)

    supervisors = (
        SupervisorProfile.objects.filter(
            company_id=company_id,
            company__school=coordinator_profile.school,
        )
        .select_related("user", "company")
        .order_by("user__last_name", "user__first_name")
    )

    return JsonResponse(
        [
            {
                "id": supervisor.id,
                "name": f"{supervisor.user.get_full_name()} ({supervisor.company.name})",
            }
            for supervisor in supervisors
        ]
    )

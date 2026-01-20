from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from .models import *
from .forms import *
from .utils import render_to_pdf

# Create your views here.


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
        has_evaluation = False

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
            has_evaluation = Evaluation.objects.filter(
                internship=active_internship
            ).exists()

        context = {
            "profile": student_profile,
            "internship": active_internship,
            "total_hours": total_hours,
            "required_hours": required_hours,
            "completion_percent": round(completion_percent, 1),
            "recent_logs": recent_logs,
            "documents_uploaded": documents_count,
            "has_evaluation": has_evaluation,
        }

        return render(request, "app/student_dashboard.html", context)

    elif user.role == User.Role.COORDINATOR:
        if not hasattr(user, "coordinator_profile"):
            return redirect("complete_coordinator_profile")

        coordinator_profile = user.coordinator_profile

        current_school = coordinator_profile.school

        total_students = StudentProfile.objects.filter(school=current_school).count()

        ongoing_internships = Internship.objects.filter(
            status="ongoing", student__school=current_school
        ).count()

        total_companies = Company.objects.filter(school=current_school).count()

        recent_deployments = (
            Internship.objects.select_related("student__user", "company")
            .filter(student__school=current_school)
            .order_by("-start_date")
        )

        context = {
            "total_students": total_students,
            "ongoing_internships": ongoing_internships,
            "total_companies": total_companies,
            "deployments": recent_deployments,
            "current_school": current_school,
        }

        return render(request, "app/coordinator_dahsboard.html", context)

    elif user.role == User.Role.SUPERVISOR:
        if not hasattr(user, "supervisor_profile"):
            return redirect("complete_supervisor_profile")

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
def complete_coordinator_profile(request):
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
            return redirect("dashboard")
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

    if Evaluation.objects.filter(internship=internship).exists():
        messages.warning(
            request, "You have already submitted an evaluation for this student."
        )
        return redirect("dashboard")

    supervisor_school = request.user.supervisor_profile.company.school
    student_school = internship.student.school

    if supervisor_school != student_school:
        messages.error(
            request, "Access Denied: This student belongs to a different school."
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


@login_required
def coordinator_student_detail(request, internship_id):
    if request.user.role != User.Role.COORDINATOR:
        messages.error(request, "Access Denied.")
        return redirect("dashboard")

    internship = get_object_or_404(Internship, id=internship_id)

    documents = internship.student_reports.all().order_by("-submitted_at")
    recent_logs = internship.daily_logs.all().order_by("-date")[:10]
    total_hours = internship.daily_logs.filter(is_verified=True).aggregate(
        Sum("hours_rendered")
    )
    approved_hours = total_hours["hours_rendered__sum"] or 0

    context = {
        "internship": internship,
        "student": internship.student,
        "documents": documents,
        "recent_logs": recent_logs,
        "approved_hours": approved_hours,
    }
    return render(request, "app/coordinator_student_detail.html", context)


@login_required
def generate_dtr_pdf(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)

    if (
        request.user != internship.student.user
        and request.user.role != User.Role.COORDINATOR
        and request.user.role != User.Role.SUPERVISOR
    ):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    logs = internship.daily_logs.filter(is_verified=True).order_by("date")
    total_data = logs.aggregate(Sum("hours_rendered"))
    total_hours = total_data["hours_rendered__sum"] or 0

    context = {
        "internship": internship,
        "logs": logs,
        "total_hours": total_hours,
        "generated_at": datetime.now(),
    }

    return render_to_pdf("app/pdf/dtr_template.html", context)


@login_required
def student_evaluation_detail(request):
    if request.user.role != User.Role.STUDENT:
        return redirect("dashboard")

    internship = Internship.objects.filter(
        student=request.user.student_profile, status="ongoing"
    ).first()

    if not internship:
        messages.error(request, "No active internship found.")
        return redirect("dashboard")

    evaluation = Evaluation.objects.filter(internship=internship).first()

    if not evaluation:
        messages.warning(
            request, "Your supervisor has not submitted an evaluation yet."
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
    if request.user.role != User.Role.COORDINATOR:
        return redirect("dashboard")

    try:
        my_school = request.user.coordinator_profile.school
    except AttributeError:
        return redirect("complete_coordinator_profile")

    if request.method == "POST":
        form = InternshipDeploymentForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            if student.school != my_school:
                messages.error(
                    request, "You cannot deploy a student from another school."
                )
                return redirect("dashboard")

            internship = form.save(commit=False)
            internship.status = "ongoing"

            estimated_days = int(internship.required_hours / 8) + 20
            if internship.start_date:
                internship.end_date = internship.start_date + timedelta(
                    days=estimated_days
                )
            else:
                internship.end_date = datetime.now().date() + timedelta(days=90)

            internship.save()

            messages.success(
                request,
                f"Successfully deployed {internship.student.user.get_full_name()}!",
            )
            return redirect("dashboard")
    else:
        form = InternshipDeploymentForm()

        busy_student_ids = Internship.objects.filter(status="ongoing").values_list(
            "student_id", flat=True
        )

        form.fields["student"].queryset = StudentProfile.objects.filter(
            school=my_school
        ).exclude(id__in=busy_student_ids)

        form.fields["company"].queryset = Company.objects.filter(school=my_school)

    return render(request, "app/coordinator_deploy_intern.html", {"form": form})


@login_required
def coordinator_add_company(request):
    if request.user.role != User.Role.COORDINATOR:
        return redirect("dashboard")

    try:
        my_school = request.user.coordinator_profile.school
    except AttributeError:
        return redirect("complete_coordinator_profile")

    if request.method == "POST":
        form = CompanyForm(request.POST, school=my_school)
        if form.is_valid():
            company = form.save(commit=False)
            company.school = my_school
            company.save()
            messages.success(request, f"Successfully added {company.name}!")
            return redirect("dashboard")
    else:
        form = CompanyForm(school=my_school)

    return render(request, "app/coordinator_add_company.html", {"form": form})


@login_required
def complete_supervisor_profile(request):
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
def complete_coordinator_profile(request):
    if hasattr(request.user, "coordinator_profile"):
        return redirect("dashboard")

    if request.method == "POST":
        form = CoordinatorProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            messages.success(request, f"Welcome to {profile.school}!")
            return redirect("dashboard")
    else:
        form = CoordinatorProfileForm()

    return render(request, "app/complete_coordinator_profile.html", {"form": form})


@login_required
def get_supervisors_for_company(request):
    company_id = request.GET.get("company_id")

    if not company_id:
        return JsonResponse([], safe=False)

    try:
        my_school = request.user.coordinator_profile.school
    except:
        return JsonResponse([], safe=False)

    supervisors = SupervisorProfile.objects.filter(
        company_id=company_id, company__school=my_school
    ).select_related("user")

    data = []
    for s in supervisors:
        data.append(
            {"id": s.id, "name": f"{s.user.get_full_name()} ({s.company.name})"}
        )

    return JsonResponse(data, safe=False)

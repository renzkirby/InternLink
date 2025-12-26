from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentRegistrationForm, User, StudentProfileForm


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
        return render(
            request, "app/student_dashboard.html", {"profile": user.student_profile}
        )
    elif user.role == User.Role.COORDINATOR:
        return render(request, "app/coordinator_dahsboard.html")
    elif user.role == User.Role.SUPERVISOR:
        return render(request, "app/supervisor_dashboard.html")

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

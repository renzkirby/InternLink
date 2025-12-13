from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import login
from .forms import StudentRegistrationForm


# Create your views here.
class DashboardView(TemplateView):
    template_name = "app/dashboard.html"


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

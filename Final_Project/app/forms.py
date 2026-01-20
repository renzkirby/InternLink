from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    User,
    StudentProfile,
    DailyLog,
    Evaluation,
    StudentReport,
    Internship,
    SupervisorProfile,
    Company,
    CoordinatorProfile,
)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, help_text="Required. Use a valid email address."
    )
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
        return user


class StudentProfileForm(forms.ModelForm):

    class Meta:
        model = StudentProfile
        fields = ["student_number", "school", "course", "year_level", "contact_number"]

        widgets = {
            "student_number": forms.TextInput(attrs={"class": "form-control"}),
            "course": forms.TextInput(attrs={"class": "form-control"}),
            "school": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Main Campus"}
            ),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
        }


class CoordinatorProfileForm(forms.ModelForm):
    class Meta:
        model = CoordinatorProfile
        fields = ["school"]
        widgets = {"school": forms.TextInput(attrs={"class": "form-control"})}


class DailyLogForm(forms.ModelForm):
    class Meta:
        model = DailyLog
        fields = ["date", "time_in", "time_out", "work_description"]

        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "time_in": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "time_out": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "work_description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What did you accomplish today?"}
            ),
        }


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            "period_start",
            "period_end",
            "punctuality",
            "work_quality",
            "communication",
            "teamwork",
            "initiative",
            "comments",
        ]

        widgets = {
            "period_start": forms.DateInput(
                attrs={"type": "date", "class": "form_control"}
            ),
            "period_end": forms.DateInput(
                attrs={"type": "date", "class": "form_control"}
            ),
            "comments": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Feedback for the student...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]
        score_fields = [
            "punctuality",
            "work_quality",
            "communication",
            "teamwork",
            "initiative",
        ]
        for field in score_fields:
            self.fields[field].widget = forms.RadioSelect(choices=SCORE_CHOICES)


class StudentReportForm(forms.ModelForm):
    class Meta:
        model = StudentReport
        fields = ["report_type", "title", "week_number", "file"]

        widgets = {
            "report_type": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Week 1 Accomplishment Report",
                }
            ),
            "week_number": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional (for Weekly Reports)",
                }
            ),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class InternshipDeploymentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.all(),
        label="Select Student",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    supervisor = forms.ModelChoiceField(
        queryset=SupervisorProfile.objects.all(),
        label="Select Supervisor",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label="Select Company",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Internship
        fields = [
            "student",
            "supervisor",
            "company",
            "required_hours",
            "start_date",
        ]

        widgets = {
            "company": forms.Select(attrs={"class": "form-select"}),
            "course": forms.TextInput(attrs={"class": "form-control"}),
            "required_hours": forms.NumberInput(
                attrs={"class": "form-control", "value": 600}
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def clean_student(self):
        student = self.cleaned_data.get("student")
        if Internship.objects.filter(student=student, status="ongoing").exists():
            raise forms.ValidationError(
                "This student already has an active internship."
            )
        return student


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "address",
            "contact_person",
            "contact_number",
            "contact_email",
        ]

        wdigets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. TechSolutions Inc.",
                }
            ),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "contact_mail": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if Company.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This company already exists.")
        return name


class SupervisorProfileForm(forms.ModelForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        empty_label="Select your Company",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = SupervisorProfile
        fields = ["company"]

    def __init__(self, *args, **kwargs):
        super(SupervisorProfileForm, self).__init__(*args, **kwargs)
        self.fields["company"].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.school})"
        )


class CoordinatorProfileForm(forms.ModelForm):
    class Meta:
        model = CoordinatorProfile
        fields = ["school"]

        widgets = {
            "school": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cavite State University - Bacoor Campus",
                }
            ),
        }

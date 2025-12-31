from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, StudentProfile, DailyLog, Evaluation, StudentReport


class StudentRegistrationForm(UserCreationForm):
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
        fields = ["student_number", "course", "year_level", "contact_number"]

        widgets = {
            "student_number": forms.TextInput(attrs={"placeholder": "e.g. 2023-0001"}),
            "course": forms.TextInput(
                attrs={"placeholder": "e.g. BS Information Technology"}
            ),
        }


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

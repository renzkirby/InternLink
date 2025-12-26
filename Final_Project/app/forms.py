from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, StudentProfile, DailyLog


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

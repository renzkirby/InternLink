from pathlib import Path

from django import forms
from django.contrib.auth.forms import UserCreationForm

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


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Required. Use a valid email address.",
    )
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = User.Role.STUDENT

        if commit:
            user.save()

        return user


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["student_number", "course", "year_level", "contact_number"]
        widgets = {
            "student_number": forms.TextInput(attrs={"class": "form-control"}),
            "course": forms.TextInput(attrs={"class": "form-control"}),
            "year_level": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 6}
            ),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
        }


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
            )
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
                attrs={
                    "rows": 4,
                    "class": "form-control",
                    "placeholder": "Describe what you accomplished today...",
                }
            ),
        }

    def __init__(self, *args, internship=None, **kwargs):
        self.internship = internship
        super().__init__(*args, **kwargs)

        if self.internship:
            self.instance.internship = self.internship

    def clean(self):
        cleaned_data = super().clean()

        if self.internship:
            log_date = cleaned_data.get("date")
            if log_date and log_date > self.internship.end_date:
                self.add_error(
                    "date",
                    "The selected date is outside the internship period.",
                )

        return cleaned_data


class DailyLogReviewForm(forms.Form):
    remarks = forms.CharField(
        label="Feedback",
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Explain what needs to be corrected...",
            }
        ),
    )


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
                attrs={"type": "date", "class": "form-control"}
            ),
            "period_end": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "comments": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                    "placeholder": "Feedback for the student...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        score_choices = [(i, str(i)) for i in range(1, 6)]
        for field_name in (
            "punctuality",
            "work_quality",
            "communication",
            "teamwork",
            "initiative",
        ):
            self.fields[field_name].widget = forms.RadioSelect(choices=score_choices)


class StudentReportForm(forms.ModelForm):
    MAX_FILE_SIZE = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

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
                    "min": 1,
                }
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.doc,.docx",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get("report_type")
        week_number = cleaned_data.get("week_number")

        if report_type == "weekly_report" and not week_number:
            self.add_error(
                "week_number",
                "Week number is required for weekly reports.",
            )
        elif report_type != "weekly_report" and week_number:
            self.add_error(
                "week_number",
                "Week number should only be provided for weekly reports.",
            )

        return cleaned_data

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")
        if not uploaded_file:
            return uploaded_file

        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                "Unsupported file type. Upload a PDF, DOC, or DOCX file."
            )

        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError(
                "File is too large. Maximum allowed size is 5 MB."
            )

        return uploaded_file


class InternshipDeploymentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(),
        label="Select Student",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    supervisor = forms.ModelChoiceField(
        queryset=SupervisorProfile.objects.none(),
        label="Select Supervisor",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(),
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
            "required_hours": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)

        if not school:
            return

        busy_student_ids = Internship.objects.filter(
            status="ongoing"
        ).values_list("student_id", flat=True)

        self.fields["student"].queryset = StudentProfile.objects.filter(
            school=school
        ).exclude(id__in=busy_student_ids)

        self.fields["company"].queryset = Company.objects.filter(school=school)

        company_id = self.data.get("company") if self.is_bound else None
        if company_id:
            self.fields["supervisor"].queryset = SupervisorProfile.objects.filter(
                company_id=company_id,
                company__school=school,
            ).select_related("user", "company")

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        company = cleaned_data.get("company")
        supervisor = cleaned_data.get("supervisor")

        if not self.school:
            raise forms.ValidationError(
                "A school context is required for internship deployment."
            )

        if student and student.school != self.school:
            self.add_error(
                "student",
                "You cannot deploy a student from another school.",
            )

        if company and company.school != self.school:
            self.add_error(
                "company",
                "You cannot assign a company from another school.",
            )

        if supervisor:
            if supervisor.company.school != self.school:
                self.add_error(
                    "supervisor",
                    "You cannot assign a supervisor from another school.",
                )
            elif company and supervisor.company_id != company.id:
                self.add_error(
                    "supervisor",
                    "The selected supervisor does not belong to the selected company.",
                )

        if student and Internship.objects.filter(
            student=student,
            status="ongoing",
        ).exists():
            self.add_error(
                "student",
                "This student already has an active internship.",
            )

        return cleaned_data


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
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. TechSolutions Inc.",
                }
            ),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, school=None, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get("name")

        if (
            self.school
            and Company.objects.filter(
                name__iexact=name,
                school=self.school,
            ).exists()
        ):
            raise forms.ValidationError(
                f"{name} is already a partner of {self.school}."
            )

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
        super().__init__(*args, **kwargs)
        self.fields["company"].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.school})"
        )

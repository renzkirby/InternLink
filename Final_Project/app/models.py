from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        COORDINATOR = "coordinator", "Coordinator"
        SUPERVISOR = "supervisor", "Supervisor"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    student_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    course = models.CharField(max_length=100, null=True, blank=True)
    year_level = models.IntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    school = models.CharField(
        max_length=100, default="Cavite State University - Bacoor Campus"
    )

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_number}"


class CoordinatorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coordinator_profile",
    )
    school = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Coordinator: {self.user.get_full_name()}"


class SupervisorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supervisor_profile",
    )
    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, related_name="supervisors"
    )
    position = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Supervisor: {self.user.get_full_name()} ({self.company.name})"


class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    school = models.CharField(
        max_length=100, default="Cavite State University - Bacoor Campus"
    )

    def __str__(self):
        return self.name


class Internship(models.Model):
    STATUS_CHOICES = [
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("terminated", "Terminated"),
        ("pending", "Pending"),
    ]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="internships"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="internships"
    )
    supervisor = models.ForeignKey(
        SupervisorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internships",
    )
    coordinator = models.ForeignKey(
        CoordinatorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internships",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    required_hours = models.PositiveIntegerField(default=600)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(status="ongoing"),
                name="unique_ongoing_internship_per_student",
            ),
            models.CheckConstraint(
                condition=Q(required_hours__gt=0),
                name="internship_required_hours_positive",
            ),
        ]

    def clean(self):
        errors = {}

        if self.required_hours is not None and self.required_hours <= 0:
            errors["required_hours"] = "Required hours must be greater than zero."

        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors["end_date"] = "End date must be on or after the start date."

        if self.student_id and self.company_id:
            if self.student.school != self.company.school:
                errors["company"] = (
                    "The student's school and company's school must match."
                )

        if self.supervisor_id and self.company_id:
            if self.supervisor.company_id != self.company_id:
                errors["supervisor"] = (
                    "The selected supervisor must belong to the selected company."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student.user.get_full_name()} @ {self.company.name}"

    @property
    def has_evaluation(self):
        return self.evaluations.exists()


class DailyLog(models.Model):
    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="daily_logs"
    )
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField()
    hours_rendered = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Total hours for the day",
        blank=True,
        null=True,
    )
    work_description = models.TextField(help_text="Summary of tasks accomplished")
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    REVIEW_STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("revision_requested", "Needs correction"),
    ]
    review_status = models.CharField(
        max_length=24,
        choices=REVIEW_STATUS_CHOICES,
        default="pending",
    )
    review_remarks = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["internship", "date"],
                name="unique_daily_log_per_internship_date",
            ),
        ]
        ordering = ["-date", "-created_at"]

    def clean(self):
        errors = {}

        if self.internship_id:
            if self.date:
                if self.date < self.internship.start_date:
                    errors["date"] = "The log date cannot be before the internship start date."
                elif self.date > self.internship.end_date:
                    errors["date"] = "The log date cannot be after the internship end date."
                elif self.date > timezone.localdate():
                    errors["date"] = "Future-dated work logs are not allowed."

            if self.date and self.internship_id:
                duplicate = DailyLog.objects.filter(
                    internship_id=self.internship_id, date=self.date
                ).exclude(pk=self.pk)
                if duplicate.exists():
                    errors["date"] = "A daily log already exists for this date."

        if self.time_in and self.time_out:
            if self.time_out <= self.time_in:
                errors["time_out"] = "Time out must be later than time in for a daily log."

            t1 = datetime.combine(date.min, self.time_in)
            t2 = datetime.combine(date.min, self.time_out)
            hours = Decimal((t2 - t1).total_seconds() / 3600)

            if hours > Decimal("16"):
                errors["time_out"] = "A daily log cannot exceed 16 rendered hours."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.time_in and self.time_out:
            t1 = datetime.combine(date.min, self.time_in)
            t2 = datetime.combine(date.min, self.time_out)
            diff = t2 - t1
            total_hours = Decimal(diff.total_seconds() / 3600).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            self.hours_rendered = total_hours

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.internship.student.user.get_full_name()} - {self.date}"


def student_report_upload_path(instance, filename):
    student_id = instance.internship.student.id
    if instance.report_type == "weekly_report" and instance.week_number:
        return f"reports/{student_id}/week_{instance.week_number}/{filename}"
    return f"reports/{student_id}/{instance.report_type}/{filename}"


class StudentReport(models.Model):
    REPORT_TYPES = [
        ("weekly_report", "Weekly Report"),
        ("narrative", "Narrative Report"),
        ("resume", "Resume/CV"),
        ("moa", "Memorandum of Agreement"),
        ("reflection", "Reflection Paper"),
        ("other", "Other"),
    ]

    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="student_reports"
    )
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=student_report_upload_path)
    week_number = models.PositiveIntegerField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    supervisor_remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.title} ({self.get_report_type_display()}) - "
            f"{self.internship.student.user.get_full_name()}"
        )


class Evaluation(models.Model):
    EVALUATOR_ROLES = [
        ("supervisor", "Supervisor"),
        ("coordinator", "Coordinator"),
    ]

    internship = models.ForeignKey(
        Internship, on_delete=models.CASCADE, related_name="evaluations"
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="evaluations_given",
    )
    evaluator_role = models.CharField(max_length=20, choices=EVALUATOR_ROLES)
    period_start = models.DateField()
    period_end = models.DateField()
    punctuality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    work_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    teamwork = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    initiative = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["internship", "evaluator_role"],
                name="unique_evaluation_per_role",
            )
        ]

    def clean(self):
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValidationError({"period_end": "Evaluation end date must be on or after the start date."})

    @property
    def total_score(self):
        return (
            self.punctuality
            + self.work_quality
            + self.communication
            + self.teamwork
            + self.initiative
        )

    @property
    def average_score(self):
        return self.total_score / 5.0

    def __str__(self):
        return (
            f"Evaluation for {self.internship.student.user.get_full_name()} "
            f"by {self.get_evaluator_role_display()}"
        )

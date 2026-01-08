from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import ROUND_HALF_UP, Decimal
from datetime import date, datetime, timedelta


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
        return f"Supervisor: {self.user.get_full_name()} ({(self.company.name)})"


class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class Internship(models.Model):
    student = models.ForeignKey(
        "StudentProfile", on_delete=models.CASCADE, related_name="internships"
    )

    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, related_name="internships"
    )

    supervisor = models.ForeignKey(
        "SupervisorProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internships",
    )

    coordinator = models.ForeignKey(
        "CoordinatorProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internships",
    )

    start_date = models.DateField()
    end_date = models.DateField()
    required_hours = models.PositiveIntegerField(default=240)
    status = models.CharField(
        max_length=20,
        choices=[
            ("ongoing", "Ongoing"),
            ("completed", "Completed"),
            ("terminated", "Terminated"),
            ("pending", "Pending"),
        ],
        default="pending",
    )

    def __str__(self):
        return f"{self.student.user.get_full_name()} @ {self.company.name}"

    @property
    def has_evaluation(self):
        return Evaluation.objects.filter(internship=self).exists()


class DailyLog(models.Model):
    internship = models.ForeignKey(
        "Internship", on_delete=models.CASCADE, related_name="daily_logs"
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

    def save(self, *args, **kwargs):
        if self.time_in and self.time_out:
            t1 = datetime.combine(date.min, self.time_in)
            t2 = datetime.combine(date.min, self.time_out)
            if t2 <= t1:
                t2 = t2 + timedelta(days=1)
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
        "Internship", on_delete=models.CASCADE, related_name="student_reports"
    )

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=student_report_upload_path)
    week_number = models.PositiveIntegerField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    supervisor_remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()}) - {self.internship.student.user.get_full_name()}"


class Evaluation(models.Model):
    EVALUATOR_ROLES = [
        ("supervisor", "Supervisor"),
        ("Coordinator", "Coordinator"),
    ]

    internship = models.ForeignKey(
        "Internship", on_delete=models.CASCADE, related_name="evaluations"
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
        return f"Evaluation for {self.internship.student.user.get_full_name()} by {self.evaluator_role.title()}"

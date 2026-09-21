from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Company,
    DailyLog,
    Internship,
    StudentProfile,
    SupervisorProfile,
    User,
)


class BackendIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student_user = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="StrongPass123!",
            first_name="Student",
            last_name="One",
            role=User.Role.STUDENT,
        )
        cls.supervisor_user = User.objects.create_user(
            username="supervisor1",
            email="supervisor@example.com",
            password="StrongPass123!",
            first_name="Supervisor",
            last_name="One",
            role=User.Role.SUPERVISOR,
        )

        cls.company = Company.objects.create(
            name="Acme Tech",
            address="Makati",
        )
        cls.supervisor = SupervisorProfile.objects.create(
            user=cls.supervisor_user,
            company=cls.company,
            position="IT Supervisor",
        )
        cls.student = cls.student_user.student_profile

    def test_public_registration_always_creates_student_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password1": "AnotherStrongPass123!",
                "password2": "AnotherStrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(
            StudentProfile.objects.filter(user=user).exists()
        )

    def test_internship_rejects_cross_school_company(self):
        self.company.school = "Another School"
        self.company.save(update_fields=["school"])

        internship = Internship(
            student=self.student,
            company=self.company,
            supervisor=self.supervisor,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            required_hours=600,
            status="ongoing",
        )

        with self.assertRaises(ValidationError):
            internship.full_clean()

    def test_daily_log_rejects_duplicate_date(self):
        internship = Internship.objects.create(
            student=self.student,
            company=self.company,
            supervisor=self.supervisor,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=30),
            required_hours=600,
            status="ongoing",
        )

        first = DailyLog.objects.create(
            internship=internship,
            date=date.today(),
            time_in=time(8, 0),
            time_out=time(17, 0),
            work_description="Completed assigned tasks.",
        )

        duplicate = DailyLog(
            internship=internship,
            date=first.date,
            time_in=time(9, 0),
            time_out=time(18, 0),
            work_description="Duplicate entry.",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_approve_log_requires_post(self):
        internship = Internship.objects.create(
            student=self.student,
            company=self.company,
            supervisor=self.supervisor,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            required_hours=600,
            status="ongoing",
        )
        log = DailyLog.objects.create(
            internship=internship,
            date=date.today(),
            time_in=time(8, 0),
            time_out=time(17, 0),
            work_description="Work completed.",
        )

        self.client.login(
            username="supervisor1",
            password="StrongPass123!",
        )
        response = self.client.get(reverse("approve_log", args=[log.id]))

        self.assertEqual(response.status_code, 405)
        log.refresh_from_db()
        self.assertFalse(log.is_verified)


class AuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student_user = User.objects.create_user(
            username="student1",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        cls.other_student_user = User.objects.create_user(
            username="student2",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        cls.supervisor_user = User.objects.create_user(
            username="supervisor1",
            password="StrongPass123!",
            role=User.Role.SUPERVISOR,
        )

        cls.student = cls.student_user.student_profile
        cls.other_student = cls.other_student_user.student_profile

        company = Company.objects.create(
            name="Acme Tech",
            address="Makati",
        )
        cls.supervisor = SupervisorProfile.objects.create(
            user=cls.supervisor_user,
            company=company,
            position="Supervisor",
        )

        cls.internship = Internship.objects.create(
            student=cls.student,
            company=company,
            supervisor=cls.supervisor,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            required_hours=600,
            status="ongoing",
        )

    def test_student_cannot_generate_another_students_dtr(self):
        self.client.login(
            username="student2",
            password="StrongPass123!",
        )
        response = self.client.get(
            reverse("generate_dtr_pdf", args=[self.internship.id])
        )

        self.assertRedirects(response, reverse("dashboard"))

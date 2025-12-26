from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Custom Fields", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Custom Fields", {"fields": ("role",)}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.register(CoordinatorProfile)
admin.site.register(SupervisorProfile)
admin.site.register(Company)
admin.site.register(Internship)
admin.site.register(StudentReport)
admin.site.register(DailyLog)
admin.site.register(Evaluation)

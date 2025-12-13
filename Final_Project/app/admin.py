from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin

admin.site.register(User, UserAdmin)
admin.site.register(StudentProfile)
admin.site.register(CoordinatorProfile)
admin.site.register(SupervisorProfile)
admin.site.register(Company)
admin.site.register(Internship)
admin.site.register(StudentReport)
admin.site.register(DailyLog)
admin.site.register(Evaluation)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import User, StudentProfile, CoordinatorProfile, SupervisorProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=instance)
            print(f"Created StudentProfile for {instance.username}")

        elif instance.role == User.Role.COORDINATOR:
            CoordinatorProfile.objects.create(user=instance)
            print(f"Created CoordinatorProfile for {instance.username}")

        elif instance.role == User.Role.SUPERVISOR:
            pass

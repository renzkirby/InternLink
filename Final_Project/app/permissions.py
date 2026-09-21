from .models import User, Internship


def is_student(user):
    return user.is_authenticated and user.role == User.Role.STUDENT


def is_coordinator(user):
    return user.is_authenticated and user.role == User.Role.COORDINATOR


def is_supervisor(user):
    return user.is_authenticated and user.role == User.Role.SUPERVISOR


def can_access_internship(user, internship):
    """Return whether the authenticated user may view this internship."""
    if not user.is_authenticated:
        return False

    if is_student(user):
        return internship.student.user_id == user.id

    if is_supervisor(user):
        profile = getattr(user, "supervisor_profile", None)
        return profile is not None and internship.supervisor_id == profile.id

    if is_coordinator(user):
        profile = getattr(user, "coordinator_profile", None)
        if profile is None:
            return False

        return (
            internship.student.school == profile.school
            and internship.company.school == profile.school
        )

    return False


def can_manage_internship(user, internship):
    """Return whether the user has workflow-management access to an internship."""
    if not user.is_authenticated:
        return False

    if is_supervisor(user):
        profile = getattr(user, "supervisor_profile", None)
        return profile is not None and internship.supervisor_id == profile.id

    if is_coordinator(user):
        return can_access_internship(user, internship)

    return False

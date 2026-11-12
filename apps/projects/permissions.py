from apps.organizations.models import Membership


def can_view_projects(membership):
    return membership is not None


def can_create_project(membership):
    return membership is not None


def can_manage_project(membership):
    return membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}

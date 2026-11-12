from .models import Membership


def can_manage_organization(membership):
    return membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}


def can_manage_members(membership):
    return can_manage_organization(membership)


def can_delete_organization(membership):
    return membership.role == Membership.Role.OWNER


def can_change_role(actor_membership, target_membership, new_role):
    if not can_manage_members(actor_membership):
        return False
    if target_membership.role == Membership.Role.OWNER:
        return False
    if new_role == Membership.Role.OWNER:
        return False
    if actor_membership.role == Membership.Role.ADMIN:
        return target_membership.role != Membership.Role.ADMIN
    return True

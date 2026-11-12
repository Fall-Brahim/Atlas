from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MembershipAddForm, MembershipRoleForm, OrganizationForm
from .models import Membership, Organization
from .permissions import (
    can_change_role,
    can_delete_organization,
    can_manage_members,
    can_manage_organization,
)


def _membership_or_404(request, slug):
    return get_object_or_404(
        Membership.objects.select_related('organization'),
        organization__slug=slug,
        user=request.user,
    )


@login_required
def organization_list(request):
    memberships = Membership.objects.filter(user=request.user).select_related('organization')
    return render(request, 'organizations/list.html', {'memberships': memberships})


@login_required
def organization_create(request):
    form = OrganizationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                organization = form.save()
                Membership.objects.create(
                    organization=organization,
                    user=request.user,
                    role=Membership.Role.OWNER,
                )
        except IntegrityError:
            form.add_error('name', 'An organization with this name already exists.')
        else:
            return redirect('organizations:detail', slug=organization.slug)
    return render(request, 'organizations/form.html', {'form': form, 'title': 'Create organization'})


@login_required
def organization_detail(request, slug):
    membership = _membership_or_404(request, slug)
    organization = membership.organization
    members = organization.memberships.select_related('user')
    add_member_form = (
        MembershipAddForm(organization=organization)
        if can_manage_members(membership)
        else None
    )
    return render(
        request,
        'organizations/detail.html',
        {
            'organization': organization,
            'membership': membership,
            'members': members,
            'add_member_form': add_member_form,
        },
    )


@require_POST
@login_required
def membership_add(request, slug):
    actor = _membership_or_404(request, slug)
    if not can_manage_members(actor):
        raise Http404

    form = MembershipAddForm(request.POST, organization=actor.organization)
    if form.is_valid():
        try:
            with transaction.atomic():
                Membership.objects.create(
                    organization=actor.organization,
                    user=form.user,
                    role=form.cleaned_data['role'],
                )
        except IntegrityError:
            messages.error(
                request,
                'This user is already a member of this organization.',
            )
        else:
            messages.success(request, 'Member added successfully.')
            return redirect('organizations:detail', slug=slug)
    else:
        messages.error(request, 'Please correct the errors below.')

    organization = actor.organization
    return render(
        request,
        'organizations/detail.html',
        {
            'organization': organization,
            'membership': actor,
            'members': organization.memberships.select_related('user'),
            'add_member_form': form,
        },
    )


@login_required
def organization_settings(request, slug):
    membership = _membership_or_404(request, slug)
    if not can_manage_organization(membership):
        raise Http404
    form = OrganizationForm(request.POST or None, instance=membership.organization)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('organizations:detail', slug=slug)
    return render(
        request,
        'organizations/form.html',
        {'form': form, 'title': 'Organization settings', 'organization': membership.organization},
    )


@require_POST
@login_required
def organization_delete(request, slug):
    membership = _membership_or_404(request, slug)
    if not can_delete_organization(membership):
        raise Http404
    try:
        membership.organization.delete()
    except ProtectedError:
        messages.error(
            request,
            'This organization cannot be deleted while it contains projects.',
        )
    return redirect('organizations:list')


@require_POST
@login_required
def membership_role(request, slug, membership_id):
    actor = _membership_or_404(request, slug)
    if not can_manage_members(actor):
        raise Http404
    target = get_object_or_404(
        Membership,
        pk=membership_id,
        organization=actor.organization,
    )
    previous_role = target.role
    allowed_roles = {Membership.Role.ADMIN, Membership.Role.MEMBER}
    form = MembershipRoleForm(request.POST, instance=target, allowed_roles=allowed_roles)
    is_valid = form.is_valid()
    if is_valid:
        target.role = previous_role
    if is_valid and can_change_role(actor, target, form.cleaned_data['role']):
        target.role = form.cleaned_data['role']
        form.save()
    return redirect('organizations:detail', slug=slug)


@require_POST
@login_required
def membership_remove(request, slug, membership_id):
    actor = _membership_or_404(request, slug)
    if not can_manage_members(actor):
        raise Http404
    target = get_object_or_404(
        Membership,
        pk=membership_id,
        organization=actor.organization,
    )
    if target.role != Membership.Role.OWNER and (
        actor.role == Membership.Role.OWNER or target.role == Membership.Role.MEMBER
    ):
        target.delete()
    return redirect('organizations:detail', slug=slug)


@require_POST
@login_required
def organization_leave(request, slug):
    membership = _membership_or_404(request, slug)
    if membership.role != Membership.Role.OWNER:
        membership.delete()
    return redirect('organizations:list')

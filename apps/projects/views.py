from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.organizations.models import Membership
from apps.templates_catalog.models import ApplicationTemplate

from .forms import ProjectForm
from .models import Project
from .permissions import can_create_project, can_manage_project, can_view_projects


def _membership_or_404(request, organization_slug):
    return get_object_or_404(
        Membership.objects.select_related('organization'),
        organization__slug=organization_slug,
        user=request.user,
    )


def _project_or_404(membership, project_slug):
    return get_object_or_404(
        Project,
        organization=membership.organization,
        slug=project_slug,
    )


@login_required
def project_list(request, organization_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_view_projects(membership):
        raise Http404
    projects = membership.organization.projects.all()
    return render(
        request,
        'projects/list.html',
        {
            'organization': membership.organization,
            'membership': membership,
            'projects': projects,
        },
    )


@login_required
def project_create(request, organization_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_create_project(membership):
        raise Http404
    initial = {}
    template_slug = request.GET.get('template', '').strip()
    if template_slug and request.method == 'GET':
        initial['template'] = get_object_or_404(
            ApplicationTemplate,
            slug=template_slug,
            is_active=True,
        )
    form = ProjectForm(
        request.POST or None,
        initial=initial,
        require_template=True,
    )
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                project = form.save(commit=False)
                project.organization = membership.organization
                project.created_by = request.user
                project.save()
        except IntegrityError:
            form.add_error(
                'name',
                'A project with this name already exists in this organization.',
            )
        else:
            messages.success(request, 'Project created successfully.')
            return redirect(
                'projects:detail',
                organization_slug=organization_slug,
                project_slug=project.slug,
            )
    return render(
        request,
        'projects/form.html',
        {
            'form': form,
            'organization': membership.organization,
            'title': 'Create project',
        },
    )


@login_required
def project_detail(request, organization_slug, project_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_view_projects(membership):
        raise Http404
    project = _project_or_404(membership, project_slug)
    return render(
        request,
        'projects/detail.html',
        {
            'organization': membership.organization,
            'membership': membership,
            'project': project,
        },
    )


@login_required
def project_edit(request, organization_slug, project_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_manage_project(membership):
        raise Http404
    project = _project_or_404(membership, project_slug)
    if project.status == Project.Status.ARCHIVED:
        raise Http404
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Project updated successfully.')
        return redirect(
            'projects:detail',
            organization_slug=organization_slug,
            project_slug=project.slug,
        )
    return render(
        request,
        'projects/form.html',
        {
            'form': form,
            'organization': membership.organization,
            'project': project,
            'title': 'Project settings',
        },
    )


@require_POST
@login_required
def project_archive(request, organization_slug, project_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_manage_project(membership):
        raise Http404
    project = _project_or_404(membership, project_slug)
    project.status = Project.Status.ARCHIVED
    project.save(update_fields=('status', 'updated_at'))
    messages.success(request, 'Project archived successfully.')
    return redirect(
        'projects:detail',
        organization_slug=organization_slug,
        project_slug=project.slug,
    )


@require_POST
@login_required
def project_restore(request, organization_slug, project_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_manage_project(membership):
        raise Http404
    project = _project_or_404(membership, project_slug)
    project.status = Project.Status.DRAFT
    project.save(update_fields=('status', 'updated_at'))
    messages.success(request, 'Project restored successfully.')
    return redirect(
        'projects:detail',
        organization_slug=organization_slug,
        project_slug=project.slug,
    )

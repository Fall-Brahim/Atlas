from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from apps.organizations.models import Membership
from apps.templates_catalog.generator import (
    StarterKitUnavailable,
    build_project_archive,
    has_starter_kit,
)
from apps.templates_catalog.models import ApplicationTemplate

from .forms import ProjectConfigurationForm, ProjectForm
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


def _active_template_or_404(reference):
    templates = ApplicationTemplate.objects.filter(is_active=True)
    if reference.isascii() and reference.isdecimal():
        if len(reference) > 19 or (
            len(reference) == 19 and reference > '9223372036854775807'
        ):
            raise Http404
        return get_object_or_404(templates, pk=int(reference))
    return get_object_or_404(templates, slug=reference)


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
def project_create_without_organization(request):
    organization_slug = request.GET.get('organization', '').strip()
    template_reference = request.GET.get('template', '').strip()
    if organization_slug:
        membership = _membership_or_404(request, organization_slug)
        if not can_create_project(membership):
            raise Http404
        return _project_create(request, membership)

    template = (
        _active_template_or_404(template_reference)
        if template_reference
        else None
    )
    memberships = Membership.objects.filter(
        user=request.user,
    ).select_related('organization')
    return render(
        request,
        'projects/organization_select.html',
        {
            'memberships': memberships,
            'template': template,
        },
    )


@login_required
def project_create(request, organization_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_create_project(membership):
        raise Http404
    return _project_create(request, membership)


def _project_create(request, membership):
    initial = {}
    template_reference = request.GET.get('template', '').strip()
    if template_reference and request.method == 'GET':
        initial['template'] = _active_template_or_404(template_reference)
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
                organization_slug=membership.organization.slug,
                project_slug=project.slug,
            )
    return render(
        request,
        'projects/form.html',
        {
            'form': form,
            'organization': membership.organization,
            'templates': form.fields['template'].queryset,
            'selected_template_id': str(form['template'].value() or ''),
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
            'has_starter_kit': has_starter_kit(project.template),
            'can_manage_project': can_manage_project(membership),
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
        updated_project = form.save(commit=False)
        if updated_project.template_id != project.template_id:
            updated_project.configuration = {}
        updated_project.save()
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
            'templates': form.fields['template'].queryset,
            'selected_template_id': str(form['template'].value() or ''),
            'project': project,
            'title': 'Project settings',
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def project_generate(request, organization_slug, project_slug):
    membership = _membership_or_404(request, organization_slug)
    if not can_manage_project(membership):
        raise Http404
    project = _project_or_404(membership, project_slug)
    if not project.template:
        raise Http404
    if not has_starter_kit(project.template):
        messages.error(
            request,
            'A starter kit is not available for this template version.',
        )
        return redirect(
            'projects:detail',
            organization_slug=organization_slug,
            project_slug=project.slug,
        )

    form = ProjectConfigurationForm(
        request.POST or None,
        template=project.template,
        initial=project.configuration,
    )
    if request.method == 'POST' and form.is_valid():
        archive = build_project_archive(
            template=project.template,
            project=project,
            configuration=form.configuration,
        )
        with transaction.atomic():
            project.configuration = form.configuration
            project.save(update_fields=('configuration', 'updated_at'))
        filename = slugify(project.name) or f'project-{project.pk}'
        response = HttpResponse(archive, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}.zip"'
        return response

    return render(
        request,
        'projects/generate.html',
        {
            'form': form,
            'organization': membership.organization,
            'project': project,
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

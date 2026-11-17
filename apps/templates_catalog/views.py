from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import TemplateSearchForm
from .models import ApplicationTemplate


@login_required
def template_list(request):
    form = TemplateSearchForm(request.GET or None)
    templates = ApplicationTemplate.objects.filter(is_active=True)
    if form.is_valid():
        query = form.cleaned_data['query'].strip()
        category = form.cleaned_data['category']
        if query:
            templates = templates.filter(
                Q(name__icontains=query)
                | Q(slug__icontains=query)
                | Q(description__icontains=query)
                | Q(technology_stack__icontains=query)
            )
        if category:
            templates = templates.filter(category=category)
    return render(
        request,
        'templates_catalog/list.html',
        {'form': form, 'templates': templates},
    )


@login_required
def template_detail(request, slug):
    template = get_object_or_404(
        ApplicationTemplate,
        slug=slug,
        is_active=True,
    )
    return render(
        request,
        'templates_catalog/detail.html',
        {'template': template},
    )


@login_required
def template_use(request, slug):
    template = get_object_or_404(
        ApplicationTemplate,
        slug=slug,
        is_active=True,
    )
    query = urlencode({'template': template.pk})
    return redirect(
        f"{reverse('projects:create_without_organization')}?{query}"
    )

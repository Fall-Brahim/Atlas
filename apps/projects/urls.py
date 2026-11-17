from django.urls import path

from . import views


app_name = 'projects'

urlpatterns = [
    path(
        'create/',
        views.project_create_without_organization,
        name='create_without_organization',
    ),
    path('<slug:organization_slug>/', views.project_list, name='list'),
    path('<slug:organization_slug>/create/', views.project_create, name='create'),
    path(
        '<slug:organization_slug>/<slug:project_slug>/',
        views.project_detail,
        name='detail',
    ),
    path(
        '<slug:organization_slug>/<slug:project_slug>/edit/',
        views.project_edit,
        name='edit',
    ),
    path(
        '<slug:organization_slug>/<slug:project_slug>/generate/',
        views.project_generate,
        name='generate',
    ),
    path(
        '<slug:organization_slug>/<slug:project_slug>/archive/',
        views.project_archive,
        name='archive',
    ),
    path(
        '<slug:organization_slug>/<slug:project_slug>/restore/',
        views.project_restore,
        name='restore',
    ),
]

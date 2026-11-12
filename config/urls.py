from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from apps.accounts.views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('organizations/', include('apps.organizations.urls')),
    path('projects/', include('apps.projects.urls')),
    path('templates/', include('apps.templates_catalog.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]

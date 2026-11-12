from django.urls import path

from . import views


app_name = 'templates_catalog'

urlpatterns = [
    path('', views.template_list, name='list'),
    path('<slug:slug>/', views.template_detail, name='detail'),
    path('<slug:slug>/use/', views.template_use, name='use'),
]

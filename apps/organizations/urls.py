from django.urls import path

from . import views


app_name = 'organizations'

urlpatterns = [
    path('', views.organization_list, name='list'),
    path('create/', views.organization_create, name='create'),
    path('<slug:slug>/', views.organization_detail, name='detail'),
    path('<slug:slug>/members/add/', views.membership_add, name='add'),
    path('<slug:slug>/settings/', views.organization_settings, name='settings'),
    path('<slug:slug>/delete/', views.organization_delete, name='delete'),
    path('<slug:slug>/members/<int:membership_id>/role/', views.membership_role, name='role'),
    path('<slug:slug>/members/<int:membership_id>/remove/', views.membership_remove, name='remove'),
    path('<slug:slug>/leave/', views.organization_leave, name='leave'),
]

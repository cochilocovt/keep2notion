"""
URL configuration for admin_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from sync_admin import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('sync-jobs/', views.sync_job_list, name='sync_job_list'),
    path('sync-jobs/<uuid:job_id>/', views.sync_job_detail, name='sync_job_detail'),
    path('sync-jobs/<uuid:job_id>/retry/', views.retry_sync_job, name='retry_sync_job'),
    path('sync-jobs/<uuid:job_id>/abort/', views.abort_sync_job, name='abort_sync_job'),
    path('sync/trigger/', views.manual_sync_trigger, name='manual_sync_trigger'),
    path('config/credentials/', views.credential_config, name='credential_config'),
    path('config/credentials/<str:user_id>/clear-sync-state/', views.clear_sync_state, name='clear_sync_state'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('api/upload/', views.upload_project, name='upload_project'),
    path('api/clear/', views.clear_database, name='clear_database'),
    path('api/tasks.geojson', views.tasks_geojson, name='tasks_geojson'),
    path('', views.dashboard, name='dashboard'),
]

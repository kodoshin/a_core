from django.urls import path
from . import views

urlpatterns = [
    path('documentation/<int:project_id>/', views.view_documentation, name='view_documentation'),
    path('documentation/sync/<int:project_id>/', views.sync_with_github, name='sync_with_github'),
    path('documentation/delete_github_sync/<int:project_id>/', views.delete_github_sync, name='delete_github_sync'),
    path('documentation/update/<int:project_id>/<str:git_repo_id>/<str:repo_name>/', views.view_modified_repo_files, name='view_modified_repo_files'),
    path('documentation/delete/<int:project_id>/', views.delete_project, name='delete_project'),
    #path('load_ai_doc/<int:project_id>/', views.load_ai_doc, name='load_ai_doc'),
    #path('documentation/<int:project_id>/', views.redirect_to_doc, name='documentation'),
]

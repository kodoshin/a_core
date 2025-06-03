from django.urls import path
from . import views

urlpatterns = [
    path('repos/', views.list_repos, name='list_repos'),
    path('repos/<str:git_repo_id>/<str:repo_name>/', views.view_repo_files, name='view_repo_files'),
    path('repos/<str:git_repo_id>/<str:repo_name>/process_selected_files/', views.process_selected_files, name='process_selected_files'),
    path('token-toturial/', views.token_tutorial, name='token_tutorial'),
    path('ajax/branches/<str:repo_name>/', views.get_repo_branches, name='get_repo_branches'),
]

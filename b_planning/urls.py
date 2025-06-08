from django.urls import path
from .views import planning_chat_view, update_default_project, update_planning_default_chatcategory, planning_chat_category_comparison_view

urlpatterns = [
    path('sana/', planning_chat_view, name='planning_view'),
    ##code_chat_updates
    path('sana/update_default_project/', update_default_project, name='planning_update_default_project'),
    path('sana/update_default_chatcategory/', update_planning_default_chatcategory, name="update_planning_default_chatcategory"),
    ##delete chat
    ##toggle importance
    path('sana/categories/comparison/', planning_chat_category_comparison_view, name="planning_chat_category_comparison"),
]
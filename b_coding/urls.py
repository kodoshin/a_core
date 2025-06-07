from django.urls import path
from .views import code_chat_view, update_default_project, update_default_chatcategory, delete_chat, get_processing_updates, toggle_chat_importance, chat_category_comparison_view

urlpatterns = [
    path('kenshi/', code_chat_view, name="code_chat_view"),
    path('ai/kenshi/updates/', get_processing_updates, name='code_chat_updates'), #To verify
    path('update_default_project/', update_default_project, name='update_default_project'),
    path('update_default_chatcategory/', update_default_chatcategory, name="update_default_chatcategory"),
    path('delete_chat/', delete_chat, name='delete_chat'),
    path('toggle_importance/', toggle_chat_importance, name='toggle_chat_importance'),
    path('kenshi/categories/comparison/', chat_category_comparison_view, name="chat_category_comparison"),
]
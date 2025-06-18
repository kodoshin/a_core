from django.urls import path
from .views import insights_chat_view, update_default_project, update_insights_default_chatcategory, insights_chat_category_comparison_view, insights_delete_chat

urlpatterns = [
    path('hiko/', insights_chat_view, name='insights_chat_view'),
    ##code_chat_updates
    path('hiko/update_default_project/', update_default_project, name='insights_update_default_project'),
    path('hiko/update_default_chatcategory/', update_insights_default_chatcategory, name="update_insights_default_chatcategory"),
    ##delete chat
    path('delete_chat/', insights_delete_chat, name='insights_delete_chat'),
    ##toggle importance
    path('hiko/categories/comparison/', insights_chat_category_comparison_view, name="insights_chat_category_comparison"),
]
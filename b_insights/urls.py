from django.urls import path
from .views import insights_chat_view, update_default_insights_project, update_insights_default_chatcategory, insights_chat_category_comparison_view, insights_delete_chat, insights_delete_group_messages

urlpatterns = [
    path('hiko/', insights_chat_view, name='insights_chat_view'),
    ##code_chat_updates
    path('hiko/update_default_project/', update_default_insights_project, name='insights_update_default_project'),
    path('hiko/update_default_chatcategory/', update_insights_default_chatcategory, name="update_insights_default_chatcategory"),
    ##delete chat
    path('hiko/delete_chat/', insights_delete_chat, name='insights_delete_chat'),
    path('insights_delete_group_messages/', insights_delete_group_messages, name='insights_delete_group_messages'),
    ##toggle importance
    path('hiko/categories/comparison/', insights_chat_category_comparison_view, name="insights_chat_category_comparison"),
]